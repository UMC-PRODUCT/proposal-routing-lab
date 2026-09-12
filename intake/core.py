"""Pure intake validation and reconciliation; no network calls or GitHub writes."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .registry import (add_business_days, coordinator_ids, effective_check_date,
                       iso, member, quiet, route_errors, route_version, stamp)

BOT_ID = 41898282
STATE_MARKER = '<!-- intake-v1-state\n'
KST = ZoneInfo('Asia/Seoul')
STATUS_LABELS = {'검토 중': 'intake:review', '수락·인계 대기': 'intake:handoff',
                 '보류': 'intake:parked', '처리 완료': 'intake:done'}
MANAGED_LABELS = set(STATUS_LABELS.values()) | {'intake:tracked', 'intake:exception'}
KINDS = {'검증 진행', '실행 진행', '보류', '종료'}
FIELDS = {'결정', '이유', '범위', '다음 행동', '실행 담당자', '재검토 담당자',
          '다음 확인일', '종료 분류', '실행 작업', '본인 수락'}


def _norm(value):
    return ' '.join(str(value or '').split())


def _digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(data.encode()).hexdigest()


def _at(comment):
    return stamp(comment['created_at'])


def _person_id(comment):
    user = comment.get('user', {})
    return user.get('id') if user.get('type', 'User') == 'User' else None


def _registered(cfg, user_id, when):
    person = member(cfg, user_id)
    if not person:
        return None
    since = person.get('registered_at')
    if since and when < stamp(since):
        return None
    return person


def _login(cfg, user_id):
    return next((m['login'] for m in cfg.get('members', []) if m.get('id') == user_id), None)


def _mention(cfg, value):
    if not re.fullmatch(r'@[A-Za-z0-9-]+', value or ''):
        return None
    matches = [m for m in cfg.get('members', [])
               if m.get('active') and m.get('login', '').lower() == value[1:].lower()]
    return matches[0]['id'] if len(matches) == 1 else None


def _task_url(value):
    try:
        url = urlparse(value or '')
        return bool(url.scheme == 'https' and url.netloc == 'github.com'
                    and not url.params and not url.query and not url.fragment
                    and re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(issues|pull)/[1-9][0-9]*', url.path))
    except ValueError:
        return False


def _lines(body):
    lines = (body or '').strip().splitlines()
    values = {}
    for line in lines[1:]:
        line = line.strip()
        line = re.sub(r'^[-*]\s+', '', line)
        if not line:
            continue
        if ':' not in line:
            raise ValueError('항목은 "이유: 내용" 형식으로 한 줄씩 작성하세요.')
        key, value = line.split(':', 1)
        key = key.strip()
        if key in values:
            raise ValueError(f'{key} 항목이 중복되었습니다.')
        values[key] = _norm(value)
    return (lines[0].strip() if lines else ''), values


def _sections(body):
    if len(body or '') > 30000:
        raise ValueError('제안 본문은 30,000자 이내로 작성하세요.')
    matches = list(re.finditer(r'^###\s+(.+?)\s*$', body or '', re.M))
    result = {}
    for index, match in enumerate(matches):
        key = match[1].strip()
        if key in result:
            raise ValueError(f'{key} 항목이 중복되었습니다.')
        end = matches[index+1].start() if index+1 < len(matches) else len(body)
        result[key] = (body[match.end():end]).strip()
    return result


def _form(issue, cfg):
    try:
        values = _sections(issue.get('body') or '')
    except ValueError as error:
        return None, [str(error)]
    errors = [f'{key} 항목을 작성하세요.' for key in ('대상', '문제', '원하는 도움')
              if _norm(values.get(key)).lower() in {'', '_no response_', '-', 'tbd'}]
    target = _norm(values.get('대상'))
    routes = [key for key, route in cfg.get('routes', {}).items()
              if any(target in {p.get('id'), p.get('label')} for p in route.get('products', []))]
    return (routes[0] if len(routes) == 1 else None), errors


def read_state(comments):
    """Trust the GitHub Actions bot identity, never a user's copied marker."""
    trusted = [c for c in comments if c.get('user', {}).get('id') == BOT_ID
               and c.get('user', {}).get('type') == 'Bot'
               and (c.get('body') or '').startswith(STATE_MARKER)]
    if len(trusted) > 1:
        raise ValueError('중복된 intake 봇 상태 댓글: 운영자 확인이 필요합니다.')
    if not trusted:
        return {}, None
    comment = trusted[0]
    try:
        encoded, _ = comment['body'][len(STATE_MARKER):].split('\n-->\n', 1)
        state = json.loads(encoded)
        if not isinstance(state, dict) or state.get('schema_version') != 1 or not isinstance(state.get('tracked'), bool):
            raise ValueError('상태 스키마 불일치')
        if state['tracked']:
            if not isinstance(state.get('submitted_at'), str):
                raise ValueError('접수 시각 누락')
            stamp(state['submitted_at'])
            if state.get('status') not in STATUS_LABELS:
                raise ValueError('상태 값 불일치')
        return state, comment['id']
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError('손상된 intake 봇 상태 댓글: 운영자 확인이 필요합니다.') from error


def _safe(value):
    return str(value).replace('<', '&lt;').replace('>', '&gt;').replace('`', '\\`')


def render_state(state):
    encoded = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(',', ':')).replace('<', '\\u003c')
    lines = [STATE_MARKER + encoded + '\n-->\n', '## 제안 처리 안내',
             f'**상태: {_safe(state.get("status", "검토 중"))}**', '',
             state.get('next_action', '담당자 연결을 기다려 주세요.'), '']
    login = state.get('decision_owner_login')
    if login:
        lines.append(f'결정 담당자: @{login}')
    elif state.get('coordinator_logins'):
        lines.append('연결 담당자: ' + ', '.join('@' + x for x in state['coordinator_logins']))
    for key, label in [('routing_due_at', '담당자 연결 기한'), ('first_response_due_at', '첫 응답 기한')]:
        if state.get(key):
            lines.append(f'{label}: {stamp(state[key]).astimezone(KST):%Y-%m-%d %H:%M} KST')
    if state.get('exceptions'):
        lines.extend(['', '**확인할 내용**', ''])
        lines.extend('- ' + _safe(x) for x in state['exceptions'])
    decision = state.get('current_decision')
    if state.get('status') == '수락·인계 대기' and decision:
        lines.extend(['', '실행 담당자는 연결할 작업을 확인한 후 아래 문안을 새 댓글로 남겨 주세요.',
                      '', '```text', f'/수락 {decision["version"]}',
                      '실행 작업: https://github.com/조직/저장소/issues/번호', '```', '',
                      '이 수락은 위 결정의 범위를 맡고 연결한 작업에서 진행을 추적하겠다는 확인입니다.'])
    elif state.get('status') == '검토 중' and login:
        lines.extend(['', '결정 담당자는 아래 문안을 새 댓글로 작성할 수 있습니다.', '', '```text',
                      '## 결정', '결정: 검증 진행 / 실행 진행 / 보류 / 종료 중 하나', '이유: 판단 이유',
                      '범위: 이번에 다룰 범위', '다음 행동: 구체적인 후속 행동',
                      '실행 담당자: @계정', '다음 확인일: YYYY-MM-DD', '```'])
    lines.extend(['', '처리 완료는 실행 작업으로의 인계 완료입니다. 개발 완료는 연결한 작업에서 확인합니다.',
                  '봇은 다른 저장소의 작업 내용·존재·접근 권한을 검증하지 않습니다.'])
    return '\n'.join(lines)


def _decision(comment, cfg, old_decision=None):
    heading, values = _lines(comment.get('body'))
    if heading != '## 결정':
        raise ValueError('결정 댓글 첫 줄은 "## 결정"이어야 합니다.')
    unknown = set(values) - FIELDS
    if unknown:
        raise ValueError('알 수 없는 결정 항목: ' + ', '.join(sorted(unknown)))
    if values.get('결정') not in KINDS or not values.get('이유'):
        raise ValueError('결정 종류와 이유가 필요합니다.')
    kind = values['결정']
    if kind != '종료':
        if not values.get('다음 행동') or not values.get('다음 확인일'):
            raise ValueError('다음 행동과 다음 확인일이 필요합니다.')
        try:
            date.fromisoformat(values['다음 확인일'])
        except ValueError as error:
            raise ValueError('다음 확인일은 YYYY-MM-DD 형식이어야 합니다.') from error
    executor = None
    owner_field = '재검토 담당자' if kind == '보류' else '실행 담당자'
    if kind != '종료':
        executor = _mention(cfg, values.get(owner_field) or values.get('실행 담당자'))
        # A previously validated immutable revision remains attributable after departure.
        if executor is None and old_decision and old_decision.get('fields') == values:
            executor = old_decision.get('executor_id')
        if not executor:
            raise ValueError(f'{owner_field}에 등록된 구성원 @계정을 지정하세요.')
    # Explicit inline acceptance/link are evidence, not part of the decision revision.
    semantic = {key: value for key, value in values.items() if key not in {'본인 수락', '실행 작업'}}
    version = f'D-{comment["id"]}-{_digest(semantic)[:16]}'
    return {'comment_id': comment['id'], 'author_id': _person_id(comment), 'version': version,
            'kind': kind, 'fields': values, 'executor_id': executor,
            'created_at': comment['created_at'], 'next_check_on': values.get('다음 확인일')}


def _role_at(cfg, route_id, role_comments, when):
    return not route_errors(cfg, route_id, role_comments, when)


def _coordinators(cfg, role_comments, now):
    result = coordinator_ids(cfg, role_comments, now)
    return sorted(result) if result else []


def _old_valid(decision, old_decision):
    return bool(old_decision and decision['version'] == old_decision.get('version')
                and decision['author_id'] == old_decision.get('author_id')
                and old_decision.get('authorized'))


def _acceptance(comment, decision, cfg, old_acceptance=None):
    heading, values = _lines(comment.get('body'))
    if heading != '/수락 ' + decision['version'] or set(values) != {'실행 작업'}:
        raise ValueError('수락은 결정 버전과 실행 작업 항목만 포함해야 합니다.')
    uid = _person_id(comment)
    fingerprint = _digest({'decision': decision['version'], 'url': values['실행 작업'], 'author_id': uid})
    if old_acceptance and old_acceptance.get('comment_id') == comment['id'] and old_acceptance.get('fingerprint') != fingerprint:
        raise ValueError('이미 확인한 수락 내용이 변경되었습니다. 새 댓글로 수락하세요.')
    previous = old_acceptance and old_acceptance.get('comment_id') == comment['id'] and old_acceptance.get('fingerprint') == fingerprint
    if uid != decision['executor_id'] or not (previous or _registered(cfg, uid, _at(comment))):
        raise ValueError('지정된 실행 담당자 본인의 수락이 필요합니다.')
    if _at(comment) < stamp(decision['created_at']):
        raise ValueError('결정 작성 이후의 수락이 필요합니다.')
    if _at(comment) < stamp(decision.get('revision_after', decision['created_at'])):
        raise ValueError('결정 내용 변경 이후 새 댓글로 수락하세요.')
    if not _task_url(values['실행 작업']):
        raise ValueError('실행 작업은 GitHub Issue 또는 PR의 https URL이어야 합니다.')
    return {'comment_id': comment['id'], 'author_id': uid, 'decision_version': decision['version'],
            'fingerprint': fingerprint, 'url': values['실행 작업'], 'created_at': comment['created_at']}


def _snapshot(route_id, route):
    return {'route_id': route_id, 'version': route_version(route), 'owner_id': route.get('owner_id'),
            'starts_at': route.get('starts_at'), 'ends_at': route.get('ends_at'),
            'acceptance_comment_id': route.get('acceptance_comment_id')}


def _result(state, issue, assignees):
    labels = {'intake:tracked', STATUS_LABELS[state['status']]}
    if state['exceptions']:
        labels.add('intake:exception')
    desired = 'closed' if state['status'] == '처리 완료' else 'open'
    return {'ignored': False, 'state': state, 'assignees': assignees,
            'labels': labels, 'issue_state': desired if issue.get('state', 'open') != desired else None}


def reconcile(cfg, issue, comments, events, role_comments, now, old=None):
    """Compute desired state from complete input; incomplete API reads must not call us."""
    old = copy.deepcopy(old or {})
    if isinstance(now, str):
        now = stamp(now)
    repo = cfg.get('repository', {})
    excluded = set(repo.get('excluded_issue_numbers', [])) | {repo.get('dashboard_issue'), repo.get('control_issue')}
    created = stamp(issue['created_at'])
    opened = repo.get('intake_opened_at')
    ignored = ('pull_request' in issue or issue['number'] in excluded)
    if not old.get('tracked'):
        ignored = ignored or not opened or created < stamp(opened) or not _registered(cfg, _person_id(issue), created)
    if ignored:
        return {'ignored': True, 'state': old, 'assignees': None, 'labels': None, 'issue_state': None}
    state = copy.deepcopy(old)
    state.update(schema_version=1, tracked=True, status='검토 중', exceptions=[], next_action='담당자 연결을 기다려 주세요.')
    state.setdefault('submitted_at', issue['created_at'])
    state.setdefault('tracked_at', iso(now))
    state.setdefault('cycle_started_at', issue['created_at'])
    state.setdefault('author_id', _person_id(issue))
    policy = cfg.get('policy', {})
    state.setdefault('routing_due_at', iso(add_business_days(cfg, created, policy.get('routing_business_days', 1))))
    state.setdefault('first_response_due_at', iso(add_business_days(cfg, created, policy.get('first_response_business_days', 3))))
    coordinators = _coordinators(cfg, role_comments, now)
    state['coordinator_ids'] = coordinators
    state['coordinator_logins'] = [login for uid in coordinators if (login := _login(cfg, uid))]

    # Reopening by a person begins another decision cycle; bot corrections do not.
    reopens = [event for event in events if event.get('event') == 'reopened'
               and event.get('actor', {}).get('id') != BOT_ID
               and event.get('actor', {}).get('type', 'User') == 'User'
               and stamp(event['created_at']) > stamp(state['cycle_started_at'])
               and event.get('id', 0) > state.get('last_human_reopen_id', 0)
               and (not old.get('completed_at') or stamp(event['created_at']) >= stamp(old['completed_at']))]
    if reopens and (old.get('completed_at') or old.get('status') == '처리 완료'):
        event = max(reopens, key=lambda e: (e['created_at'], e.get('id', 0)))
        state['cycle_started_at'] = event['created_at']
        state['last_human_reopen_id'] = event.get('id', 0)
        state['reopened_review'] = True
        for key in ('current_decision', 'seen_latest_decision', 'current_acceptance', 'seen_latest_acceptance', 'completed_at'):
            state.pop(key, None)
        old = copy.deepcopy(state)

    form_route, form_errors = _form(issue, cfg)
    route_id = state.get('route_id') or form_route
    # Explicit reroutes stick even when the request body is later edited.
    reroutes = sorted([c for c in comments if (c.get('body') or '').strip().startswith('/연결 ')
                       and c['id'] >= state.get('last_route_comment_id', 0)], key=lambda c: c['id'])
    for comment in reroutes:
        uid = _person_id(comment)
        changed_at = stamp(comment.get('updated_at', comment['created_at']))
        current_owner = cfg.get('routes', {}).get(route_id, {}).get('owner_id')
        authorized = (uid in _coordinators(cfg, role_comments, _at(comment))
                      and uid in _coordinators(cfg, role_comments, changed_at)) or (
            uid == current_owner and route_id and _role_at(cfg, route_id, role_comments, _at(comment))
            and _role_at(cfg, route_id, role_comments, changed_at))
        if not authorized or not _registered(cfg, uid, _at(comment)):
            continue
        try:
            heading, fields = _lines(comment.get('body'))
            target = heading.removeprefix('/연결 ').strip()
            if not fields.get('사유') or target not in cfg.get('routes', {}):
                raise ValueError('재연결에는 유효한 책임 ID와 사유가 필요합니다.')
            command_hash = _digest({'target': target, 'reason': fields['사유']})
            if comment['id'] == state.get('last_route_comment_id') and command_hash == state.get('last_route_fingerprint'):
                continue
            if not _role_at(cfg, target, role_comments, now):
                raise ValueError('대상 책임의 등록·역할 수락·임기가 유효하지 않습니다.')
        except ValueError as error:
            state['exceptions'].append(str(error))
            continue
        state['last_route_comment_id'] = comment['id']
        state['last_route_fingerprint'] = command_hash
        if target != route_id:
            route_id = target
            state['cycle_started_at'] = comment['created_at']
            for key in ('current_decision', 'seen_latest_decision', 'current_acceptance', 'seen_latest_acceptance', 'completed_at'):
                state.pop(key, None)
            old = copy.deepcopy(state)

    state['route_id'] = route_id
    route = cfg.get('routes', {}).get(route_id, {})
    state['decision_owner_id'] = route.get('owner_id')
    state['decision_owner_login'] = _login(cfg, route.get('owner_id'))
    errors = route_errors(cfg, route_id, role_comments, now) if route else ['담당자 연결이 필요합니다.']
    ready = bool(route) and not errors
    if route:
        state['route_version'] = route_version(route)
        previous = old.get('appointment')
        owner_changed = previous and previous.get('owner_id') != route.get('owner_id')
        if owner_changed and not old.get('completed_at'):
            expected = f'/인계수락 {route_id} {route_version(route)}'
            handoff = next((c for c in role_comments if c['id'] == route.get('handoff_comment_id')
                            and _person_id(c) == route.get('owner_id')
                            and (c.get('body') or '').strip().split('\n', 1)[0] == expected
                            and _registered(cfg, _person_id(c), _at(c))
                            and _at(c) <= now
                            and stamp(c.get('updated_at', c['created_at'])) <= now
                            and _role_at(cfg, route_id, role_comments, _at(c))
                            and _role_at(cfg, route_id, role_comments, stamp(c.get('updated_at', c['created_at'])))), None)
            if not handoff:
                ready = False
                errors.append('후임 담당자의 미결 요청 인계 수락이 필요합니다.')
        if ready:
            state['appointment'] = _snapshot(route_id, route)
            assigned = [event for event in events if event.get('event') == 'assigned'
                        and event.get('assignee', {}).get('id') == route.get('owner_id')
                        and stamp(event['created_at']) >= created]
            if assigned:
                state.setdefault('first_assigned_at', min(event['created_at'] for event in assigned))
    assignees = [state['decision_owner_login']] if ready and state.get('decision_owner_login') else []
    if ready:
        state['next_action'] = f'결정 담당자 @{state["decision_owner_login"]}가 제안을 검토하고 결정을 기록해 주세요.'

    old_decision = old.get('current_decision')
    cycle = stamp(state['cycle_started_at'])
    current = None
    min_decision_id = state.get('seen_latest_decision', 0)
    candidates = []
    for comment in comments:
        if (comment.get('body') or '').strip().split('\n', 1)[0].strip() != '## 결정' or _at(comment) < cycle:
            continue
        uid = _person_id(comment)
        retained = old_decision and comment['id'] == old_decision.get('comment_id') and uid == old_decision.get('author_id')
        authorized = (uid == route.get('owner_id') and route and _role_at(cfg, route_id, role_comments, _at(comment)))
        cleanup = uid in _coordinators(cfg, role_comments, _at(comment))
        if cleanup and not authorized and not retained:
            try:
                _, cleanup_fields = _lines(comment.get('body'))
                cleanup = cleanup_fields.get('결정') == '종료' and cleanup_fields.get('종료 분류') in {'범위 밖', '중복'}
            except ValueError:
                cleanup = False
        if retained or ((_registered(cfg, uid, _at(comment))) and (authorized or cleanup)):
            candidates.append((comment, bool(authorized), bool(cleanup)))
    candidates.sort(key=lambda x: x[0]['id'])
    eligible = [entry for entry in candidates if entry[0]['id'] >= min_decision_id]
    if eligible:
        comment, authorized, cleanup = eligible[-1]
        state['seen_latest_decision'] = comment['id']
        try:
            current = _decision(comment, cfg, old_decision)
            cleanup = cleanup and current['kind'] == '종료' and current['fields'].get('종료 분류') in {'범위 밖', '중복'}
            retained = _old_valid(current, old_decision)
            # A changed/new revision must be authorized now as well as when posted.
            if not retained and not (cleanup or (authorized and ready)):
                raise ValueError('현재 책임자의 유효한 결정이 필요합니다.')
            revised_at = stamp(comment.get('updated_at', comment['created_at']))
            if not retained and not cleanup and not _role_at(cfg, route_id, role_comments, revised_at):
                raise ValueError('결정 작성·변경 시점에 유효한 역할 수락이 필요합니다.')
            if not retained and comment.get('updated_at') and route.get('ends_at') and stamp(comment['updated_at']) >= stamp(route['ends_at']) and not cleanup:
                raise ValueError('임기 종료 이후 변경된 결정은 현 담당자의 재확인이 필요합니다.')
            current['authorized'] = True
            current['registry_version'] = old_decision.get('registry_version') if retained else (route_version(route) if route else None)
            current['verified_at'] = old_decision.get('verified_at') if retained else iso(now)
            current['revision_after'] = old_decision.get('revision_after', current['created_at']) if retained else iso(revised_at)
        except ValueError as error:
            state['exceptions'].append(str(error))
            current = None
    elif min_decision_id:
        state['exceptions'].append('관측했던 최신 결정이 삭제되거나 형식이 변경되었습니다. 새 결정이 필요합니다.')
    state['current_decision'] = current
    state['current_acceptance'] = None
    state['check_owner_id'] = None
    state['execution_owner_id'] = None
    state.pop('next_check_on', None)
    state.pop('effective_check_on', None)

    if not state.get('first_response_at') and route.get('owner_id'):
        replies = [c for c in comments if _person_id(c) == route['owner_id'] and _at(c) >= created
                   and _registered(cfg, _person_id(c), _at(c))
                   and _role_at(cfg, route_id, role_comments, _at(c))]
        if replies:
            state['first_response_at'] = min(replies, key=lambda c: c['created_at'])['created_at']

    if current:
        state.pop('reopened_review', None)
        kind = current['kind']
        state['next_check_on'] = current.get('next_check_on')
        if kind == '종료':
            state['status'] = '처리 완료'
            state['next_action'] = '종료 이유가 기록되었습니다. 새로운 검토가 필요하면 이 Issue를 다시 열어 주세요.'
        elif kind == '보류':
            state['status'] = '보류'
            state['check_owner_id'] = current['executor_id']
            reviewer = _login(cfg, current['executor_id'])
            state['next_action'] = f'재검토 담당자 @{reviewer}는 {current["next_check_on"]}에 다음 행동을 확인해 주세요.'
        else:
            state['status'] = '수락·인계 대기'
            state['execution_owner_id'] = current['executor_id']
            executor = _login(cfg, current['executor_id'])
            state['next_action'] = f'실행 담당자 @{executor}가 결정 범위를 수락하고 실행 작업 링크를 남겨 주세요.'
            old_acceptance = old.get('current_acceptance')
            if old_decision and old_decision.get('comment_id') == current['comment_id'] and old_decision.get('version') != current['version'] and old_acceptance:
                state['inline_blocked_comment_id'] = current['comment_id']
            threshold = state.get('seen_latest_acceptance', {})
            minimum = threshold.get('comment_id', 0) if threshold.get('decision_version') == current['version'] else 0
            acceptance = None
            inline = (current['fields'].get('본인 수락') == '예' and current['author_id'] == current['executor_id']
                      and state.get('inline_blocked_comment_id') != current['comment_id'])
            if inline and _task_url(current['fields'].get('실행 작업')):
                acceptance = {'comment_id': current['comment_id'], 'author_id': current['author_id'],
                              'decision_version': current['version'], 'url': current['fields']['실행 작업'],
                              'fingerprint': _digest({'inline': current['version'], 'url': current['fields']['실행 작업']}),
                              'created_at': current['created_at'], 'inline': True}
            matching = [c for c in comments if (c.get('body') or '').strip().split('\n', 1)[0].strip() == '/수락 ' + current['version']
                        and _person_id(c) == current['executor_id'] and c['id'] >= minimum]
            if matching:
                comment = max(matching, key=lambda c: c['id'])
                state['seen_latest_acceptance'] = {'decision_version': current['version'], 'comment_id': comment['id']}
                try:
                    if comment['id'] <= state.get('invalidated_acceptance_id', 0):
                        raise ValueError('변경되었던 수락은 복원해도 재사용하지 않습니다. 새 댓글로 수락하세요.')
                    acceptance = _acceptance(comment, current, cfg, old_acceptance)
                except ValueError as error:
                    state['exceptions'].append(str(error))
                    if old_acceptance and old_acceptance.get('comment_id') == comment['id']:
                        state['invalidated_acceptance_id'] = comment['id']
                    acceptance = None
            elif minimum:
                state['exceptions'].append('관측했던 최신 수락이 삭제되거나 변경되었습니다. 새 수락이 필요합니다.')
                state['invalidated_acceptance_id'] = max(minimum, state.get('invalidated_acceptance_id', 0))
                acceptance = None
            if acceptance:
                state['current_acceptance'] = acceptance
                state['status'] = '처리 완료'
                state['next_action'] = '실행 담당자가 작업 인계를 수락했습니다. 진행 상황은 연결한 작업에서 확인해 주세요.'

    historical_done = (state['status'] == '처리 완료' and old.get('completed_at') and current
                       and _old_valid(current, old_decision))
    cleanup_done = current and current['kind'] == '종료' and current['fields'].get('종료 분류') in {'범위 밖', '중복'}
    if not historical_done and not cleanup_done:
        state['exceptions'].extend(errors)
        state['exceptions'].extend(form_errors)
        if not ready or form_errors:
            state['status'] = '검토 중'
            state['next_action'] = '제안 내용을 보완하거나 연결 담당자의 담당자 확인을 기다려 주세요.'
    if historical_done:
        # Historical records retain their verified decision owner despite current roster changes.
        owner_id = current['author_id']
        state['decision_owner_id'] = owner_id
        state['decision_owner_login'] = _login(cfg, owner_id) or old.get('decision_owner_login')
        if old.get('appointment'):
            state['appointment'] = old['appointment']
        assignees = [state['decision_owner_login']] if ready and owner_id == route.get('owner_id') else None
    if route and not historical_done:
        if not ready and old.get('appointment'):
            state['exceptions'].append('담당자의 임기·등록 상태를 확인하고 미결 요청을 인계하세요.')
        if route.get('review_on') and now.astimezone(KST).date() >= date.fromisoformat(str(route['review_on'])) and not quiet(cfg, now):
            state['exceptions'].append('Acting 임기 재검토일이 도래했습니다.')
    if state['status'] == '처리 완료':
        state.setdefault('completed_at', iso(now))
    else:
        state.pop('completed_at', None)
        if not quiet(cfg, now):
            if not ready and now > stamp(state['routing_due_at']):
                state['exceptions'].append('담당자 연결 기한이 지났습니다.')
            if ready and not state.get('first_response_at') and now > stamp(state['first_response_due_at']):
                state['exceptions'].append('담당자의 첫 응답 기한이 지났습니다.')
            if current and current.get('next_check_on'):
                effective = effective_check_date(cfg, date.fromisoformat(current['next_check_on']))
                state['effective_check_on'] = effective.isoformat()
                if now.astimezone(KST).date() >= effective:
                    state['exceptions'].append('다음 확인일이 도래했습니다.')
    if issue.get('state') == 'closed' and state['status'] != '처리 완료':
        state['exceptions'].append('완료 근거가 부족한 종료를 다시 엽니다.')
    if state.get('reopened_review'):
        state['exceptions'].append('다시 열린 제안의 새 검토가 필요합니다.')
    state['exceptions'] = list(dict.fromkeys(state['exceptions']))
    return _result(state, issue, assignees)
