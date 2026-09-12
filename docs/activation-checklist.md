# v1 활성화 체크리스트

코드 배포와 운영 개시는 별개입니다. 준비된 모든 팀을 함께 시작하며, 값이 없는 팀만 비활성으로 남깁니다. 공통 예외 담당자·보호 설정이 준비되지 않으면 전체 활성화를 보류합니다.

## 계정과 역할 등록

1. 조사한 실제 GitHub 계정을 API로 조회해 숫자 ID·현재 사용자명을 확인하고 `members`에 실제 등록 시각을 기록합니다. 이메일·Discord 표시명은 필요하지 않습니다. 과거 시각으로 소급하지 않습니다.
2. 기존 네 PM의 팀 배치를 유지하며 해당 책임의 owner_id를 연결합니다. 부총괄·총괄은 coordination에, 검토자는 registry/automation 영역별로 연결합니다. 각 검토 영역에 최소 두 명의 서로 다른 검토자가 필요합니다.
3. `python -m intake.generate`로 책임별 버전을 확인합니다. 본인이 제어 Issue #1에 `/역할수락 <책임 ID> <버전>`을 작성한 뒤 그 댓글 ID를 Registry에 연결합니다. 예외 담당자는 각각 `/역할수락 coordination.primary`, `/역할수락 coordination.backup`을 작성합니다.
4. 후임은 미결 목록을 확인하고 역할 수락 이후 `/인계수락 <책임 ID> <버전>`을 작성합니다. handoff_comment_id에 연결합니다. 담당자를 대신해 수락하지 않습니다.
5. 운영 현황 Issue의 본문 첫 줄에 `<!-- intake-v1-dashboard -->`를 두고 dashboard_issue에 번호를 기록합니다. #1~5와 운영 현황 번호는 집계에서 제외합니다.

## 공개와 보호

- 현재 파일뿐 아니라 모든 브랜치·태그의 Git 이력, Issue·댓글·첨부, Actions 로그의 공개 적합성을 확인합니다. 민감 정보 발견 시 공개를 보류하고 정리 범위를 결정합니다. 이력 재작성·삭제를 자동 수행하지 않습니다.
- 일반 구성원 Read, Issue 운영자 Triage, 필요한 유지보수자만 Write로 등록합니다. 기존 관리자 계정만으로 조직상 역할을 추정하지 않습니다.
- `reviewers`에 확정된 Registry/자동화 검토자를 구분해 넣어 `.github/CODEOWNERS`를 생성하고 CODEOWNERS 자체도 보호합니다. 작성자 외 승인이 가능해야 합니다.
- main에 PR 필수, 승인 1인, CODEOWNERS 승인, 새 변경 후 재승인, CI `verify` 필수, 강제 push·삭제 금지, 관리자 포함 우회 금지를 적용합니다. [브랜치 보호 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)를 따르고 API로 재조회합니다.
- 보호 JSON과 CODEOWNERS 오류 조회 결과, 미승인·CI 실패 PR의 병합 차단 결과를 기록한 후 protection_verified를 true로 바꿉니다. 파일만 만들거나 체크박스만 표시해 완료 처리하지 않습니다.
- `PILOT_ACTIVE=false`, `AUTO_ROUTING_ENABLED=false`, `INTAKE_MODE=observe`를 확인하고 옛 파일럿 워크플로를 자동 실행 경로에서 제거합니다. Discord job은 새 워크플로에 없습니다.

## 검증과 시작

- CI에서 전체 합성 테스트·Registry 스키마·생성 파일 정합성을 통과합니다.
- 실제 일반 구성원 계정으로 양식 제출·본인 수락, Triage 계정으로 운영을 확인합니다. API fixture 테스트가 이 검증을 대신하지 않습니다. 합성 검증 Issue는 별도 번호로 제외 설정합니다.
- 신규 구성원 3명(비개발 직군 포함)이 별도 설명 없이 제출하고 담당자·다음 행동을 찾는지 확인합니다. 반복해서 막힌 문구는 수정한 후 usability_verified를 true로 바꿉니다.
- 준비된 팀의 enabled, 실제 intake_opened_at, 모든 공통 증거를 PR로 반영하고 observe 전체 검사를 확인합니다. 임기 시작일과 intake_opened_at은 별개이며 등록 전 행동은 인정하지 않습니다.
- `INTAKE_MODE=active`로 전환하고 첫 전체 검사·운영 현황·새 요청 처리를 확인합니다. 시작 2주 후 사용성·예외 적체·잘못된 교정을 검토합니다. 2주 경과만으로 자동 종료하지 않습니다.

입력값이 비어 있는 상태는 의도적으로 활성화가 차단된 준비 상태입니다. 실제 입력과 검증 근거 없이 true·계정·수락을 채우지 않습니다.
