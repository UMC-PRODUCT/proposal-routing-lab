# 구축 및 검증 기록

상태: **저장소·Workflow·Discord 비활성 구축 완료, Project·브라우저 검증은 로그인 대기.** 아래 미확인 항목은 활성화 전까지 완료해야 합니다.

## 완료한 준비

- 2026-09-12: GitHub 조직 기본 저장소 접근권한 `none`, Free 플랜 확인.
- 2026-09-12: 파일럿 저장소 미존재 확인 후 신규 구축 착수.
- 2026-09-12: CLI에 `read:project` 범위가 없고 Codex 브라우저가 로그아웃 상태임을 확인. Project 설정은 로그인 또는 CLI Project 권한이 필요함.
- 2026-09-12: Private 저장소, `PILOT_ACTIVE=false`·`AUTO_ROUTING_ENABLED=false`, Label 19개, [활성화 Issue #1](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)을 생성했다.
- 2026-09-12: [비공개 Discord 준비 채널](https://discord.com/channels/1442030160311484416/1548251856549974136)을 만들었다. 일반 구성원의 View 권한을 차단하고 관리자 예외·봇만 접근하도록 구성했다. 실제 참가자에게는 아직 권한을 부여하지 않았다.
- 2026-09-12: 준비 안내를 고정하고 Webhook을 저장소 Secret `DISCORD_PROPOSAL_PILOT_WEBHOOK`에 직접 등록했다. 자격증명은 로컬 파일·로그에 저장하지 않았다.

## 검증 결과

- 로컬 Python 3.9에서 단위·어댑터 테스트 29개 통과. 비활성 gate, 수락 작성자·수정 시각, 수동 Routing, 휴무일·접수 종료, 위조 상태, 중복·불명확 전송·Webhook 실패 격리, Form·Workflow YAML, 문서 링크·지속 보존 Fixture를 확인했다.
- 최초 커밋의 [GitHub Actions CI](https://github.com/UMC-PRODUCT/proposal-routing-lab/actions/runs/34683928299)는 Python 3.12에서 당시 테스트 28개를 통과했다. Fixture 회귀 테스트 추가 후 최신 커밋의 CI 결과도 Actions에서 확인한다.
- [실제 Pilot Workflow 실행](https://github.com/UMC-PRODUCT/proposal-routing-lab/actions/runs/34683987968): `records` 성공, `discord` 건너뜀.
- [제품 정상 입력 #2](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/2), [Design System 정상 입력 #3](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/3): 시나리오 검증 성공, 오류 없음.
- [필수 정보 누락 #4](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/4): `needs:information`과 누락 목록 7개 확인.
- [비활성 일반 제안 #5](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/5): 비활성 안내만 기록하고 실제 접수하지 않음. 활성화 이전 생성 건이므로 향후 운영 Cohort에도 포함되지 않음.
- 네 Issue 모두 Assignee 없음·결정 기한 없음·알림 큐 없음 확인. Discord에는 준비 안내와 고정 시스템 메시지만 있고 **Webhook 메시지 0건**이다.
- `tests/fixtures`는 위 합성 Issue의 API 왕복 본문을 보존했다. 실제 Issue Form 화면에서 생성한 Fixture라고 간주하지 않는다.
- 저장소 Private, Issues 활성, Wiki·Discussions·저장소 자체 Project 비활성, 두 운영 변수 false, 지정 Secret 이름 존재를 재조회했다.

## 활성화 전에 남겨 둘 항목

- Pilot DRI·참가자·결정권자·Backup의 인명 확정과 본인 수락.
- 합의된 실제 계정으로 Read·Triage·Admin, Project·Discord 접근권한 비교.
- Project 필드·View·Auto-add의 실제 화면·새 제출 결과 확인.
- 실제 Form 렌더링과 생성된 Markdown Fixture 확인.
- 실제 Discord 알림 전송·오류·중복의 운영 검증은 활성화 전송 허용 이후 수행. 비활성 환경에서는 실제 제안 알림을 보내지 않음.

환경 준비와 운영 인계·파일럿 효과 검증은 별개의 상태입니다. 계획의 합격 기준을 구현 결과로 간주하지 않습니다.
