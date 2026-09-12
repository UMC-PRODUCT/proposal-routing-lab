import copy
import unittest

from intake import core
from intake.registry import route_version, stamp


def comment(cid, uid, body, when='2026-09-14T01:00:00Z'):
    return {'id': cid, 'user': {'id': uid, 'login': f'user{uid}', 'type': 'User'},
            'body': body, 'created_at': when, 'updated_at': when}


def fixture():
    cfg = {
        'repository': {'full_name': 'fixture/intake', 'intake_opened_at': '2026-09-13T00:00:00Z',
                       'control_issue': 1, 'dashboard_issue': 6, 'excluded_issue_numbers': [1, 2, 3, 4, 5, 6]},
        'members': [{'id': uid, 'login': f'user{uid}', 'active': True, 'registered_at': '2026-09-01T00:00:00Z'}
                    for uid in (11, 12, 13, 14, 15, 16)],
        'coordination': {'primary': {'user_id': 15, 'acceptance_comment_id': 901},
                         'backup': {'user_id': 16, 'acceptance_comment_id': 902}},
        'calendar': {'timezone': 'Asia/Seoul', 'non_working_dates': [],
                     'quiet_periods': [{'start': '2026-10-19', 'end': '2026-10-24'}]},
        'policy': {'routing_business_days': 1, 'first_response_business_days': 3},
        'routes': {'brand-and-growth': {'name': 'Brand & Growth', 'type': 'Purpose', 'scope': '제안',
                  'display_name': 'PM', 'owner_id': 12, 'enabled': True, 'acting': True,
                  'starts_at': '2026-09-13T00:00:00+09:00', 'ends_at': '2026-11-08T00:00:00+09:00',
                  'review_on': '2026-10-26', 'acceptance_comment_id': 900, 'handoff_comment_id': None,
                  'products': [{'id': 'web', 'label': '공식 홈페이지'}]}}}
    route = cfg['routes']['brand-and-growth']
    roles = [comment(900, 12, '/역할수락 brand-and-growth ' + route_version(route), '2026-09-13T00:00:00Z'),
             comment(901, 15, '/역할수락 coordination.primary', '2026-09-13T00:00:00Z'),
             comment(902, 16, '/역할수락 coordination.backup', '2026-09-13T00:00:00Z')]
    issue = {'number': 7, 'user': {'id': 11, 'type': 'User', 'login': 'user11'},
             'body': '### 대상\n\n공식 홈페이지\n\n### 문제\n\n안내 혼선\n\n### 원하는 도움\n\n개선 검토',
             'title': '[제품] 안내 개선', 'created_at': '2026-09-14T00:00:00Z',
             'updated_at': '2026-09-14T00:00:00Z', 'state': 'open', 'labels': [], 'assignees': []}
    return cfg, roles, issue


class IntakeCoreTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.roles, self.issue = fixture()
        self.comments, self.events = [], []
        self.now = stamp('2026-09-14T05:00:00Z')

    def run_case(self, old=None):
        return core.reconcile(self.cfg, self.issue, self.comments, self.events, self.roles, self.now, old)

    def decision(self, kind='실행 진행', uid=12, cid=100, inline=False):
        fields = ['## 결정', f'결정: {kind}', '이유: 사용자 혼선', '범위: 완료 안내',
                  '다음 행동: 안내 개선', '실행 담당자: @user13', '다음 확인일: 2026-09-21']
        if kind == '보류':
            fields.append('재검토 담당자: @user13')
        if inline:
            fields[5] = '실행 담당자: @user12'
            fields += ['본인 수락: 예', '실행 작업: https://github.com/fixture/product/issues/9']
        record = comment(cid, uid, '\n'.join(fields))
        self.comments.append(record)
        return record

    def accepted(self):
        self.decision()
        state = self.run_case()['state']
        version = state['current_decision']['version']
        self.comments.append(comment(101, 13, '/수락 ' + version + '\n실행 작업: https://github.com/fixture/product/issues/9',
                                     '2026-09-14T02:00:00Z'))
        return self.run_case(state)['state']

    def test_registered_member_routes_without_labels_or_assignee(self):
        result = self.run_case()
        self.assertFalse(result['ignored'])
        self.assertEqual(['user12'], result['assignees'])
        self.assertEqual('검토 중', result['state']['status'])
        self.assertEqual('2026-09-17T14:59:59Z', result['state']['first_response_due_at'])

    def test_assignment_metric_uses_actual_github_event_not_desired_write(self):
        state = self.run_case()['state']
        self.assertNotIn('first_assigned_at', state)
        self.events.append({'id': 1000, 'event': 'assigned', 'assignee': {'id': 12},
                            'created_at': '2026-09-14T05:01:00Z'})
        self.now = stamp('2026-09-14T06:00:00Z')
        self.assertEqual('2026-09-14T05:01:00Z', self.run_case(state)['state']['first_assigned_at'])

    def test_unknown_target_is_coordinator_queue(self):
        self.issue['body'] = self.issue['body'].replace('공식 홈페이지', '모르겠음 / 여러 영역에 해당')
        result = self.run_case()
        self.assertEqual([], result['assignees'])
        self.assertEqual({15, 16}, set(result['state']['coordinator_ids']))

    def test_disabled_route_and_missing_role_ack_do_not_assign(self):
        for change in ('disabled', 'ack'):
            with self.subTest(change=change):
                self.setUp()
                if change == 'disabled':
                    self.cfg['routes']['brand-and-growth']['enabled'] = False
                else:
                    self.roles.pop(0)
                self.assertEqual([], self.run_case()['assignees'])

    def test_external_and_pr_and_excluded_are_ignored(self):
        for change in ('external', 'pr', 'excluded', 'before'):
            with self.subTest(change=change):
                self.setUp()
                if change == 'external': self.issue['user']['id'] = 999
                if change == 'pr': self.issue['pull_request'] = {}
                if change == 'excluded': self.issue['number'] = 3
                if change == 'before': self.issue['created_at'] = '2026-09-01T00:00:00Z'
                self.assertTrue(self.run_case()['ignored'])

    def test_registered_later_does_not_retroactively_intake(self):
        self.cfg['members'][0]['registered_at'] = '2026-09-14T00:01:00Z'
        self.assertTrue(self.run_case()['ignored'])

    def test_tracked_author_departure_and_label_deletion_do_not_erase(self):
        state = self.run_case()['state']
        self.cfg['members'][0]['active'] = False
        self.issue['labels'] = []
        self.issue['body'] = ''
        result = self.run_case(state)
        self.assertFalse(result['ignored'])
        self.assertIn('intake:tracked', result['labels'])

    def test_author_identity_is_numeric_not_login(self):
        self.issue['user']['login'] = 'renamed'
        self.assertFalse(self.run_case()['ignored'])
        record = self.decision()
        record['user']['login'] = 'renamed-pm'
        self.assertEqual('수락·인계 대기', self.run_case()['state']['status'])

    def test_normal_execution_acceptance_closes(self):
        state = self.accepted()
        self.assertEqual('처리 완료', state['status'])
        result = self.run_case(state)
        self.assertEqual('closed', result['issue_state'])
        self.assertIn('/fixture/product/issues/9', state['current_acceptance']['url'])

    def test_wrong_author_acceptance_and_wrong_revision_do_not_close(self):
        self.decision()
        state = self.run_case()['state']
        version = state['current_decision']['version']
        for uid, token in [(11, version), (13, 'D-wrong')]:
            self.comments.append(comment(101 + uid, uid, f'/수락 {token}\n실행 작업: https://github.com/fixture/product/issues/9'))
        self.assertEqual('수락·인계 대기', self.run_case(state)['state']['status'])

    def test_external_decision_and_coordinator_product_decision_do_not_override(self):
        state = self.accepted()
        self.decision(uid=999, cid=200)
        self.decision(uid=15, cid=201)
        self.assertEqual('처리 완료', self.run_case(state)['state']['status'])
        self.assertEqual(100, self.run_case(state)['state']['current_decision']['comment_id'])

    def test_explicit_inline_self_acceptance(self):
        self.decision(inline=True)
        self.assertEqual('처리 완료', self.run_case()['state']['status'])
        self.comments[0]['body'] = self.comments[0]['body'].replace('본인 수락: 예', '본인 수락: 아니오')
        self.assertEqual('수락·인계 대기', self.run_case()['state']['status'])

    def test_inline_acceptance_is_not_reused_after_semantic_edit(self):
        self.decision(inline=True)
        completed = self.run_case()['state']
        self.comments[0]['body'] = self.comments[0]['body'].replace('완료 안내', '전체 신청 과정')
        self.comments[0]['updated_at'] = '2026-09-14T03:00:00Z'
        pending = self.run_case(completed)['state']
        self.assertEqual('수락·인계 대기', pending['status'])
        # Another scan must not forget that the old inline consent was invalidated.
        pending = self.run_case(pending)['state']
        self.assertEqual('수락·인계 대기', pending['status'])
        self.comments.append(comment(101, 12, '/수락 ' + pending['current_decision']['version']
                                     + '\n실행 작업: https://github.com/fixture/product/issues/9', '2026-09-14T04:00:00Z'))
        self.assertEqual('처리 완료', self.run_case(pending)['state']['status'])

    def test_acceptance_url_edit_requires_new_comment_even_after_restore(self):
        completed = self.accepted()
        original = self.comments[-1]['body']
        self.comments[-1]['body'] = original.replace('/issues/9', '/issues/10')
        pending = self.run_case(completed)['state']
        self.assertEqual('수락·인계 대기', pending['status'])
        self.assertEqual('수락·인계 대기', self.run_case(pending)['state']['status'])
        self.comments[-1]['body'] = original
        pending = self.run_case(pending)['state']
        self.assertEqual('수락·인계 대기', pending['status'])
        replacement = copy.deepcopy(self.comments[-1])
        replacement['id'] = 102
        self.comments.append(replacement)
        self.assertEqual('처리 완료', self.run_case(pending)['state']['status'])

    def test_semantic_edit_needs_new_acceptance_but_whitespace_does_not(self):
        state = self.accepted()
        original_version = state['current_decision']['version']
        self.comments[0]['body'] = self.comments[0]['body'].replace('이유: 사용자 혼선', '  이유:  사용자   혼선  ')
        self.comments[0]['updated_at'] = '2026-09-14T03:00:00Z'
        result = self.run_case(state)
        self.assertEqual('처리 완료', result['state']['status'])
        self.assertEqual(original_version, result['state']['current_decision']['version'])
        self.comments[0]['body'] = self.comments[0]['body'].replace('완료 안내', '전체 신청 과정')
        changed = self.run_case(result['state'])['state']
        self.assertEqual('수락·인계 대기', changed['status'])
        self.assertNotEqual(original_version, changed['current_decision']['version'])

    def test_reverting_semantic_edit_does_not_resurrect_old_acceptance(self):
        state = self.accepted()
        original = self.comments[0]['body']
        self.comments[0]['body'] = original.replace('완료 안내', '전체 신청 과정')
        self.comments[0]['updated_at'] = '2026-09-14T03:00:00Z'
        state = self.run_case(state)['state']
        self.comments[0]['body'] = original
        self.comments[0]['updated_at'] = '2026-09-14T04:00:00Z'
        self.assertEqual('수락·인계 대기', self.run_case(state)['state']['status'])

    def test_deleted_latest_decision_never_revives_previous(self):
        self.decision('종료', cid=99)
        self.decision('종료', cid=100)
        state = self.run_case()['state']
        self.comments.pop()
        result = self.run_case(state)
        self.assertEqual('검토 중', result['state']['status'])
        self.assertIsNone(result['state']['current_decision'])

    def test_deleted_latest_acceptance_never_revives_previous(self):
        state = self.accepted()
        new_acceptance = copy.deepcopy(self.comments[-1])
        new_acceptance['id'] = 102
        self.comments.append(new_acceptance)
        state = self.run_case(state)['state']
        self.comments.pop()
        self.assertEqual('수락·인계 대기', self.run_case(state)['state']['status'])

    def test_bad_closed_issue_is_reopened(self):
        self.issue['state'] = 'closed'
        self.assertEqual('open', self.run_case()['issue_state'])

    def test_human_reopen_starts_new_cycle(self):
        state = self.accepted()
        self.now = stamp('2026-09-14T07:00:00Z')
        self.events = [{'id': 1000, 'event': 'reopened', 'actor': {'id': 11, 'type': 'User'},
                        'created_at': '2026-09-14T06:00:00Z'}]
        result = self.run_case(state)
        self.assertEqual('검토 중', result['state']['status'])
        self.assertIsNone(result['state']['current_decision'])

    def test_bot_reopen_does_not_start_new_cycle(self):
        state = self.accepted()
        self.events = [{'id': 1000, 'event': 'reopened', 'actor': {'id': core.BOT_ID, 'type': 'Bot'},
                        'created_at': '2026-09-14T04:00:00Z'}]
        self.assertEqual('처리 완료', self.run_case(state)['state']['status'])

    def test_parked_date_is_deferred_past_exam_break(self):
        self.decision('보류')
        self.comments[0]['body'] = self.comments[0]['body'].replace('2026-09-21', '2026-10-20')
        self.now = stamp('2026-10-21T01:00:00Z')
        quiet_state = self.run_case()['state']
        self.assertEqual('보류', quiet_state['status'])
        self.assertNotIn('다음 확인일이 도래했습니다.', quiet_state['exceptions'])
        self.now = stamp('2026-10-26T01:00:00Z')
        state = self.run_case(quiet_state)['state']
        self.assertEqual('2026-10-26', state['effective_check_on'])
        self.assertIn('다음 확인일이 도래했습니다.', state['exceptions'])

    def test_oct16_three_day_deadline_is_oct28(self):
        self.issue['created_at'] = '2026-10-16T00:00:00Z'
        self.now = stamp('2026-10-16T01:00:00Z')
        self.assertEqual('2026-10-28T14:59:59Z', self.run_case()['state']['first_response_due_at'])

    def test_expiry_blocks_new_decisions_but_preserves_completed(self):
        done = self.accepted()
        self.now = stamp('2026-11-07T15:00:00Z')
        self.assertEqual('처리 완료', self.run_case(done)['state']['status'])
        self.comments[0]['body'] = self.comments[0]['body'].replace('완료 안내', '다른 범위')
        self.comments[0]['updated_at'] = '2026-11-07T15:00:00Z'
        self.assertEqual('검토 중', self.run_case(done)['state']['status'])

    def test_departed_decider_and_executor_preserve_existing_completion(self):
        state = self.accepted()
        for person in self.cfg['members']:
            if person['id'] in (12, 13):
                person['active'] = False
        result = self.run_case(state)
        self.assertEqual('처리 완료', result['state']['status'])
        self.assertIsNone(result['assignees'])

    def test_renamed_executor_does_not_change_recorded_identity(self):
        state = self.accepted()
        self.cfg['members'][2]['login'] = 'renamed-executor'
        self.comments[-1]['user']['login'] = 'renamed-executor'
        result = self.run_case(state)
        self.assertEqual('처리 완료', result['state']['status'])
        self.assertEqual(13, result['state']['current_acceptance']['author_id'])

    def test_expiry_sends_pending_to_handoff(self):
        self.decision()
        pending = self.run_case()['state']
        self.now = stamp('2026-11-07T15:00:00Z')
        state = self.run_case(pending)['state']
        self.assertEqual('검토 중', state['status'])
        self.assertTrue(any('인계' in x for x in state['exceptions']))

    def test_adding_inline_acceptance_after_expiry_cannot_close_pending(self):
        self.decision(inline=True)
        self.comments[0]['body'] = self.comments[0]['body'].replace('본인 수락: 예', '본인 수락: 아니오')
        pending = self.run_case()['state']
        self.comments[0]['body'] = self.comments[0]['body'].replace('본인 수락: 아니오', '본인 수락: 예')
        self.comments[0]['updated_at'] = '2026-11-07T15:01:00Z'
        self.now = stamp('2026-11-07T16:00:00Z')
        result = self.run_case(pending)
        self.assertEqual('검토 중', result['state']['status'])
        self.assertIsNone(result['issue_state'])

    def test_decision_before_role_acceptance_is_not_authorized(self):
        self.roles[0]['created_at'] = self.roles[0]['updated_at'] = '2026-09-14T03:00:00Z'
        self.decision()
        self.assertIsNone(self.run_case()['state']['current_decision'])

    def test_scope_change_other_route_does_not_invalidate_completion(self):
        done = self.accepted()
        self.cfg['routes']['unrelated'] = copy.deepcopy(self.cfg['routes']['brand-and-growth'])
        self.cfg['routes']['unrelated']['scope'] = '새로운 별도 범위'
        self.assertEqual('처리 완료', self.run_case(done)['state']['status'])

    def test_owner_handoff_requires_new_owner_acknowledgement(self):
        state = self.run_case()['state']
        route = self.cfg['routes']['brand-and-growth']
        route['owner_id'] = 14
        route['acceptance_comment_id'] = 903
        version = route_version(route)
        self.roles.append(comment(903, 14, '/역할수락 brand-and-growth ' + version))
        self.assertEqual([], self.run_case(state)['assignees'])
        route['handoff_comment_id'] = 904
        self.roles.append(comment(904, 14, '/인계수락 brand-and-growth ' + version))
        self.assertEqual(['user14'], self.run_case(state)['assignees'])

    def test_handoff_before_actual_role_acceptance_is_rejected(self):
        state = self.run_case()['state']
        route = self.cfg['routes']['brand-and-growth']
        route.update(owner_id=14, acceptance_comment_id=903, handoff_comment_id=904)
        version = route_version(route)
        self.roles.append(comment(903, 14, '/역할수락 brand-and-growth ' + version, '2026-09-14T03:00:00Z'))
        self.roles.append(comment(904, 14, '/인계수락 brand-and-growth ' + version, '2026-09-14T02:00:00Z'))
        self.assertEqual([], self.run_case(state)['assignees'])

    def test_reroute_edit_after_owner_expiry_is_not_authorized(self):
        pending = self.run_case()['state']
        target = copy.deepcopy(self.cfg['routes']['brand-and-growth'])
        target.update(name='다른 팀', owner_id=14, ends_at='2026-12-01T00:00:00+09:00', acceptance_comment_id=905,
                      products=[{'id': 'other', 'label': '다른 제품'}])
        self.cfg['routes']['other'] = target
        self.roles.append(comment(905, 14, '/역할수락 other ' + route_version(target)))
        reroute = comment(100, 12, '/연결 other\n사유: 다른 팀 범위')
        reroute['updated_at'] = '2026-11-07T15:01:00Z'
        self.comments = [reroute]
        self.now = stamp('2026-11-07T16:00:00Z')
        self.assertEqual('brand-and-growth', self.run_case(pending)['state']['route_id'])

    def test_coordinator_scope_cleanup_does_not_require_product_owner(self):
        self.issue['body'] = self.issue['body'].replace('공식 홈페이지', '모르겠음 / 여러 영역에 해당')
        self.comments.append(comment(100, 15, '## 결정\n결정: 종료\n이유: 조직 회의 변경 제안\n종료 분류: 범위 밖'))
        self.assertEqual('처리 완료', self.run_case()['state']['status'])

    def test_reroute_needs_authorized_actor_reason_and_ready_target(self):
        self.issue['body'] = self.issue['body'].replace('공식 홈페이지', '모르겠음 / 여러 영역에 해당')
        self.comments.append(comment(100, 11, '/연결 brand-and-growth\n사유: 홈페이지'))
        self.assertIsNone(self.run_case()['state']['route_id'])
        self.comments.append(comment(101, 15, '/연결 brand-and-growth\n사유: 홈페이지'))
        state = self.run_case()['state']
        self.assertEqual('brand-and-growth', state['route_id'])
        self.comments.pop()
        self.assertEqual('brand-and-growth', self.run_case(state)['state']['route_id'])

    def test_invalid_urls_are_not_handoff_evidence(self):
        for url in ('https://github.com.evil.invalid/x/y/issues/1', 'https://github.com/x/y',
                    'https://github.com/x/y/issues/1#x', 'http://github.com/x/y/issues/1'):
            with self.subTest(url=url):
                self.setUp()
                state = self.accepted()
                self.comments[-1]['body'] = self.comments[-1]['body'].replace('https://github.com/fixture/product/issues/9', url)
                self.assertEqual('수락·인계 대기', self.run_case(state)['state']['status'])

    def test_state_comment_trust_corruption_and_duplicates(self):
        state = self.run_case()['state']
        body = core.render_state(state)
        fake = comment(500, 11, body)
        self.assertEqual(({}, None), core.read_state([fake]))
        trusted = comment(501, core.BOT_ID, body)
        trusted['user']['type'] = 'Bot'
        self.assertEqual(state, core.read_state([trusted])[0])
        with self.assertRaises(ValueError): core.read_state([trusted, trusted])
        trusted['body'] = core.STATE_MARKER + 'garbage\n-->\n'
        with self.assertRaises(ValueError): core.read_state([trusted])

    def test_state_comment_marker_injection_is_escaped(self):
        state = self.run_case()['state']
        state['exceptions'] = ['-->\n<script>payload</script>']
        rendered = core.render_state(state)
        self.assertEqual(1, rendered.count('\n-->\n'))
        self.assertNotIn('<script>', rendered)

    def test_malformed_record_cannot_become_completion(self):
        for body in ('## 결정\n결정: 종료\n결정: 종료\n이유: 중복',
                     '## 결정\n결정: 종료\n이유:',
                     '## 결정\n결정: 실행 진행\n이유: 근거\n다음 행동: 개선\n실행 담당자: @user13\n다음 확인일: 내일'):
            with self.subTest(body=body):
                self.comments = [comment(100, 12, body)]
                self.assertEqual('검토 중', self.run_case()['state']['status'])


if __name__ == '__main__':
    unittest.main()
