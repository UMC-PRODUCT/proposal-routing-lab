# Project 만들고 운영에 사용하기

파일럿 운영 담당자가 GitHub Organization Project를 준비할 때 사용하는 문서입니다. 제안별 결정·기한의 기준은 Issue이며, Project는 여러 제안을 모아 확인하는 화면입니다. 이 문서는 설정 절차를 설명하며 실제 완료 여부는 [활성화 이슈](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)에 기록합니다.

## 준비 조건

Project를 만들고 권한·자동 등록을 설정할 수 있는 계정으로 로그인합니다. 저장소와 Project의 비공개 설정 및 접근권한은 각각 확인해야 합니다. CLI의 저장소 접근 성공만으로 Organization Project 권한까지 확인한 것은 아닙니다.

## 필드 만들기

Private Organization Project `Proposal Routing Pilot · 2026-09`를 만듭니다. 실제 시작 월이 달라지면 이름도 맞춥니다.

| 필드 | 값 | 기록 방법 |
|---|---|---|
| Status | Proposed, Reviewing, Validating, Active, Parked, Rejected | 검토 중인 단계와 Issue의 현재 결정을 맞춥니다. |
| Proposal Type | Product, Design System | Issue의 제안 종류를 복사합니다. |
| Purpose | Brand & Growth, Learning & Activity, Community & Connection, Operations Enablement, Design Platform, Unknown | 확정한 분류 경로의 목적팀을 표시합니다. 아직 연결하지 않았다면 Unknown입니다. |
| Decision Due | Date | Issue에 기록된 첫 결정 기한의 한국 날짜를 복사합니다. 정확한 시각은 Issue에서 확인합니다. |
| Assignees / Labels | 기본 필드 표시 | Issue의 담당자와 보완·결정 라벨을 함께 확인합니다. |

완료 확인: 필드별 형식과 선택값이 표와 일치하고, 예시 Issue를 추가했을 때 값을 입력할 수 있어야 합니다.

## 확인할 일에 따라 보기 만들기

| View | 설정 | 언제 무엇을 확인하나요? |
|---|---|---|
| Intake | Table, Proposed·Reviewing, Decision Due 오름차순 | 새 제안을 검토하고 기한이 가까운 건부터 확인합니다. |
| Decision Board | Board, Status별 그룹 | 현재 검토·진행·보류·종료 상태를 비교합니다. |
| Routing Gaps | `needs:routing` 또는 Assignee 없음 | 부총괄이 아직 결정권자를 연결하지 못한 제안을 찾습니다. |
| Overdue | Decision Due가 오늘 전이며 Proposed·Reviewing | 첫 결정 기한을 넘긴 제안의 사유와 필요한 다음 행동을 확인합니다. |

Routing Gaps의 OR 조건을 UI에서 표현할 수 없다면 라벨 기준과 담당자 없음 기준의 보기를 각각 만듭니다. 이 경우 기본 네 목적 중 하나를 두 보기로 확인하게 됩니다. 필터 이름만 만들지 말고 조건에 해당하는 예시 Issue가 실제로 표시되는지 확인하세요.

## 자동 등록과 기본 상태 설정하기

1. Project의 `Auto-add to project`에서 이 저장소의 `is:issue label:proposal`을 등록 대상으로 설정합니다.
2. `Item added to project`에서 Status를 `Proposed`로 설정합니다.
3. 실제 Read 참가자 계정으로 양식을 제출했을 때 Issue가 등록되고 기본 상태가 설정되는지 확인합니다. Form에 `projects` 키를 추가하지 않습니다.
4. 기존 시나리오는 Auto-add 활성화만으로 소급 등록되지 않으므로 수동 추가하거나 Issue를 수정해 등록 여부를 확인합니다. 테스트용 표시는 보존하고 실제 운영 표본과 구분합니다.

완료 확인: 새 제출이 목록에 보이며 `Proposed`로 시작해야 합니다. 자동 등록은 종류·Purpose·기한·이후 결정 상태를 모두 동기화하는 기능이 아닙니다. 이 값은 운영 담당자가 Issue 기록에 맞춰 갱신합니다.

## 실제 계정으로 권한 확인하기

일반 참가자는 Project Read, 결정권자·Backup은 Write, 부총괄은 Admin으로 설정합니다. 조직 기본 접근권한은 None으로 확인하고 관리자 예외를 기록합니다. 권한은 합의한 명단에만 부여합니다.

각 계정으로 읽기·수정 가능 범위를 확인한 뒤 수행자·확인일·근거를 활성화 이슈에 남깁니다. 저장소 접근과 Discord 채널 접근도 [운영 준비 절차](operator-guide.md#activate)에서 함께 확인합니다.

## 운영 중 값이 다르면

해당 Issue의 제안 운영 기록과 결정 댓글을 확인하고, Project 값을 다음 영업일까지 맞춥니다. Project에서 날짜를 수정해도 실제 알림 기한은 바뀌지 않습니다. 워크플로는 Organization Project API나 개인 Project 토큰을 사용하지 않습니다.
