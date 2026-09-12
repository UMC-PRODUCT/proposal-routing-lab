# Organization Project 설정

Private Organization Project `Proposal Routing Pilot · 2026-09`를 만듭니다. 시작 월이 바뀌면 이름도 맞춥니다. 저장소의 Private 설정과 Project 접근권한은 별개입니다.

| 필드 | 값 |
|---|---|
| Status | Proposed, Reviewing, Validating, Active, Parked, Rejected |
| Proposal Type | Product, Design System |
| Purpose | Brand & Growth, Learning & Activity, Community & Connection, Operations Enablement, Design Platform, Unknown |
| Decision Due | Date |
| Assignees / Labels | 기본 필드 표시 |

| View | 표시와 필터 |
|---|---|
| Intake | Table, Proposed·Reviewing, Decision Due 오름차순 |
| Decision Board | Board, Status별 그룹 |
| Routing Gaps | `needs:routing` 또는 Assignee 없음인 건. UI가 OR 필터를 지원하지 않으면 두 보기를 따로 만들어 누락 없이 확인 |
| Overdue | Decision Due가 오늘 전이며 Proposed·Reviewing인 건 |

기본 Workflow:

1. `Auto-add to project`: 이 저장소의 `is:issue label:proposal`을 자동 등록.
2. `Item added to project`: Status를 `Proposed`로 설정.
3. Form에 `projects` 키를 추가하지 않음. Read 참가자가 제출해도 자동 등록되는지 확인.
4. 기존 시나리오는 Auto-add 활성화만으로 소급 등록되지 않으므로 수동 추가하거나 Issue를 수정해 등록 확인.

일반 참가자 Project Read, 결정권자·Backup Write, 부총괄 Admin으로 설정합니다. 조직 기본 접근권한은 None으로 확인하고 관리자 예외를 기록합니다. 사람별 권한은 활성화 전 합의된 명단으로만 부여합니다.

기한·결정은 Issue 기록에서 복사합니다. Project 수정은 실제 알림 기한을 바꾸지 않습니다. Workflow는 Organization Project API나 개인 Project 토큰을 사용하지 않습니다.
