# 구축 및 검증 기록

상태: 구축 진행 중. 아래 미확인 항목은 활성화 전까지 완료해야 합니다.

## 완료한 준비

- 2026-09-12: GitHub 조직 기본 저장소 접근권한 `none`, Free 플랜 확인.
- 2026-09-12: 파일럿 저장소 미존재 확인 후 신규 구축 착수.
- 2026-09-12: CLI에 `read:project` 범위가 없고 Codex 브라우저가 로그아웃 상태임을 확인. Project 설정은 로그인 또는 CLI Project 권한이 필요함.
- 2026-09-12: Private 저장소, `PILOT_ACTIVE=false`·`AUTO_ROUTING_ENABLED=false`, Label 19개, [활성화 Issue #1](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)을 생성했다.
- 2026-09-12: [비공개 Discord 준비 채널](https://discord.com/channels/1442030160311484416/1548251856549974136)을 만들었다. 일반 구성원의 View 권한을 차단하고 관리자 예외·봇만 접근하도록 구성했다. 실제 참가자에게는 아직 권한을 부여하지 않았다.

## 검증 결과

- 로컬 Python 3.9에서 단위·어댑터 테스트 28개 통과. 비활성 gate, 수락 작성자·수정 시각, 수동 Routing, 휴무일·접수 종료, 위조 상태, 중복·불명확 전송·Webhook 실패 격리, Form·Workflow YAML 및 문서 링크를 확인했다.
- GitHub Actions(Python 3.12)와 실제 리소스 검증은 배포 후 결과를 추가한다.

## 활성화 전에 남겨 둘 항목

- Pilot DRI·참가자·결정권자·Backup의 인명 확정과 본인 수락.
- 합의된 실제 계정으로 Read·Triage·Admin, Project·Discord 접근권한 비교.
- Project 필드·View·Auto-add의 실제 화면·새 제출 결과 확인.
- 실제 Form 렌더링과 생성된 Markdown Fixture 확인.
- 실제 Discord 알림 전송·오류·중복의 운영 검증은 활성화 전송 허용 이후 수행. 비활성 환경에서는 실제 제안 알림을 보내지 않음.

환경 준비와 운영 인계·파일럿 효과 검증은 별개의 상태입니다. 계획의 합격 기준을 구현 결과로 간주하지 않습니다.
