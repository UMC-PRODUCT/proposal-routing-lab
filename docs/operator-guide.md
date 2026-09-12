# Routing·결정·운영 메모

## 활성화 설정과 수락

활성화 Issue의 `#issuecomment-123456` URL에서 숫자 부분이 댓글 ID입니다. 역할 수락과 활성화 승인은 반드시 그 Issue의 댓글이어야 합니다. 타인이 대신 쓰면 인정하지 않습니다.

```text
/pilot-accept pilot_owner
```

```text
/pilot-accept brand-and-growth.primary
```

```text
/pilot-accept brand-and-growth.backup
```

한 사람이 여러 역할을 합의해 맡으면 같은 댓글에 각 명령을 한 줄씩 적어도 됩니다. 같은 Route의 Primary와 Backup은 서로 달라야 합니다. 설정에는 실제 사용할 Route만 `enabled_routes`에 넣습니다. 역할 담당자는 `participants`에도 포함합니다.

부총괄의 활성화 승인:

```text
/pilot-activate <Pilot checks에서 확인한 16자리 fingerprint>
```

`activation_approval`·`role_acceptances`의 댓글 ID를 채우는 동작 자체는 fingerprint를 바꾸지 않습니다. 참가자·기간·운영 규칙 등 다른 설정이 바뀌면 새 승인 댓글이 필요합니다.

## 수동 Routing

부총괄이 해당 Proposal에 명령 한 줄과 분류 이유를 적습니다.

```text
/pilot-route brand-and-growth primary

분류 이유: 모집 진입 과정의 문제라 Brand & Growth로 연결합니다.
```

허용 Route는 `brand-and-growth`, `learning-and-activity`, `community-and-connection`, `operations-enablement`, `design-platform` 중 활성화된 항목입니다. Design System Proposal은 `design-platform`만 사용합니다. Backup에게 인계할 때는 `primary` 대신 `backup`을 적습니다. **재지정은 기존 댓글을 지우지 말고 새 댓글**로 남깁니다. Assignee를 직접 바꿨다면 확정된 Route와 일치시켜야 결정을 인정합니다.

## 첫 결정

```markdown
## First decision
- Decision: Active
- Reason: 확인한 근거에 따라 작은 검증을 진행하기로 함
- Proposal DRI: @담당계정
- Acceptance: https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/번호#issuecomment-수락댓글ID
- Next action: @담당계정 검증 범위를 정리하고 기존 팀 Backlog에 연결
- Reconsideration condition/date: 결과 확인일과 재검토 조건
```

결정권자가 직접 작성하고 `decision:active`처럼 Decision에 맞는 Label 하나만 남깁니다. 이전 결정 Label은 제거합니다. `decision:pending`은 Workflow가 관리합니다.

다른 사람을 Proposal DRI로 지명하면 그 사람이 같은 Issue에 다음 댓글을 남깁니다. 숫자는 **First decision 댓글의 ID**입니다.

```text
/pilot-accept-decision 123456
```

수락은 해당 결정에만 적용됩니다. 결정권자가 직접 Proposal DRI를 맡으면 `Acceptance: Self accepted`로 명시할 수 있습니다. 명령·양식 안의 예시 계정은 실제 계정으로 치환해야 합니다.

- `Validating`·`Active`: 실행할 Proposal DRI와 본인 수락 필수.
- `Parked`: 재검토 조건·날짜 필수. 실행 담당자를 만들지 않으면 `Proposal DRI: None (실행 보류)`, `Acceptance: N/A (실행 책임 없음)`으로 적고 Next action에는 결정권자 계정을 씁니다.
- `Rejected`: 종료 이유와 제안자에게 돌아갈 안내를 적습니다. 실행 담당자가 없으면 위와 같이 None을 사용할 수 있습니다.
- Next action 담당자는 현재 결정권자 또는 수락한 Proposal DRI로 제한합니다. 추가 협업자의 실행 책임은 기존 팀 Backlog에서 별도 합의합니다.

계약이 완성된 최초 시각을 기록하고, 이후 수정·삭제로 기록이 깨지면 재확인 Label을 붙입니다. 과거의 최초 결정 측정값은 보존합니다. 부총괄이 수정으로 책임·범위가 바뀌었는지 확인하고 필요하면 **새 First decision 댓글과 새로운 수락**을 받습니다.

## 기한과 예외

유효 접수를 처음 확인한 KST 날짜 다음부터 3영업일째 23:59가 최초 기한입니다. 보완 대기는 별도 보고합니다. 최초 기한을 임의로 연장해 SLA 성적을 바꾸지 않습니다. 예외 기한은 Issue에 이유·합의자·새 날짜를 댓글로 남기되 기본 알림과 측정은 최초 기한을 유지합니다.

## 운영 메모

```markdown
## 운영 메모
- 처리시간(분):
- 담당자 재탐색 횟수와 이유:
- 제안자의 다음 행동 확인: 확인됨 | 불명확 | 무응답
- 규칙 판단: 유지 | 변경
- 판단 이유:
- 후속 업무·인계 링크:
```

회고에서는 유효 표본 수, 최초 Routing·기한 준수의 성공 건수/전체 건수, 보완 대기, 결정 분포, 처리시간, 다음 행동 이해, 재원 개입을 함께 봅니다. 표본 부족은 판단 유보이며 자동 Routing을 하지 않았다고 실패로 보지 않습니다.

## 알림 실패·불명확 전송

알림 Job은 GitHub 기록 처리와 별개입니다. 상태가 `sending`·`uncertain`이면 Discord에서 실제 메시지가 왔는지 먼저 확인합니다. **전송되지 않았음을 확인한 경우에만** 부총괄이 같은 Issue에 다음 명령을 적습니다.

```text
/pilot-retry-notification new
```

이벤트는 `new`, `decision`, `due`, `escalation` 중 하나입니다. 자동 재전송하지 않으므로 불명확 전송을 중복 메시지로 바꾸지 않습니다. 이미 전송됐으면 재시도하지 말고 해당 Discord 메시지 링크를 운영 메모에 남깁니다.
