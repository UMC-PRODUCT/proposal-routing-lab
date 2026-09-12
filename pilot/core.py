"""Pure validation/state transitions. Network access lives in runner.py."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')
BOT_ID = 41898282
STATE_MARKER = '<!-- proposal-pilot-state:v1\n'
PRODUCT_FIELDS = ('Purpose Team', '사용자 문제', 'Mission 연결', '근거', '가장 작은 검증', '성공·중단 조건', '필요한 협업', 'DRI 의향')
DESIGN_FIELDS = ('플랫폼 범위', '관련 Purpose·사용자 문제', 'Figma Node Link 또는 미존재 사유', '공통 행동·상태', '플랫폼별 표현·이유', 'Component·Token·Migration 영향', '성공·중단 조건', 'DRI 의향')
KINDS = {'proposal:product': PRODUCT_FIELDS, 'proposal:design-system': DESIGN_FIELDS}
DECISIONS = {'Validating', 'Active', 'Parked', 'Rejected'}
DECISION_FIELDS = ('Decision', 'Reason', 'Proposal DRI', 'Acceptance', 'Next action', 'Reconsideration condition/date')
MANAGED = {'needs:information', 'needs:routing', 'needs:decision-record', 'needs:owner-acceptance', 'decision:pending'}


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone is required')
    return result


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def business_day(day, settings):
    return day.weekday() < 5 and day.isoformat() not in settings['non_working_dates']


def add_business_days(day, count, settings):
    while count:
        day += timedelta(days=1)
        if business_day(day, settings):
            count -= 1
    return day


def deadline(valid_at, settings):
    day = add_business_days(stamp(valid_at).astimezone(KST).date(), settings['decision_sla_business_days'], settings)
    return iso(datetime.combine(day, time(23, 59), KST))


def config_hash(settings):
    operational = {k: v for k, v in settings.items() if k not in {'activation_approval', 'role_acceptances'}}
    return hashlib.sha256(json.dumps(operational, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def role_holders(settings):
    result = {'pilot_owner': settings.get('pilot_owner')}
    for route in settings.get('enabled_routes', []):
        for role in ('primary', 'backup'):
            result[f'{route}.{role}'] = settings.get('routing_map', {}).get(route, {}).get(role)
    return result


def login_ok(value):
    return isinstance(value, str) and value.lower() not in {'tbd', 'none', 'null'} and bool(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', value))


def has_line(comment, line):
    return line in [x.strip() for x in comment.get('body', '').splitlines()]


def activation_errors(settings, comments, repo, active):
    if active != 'true':
        return ['PILOT_ACTIVE=false: 실제 접수·지정·알림 비활성']
    errors = []
    try:
        if settings.get('timezone') != 'Asia/Seoul':
            errors.append('timezone은 Asia/Seoul이어야 합니다.')
        participants = settings['participants']
        if not isinstance(participants, list) or not participants or not all(login_ok(x) for x in participants):
            errors.append('participants를 확정하세요.')
        if isinstance(participants, list) and all(isinstance(x, str) for x in participants) and len({x.lower() for x in participants}) != len(participants):
            errors.append('participants가 중복됩니다.')
        if not settings.get('enabled_routes'):
            errors.append('enabled_routes를 확정하세요.')
        for role, holder in role_holders(settings).items():
            if not login_ok(holder) or holder not in participants:
                errors.append(f'{role}의 참가자·담당자를 확정하세요.')
                continue
            ref = settings.get('role_acceptances', {}).get(role)
            matching = [c for c in comments if c['id'] == ref and c['user']['login'] == holder and has_line(c, f'/pilot-accept {role}')]
            if not matching:
                errors.append(f'{role} 본인의 역할 수락이 없습니다.')
        for route in settings.get('enabled_routes', []):
            row = settings['routing_map'][route]
            if row['primary'] == row['backup']:
                errors.append(f'{route}의 Primary와 Backup은 달라야 합니다.')
        if type(settings.get('decision_sla_business_days')) is not int or not 1 <= settings['decision_sla_business_days'] <= 10:
            errors.append('SLA는 1~10영업일로 지정하세요.')
        if type(settings.get('weekly_ops_budget_minutes')) is not int or settings['weekly_ops_budget_minutes'] <= 0:
            errors.append('주간 운영 허용시간을 확정하세요.')
        for day in settings['non_working_dates']:
            date.fromisoformat(day)
        start = date.fromisoformat(settings['activation_date'])
        close = stamp(settings['intake_close_at']).astimezone(KST)
        if not business_day(start, settings) or close.date() != add_business_days(start, 9, settings) or close.time().replace(tzinfo=None) != time(23, 59):
            errors.append('접수 마감은 활성화일부터 10영업일째 23:59 KST여야 합니다.')
        if type(settings.get('activation_issue')) is not int or settings['activation_issue'] <= 0:
            errors.append('활성화 Issue 번호를 지정하세요.')
        approved = [c for c in comments if c['id'] == settings.get('activation_approval') and c['user']['login'] == settings['pilot_owner'] and has_line(c, f'/pilot-activate {config_hash(settings)}')]
        if not approved:
            errors.append('현재 설정에 대한 Pilot DRI의 활성화 승인이 없습니다.')
        for c in comments:
            if c['issue_url'] != f'https://api.github.com/repos/{repo}/issues/{settings["activation_issue"]}':
                errors.append('수락·활성화 댓글은 활성화 Issue 안에 있어야 합니다.')
                break
    except (ValueError, TypeError, KeyError):
        errors.append('필수 설정이 비어 있거나 날짜·Route 형식이 잘못됐습니다.')
    return errors


def sections(body):
    result = {}
    matches = list(re.finditer(r'^### (.+?)\s*$', body, re.M))
    for i, match in enumerate(matches):
        key = match[1].strip()
        if key in result:
            raise ValueError('중복 필드: ' + key)
        result[key] = body[match.end():matches[i+1].start() if i+1 < len(matches) else len(body)].strip()
    return result


def meaningful(value):
    return bool(value and value.strip().lower() not in {'_no response_', 'tbd', 'n/a', 'none', '-', '미정'})


def form_errors(issue):
    labels = set(label_names(issue))
    selected = [kind for kind in KINDS if kind in labels]
    if len(selected) != 1:
        return ['Proposal 종류 Label은 하나여야 합니다.'], None
    kind = selected[0]
    body = issue.get('body') or ''
    if len(body) > 12000:
        return ['본문을 12,000자 이내로 줄이세요.'], kind
    try:
        fields = sections(body)
    except ValueError as error:
        return [str(error)], kind
    errors = [f'{key}: 필수 정보 누락' for key in KINDS[kind] if not meaningful(fields.get(key))]
    if kind == 'proposal:design-system':
        value = fields.get('Figma Node Link 또는 미존재 사유', '')
        if not value.startswith('미존재:'):
            parsed = urlparse(value)
            if parsed.scheme != 'https' or parsed.hostname not in {'figma.com', 'www.figma.com'} or not re.match(r'^/(design|file)/[^/]+', parsed.path) or not re.search(r'(?:^|&)node-id=[\w:%-]+', parsed.query):
                errors.append('Figma Node Link 또는 "미존재: 구체적 사유"를 입력하세요.')
        elif len(value.removeprefix('미존재:').strip()) < 3:
            errors.append('Figma 대상 미존재 사유를 구체적으로 입력하세요.')
    return errors, kind


def label_names(issue):
    return [x['name'] if isinstance(x, dict) else x for x in issue.get('labels', [])]


def read_state(comments):
    trusted = [c for c in comments if c['user'].get('id') == BOT_ID and c['user'].get('type') == 'Bot' and c.get('body', '').startswith(STATE_MARKER)]
    if len(trusted) > 1:
        raise ValueError('중복된 봇 상태 댓글: 운영자 확인 필요')
    if not trusted:
        return {}, None
    c = trusted[0]
    return json.loads(c['body'][len(STATE_MARKER):].split('\n-->\n', 1)[0]), c['id']


def _display_timestamp(value):
    try:
        return stamp(value).astimezone(KST).strftime('%Y-%m-%d %H:%M:%S KST')
    except (ValueError, TypeError, AttributeError):
        return f'{value} (시각 형식 확인 필요)'


def _next_steps(state):
    status = state.get('status', '')
    errors = state.get('errors', [])
    if status.startswith('비활성'):
        return '운영 담당자는 활성화 이슈에서 설정과 역할 수락을 확인하세요. 제출자는 접수 시작 안내를 기다려 주세요.'
    if status.startswith('테스트 시나리오'):
        return ('테스트 담당자는 아래 입력 오류가 의도한 결과인지 확인하세요.' if errors else
                '테스트 담당자는 입력 검증 결과를 기록하세요.') + ' 이 이슈는 운영 표본에 포함되지 않으며 실제 담당자 지정이나 결정 수락은 진행하지 않습니다.'
    if status.startswith('접수 제외'):
        return '운영 담당자는 제출자의 파일럿 참가 여부를 확인하세요. 참가자로 확인되기 전에는 실제 접수로 처리하지 않습니다.'
    if status.startswith('접수 기간 밖'):
        return '운영 담당자는 활성화 이슈의 접수 기간과 이슈 생성 시각을 확인하세요. 이 이슈는 이번 접수 표본에 포함되지 않습니다.'
    if status == '필수 정보 보완 대기':
        return '제안자는 아래 확인 항목에 맞춰 이슈 본문을 수정하세요. 수정 후 이 댓글에서 유효 접수 시각과 첫 결정 기한이 표시되는지 확인하세요.'
    if status in {'첫 결정 대기', '결정 기록 재확인 필요'}:
        steps = []
        if errors and state.get('delivery_allowed') is False:
            steps.append('제안자는 아래 본문 입력 오류를 보완하세요. 이미 기록된 유효 접수 시각과 첫 결정 기한은 유지됩니다.')
        if not state.get('route'):
            steps.append('부총괄은 운영 가이드의 담당자 지정 절차에 따라 결정권자를 지정하세요. 처리 후 이슈의 Assignee와 이 댓글의 결정권자가 같은지 확인하세요.')
        elif any('해당 결정 수락' in error for error in errors):
            steps.append('지명된 실행 담당자와 결정권자는 운영 가이드의 첫 결정과 실행 책임 절차에 따라 수락을 기록하세요. 결정권자가 수락 댓글 링크를 반영한 뒤, 실행 담당자는 기존 수락 댓글에 확인 문장을 추가해 다시 수락하세요. 수락 명령과 댓글 URL은 유지하세요.')
        else:
            steps.append('결정권자는 운영 가이드의 첫 결정 절차에 따라 결정 댓글, 결정 라벨, 실행 담당자의 수락을 확인하세요.')
        if status == '결정 기록 재확인 필요':
            steps.append('최초 결정 완료 시각은 보존됩니다. 아래 확인 항목을 해결한 뒤 현재 결정 기록이 다시 유효해졌는지 확인하세요.')
        return ' '.join(steps)
    if state.get('current_decision'):
        return '결정 댓글에 지정된 담당자는 다음 행동을 진행하고, 재검토 조건이나 날짜가 되면 이 이슈에 결과를 기록하세요.'
    return '운영 담당자는 워크플로 처리 후 이 댓글에 접수 상태가 표시되는지 확인하세요.'


def render_state(state):
    status = state.get('status', '검증 대기')
    statuses = {
        '테스트 시나리오 — 운영 표본 제외': '테스트 시나리오: 운영 표본 제외',
        '비활성 — 실제 접수·기한·알림 없음': '비활성: 현재 실제 접수·담당자 지정·알림을 처리하지 않습니다.',
        '접수 제외 — 참가자 확인 필요': '접수 제외: 참가자 확인 필요',
        '접수 기간 밖 — Cohort 편입 없음': '접수 기간 밖: 이번 접수 표본에 포함되지 않습니다.',
    }
    decisions = {'Validating': '검증 진행', 'Active': '실행 진행', 'Parked': '보류', 'Rejected': '반려'}
    decision = state.get('current_decision', {}).get('decision') if state.get('current_decision') else None
    visible_status = statuses.get(status, status)
    if status.startswith('유효한 첫 결정:') and decision:
        visible_status = f'첫 결정 기록 완료: {decisions.get(decision, decision)} (`{decision}`)'
    lines = ['## 제안 운영 기록', '', visible_status, '', '### 다음 행동', '', _next_steps(state)]
    timestamps = [('submitted_at', '제안 제출 시각'), ('valid_at', '유효 접수 시각'),
                  ('decision_due_at', '첫 결정 기한'), ('first_decision_at', '최초 결정 완료 시각')]
    if any(state.get(key) for key, _ in timestamps) or state.get('route'):
        lines.extend(['', '### 접수·결정 기록', ''])
        if status.startswith(('비활성', '테스트 시나리오', '접수 제외', '접수 기간 밖')):
            lines.extend(['아래 내용은 이전에 기록된 이력입니다. 현재 접수 여부는 위 상태를 확인하세요.', ''])
        for key, label in timestamps:
            if state.get(key):
                lines.append(f'- {label}: {_display_timestamp(state[key])}')
        if state.get('route'):
            route = state['route']
            slot = {'primary': '기본 담당', 'backup': '대체 담당'}.get(route.get('slot'), '담당 구분 미기록')
            lines.append(f'- 결정권자: @{route["assignee"]} ({slot})')
            lines.append(f'- 제안을 검토할 목적·플랫폼 구분: `{route["key"]}`')
        if state.get('valid_at'):
            lines.extend(['', '유효 접수 시각은 필수 입력과 접수 조건을 충족한 시각이며, 첫 결정 기한을 계산하는 기준입니다.'])
    if state.get('errors'):
        heading = '운영 담당자가 확인할 활성화 조건' if status.startswith('비활성') else '확인할 항목'
        lines.extend(['', f'### {heading}', ''])
        lines.extend(f'- {error}' for error in state['errors'])
    if state.get('deliveries'):
        events = {'new': '신규 접수', 'decision': '첫 결정 완료', 'due': '결정 기한 당일 안내', 'escalation': '결정 기한 경과 안내'}
        deliveries = {'queued': '전송 대기', 'sending': '전송 시도 기록됨, 수신 확인 필요',
                      'sent': '전송 완료', 'uncertain': '수신 여부 확인 필요', 'failed': '전송 실패',
                      'cancelled': '전송 취소, 후속 결정 또는 기한 경과 안내로 대체됨'}
        lines.extend(['', '### Discord 알림 기록', ''])
        for event, delivery in state['deliveries'].items():
            lines.append(f'- {events.get(event, event)}: {deliveries.get(delivery["status"], delivery["status"])}')
        if state.get('delivery_allowed') is False:
            lines.extend(['', '현재 알림 전송이 보류되어 있습니다. 위 다음 행동과 확인 항목을 먼저 확인하세요.'])
        elif any(d['status'] in {'sending', 'uncertain', 'failed'} for d in state['deliveries'].values()):
            lines.extend(['', '운영 담당자는 Discord 채널에서 수신 여부를 확인하세요. 재전송이 필요하면 운영 가이드의 알림 재시도 절차를 따르세요.'])
    lines.extend(['', '접수 시각·첫 결정 기한·결정 기록은 이 이슈를 기준으로 확인합니다. 운영 담당자는 이 기록에 맞춰 Project 필드를 갱신하세요.'])
    return STATE_MARKER + json.dumps(state, ensure_ascii=False, sort_keys=True) + '\n-->\n' + '\n'.join(lines)


def decision_fields(comment):
    if not re.search(r'^## First decision\s*$', comment.get('body', ''), re.M):
        return None
    fields = {}
    for line in comment['body'].splitlines():
        match = re.fullmatch(r'- ([^:]+):\s*(.*)', line)
        if match:
            if match[1] in fields:
                return None
            fields[match[1]] = match[2].strip()
    return fields


def acceptance_time(holder, decision, comments, fields, issue, repo):
    # Acceptances bind to the decision comment ID, so an old role acceptance cannot be reused.
    if holder == decision['user']['login'] and fields['Acceptance'] == 'Self accepted':
        return stamp(decision['updated_at'])
    pattern = rf'https://github\.com/{re.escape(repo)}/issues/{issue["number"]}#issuecomment-(\d+)'
    match = re.fullmatch(pattern, fields['Acceptance'])
    if not match:
        return None
    for c in comments:
        if c['id'] == int(match[1]) and c['user']['login'] == holder and has_line(c, f'/pilot-accept-decision {decision["id"]}') and stamp(c['updated_at']) >= stamp(decision['updated_at']):
            return stamp(c['updated_at'])
    return None


def validate_decision(issue, comments, events, route, repo):
    if not route:
        return None, ['결정권자 Routing 대기'], False
    candidates = [c for c in comments if c['user']['login'] == route['assignee'] and re.search(r'^## First decision\s*$', c.get('body', ''), re.M)]
    if not candidates:
        return None, ['확정된 결정권자의 First decision 댓글이 없습니다.'], False
    c = max(candidates, key=lambda x: (x['id']))
    fields = decision_fields(c)
    if fields is None:
        return None, ['가장 최근 First decision의 중복·잘못된 필드를 수정하세요.'], False
    errors = [f'{key}: 결정 필드 누락' for key in DECISION_FIELDS if not fields.get(key)]
    decision = fields.get('Decision')
    if decision not in DECISIONS:
        errors.append('허용되지 않은 Decision')
    labels = [x for x in label_names(issue) if x.startswith('decision:') and x != 'decision:pending']
    if labels != [f'decision:{str(decision).lower()}']:
        errors.append('결정 Label 하나와 Decision이 일치해야 합니다.')
    if [x['login'] for x in issue.get('assignees', [])] != [route['assignee']]:
        errors.append('Assignee와 확정된 결정권자가 다릅니다.')
    if decision == 'Parked' and not meaningful(fields.get('Reconsideration condition/date')):
        errors.append('Parked의 재검토 조건·날짜가 필요합니다.')
    owner = fields.get('Proposal DRI', '')
    holder = owner[1:] if re.fullmatch(r'@[\w-]+', owner) else None
    if decision in {'Active', 'Validating'} and not holder:
        errors.append('Active·Validating에는 Proposal DRI가 필요합니다.')
    if not holder and not re.fullmatch(r'None \(.+\)', owner):
        errors.append('Proposal DRI는 @account 또는 None (사유)로 적으세요.')
    next_holders = set(re.findall(r'@([\w-]+)', fields.get('Next action', '')))
    if not next_holders or next_holders - {route['assignee'], holder}:
        errors.append('Next action 담당자는 결정권자 또는 수락한 Proposal DRI여야 합니다.')
    missing_acceptance = False
    times = [stamp(c['updated_at']), stamp(route['at'])]
    if holder and not errors:
        accepted = acceptance_time(holder, c, comments, fields, issue, repo)
        if accepted is None:
            missing_acceptance = True
            errors.append('지명된 Proposal DRI의 해당 결정 수락이 없습니다.')
        else:
            times.append(accepted)
    labeled = [e for e in events if e.get('event') == 'labeled' and e.get('label', {}).get('name') == f'decision:{str(decision).lower()}']
    if labeled:
        times.append(stamp(max(labeled, key=lambda e:e['created_at'])['created_at']))
    else:
        errors.append('결정 Label 적용 이력이 없습니다.')
    if errors:
        return None, errors, missing_acceptance
    return {'at': iso(max(times)), 'comment_id': c['id'], 'decision': decision, 'proposal_dri': holder, 'fields': fields}, [], False


def reconcile(settings, issue, comments, events, now, repo, activation_comments, active='false', state=None):
    state = copy.deepcopy(state or {})
    labels = set(label_names(issue))
    result = {'state': state, 'labels': None, 'assignee': None, 'ignored': False}
    state['delivery_allowed'] = False
    if 'proposal' not in labels or 'pull_request' in issue:
        result['ignored'] = True
        return result
    errors, kind = form_errors(issue)
    if 'pilot:scenario' in labels:
        state.update(status='테스트 시나리오 — 운영 표본 제외', scenario=True, errors=errors, kind=kind)
        result['labels'] = sorted((labels - MANAGED) | ({'needs:information'} if errors else set()))
        return result
    gates = activation_errors(settings, activation_comments, repo, active)
    if gates:
        state.update(status='비활성 — 실제 접수·기한·알림 없음', errors=gates)
        return result
    if issue['user']['login'] not in settings['participants']:
        state.update(status='접수 제외 — 참가자 확인 필요', errors=[])
        return result
    approved = next(c for c in activation_comments if c['id'] == settings['activation_approval'])
    start = max(datetime.combine(date.fromisoformat(settings['activation_date']), time.min, KST), stamp(approved['updated_at']))
    close = stamp(settings['intake_close_at'])
    if not state.get('valid_at') and not (start <= stamp(issue['created_at']) <= close and now <= close):
        state.update(status='접수 기간 밖 — Cohort 편입 없음', errors=[])
        return result
    wanted = labels - MANAGED
    state.update(kind=kind, submitted_at=issue['created_at'], scenario=False, errors=errors)
    state['delivery_allowed'] = not errors
    if not state.get('valid_at') and not errors:
        state.update(valid_at=iso(now), decision_due_at=deadline(iso(now), settings), config_version=config_hash(settings), intake_body=issue.get('body') or '', deliveries={})
        state['deliveries']['new'] = {'status': 'queued'}
    if errors:
        wanted.add('needs:information')
    if not state.get('valid_at'):
        state['status'] = '필수 정보 보완 대기'
        result['labels'] = sorted(wanted)
        return result
    routing = []
    for c in comments:
        if c['user']['login'] == settings['pilot_owner']:
            for line in c.get('body', '').splitlines():
                match = re.fullmatch(r'/pilot-route ([a-z-]+) (primary|backup)', line.strip())
                if match:
                    routing.append((c, match[1], match[2]))
    if routing:
        c, key, slot = max(routing, key=lambda x:x[0]['id'])
        signature = f'{c["id"]}:{c["updated_at"]}'
        if signature != state.get('routing_command'):
            if key in settings['enabled_routes'] and (kind != 'proposal:design-system' or key == 'design-platform') and (kind != 'proposal:product' or key != 'design-platform'):
                route = {'key': key, 'assignee': settings['routing_map'][key][slot], 'at': c['updated_at'], 'comment_id': c['id'], 'slot': slot}
                state.setdefault('routing_history', []).append(route)
                state.update(route=route, routing_command=signature)
                result['assignee'] = route['assignee']
                # Validate the fetched state after the explicit manual assignment on the next run.
            else:
                state.pop('route', None)
                state['errors'].append('수동 Route가 접수 종류·허용 범위와 맞지 않습니다.')
    route = state.get('route')
    if route and route['assignee'] != settings['routing_map'].get(route['key'], {}).get(route['slot']):
        route = None
        state.pop('route', None)
        state['errors'].append('Route 담당자 변경: 부총괄의 새 Routing 기록 필요')
    wanted = {label for label in wanted if not label.startswith('purpose:')}
    wanted.add('purpose:' + (route['key'] if route else 'unknown'))
    if not route:
        wanted.add('needs:routing')
    decision, decision_errors, needs_acceptance = validate_decision(issue, comments, events, route, repo)
    if errors:
        decision = None
    if decision:
        state['status'] = f'유효한 첫 결정: {decision["decision"]}'
        if not state.get('first_decision_at'):
            state.update(first_decision_at=iso(max(stamp(decision['at']), stamp(state['valid_at']))), first_decision=decision, decision_body=issue.get('body') or '')
            state['deliveries']['decision'] = {'status':'queued'}
        state['current_decision'] = decision
    else:
        state['status'] = '첫 결정 대기' if not state.get('first_decision_at') else '결정 기록 재확인 필요'
        state['errors'].extend(decision_errors)
        state['current_decision'] = None
        wanted.add('decision:pending')
        if route:
            wanted.add('needs:owner-acceptance' if needs_acceptance else 'needs:decision-record')
    # Mark the business-day boundary using the original accepted SLA snapshot.
    due = stamp(state['decision_due_at']).astimezone(KST)
    today = now.astimezone(KST).date()
    if not decision and not state.get('first_decision_at') and business_day(today, settings) and now.astimezone(KST).time().replace(tzinfo=None) >= time(9):
        event = 'escalation' if today > due.date() else 'due' if today == due.date() else None
        if event and event not in state['deliveries']:
            state['deliveries'][event] = {'status':'queued'}
    # A later valid decision cancels obsolete queued reminders before notification.
    for event in ('due', 'escalation'):
        if decision and state['deliveries'].get(event, {}).get('status') == 'queued':
            state['deliveries'][event]['status'] = 'cancelled'
    if state['deliveries'].get('escalation', {}).get('status') == 'queued' and state['deliveries'].get('due', {}).get('status') == 'queued':
        state['deliveries']['due']['status'] = 'cancelled'
    for c in comments:
        if c['user']['login'] != settings['pilot_owner']:
            continue
        for line in c.get('body', '').splitlines():
            match = re.fullmatch(r'/pilot-retry-notification (new|decision|due|escalation)', line.strip())
            if match:
                delivery = state['deliveries'].get(match[1], {})
                if delivery.get('status') in {'uncertain','sending','failed'} and c['id'] > delivery.get('retry_comment', 0) and delivery.get('attempted_at') and stamp(c['updated_at']) >= stamp(delivery['attempted_at']):
                    delivery.update(status='queued', retry_comment=c['id'])
    result['labels'] = sorted(wanted)
    return result


def notification_payload(repo, issue, state, event, settings):
    # Deliberately use a generated title: arbitrary titles can contain private data.
    owner = settings['pilot_owner'] if event == 'escalation' else state.get('route', {}).get('assignee', settings['pilot_owner'])
    title = {'new':'신규 Proposal', 'decision':'첫 결정 기록 완료', 'due':'오늘 결정 기한', 'escalation':'결정 기한 경과'}[event]
    fields = [
        {'name':'종류','value':state['kind'].removeprefix('proposal:')},
        {'name':'Route','value':state.get('route', {}).get('key', 'Routing 대기')},
        {'name':'담당 GitHub 계정','value':owner},
        {'name':'최초 결정 기한','value':state['decision_due_at']},
    ]
    return {'allowed_mentions':{'parse':[]}, 'embeds':[{'title':f'{title} #{issue["number"]}', 'url':f'https://github.com/{repo}/issues/{issue["number"]}', 'fields':fields}]}
