"""GitHub adapter and isolated Discord delivery job. Never prints credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pilot.core import (activation_errors, config_hash, iso, label_names, notification_payload,
                        read_state, reconcile, render_state)


class APIError(RuntimeError):
    pass


class GitHub:
    def __init__(self, repo, token):
        self.repo = repo
        self.token = token

    def request(self, method, path, payload=None):
        req = urllib.request.Request('https://api.github.com' + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method, headers={'Authorization':f'Bearer {self.token}', 'Accept':'application/vnd.github+json',
                'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json','User-Agent':'proposal-routing-lab'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            raise APIError(f'GitHub {method}: HTTP {error.code}') from None
        except (OSError, ValueError):
            raise APIError(f'GitHub {method}: request failed') from None

    def paged(self, path):
        result = []
        page = 1
        while True:
            rows = self.request('GET', f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
            result.extend(rows)
            if len(rows) < 100:
                return result
            page += 1

    def base(self, suffix=''):
        return f'/repos/{self.repo}' + suffix

    def comments(self, number):
        return self.paged(self.base(f'/issues/{number}/comments'))

    def save_state(self, number, state, comment_id):
        body = render_state(state)
        if len(body.encode()) > 60000:
            raise APIError('State too large; manual archival is required')
        if comment_id:
            self.request('PATCH', self.base(f'/issues/comments/{comment_id}'), {'body':body})
        else:
            self.request('POST', self.base(f'/issues/{number}/comments'), {'body':body})


def fetch_activation(api, settings):
    number = settings.get('activation_issue')
    return api.comments(number) if type(number) is int and number > 0 else []


def sync_one(api, settings, issue, activation, active, now):
    comments = api.comments(issue['number'])
    old, comment_id = read_state(comments)
    # Scenario/inactive processing does not need issue events or network-side assignment.
    events = api.paged(api.base(f'/issues/{issue["number"]}/events')) if active == 'true' and 'pilot:scenario' not in label_names(issue) else []
    result = reconcile(settings, issue, comments, events, now, api.repo, activation, active, old)
    if result['ignored']:
        return old
    if result['assignee']:
        issue = api.request('PATCH', api.base(f'/issues/{issue["number"]}'), {'assignees':[result['assignee']]})
        # Explicit manual routing is executed in the same run, not via recursive bot events.
        result = reconcile(settings, issue, comments, events, now, api.repo, activation, active, result['state'])
    wanted = result['labels']
    if wanted is not None:
        before = set(label_names(issue))
        after = set(wanted)
        # Only touch managed labels; never replace the entire label set from a stale snapshot.
        for label in sorted(after-before):
            api.request('POST', api.base(f'/issues/{issue["number"]}/labels'), {'labels':[label]})
        for label in sorted(before-after):
            api.request('DELETE', api.base(f'/issues/{issue["number"]}/labels/{urllib.parse.quote(label, safe="")}'))
    if result['state'] != old:
        api.save_state(issue['number'], result['state'], comment_id)
    return result['state']


def active_issues(api):
    return [x for x in api.paged(api.base('/issues?state=all&labels=proposal')) if 'pull_request' not in x]


def run_reconcile(api, settings, active):
    activation = fetch_activation(api, settings)
    now = datetime.now(timezone.utc)
    count = 0
    for issue in active_issues(api):
        state = sync_one(api, settings, issue, activation, active, now)
        print(f'Issue #{issue["number"]}: {state.get("status", "ignored")}')
        count += 1
    print(f'Checked {count} proposals; active={active == "true"}')


def discord_post(url, payload):
    # A secret must target the Discord webhook endpoint; redirects must not forward it.
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'discord.com' or not parsed.path.startswith('/api/webhooks/'):
        raise APIError('Discord webhook configuration invalid')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    target = urllib.parse.urlunparse(parsed._replace(query='wait=true'))
    req = urllib.request.Request(target, data=json.dumps(payload).encode(), method='POST',
        headers={'Content-Type':'application/json','User-Agent':'proposal-routing-lab'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
            return json.loads(response.read())['id']
    except urllib.error.HTTPError as error:
        # No URL, response body or headers: webhook tokens must never enter logs.
        raise APIError(f'Discord response HTTP {error.code}; check delivery before retry') from None
    except (OSError, ValueError, KeyError):
        raise APIError('Discord delivery uncertain; check channel before retry') from None


def run_notify(api, settings, active, webhook):
    activation = fetch_activation(api, settings)
    gates = activation_errors(settings, activation, api.repo, active)
    if gates:
        print('Discord delivery disabled: activation gate is not satisfied')
        return
    failed = False
    for initial in active_issues(api):
        if 'pilot:scenario' in label_names(initial):
            continue
        # Re-read GitHub immediately before posting; scheduled work may have become obsolete.
        sync_one(api, settings, initial, activation, active, datetime.now(timezone.utc))
        issue = api.request('GET', api.base(f'/issues/{initial["number"]}'))
        state, comment_id = read_state(api.comments(issue['number']))
        if not state.get('valid_at') or state.get('scenario') or not state.get('delivery_allowed'):
            continue
        for event, delivery in state.get('deliveries', {}).items():
            if delivery['status'] != 'queued':
                continue
            if event in {'due','escalation'} and state.get('current_decision'):
                continue
            if event == 'decision' and not state.get('current_decision'):
                continue
            if not webhook:
                delivery.update(status='failed', error='Webhook secret missing', attempted_at=iso(datetime.now(timezone.utc)))
                api.save_state(issue['number'], state, comment_id)
                failed = True
                continue
            # Write intent first. A crash afterwards is reviewed, never blindly retried.
            delivery.update(status='sending', attempted_at=iso(datetime.now(timezone.utc)))
            api.save_state(issue['number'], state, comment_id)
            try:
                message = discord_post(webhook, notification_payload(api.repo, issue, state, event, settings))
                delivery.update(status='sent', message_id=message)
            except APIError as error:
                delivery.update(status='uncertain', error=str(error))
                failed = True
            api.save_state(issue['number'], state, comment_id)
            print(f'Issue #{issue["number"]} {event}: {delivery["status"]}')
    if failed:
        raise APIError('Notification job needs operator attention; GitHub decisions are preserved')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['reconcile','notify','check-config','summary'])
    parser.add_argument('--settings', default='config/pilot-settings.yml')
    args = parser.parse_args()
    settings = yaml.safe_load(Path(args.settings).read_text())
    repo = os.environ.get('GITHUB_REPOSITORY','UMC-PRODUCT/proposal-routing-lab')
    if args.mode == 'check-config':
        print('Config approval fingerprint:', config_hash(settings))
        for error in activation_errors(settings, [], repo, 'true'):
            print('-', error)
        return
    api = GitHub(repo, os.environ['GH_TOKEN'])
    active = os.environ.get('PILOT_ACTIVE', 'false')
    if args.mode == 'reconcile':
        run_reconcile(api, settings, active)
    elif args.mode == 'notify':
        run_notify(api, settings, active, os.environ.get('DISCORD_WEBHOOK', ''))
    else:
        rows = []
        for issue in active_issues(api):
            state, _ = read_state(api.comments(issue['number']))
            rows.append({k:state.get(k) for k in ('submitted_at','valid_at','decision_due_at','first_decision_at','scenario','status')} | {'issue':issue['number'],'url':issue['html_url']})
        print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (APIError, KeyError, ValueError, TypeError) as error:
        print(f'Pilot error: {type(error).__name__}: {error}', file=sys.stderr)
        raise SystemExit(1)
