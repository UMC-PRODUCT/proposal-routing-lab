import copy
import json
import unittest

from pilot import core


def visible(state):
    return core.render_state(state).split('\n-->\n', 1)[1]


class RenderStateTests(unittest.TestCase):
    def test_visible_copy_preserves_exact_hidden_state_and_roundtrip(self):
        state = {
            'status': '첫 결정 대기', 'submitted_at': '2026-09-14T23:30:00Z',
            'valid_at': '2026-09-14T23:31:00Z', 'decision_due_at': '2026-09-18T14:59:00Z',
            'delivery_allowed': True, 'deliveries': {'new': {'status': 'sent', 'message_id': '123'}},
            'errors': [], 'intake_body': '원래 제안 본문', 'routing_history': [],
        }
        before = copy.deepcopy(state)
        rendered = core.render_state(state)
        expected = core.STATE_MARKER + json.dumps(state, ensure_ascii=False, sort_keys=True) + '\n-->\n'
        self.assertTrue(rendered.startswith(expected))
        comment = {'id': 17, 'user': {'id': core.BOT_ID, 'type': 'Bot'}, 'body': rendered}
        self.assertEqual((before, 17), core.read_state([comment]))
        self.assertEqual(before, state)

    def test_timestamps_show_kst_and_date_rollover_without_changing_values(self):
        state = {
            'submitted_at': '2026-09-14T23:30:00Z', 'valid_at': '2026-09-14T23:31:00Z',
            'decision_due_at': '2026-09-18T14:59:00Z', 'first_decision_at': '2026-09-15T01:00:00Z',
        }
        body = visible(state)
        self.assertIn('제안 제출 시각: 2026-09-15 08:30:00 KST', body)
        self.assertIn('유효 접수 시각: 2026-09-15 08:31:00 KST', body)
        self.assertIn('첫 결정 기한: 2026-09-18 23:59:00 KST', body)
        self.assertIn('최초 결정 완료 시각: 2026-09-15 10:00:00 KST', body)
        self.assertNotIn('submitted_at', body)
        self.assertEqual('2026-09-14T23:30:00Z', state['submitted_at'])
        self.assertIn('형식 확인 필요', visible({'valid_at': 'forged'}))

    def test_non_operating_states_direct_the_right_person_without_intake_commands(self):
        cases = [
            ('비활성 — 실제 접수·기한·알림 없음', ['participants를 확정하세요.'], '운영 담당자는 활성화 이슈'),
            ('테스트 시나리오 — 운영 표본 제외', ['사용자 문제: 필수 정보 누락'], '테스트 담당자는 아래 입력 오류'),
            ('접수 제외 — 참가자 확인 필요', [], '제출자의 파일럿 참가 여부'),
            ('접수 기간 밖 — Cohort 편입 없음', [], '접수 기간과 이슈 생성 시각'),
        ]
        for status, errors, expected in cases:
            with self.subTest(status=status):
                body = visible({'status': status, 'errors': errors, 'delivery_allowed': False})
                self.assertIn(expected, body)
                self.assertNotIn('제안자는 아래', body)
                self.assertNotIn('/pilot-', body)
                self.assertNotIn('—', body)
        inactive = visible({'status': cases[0][0], 'errors': cases[0][1]})
        self.assertIn('운영 담당자가 확인할 활성화 조건', inactive)

    def test_missing_information_and_decision_wait_have_different_next_actions(self):
        missing = visible({'status': '필수 정보 보완 대기', 'errors': ['사용자 문제: 필수 정보 누락']})
        self.assertIn('제안자는 아래 확인 항목', missing)
        self.assertIn('유효 접수 시각과 첫 결정 기한이 표시되는지', missing)
        waiting = {'status': '첫 결정 대기', 'delivery_allowed': True, 'errors': ['결정권자 Routing 대기']}
        self.assertIn('부총괄은 운영 가이드의 담당자 지정', visible(waiting))
        waiting['route'] = {'assignee': 'fixture-primary', 'key': 'brand-and-growth', 'slot': 'primary'}
        waiting['errors'] = ['확정된 결정권자의 First decision 댓글이 없습니다.']
        self.assertIn('결정권자는 운영 가이드의 첫 결정', visible(waiting))
        self.assertNotIn('제안자는 아래', visible(waiting))
        waiting['errors'] = ['지명된 Proposal DRI의 해당 결정 수락이 없습니다.']
        body = visible(waiting)
        self.assertIn('지명된 실행 담당자와 결정권자는 운영 가이드의 첫 결정과 실행 책임', body)
        self.assertIn('링크를 반영한 뒤, 실행 담당자는 기존 수락 댓글에 확인 문장을 추가해 다시 수락', body)
        self.assertIn('수락 명령과 댓글 URL은 유지', body)

    def test_completion_and_reconfirmation_preserve_the_first_measurement(self):
        state = {
            'status': '유효한 첫 결정: Parked', 'first_decision_at': '2026-09-15T01:00:00Z',
            'current_decision': {'decision': 'Parked'},
            'route': {'assignee': 'fixture-backup', 'key': 'brand-and-growth', 'slot': 'backup'},
            'delivery_allowed': True,
        }
        body = visible(state)
        self.assertIn('첫 결정 기록 완료: 보류 (`Parked`)', body)
        self.assertIn('결정 댓글에 지정된 담당자는 다음 행동', body)
        self.assertIn('@fixture-backup (대체 담당)', body)
        state.update(status='결정 기록 재확인 필요', current_decision=None,
                     errors=['사용자 문제: 필수 정보 누락'], delivery_allowed=False)
        body = visible(state)
        self.assertIn('제안자는 아래 본문 입력 오류를 보완', body)
        self.assertIn('최초 결정 완료 시각은 보존됩니다.', body)
        self.assertIn('2026-09-15 10:00:00 KST', body)

    def test_delivery_history_distinguishes_receipt_uncertainty_and_current_pause(self):
        state = {
            'status': '첫 결정 대기', 'delivery_allowed': True,
            'deliveries': {'new': {'status': 'sent'}, 'due': {'status': 'cancelled'},
                           'escalation': {'status': 'uncertain'}},
        }
        body = visible(state)
        self.assertIn('신규 접수: 전송 완료', body)
        self.assertIn('결정 기한 경과 안내: 수신 여부 확인 필요', body)
        self.assertIn('Discord 채널에서 수신 여부를 확인', body)
        state.update(status='비활성 — 실제 접수·기한·알림 없음', delivery_allowed=False)
        body = visible(state)
        self.assertIn('현재 알림 전송이 보류', body)
        self.assertNotIn('재전송이 필요하면', body)


if __name__ == '__main__':
    unittest.main()
