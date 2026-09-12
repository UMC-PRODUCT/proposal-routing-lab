"""Reconcile GitHub records without a database or a second transport."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from pilot.runner import APIError, GitHub
from intake import core, registry

REPORT_MARKER = '<!-- intake-v1-dashboard -->'
DIGEST_MARKER = '<!-- intake-v1-digest:'


def fingerprint(issue, comments, events, role_comments):
    """Detect intervening edits before performing writes from a read snapshot."""
    payload = [issue, comments, events, role_comments]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def identity_snapshot(api, cfg):
    result = copy.deepcopy(cfg)
    for person in result.get('members', []):
        if not person.get('active', True):
            continue
        actual = api.request('GET', f'/user/{person["id"]}')
        if actual.get('id') != person['id'] or actual.get('type') != 'User':
            raise APIError('Registered account identity could not be verified')
        person['login'] = actual['login']
    return result


def read_issue(api, number):
    issue = api.request('GET', api.base(f'/issues/{number}'))
    comments = api.comments(number)
    events = api.paged(api.base(f'/issues/{number}/events'))
    return issue, comments, events


def read_roles(api, cfg):
    number = cfg['repository'].get('control_issue')
    return api.comments(number) if isinstance(number, int) else []


def save_state(api, number, state, comment_id):
    body = core.render_state(state)
    if len(body.encode()) > 60000:
        raise APIError('State exceeds safe comment size')
    if comment_id:
        api.request('PATCH', api.base(f'/issues/comments/{comment_id}'), {'body': body})
        return
    # A prior POST may have succeeded even if its response was lost.
    current, found = core.read_state(api.comments(number))
    if found:
        if current != state:
            api.request('PATCH', api.base(f'/issues/comments/{found}'), {'body': body})
    else:
        api.request('POST', api.base(f'/issues/{number}/comments'), {'body': body})


def sync_one(api, cfg, number, mode, now, registry_ref):
    issue, comments, events = read_issue(api, number)
    roles = read_roles(api, cfg)
    old, comment_id = core.read_state(comments)
    if mode == 'drain' and not old.get('tracked'):
        return {'number': number, 'ignored': True, 'reason': 'new_intake_paused'}
    outcome = core.reconcile(cfg, issue, comments, events, roles, now, old)
    if outcome['ignored']:
        return {'number': number, 'ignored': True}
    state = outcome['state']
    state['registry_ref'] = registry_ref
    if mode == 'observe':
        return {'number': number, 'ignored': False, 'state': state}
    gates = registry.activation_errors(cfg, roles, now, require_ready_route=mode != 'drain')
    if gates:
        raise APIError('Activation evidence changed; writes stopped')
    latest_issue, latest_comments, latest_events = read_issue(api, number)
    latest_roles = read_roles(api, cfg)
    if fingerprint(issue, comments, events, roles) != fingerprint(latest_issue, latest_comments, latest_events, latest_roles):
        raise APIError('Records changed during inspection; retry on the next scan')
    # Write the evidence snapshot BEFORE close. A lost response is recoverable.
    existing = next((c.get('body') for c in comments if c['id'] == comment_id), None)
    if existing != core.render_state(state):
        save_state(api, number, state, comment_id)
    wanted_assignees = outcome.get('assignees')
    if wanted_assignees is not None:
        actual = sorted(p['login'] for p in issue.get('assignees', []))
        if actual != sorted(wanted_assignees):
            api.request('PATCH', api.base(f'/issues/{number}'), {'assignees': wanted_assignees})
    wanted = outcome.get('labels')
    if wanted is not None:
        before = {label['name'] if isinstance(label, dict) else label for label in issue.get('labels', [])}
        managed = core.MANAGED_LABELS
        for label in sorted(set(wanted) - before):
            api.request('POST', api.base(f'/issues/{number}/labels'), {'labels': [label]})
        for label in sorted((before & managed) - set(wanted)):
            api.request('DELETE', api.base(f'/issues/{number}/labels/{quote(label, safe="")}'))
    target_state = outcome.get('issue_state')
    if target_state and target_state != issue.get('state'):
        # Comments can change while labels/assignees are being written. Re-evaluate
        # the final state change from fresh evidence, including our own snapshot.
        fresh_issue, fresh_comments, fresh_events = read_issue(api, number)
        fresh_roles = read_roles(api, cfg)
        if registry.activation_errors(cfg, fresh_roles, now, require_ready_route=mode != 'drain'):
            raise APIError('Activation evidence changed before state transition')
        fresh_old, fresh_comment_id = core.read_state(fresh_comments)
        fresh = core.reconcile(cfg, fresh_issue, fresh_comments, fresh_events, fresh_roles, now, fresh_old)
        if fresh['ignored']:
            raise APIError('Evidence changed before state transition')
        fresh['state']['registry_ref'] = registry_ref
        if fresh['state'] != state:
            save_state(api, number, fresh['state'], fresh_comment_id)
        if fresh.get('issue_state') != target_state:
            raise APIError('Evidence changed before state transition; next scan will repair')
        state = fresh['state']
        api.request('PATCH', api.base(f'/issues/{number}'), {'state': target_state})
    return {'number': number, 'ignored': False, 'state': state}


def due_digest(cfg, now):
    local = now.astimezone(registry.KST)
    return (registry.business_day(cfg, local.date())
            and not registry.quiet(cfg, now)
            and (local.hour, local.minute) >= (9, 17))


def dashboard_body(report, previous_body=''):
    # Preserve the last fully successful scan rather than displaying a false zero.
    last_success = report.get('last_success')
    if not last_success:
        for line in previous_body.splitlines():
            if line.startswith('마지막 전체 성공: '):
                last_success = line.removeprefix('마지막 전체 성공: ')
                break
    lines = [REPORT_MARKER, '# 제안 운영 현황', '',
             f'검사 시각: {report["checked_at"]}',
             f'마지막 전체 성공: {last_success or "아직 없음"}',
             f'조회 결과: {"전체 성공" if report["complete"] else "일부 또는 전체 실패 — 전체 0건으로 해석하지 마세요"}',
             f'조회 Issue: {report["total"]} · 검사 성공: {len(report["results"])} · 실패: {len(report["errors"])}', '',
             '| 요청 | 현재 상태 | 확인할 내용 |', '|---|---|---|']
    for row in report['results']:
        if row.get('ignored'):
            continue
        state = row['state']
        status = str(state.get('status', '확인 필요')).replace('|', '/')
        notes = ', '.join(state.get('exceptions', [])) or '기록 정상'
        lines.append(f'| #{row["number"]} | {status} | {notes.replace("|", "/")} |')
    for error in report['errors']:
        lines.append(f'| {"#" + str(error["number"]) if error.get("number") else "전체 조회"} | 확인 필요 | {error["kind"]} |')
    if not report['complete'] and previous_body:
        # Carry forward unseen rows without recursively copying past dashboards.
        seen = {r['number'] for r in report['results']}
        previous_rows = []
        for line in previous_body.splitlines():
            if line.startswith('| #'):
                try:
                    number = int(line.split('|')[1].strip().lstrip('#'))
                except ValueError:
                    continue
                if number not in seen:
                    previous_rows.append(line)
                    seen.add(number)
        if previous_rows:
            lines.extend(['', '## 이전 검사 기록 — 이번 검사에서 확인하지 못함', '',
                          '| 요청 | 이전 상태 | 당시 확인할 내용 |', '|---|---|---|', *previous_rows])
    if report.get('role_reviews'):
        lines.extend(['', '## 역할 재검토', ''])
        lines.extend(f'- {name}: 재검토일 도래' for name in report['role_reviews'])
    lines.extend(['', '이 목록은 등록된 제안의 처리 현황입니다. 기능 개발 완료나 실제 작업시간을 나타내지 않습니다.'])
    body = '\n'.join(lines) + '\n'
    if len(body.encode()) > 60000:
        raise APIError('Dashboard exceeds safe body size; no partial table published')
    return body


def publish_dashboard(api, cfg, report, roles, now):
    number = cfg['repository']['dashboard_issue']
    issue = api.request('GET', api.base(f'/issues/{number}'))
    old = issue.get('body') or ''
    if not old.startswith(REPORT_MARKER):
        raise APIError('Dashboard lacks its dedicated management marker')
    body = dashboard_body(report, old)
    if body != old:
        api.request('PATCH', api.base(f'/issues/{number}'), {'body': body})
    if not report['complete'] or not due_digest(cfg, now):
        return
    pending = [row for row in report['results'] if not row.get('ignored') and row['state'].get('exceptions')]
    if not pending and not report['role_reviews']:
        return
    day = now.astimezone(registry.KST).date().isoformat()
    marker = f'{DIGEST_MARKER}{day} -->'
    # Idempotency uses an authored marker, never a user's copied comment.
    comments = api.comments(number)
    if any(c.get('user', {}).get('id') == 41898282 and c.get('user', {}).get('type') == 'Bot'
           and c.get('body', '').startswith(marker) for c in comments):
        return
    ids = registry.coordinator_ids(cfg, roles, now)
    recipients = {registry.member(cfg, uid)['login'] for uid in ids if registry.member(cfg, uid)}
    for row in pending:
        for key in ('decision_owner_id', 'check_owner_id', 'execution_owner_id'):
            person = registry.member(cfg, row['state'].get(key))
            if person:
                recipients.add(person['login'])
    text = marker + '\n' + ' '.join('@' + login for login in sorted(recipients))
    text += '\n오늘 확인할 요청: ' + (', '.join('#' + str(r['number']) for r in pending) or '역할 재검토')
    text += '\n위 운영 현황에서 다음 행동과 역할 재검토 항목을 확인해주세요.'
    api.request('POST', api.base(f'/issues/{number}/comments'), {'body': text})


def run(api, cfg, mode='observe', now=None, event=None, registry_ref='local'):
    now = now or datetime.now(timezone.utc)
    mode = mode if mode in {'observe', 'active', 'drain'} else 'observe'
    report = {'checked_at': registry.iso(now), 'mode': mode, 'complete': False,
              'total': 0, 'results': [], 'errors': [], 'role_reviews': [], 'activation_errors': []}
    target, roles, dashboard_attempted, common_ready = None, [], False, False
    try:
        cfg = identity_snapshot(api, cfg)
        roles = read_roles(api, cfg)
        report['activation_errors'] = registry.activation_errors(cfg, roles, now)
        common_ready = not registry.activation_errors(cfg, roles, now, require_ready_route=False)
        if not common_ready:
            mode = 'observe'
            report['mode'] = mode
        elif mode == 'active' and report['activation_errors']:
            mode = 'drain'
            report['mode'] = mode
        if event and 'issue' in event:
            sender = event.get('sender', {})
            if not registry.member(cfg, sender.get('id')):
                report.update(skipped='external_event', complete=True)
                return report
            if event['issue'].get('pull_request'):
                report.update(skipped='pull_request_event', complete=True)
                return report
            target = event['issue']['number']
            if target == cfg['repository'].get('control_issue'):
                target = None
        if target:
            numbers = [target]
        else:
            issues = api.paged(api.base('/issues?state=all'))
            numbers = sorted(i['number'] for i in issues if 'pull_request' not in i)
        report['total'] = len(numbers)
        excluded = set(cfg['repository'].get('excluded_issue_numbers', []))
        excluded.update(x for x in (cfg['repository'].get('control_issue'), cfg['repository'].get('dashboard_issue')) if x)
        for number in numbers:
            if number in excluded:
                report['results'].append({'number': number, 'ignored': True})
                continue
            try:
                report['results'].append(sync_one(api, cfg, number, mode, now, registry_ref))
            except Exception as error:
                # Continue without exposing API response bodies or raw input.
                report['errors'].append({'number': number, 'kind': type(error).__name__})
        today = now.astimezone(registry.KST).date()
        for route in cfg['routes'].values():
            review = route.get('review_on')
            if route.get('enabled') and review and today >= registry.effective_check_date(cfg, datetime.fromisoformat(review).date()):
                report['role_reviews'].append(route['name'])
        report['complete'] = not report['errors']
        report['full_scan'] = target is None
        if report['complete'] and target is None:
            report['last_success'] = registry.iso(now)
        if mode != 'observe' and target is None:
            dashboard_attempted = True
            publish_dashboard(api, cfg, report, roles, now)
    except Exception as error:
        report['errors'].append({'number': None, 'kind': type(error).__name__})
        report['complete'] = False
        if common_ready and mode != 'observe' and target is None and not dashboard_attempted:
            try:
                publish_dashboard(api, cfg, report, roles, now)
            except Exception as dashboard_error:
                report['errors'].append({'number': cfg['repository'].get('dashboard_issue'),
                                         'kind': type(dashboard_error).__name__})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['reconcile', 'check-config', 'authorize'])
    parser.add_argument('--registry', default='registry/ownership.yml')
    args = parser.parse_args()
    cfg = registry.load_registry(args.registry)
    errors = registry.validate_registry(cfg)
    if errors:
        print(json.dumps({'configuration_errors': errors}, ensure_ascii=False))
        return 1
    if args.command == 'check-config':
        print('Registry schema valid. This does not certify activation or live permissions.')
        return 0
    if args.command == 'authorize':
        path = os.environ.get('GITHUB_EVENT_PATH')
        event = json.loads(Path(path).read_text()) if path else {}
        allowed = ('issue' not in event or (
            not event['issue'].get('pull_request')
            and registry.member(cfg, event.get('sender', {}).get('id')) is not None))
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as stream:
                stream.write(f'allowed={str(allowed).lower()}\n')
        print('Allowed event' if allowed else 'External or pull-request event excluded')
        return 0
    expected = cfg['repository']['full_name']
    if os.environ.get('GITHUB_REPOSITORY', expected) != expected:
        print('Repository mismatch; no writes performed')
        return 1
    api = GitHub(expected, os.environ['GH_TOKEN'])
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    event = json.loads(Path(event_path).read_text()) if event_path else None
    report = run(api, cfg, os.environ.get('INTAKE_MODE', 'observe'), event=event,
                 registry_ref=os.environ.get('REGISTRY_REF', 'local'))
    # Reports intentionally exclude raw comments, issue bodies and tokens.
    sanitized = {k: v for k, v in report.items() if k != 'results'}
    sanitized['inspected'] = [{'number': r['number'], 'ignored': r.get('ignored'),
                               'status': r.get('state', {}).get('status')} for r in report['results']]
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        Path(summary).write_text('```json\n' + json.dumps(sanitized, ensure_ascii=False, indent=2) + '\n```\n')
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
