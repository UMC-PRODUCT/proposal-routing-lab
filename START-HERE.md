# 시작·운영 안내

**아직 실제 접수하지 않습니다.** 부총괄이 수락한 뒤 `PILOT_ACTIVE=true`로 시작합니다. 자동 Routing은 첫 범위에 없고 `AUTO_ROUTING_ENABLED=false`를 유지합니다.

## 시작 전 준비

참여자·결정권자·Backup의 합의와 권한 준비 시간은 15분 활성화 검토에 포함하지 않습니다. 일반 참가자에게 저장소·Project Read, 결정권자·Backup에게 저장소 Triage·Project Write, 부총괄에게 파일럿 저장소·Project Admin을 부여합니다. 실제 계정별 권한 테스트와 Discord 비공개 채널 접근 확인을 마칩니다.

## 준비된 설정을 15분 안에 검토하기

1. [활성화 체크리스트](docs/activation-checklist.md)를 열고 해당 Issue를 확인합니다. [설정](config/pilot-settings.yml)의 참가자·사용할 Route·역할·기간·휴무일·운영 허용시간을 확정합니다.
2. 활성화 Issue에 각 담당자가 `/pilot-accept pilot_owner`, `/pilot-accept brand-and-growth.primary` 같은 자기 역할 수락 댓글을 남깁니다. 댓글 ID를 설정의 `role_acceptances`에 넣습니다. [명령과 작성 예시](docs/operator-guide.md)
3. 설정 변경 후 Actions의 `Pilot checks` 실행에서 `check-config`의 **Config approval fingerprint**를 확인합니다. 부총괄이 활성화 Issue에 `/pilot-activate <fingerprint>`를 남기고 그 댓글 ID를 `activation_approval`에 넣습니다.
4. [Project 설정](docs/project-setup.md), Discord 연결, 실제 계정 권한 테스트의 미완료 항목이 없음을 확인한 뒤 Variables의 `PILOT_ACTIVE`만 `true`로 바꿉니다. 설정이나 수락이 빠졌으면 Workflow는 계속 비활성으로 처리합니다.
5. Actions에서 `Proposal Intake · Decision Record · Reminder`를 수동 실행해 gate 오류가 없는지 확인합니다. 준비가 덜 됐다면 변수를 `false`로 두고 보류 이유·다음 확인일을 적습니다.

`activation_date`는 영업일로 지정하고 접수 마감은 그날부터 10영업일째 23:59 KST입니다. 최초 활성화 승인 이후에 생성된 Proposal만 실제 접수 대상입니다. 운영 설정이 바뀌면 fingerprint도 바뀌므로 부총괄이 변경을 검토하고 새 활성화 승인 댓글을 연결합니다.

## 매일 하는 일

- 새 Proposal에서 부총괄이 `/pilot-route <route> primary`로 결정권자를 선택합니다. Workflow는 이 **수동 결정**에 따라 Assignee 한 명을 설정합니다. 표를 보고 자동 분류하지 않습니다.
- 결정권자가 [첫 결정 양식](docs/operator-guide.md)을 작성하고 같은 결정 Label 하나를 붙입니다. 실행 책임을 맡는 사람은 해당 결정에 수락 댓글을 남깁니다.
- Project의 종류·Purpose·기한은 Issue 기록에서 복사하고, 현재 결정 상태도 맞춥니다. 불일치는 다음 영업일까지 정리합니다.
- 건당 처리시간·담당자 재탐색·제안자의 다음 행동 이해 여부를 [운영 메모](docs/operator-guide.md)에 기록합니다. 규칙은 유지해도 됩니다. 판단 이유를 남깁니다.

## 접수 마감·중단·인계

접수 마감은 설정한 시각에 자동 적용됩니다. **관찰이 끝나기 전에는 `PILOT_ACTIVE=false`로 바꾸지 않습니다.** 마감 때 이미 유효했던 건은 마지막 최초 결정 기한까지 처리하고, 미완성 건은 별도 인계합니다.

비상시에는 `PILOT_ACTIVE=false`로 바꾸고 실행 중인 Pilot Workflow도 취소합니다. 이미 전송된 알림은 되돌리지 않습니다. 미결정·재검토·후속 업무의 담당자 수락과 기존 팀 Backlog 링크를 확인한 뒤 Webhook 폐기 → Project Auto-add 중지·종료 → 저장소 Archive 순서로 마칩니다.

재원에게는 권한·보안·팀 간 충돌·결정권자 공백처럼 부총괄이 해결할 수 없는 예외만 요청합니다. 인계되지 않은 건이 있으면 아카이브를 보류합니다.
