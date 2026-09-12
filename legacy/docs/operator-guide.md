# 파일럿 운영 가이드

부총괄인 파일럿 운영 담당자와 각 제안의 결정권자가 읽는 문서입니다. 준비·활성화, 결정권자 지정, 첫 결정 기록, 접수 종료와 인계의 순서로 사용합니다. 제안자는 [제출 안내](../START-HERE.md)를 먼저 읽으세요.

<a id="activate"></a>
## 1. 역할과 시작 조건 준비하기

참여자와 역할은 당사자의 합의로 확정합니다. 계정 초대·권한 준비·사전 합의에 걸리는 시간은 준비 후 진행하는 15분 활성화 검토에 포함하지 않습니다.

| 역할 | 하는 일 | 저장소 / Project 권한 |
|---|---|---|
| 일반 참가자 | 제안을 제출하고 보완·결정을 확인합니다. | Read / Read |
| 결정권자(Primary) | 배정된 제안의 첫 결정을 작성합니다. | Triage / Write |
| 대체 결정권자(Backup) | 인계받은 제안의 결정을 대신 맡습니다. | Triage / Write |
| 파일럿 운영 담당자(Pilot DRI, 부총괄) | 시작·수동 분류·권한·운영 부담·인계를 관리합니다. | Admin / Admin |

Proposal DRI는 특정 제안의 실행을 맡기로 수락한 사람입니다. 파일럿 전체를 운영하는 Pilot DRI와 구분합니다. 분류 경로인 Route는 제안을 어느 목적팀의 결정권자에게 연결할지 나타내는 설정입니다.

1. [이번 활성화 이슈](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)에 참가자·역할·주간 운영 허용시간을 합의한 근거를 기록합니다. 체크리스트 파일은 [재사용 양식](activation-checklist.md)이고, 이번 준비의 실제 완료 기록은 이슈에 남깁니다.
2. [설정 파일](../config/pilot-settings.yml)에 참가자, 사용할 Route, 역할별 계정, 기간, 휴무일, 운영 허용시간을 반영합니다. 사용할 Route만 `enabled_routes`에 넣고 모든 역할 담당자를 `participants`에도 포함합니다. 같은 Route의 Primary와 Backup은 서로 다른 사람이어야 합니다.
3. [Project 설정 절차](project-setup.md)를 수행하고, 실제 계정별 저장소·Project·Discord 접근권한을 확인합니다. 비참가자의 접근 차단과 관리자 예외도 기록합니다.

완료 확인: 활성화 이슈에 합의와 권한 확인의 수행자·날짜·근거 링크가 있고, 설정의 실제 계정과 일치해야 합니다. 담당자나 접근권한이 준비되지 않았다면 `PILOT_ACTIVE=false`를 유지하고 남은 준비와 다음 확인일을 기록합니다.

## 2. 역할 수락과 설정 승인 기록하기

각 담당자가 **활성화 이슈에 직접** 자기 역할의 수락 댓글을 작성합니다. 다음은 역할별 예시입니다. 한 사람이 여러 역할을 합의해 맡으면 같은 댓글에 해당 명령을 한 줄씩 적을 수 있습니다.

```text
/pilot-accept pilot_owner
```

```text
/pilot-accept brand-and-growth.primary
```

```text
/pilot-accept brand-and-growth.backup
```

댓글 링크가 `#issuecomment-123456`으로 끝나면 `123456`이 댓글 ID입니다. 설정을 편집하는 담당자는 각 댓글 ID를 `role_acceptances`의 해당 역할에 넣습니다. 다른 사람이 대신 작성한 수락과 다른 이슈의 댓글은 인정하지 않습니다.

운영 설정을 준비한 뒤 다음 순서로 승인합니다.

1. 설정 변경을 `main`에 반영합니다. Actions의 `Pilot checks` 실행에서 `python -m pilot.runner check-config` 단계 로그를 엽니다.
2. 로그의 `Config approval fingerprint` 뒤에 나오는 16자리 값을 확인합니다. 이 값은 승인할 설정을 구별하는 식별값입니다.
3. 부총괄이 활성화 이슈에 아래 명령을 작성합니다. `<fingerprint>` 전체를 방금 확인한 값으로 바꾸세요.
4. 해당 승인 댓글 ID를 설정의 `activation_approval`에 넣고 `main`에 반영합니다.

```text
/pilot-activate <fingerprint>
```

`activation_approval`과 `role_acceptances`의 댓글 ID만 채우면 식별값은 바뀌지 않습니다. 참가자·기간·운영 규칙 등 다른 설정이 바뀌면 부총괄이 변경을 검토하고 새 승인 댓글을 남겨야 합니다.

완료 확인: 승인 댓글의 작성자가 설정의 `pilot_owner`이고, 명령의 식별값이 현재 설정과 일치해야 합니다. **`check-config`는 실제 댓글을 조회하지 않습니다.** 따라서 이 로그에 역할 수락·활성화 승인 누락이 표시될 수 있으며, 실행 성공도 실제 수락 검증을 뜻하지 않습니다. 실제 댓글까지 포함한 판정은 다음 단계에서 확인합니다.

<a id="ready-check"></a>
## 3. 활성화하고 실제 접수 상태 확인하기

부총괄이 설정과 수락을 검토하고, 활성화 이슈의 Project·권한·Form·알림 준비 항목을 확인한 뒤 수행합니다. `activation_date`는 영업일이며, 접수 마감은 그날부터 10영업일째 23:59 KST입니다.

1. 저장소 Settings → Secrets and variables → Actions → Variables에서 `PILOT_ACTIVE`를 `true`로 바꿉니다. `AUTO_ROUTING_ENABLED=false`는 유지합니다.
2. Actions에서 `Proposal Intake · Decision Record · Reminder`를 수동 실행합니다. `records` 작업의 `python -m pilot.runner reconcile` 로그를 확인합니다.
3. 각 Issue의 **제안 운영 기록**에서 실제 상태와 필요한 조치를 확인합니다. 설정 또는 수락이 빠지면 실행이 성공해도 비활성 상태와 사유가 기록됩니다.
4. 합의된 시작 이후 참가자가 제출한 유효한 제안에서 유효 접수 시각과 첫 결정 기한이 기록되는지 확인합니다. 최초 승인 전 생성한 이슈와 `pilot:scenario` 이슈는 이 확인을 대신할 수 없습니다.
5. 활성화 이슈에 판단자·판단일·접수 기간·확인 근거를 남깁니다. 접수 시작 안내를 문서에 반영할 때 README와 START-HERE의 접수 전 안내도 함께 갱신합니다.

완료 확인은 두 단계입니다. 변수·설정·본인 승인 확인을 마치면 시작 안내를 할 수 있고, 이후 실제 접수 동작은 시작 후 유효 제안의 기록으로 확인합니다. 아직 실제 제안이 없다면 “시작 설정 완료, 실제 접수 미확인”으로 구분해 기록합니다. 준비가 빠졌다면 변수를 `false`로 되돌리고 보류 이유와 다음 확인일을 남깁니다.

<a id="route"></a>
## 4. 제안에 결정권자 지정하기

부총괄은 유효 접수된 제안을 검토하고 해당 Issue에 명령과 분류 이유를 적습니다. 다음 예시의 `brand-and-growth`는 실제로 합의해 활성화한 Route로 바꿉니다.

```text
/pilot-route brand-and-growth primary

분류 이유: 모집 진입 과정의 문제라 Brand & Growth로 연결합니다.
```

허용 Route는 `brand-and-growth`, `learning-and-activity`, `community-and-connection`, `operations-enablement`, `design-platform` 중 활성화한 항목입니다. Design System 제안은 `design-platform`만 사용합니다. Backup에게 인계할 때는 `primary` 대신 `backup`을 적습니다.

완료 확인: 워크플로 처리 후 Issue의 Assignee 한 명과 운영 기록의 결정권자가 선택한 계정과 일치하는지 확인합니다. 시스템은 부총괄의 수동 명령에 따라 지정하며, 표나 양식의 선택값만으로 자동 분류하지 않습니다.

재지정은 기존 댓글을 지우지 말고 새 댓글로 남깁니다. Assignee를 직접 바꿨다면 확정된 Route와 일치시켜야 결정을 인정합니다. 반영되지 않았다면 Issue 운영 기록의 사유와 워크플로 실행 로그를 확인합니다.

<a id="decision"></a>
## 5. 첫 결정과 실행 책임 기록하기

배정된 결정권자가 같은 Issue에 아래 양식으로 댓글을 작성합니다. 영문 필드명은 자동 검증에 쓰이므로 그대로 사용하고, 예시 값과 계정·링크를 실제 내용으로 바꿉니다.

```markdown
## First decision
- Decision: Active
- Reason: 확인한 근거에 따라 작은 검증을 진행하기로 함
- Proposal DRI: @담당계정
- Acceptance: https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/번호#issuecomment-수락댓글ID
- Next action: @담당계정 검증 범위를 정리하고 기존 팀 Backlog에 연결
- Reconsideration condition/date: 결과 확인일과 재검토 조건
```

결정권자는 `decision:active`처럼 Decision과 일치하는 결정 Label 하나를 남깁니다. 이전 결정 Label은 제거합니다. `decision:pending`은 워크플로가 관리합니다.

| 결정 | 반드시 기록할 내용 |
|---|---|
| `Validating`·`Active` | 실행할 Proposal DRI, 해당 결정에 대한 본인 수락, 다음 행동 |
| `Parked` | 보류 이유, 재검토 조건·날짜, 그때까지 할 다음 행동 |
| `Rejected` | 종료 이유, 제안자에게 돌아갈 안내와 다음 행동 |

다른 사람을 Proposal DRI로 제안했다면 그 사람이 결정 범위를 확인하고 같은 Issue에 다음 댓글을 남깁니다. 숫자는 **수락할 First decision 댓글의 ID**로 바꾸세요.

```text
/pilot-accept-decision 123456
```

결정권자는 이 수락 댓글의 URL을 결정 양식의 `Acceptance`에 넣습니다. 링크를 넣는 것도 결정 댓글의 수정에 해당합니다. 실행 담당자는 반영된 결정 내용을 확인한 뒤 **기존 수락 댓글을 수정해 확인 문장을 덧붙입니다.** `/pilot-accept-decision` 명령은 그대로 남겨 두세요. 기존 댓글을 수정하면 수락 URL을 바꾸지 않고 결정의 최종 수정 이후에 수락했다는 기록을 남길 수 있습니다.

수락은 해당 결정에만 적용되며, 결정 댓글을 다시 수정하면 그 이후의 본인 수락이 필요합니다. 결정권자가 직접 Proposal DRI를 맡으면 `Acceptance: Self accepted`로 적을 수 있습니다.

실행 담당자가 없는 `Parked`·`Rejected`는 `Proposal DRI: None (실행 보류)`, `Acceptance: N/A (실행 책임 없음)`처럼 이유를 적을 수 있습니다. 이때 Next action에는 결정권자 계정을 씁니다. Next action 담당자는 현재 결정권자 또는 수락한 Proposal DRI로 제한합니다. 다른 협업자의 실행 책임은 기존 팀 작업 목록에서 별도로 합의합니다.

완료 확인: Issue 운영 기록이 `첫 결정 기록 완료: ...`로 표시되고 최초 결정 시각이 생기는지 확인합니다. 수락·라벨·담당자가 맞지 않으면 표시된 사유를 확인합니다. 이후 기록이 수정·삭제되어 재확인이 필요해져도 과거 최초 결정 시각은 보존됩니다. 책임이나 범위가 바뀌었다면 부총괄이 확인한 뒤 새 First decision 댓글과 새 수락을 받습니다.

## 6. 기한과 운영 부담 기록하기

첫 결정 기한은 유효 접수를 처음 확인한 KST 날짜 다음부터 기본 3영업일째 23:59입니다. 주말과 설정한 휴무일을 제외합니다. 필수 정보 보완 대기는 별도로 보고하며, 최초 기한을 임의로 연장해 기한 준수 성적을 바꾸지 않습니다.

예외 기한은 같은 Issue에 이유·합의자·새 날짜를 댓글로 남깁니다. 기본 알림과 측정은 최초 기한을 유지합니다. Project의 종류·목적팀·기한·상태는 Issue에서 복사하고, 불일치는 다음 영업일까지 정리합니다. Project의 날짜를 수정해도 실제 알림 기한은 바뀌지 않습니다.

부총괄은 각 제안을 처리한 뒤 같은 Issue에 운영 메모를 남깁니다.

```markdown
## 운영 메모
- 처리시간(분):
- 담당자 재탐색 횟수와 이유:
- 제안자의 다음 행동 확인: 확인됨 | 불명확 | 무응답
- 규칙 판단: 유지 | 변경
- 판단 이유:
- 후속 업무·인계 링크:
```

회고에서는 유효 표본 수, 최초 담당자 연결·기한 준수의 성공 건수/전체 건수, 보완 대기, 결정 분포, 처리시간, 다음 행동 이해, 총괄 개입을 함께 봅니다. 규칙은 유지해도 되며 판단 이유를 남깁니다. 표본이 부족하면 판단을 유보하고, 자동 분류를 사용하지 않았다는 이유로 실패로 평가하지 않습니다.

<a id="notifications"></a>
## 7. 알림 실패 확인하기

알림 작업은 GitHub의 기록 처리와 별개입니다. 댓글에 “전송 시도 기록됨, 수신 확인 필요” 또는 “수신 여부 확인 필요”가 표시되면 부총괄이 Discord에서 실제 메시지가 왔는지 먼저 확인합니다. **전송되지 않았음을 확인한 경우에만** 같은 Issue에 다음 명령을 적습니다.

```text
/pilot-retry-notification new
```

대상 이벤트는 `new`(신규 접수), `decision`(결정), `due`(기한 당일), `escalation`(기한 경과) 중 하나입니다. 완료 확인은 해당 Discord 메시지와 Issue의 전송 기록을 함께 봅니다. 이미 전송됐다면 재시도하지 말고 Discord 메시지 링크를 운영 메모에 남깁니다. 전송 여부가 불명확한 상태에서 자동 재전송하지 않습니다.

<a id="close"></a>
## 8. 접수 마감·비상 중단·인계하기

접수 마감은 설정한 시각에 자동 적용됩니다. 마감 때 이미 유효했던 제안은 마지막 최초 결정 기한까지 처리하고, 미완성 제안은 별도로 인계합니다. **이 관찰이 끝나기 전에는 `PILOT_ACTIVE=false`로 바꾸지 않습니다.** 접수 마감과 전체 운영 종료는 서로 다른 시점입니다.

비상 중단이 필요하면 부총괄이 `PILOT_ACTIVE=false`로 바꾸고 실행 중인 Pilot 워크플로도 취소합니다. 이미 보낸 알림은 되돌리지 않습니다. 중단 사유·미결정 제안·다음 확인일을 활성화 이슈에 남깁니다.

관찰을 마치면 미결정·Parked 재검토·후속 업무마다 인수자의 수락과 기존 팀 작업 목록 링크를 확인합니다. 인계 완료 후 알림을 중지하고 Webhook 폐기 → Project Auto-add 중지·종료 → 저장소 Archive 순서로 마칩니다.

완료 확인: 활성화 이슈에서 모든 미완료 건의 인수자 수락과 목적지 링크를 확인할 수 있어야 합니다. 인계되지 않은 건이 있으면 아카이브를 보류합니다. 총괄에게는 권한·보안·팀 간 충돌·결정권자 공백처럼 부총괄이 해결할 수 없는 예외를 요청합니다.
