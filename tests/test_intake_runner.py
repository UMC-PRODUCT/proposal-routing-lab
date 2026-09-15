import copy
import unittest
from unittest.mock import patch

from intake import core, registry, runner
from pilot.runner import APIError, GitHub
from test_intake_registry import prepared, NOW


class FakeGitHub:
    def __init__(self, cfg, roles):
        self.cfg = cfg
        self.repo = cfg['repository']['full_name']
        self.calls = []
        self.hook = None
        self.issues = {
            6: {'number': 6, 'state': 'open', 'body': runner.REPORT_MARKER},
            7: {'number': 7, 'state': 'open', 'title': '제안',
                'body': '### 대상\n\n공식 홈페이지·테크 블로그·대외 콘텐츠\n\n### 문제\n\n안내 혼선\n\n### 원하는 도움\n\n검토',
                'user': {'id': 13, 'login': 'test-user-13', 'type': 'User'},
                'created_at': '2026-09-15T00:00:00Z', 'updated_at': '2026-09-15T00:00:00Z',
                'labels': [{'name': 'keep-me'}], 'assignees': []},
            8: {'number': 8, 'pull_request': {}}}
        self.notes = {1: copy.deepcopy(roles), 6: [], 7: []}
        self.events = {7: []}
        self.next_id = 1000

    def base(self, suffix=''):
        return '/repos/' + self.repo + suffix

    def comments(self, number):
        return self.paged(self.base(f'/issues/{number}/comments'))

    def paged(self, path):
        return self.request('GET', path)

    def request(self, method, path, payload=None):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if self.hook:
            self.hook(method, path, payload)
        if path.startswith('/user/'):
            uid = int(path.split('/')[-1])
            return {'id': uid, 'login': f'test-user-{uid}', 'type': 'User'}
        tail = path.removeprefix(self.base())
        if tail == '/issues?state=all':
            return copy.deepcopy(list(self.issues.values()))
        parts = tail.strip('/').split('/')
        if parts[:2] == ['issues', 'comments']:
            for comments in self.notes.values():
                for comment in comments:
                    if comment['id'] == int(parts[2]):
                        comment.update(payload)
                        return copy.deepcopy(comment)
            raise APIError('missing comment')
        number = int(parts[1])
        if len(parts) == 2:
            issue = self.issues[number]
            if method == 'PATCH':
                issue.update(payload)
                if 'assignees' in payload:
                    issue['assignees'] = [{'login': x} for x in payload['assignees']]
                if 'state' in payload:
                    self.events[number].append({'id': 5000, 'event': 'closed' if payload['state'] == 'closed' else 'reopened',
                                                'actor': {'id': core.BOT_ID, 'type': 'Bot'}, 'created_at': registry.iso(NOW)})
            return copy.deepcopy(issue)
        if parts[2] == 'comments':
            if method == 'POST':
                self.notes.setdefault(number, []).append({'id': self.next_id, 'body': payload['body'],
                    'user': {'id': core.BOT_ID, 'type': 'Bot'},
                    'created_at': registry.iso(NOW), 'updated_at': registry.iso(NOW)})
                self.next_id += 1
            return copy.deepcopy(self.notes[number])
        if parts[2] == 'events':
            return copy.deepcopy(self.events[number])
        if parts[2] == 'labels':
            if method == 'POST':
                self.issues[number]['labels'].extend({'name': x} for x in payload['labels'])
            return []
        raise AssertionError((method, tail))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.roles = prepared()
        self.api = FakeGitHub(self.cfg, self.roles)

    def run_scan(self, mode='active', event=None, now=NOW):
        return runner.run(self.api, self.cfg, mode, now, event, 'fixture-ref')

    def writes(self):
        return [c for c in self.api.calls if c[0] != 'GET']

    def finish_inputs(self):
        decision = {'id': 200, 'user': {'id': 10, 'type': 'User'},
                    'created_at': '2026-09-15T01:00:00Z', 'updated_at': '2026-09-15T01:00:00Z',
                    'body': '## 결정\n결정: 실행 진행\n이유: 확인\n다음 행동: 수정\n실행 담당자: @test-user-13\n다음 확인일: 2026-09-20'}
        self.api.notes[7] = [decision]
        state = core.reconcile(self.cfg, self.api.issues[7], [decision], [], self.roles, NOW)['state']
        acceptance = {'id': 201, 'user': {'id': 13, 'type': 'User'},
                      'created_at': '2026-09-15T02:00:00Z', 'updated_at': '2026-09-15T02:00:00Z',
                      'body': '/수락 ' + state['current_decision']['version'] + '\n실행 작업: https://github.com/example/work/issues/9'}
        self.api.notes[7].append(acceptance)

    def test_observe_reads_closed_all_and_excludes_pr_without_writes(self):
        self.api.issues[7]['state'] = 'closed'
        result = self.run_scan('observe')
        self.assertTrue(result['complete'], result)
        self.assertEqual(2, result['total'])
        self.assertFalse(self.writes())
        self.assertTrue(any(path.endswith('/issues?state=all') for _, path, _ in self.api.calls))
        self.assertEqual('open', core.reconcile(self.cfg, self.api.issues[7], [], [], self.roles, NOW)['issue_state'])

    def test_active_routes_and_keeps_unmanaged_labels(self):
        result = self.run_scan()
        self.assertTrue(result['complete'], result)
        self.assertEqual([{'login': 'test-user-10'}], self.api.issues[7]['assignees'])
        self.assertIn({'name': 'keep-me'}, self.api.issues[7]['labels'])
        self.assertTrue(core.read_state(self.api.notes[7])[0]['tracked'])

    def test_missing_common_readiness_forces_observe(self):
        self.cfg['readiness']['protection_verified'] = False
        self.assertEqual('observe', self.run_scan()['mode'])
        self.assertFalse(self.writes())

    def test_drain_ignores_new_but_expiry_keeps_tracked_handoff_writable(self):
        result = self.run_scan('drain')
        self.assertTrue(next(r for r in result['results'] if r['number'] == 7)['ignored'])
        self.run_scan()
        result = self.run_scan(now=registry.stamp('2026-11-09T03:00:00Z'))
        self.assertEqual('drain', result['mode'])
        self.assertTrue(result['complete'], result)
        self.assertIn('임기 종료', str(core.read_state(self.api.notes[7])[0]['exceptions']))

    def test_external_event_never_writes(self):
        result = self.run_scan(event={'issue': self.api.issues[7], 'sender': {'id': 999}})
        self.assertEqual('external_event', result['skipped'])
        self.assertFalse(self.writes())

    def test_control_acceptance_event_causes_full_scan(self):
        result = self.run_scan(event={'issue': {'number': 1}, 'sender': {'id': 10}})
        self.assertTrue(result['full_scan'])
        self.assertTrue(core.read_state(self.api.notes[7])[0]['tracked'])

    def test_partial_read_isolated_and_cannot_close(self):
        other = copy.deepcopy(self.api.issues[7]); other['number'] = 9
        self.api.issues[9], self.api.notes[9], self.api.events[9] = other, [], []
        def fail(method, path, payload):
            if path.endswith('/issues/7/comments'):
                raise APIError('private error text')
        self.api.hook = fail
        result = self.run_scan()
        self.assertFalse(result['complete'])
        self.assertTrue(any(r['number'] == 9 for r in result['results']))
        self.assertFalse(any(p == {'state': 'closed'} for _, _, p in self.writes()))
        self.assertNotIn('private error text', str(result))
        self.assertIn('일부 또는 전체 실패', self.api.issues[6]['body'])

    def test_global_listing_failure_updates_dashboard_and_preserves_rows(self):
        self.run_scan()
        before = self.api.issues[6]['body']
        def fail(method, path, payload):
            if path.endswith('/issues?state=all'):
                raise APIError('unavailable')
        self.api.hook = fail
        result = self.run_scan()
        self.assertFalse(result['complete'])
        after = self.api.issues[6]['body']
        self.assertIn('| #7 |', after)
        self.assertIn('이전 검사 기록', after)
        self.assertIn(next(x for x in before.splitlines() if x.startswith('마지막 전체 성공:')), after)

    def test_final_close_rereads_acceptance_after_label_writes(self):
        self.finish_inputs()
        def mutate(method, path, payload):
            if method == 'POST' and path.endswith('/labels'):
                self.api.notes[7] = [c for c in self.api.notes[7] if c['id'] != 201]
        self.api.hook = mutate
        result = self.run_scan()
        self.assertFalse(result['complete'])
        self.assertEqual('open', self.api.issues[7]['state'])

    def test_normal_completion_and_second_run_no_duplicate_snapshot(self):
        self.finish_inputs()
        self.assertTrue(self.run_scan()['complete'])
        self.assertEqual('closed', self.api.issues[7]['state'])
        self.assertTrue(self.run_scan()['complete'])
        self.assertEqual(1, sum(c.get('user', {}).get('id') == core.BOT_ID for c in self.api.notes[7]))

    def test_lost_post_response_recovers_from_existing_snapshot(self):
        original = self.api.request
        lost = []
        def request(method, path, payload=None):
            result = original(method, path, payload)
            if not lost and method == 'POST' and path.endswith('/issues/7/comments'):
                lost.append(True)
                raise APIError('response lost')
            return result
        self.api.request = request
        self.assertFalse(self.run_scan()['complete'])
        self.assertTrue(self.run_scan()['complete'])
        self.assertEqual(1, len(self.api.notes[7]))

    def test_daily_digest_once_and_exam_quiet(self):
        now = registry.stamp('2026-09-21T01:00:00Z')
        self.run_scan(now=now); self.run_scan(now=now)
        digests = [c for c in self.api.notes[6] if c['body'].startswith(runner.DIGEST_MARKER)]
        self.assertEqual(1, len(digests))
        self.run_scan(now=registry.stamp('2026-10-20T03:00:00Z'))
        self.assertEqual(1, len([c for c in self.api.notes[6] if c['body'].startswith(runner.DIGEST_MARKER)]))

    def test_username_resolution_uses_numeric_id(self):
        self.cfg['members'][0]['login'] = 'old-name'
        snapshot = runner.identity_snapshot(self.api, self.cfg)
        self.assertEqual('test-user-10', snapshot['members'][0]['login'])
        self.assertEqual('old-name', self.cfg['members'][0]['login'])

    def test_pages_over_100_and_failure_are_not_partial_success(self):
        api = GitHub('fixture/repo', 'never-used')
        with patch.object(api, 'request', side_effect=[list(range(100)), [100]]) as get:
            self.assertEqual(101, len(api.paged('/issues?state=all')))
            self.assertEqual('/issues?state=all&per_page=100&page=2', get.call_args[0][1])
        with patch.object(api, 'request', side_effect=[list(range(100)), APIError('page2')]):
            with self.assertRaises(APIError): api.paged('/issues?state=all')


if __name__ == '__main__':
    unittest.main()
