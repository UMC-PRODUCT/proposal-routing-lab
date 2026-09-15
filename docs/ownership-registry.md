# 제안 접수 Ownership Registry

> 이 문서는 `python -m intake.generate`로 생성합니다. 배정 변경은 [registry/ownership.yml](../registry/ownership.yml)의 PR로 기록합니다.

제품·기능 개선 및 Design System 제안의 연결·결정 책임만 포함합니다. 조직의 전체 임명권·인사·배치 평가 자료는 이 공개 문서에 포함하지 않습니다.
등록된 계정·본인 수락·운영 개시·보호 설정을 확인해야 자동화가 활성화됩니다. 아래 등록 표만으로 운영 중이거나 본인이 수락했다고 판단하지 않습니다.

| 책임 | Type | 확정 배치 | GitHub 계정 | 등록 상태 | 시작 | 임기 종료 | 재검토 |
|---|---|---|---|---|---|---|---|
| Brand & Growth | Purpose | 돌민 — Acting Lead | 미등록 | 준비 중 | 2026-09-13T00:00:00+09:00 | 2026-11-08T00:00:00+09:00 | 2026-10-26 |
| Learning & Activity | Purpose | 조이 — Acting Lead | 미등록 | 준비 중 | 2026-09-13T00:00:00+09:00 | 2026-11-08T00:00:00+09:00 | 2026-10-26 |
| Community & Connection | Purpose | 모루 — Acting Lead | 미등록 | 준비 중 | 2026-09-13T00:00:00+09:00 | 2026-11-08T00:00:00+09:00 | 2026-10-26 |
| Operations Enablement | Purpose | 루씨 — Acting Lead | 미등록 | 준비 중 | 2026-09-13T00:00:00+09:00 | 2026-11-08T00:00:00+09:00 | 2026-10-26 |
| Design Platform | Standing | 미정 | 미등록 | 준비 중 | 미등록 | 미등록 | 미등록 |

## 제품 연결과 범위

제품 이름은 조직 운영 모델의 제품·도메인 Ownership Map을 따릅니다. 계정이 미등록된 영역은 정상 자동 접수를 시작하지 않습니다.

### Brand & Growth (`brand-and-growth`)

공식 홈페이지·테크 블로그·대외 콘텐츠와 리크루팅 전체 Journey의 제품·기능 개선. 공통 인증·Forms 기반과 다른 목적팀 제품은 제외.

- 공식 홈페이지·테크 블로그·대외 콘텐츠 (`brand-content`)
- 리크루팅 전체 Journey (`recruiting`)

현재 책임 버전: `8e33a10aa0ec6f05c8ac367851e2546abd4b84e0423943aa8cd65baa4741e6e9`

### Learning & Activity (`learning-and-activity`)

UPMS·프로젝트 활동과 커리큘럼·워크북·미션·피드백·출석·일정·수료의 제품·기능 개선. 공통 Forms·인증·알림 기반은 제외.

- UPMS·프로젝트 매칭·프로젝트 활동 (`projects`)
- 커리큘럼·워크북·미션·피드백·출석·일정·수료 (`learning`)

현재 책임 버전: `998de70dbee00a53a1e73c7cf9ff2b8a35765b10c37a8ebe930cdbe782d4cadf`

### Community & Connection (`community-and-connection`)

커뮤니티·Connect·전자명함·관계 경험의 제품·기능 개선. 공통 WebSocket·메시징·계정 기반은 제외.

- 커뮤니티·Connect·전자명함·관계 경험 (`community`)

현재 책임 버전: `9fedc649051c1abf27ebb0fe1ad0b526212957558910621493c7393eb628c688`

### Operations Enablement (`operations-enablement`)

기수·조직·구성원·역할·상벌점·운영 승인과 공지·Analytics·감사 조회의 제품·기능 개선. 조직 인사·회의·운영 제도 변경과 공통 인증·전달 기반은 제외.

- 기수·조직·구성원·역할·상벌점·운영 승인 (`operations`)
- 공지 작성·대상 결정 (`announcements`)
- 운영 Analytics·감사 조회 (`operations-analytics`)

현재 책임 버전: `93c8da6b7bc73ca89c48cb1887f4a0dfcf21af80089a6dd99234a871078f3a47`

### Design Platform (`design-platform`)

iOS·Android·Web Design System·Figma Library의 공통 컴포넌트·토큰·패턴과 플랫폼 간 계약. 목적팀의 일상 화면 변경은 제외.

- iOS·Android·Web Design System·Figma Library (`design-system`)

현재 책임 버전: `27c636f4f590f75be98592317ed23edc28fbb446368005191cdad8ddb0825f93`

## 등록과 변경

구성원 등록 시 GitHub의 숫자 사용자 ID·현재 사용자명·실제 등록 시각(`registered_at`)을 기록합니다. 사용자명이 바뀌어도 ID로 본인을 확인하며, 등록 전 행동을 소급 인정하지 않습니다.
역할자는 운영 제어 Issue에서 첫 줄이 `/역할수락 <책임 ID> <현재 책임 버전>`인 댓글을 직접 작성합니다. 그 댓글 ID를 해당 책임의 `acceptance_comment_id`에 등록합니다.
부총괄·총괄의 연결 역할 수락은 각각 `/역할수락 coordination.primary`, `/역할수락 coordination.backup`으로 기록합니다. 연결 역할은 제품 채택 결정권을 대신하지 않습니다.
후임자는 자신의 역할 수락과 `/인계수락 <책임 ID> <현재 책임 버전>` 댓글로 미결 요청의 인수를 확인하고, 해당 댓글 ID를 `handoff_comment_id`에 연결합니다.
책임별 버전은 범위·담당자·임기·제품 연결을 포함합니다. 다른 팀의 변경이나 같은 담당자의 닉네임 표기 변경만으로 기존 책임의 수락이 무효화되지 않습니다.

## 일정과 운영 준비

책임별 시작·임기 종료·재검토일은 위 표를 따릅니다. 종료 시각부터 신규 자동 배정과 새 결정권을 인정하지 않으며, 임기는 자동 연장되지 않습니다.
기한 계산·독촉 알림 휴식 기간(KST, 양 끝 날짜 포함): 2026-10-19 ~ 2026-10-24. 접수·배정·결정·수락은 계속 처리합니다.
운영 개시일·구성원 계정·리뷰어·예외 담당자 수락·보호 설정·사용성 검증이 준비되어야 활성화합니다. 비활성 상태의 문서는 실제 운영 완료를 뜻하지 않습니다.
