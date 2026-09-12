# 구축 및 검증 기록

이 문서는 실제로 수행한 확인과 남은 검증을 구분해 보관합니다. 항목의 날짜·환경·근거가 가리키는 시점의 결과이며, 현재 상태나 활성화 승인을 대신하지 않습니다. 이번 파일럿의 준비 판단은 [활성화 이슈 #1](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)에 기록합니다.

## 구축 당시 확인한 결과

| 확인일 | 대상·환경 | 확인한 결과 | 근거 |
|---|---|---|---|
| 2026-09-12 | GitHub 조직과 신규 저장소 | 조직 기본 저장소 접근권한 `none`, Free 플랜, 비공개 저장소 생성, 두 운영 변수 `false`, Label 19개, 활성화 이슈 생성. Wiki·Discussions·저장소 자체 Project 비활성. | [저장소](https://github.com/UMC-PRODUCT/proposal-routing-lab), [활성화 이슈](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1). 상세 설정은 해당 권한이 있는 계정으로 확인. |
| 2026-09-12 | Discord 준비 채널 | 일반 구성원 접근 차단, 관리자 예외·봇 접근, 준비 안내 고정, Webhook을 저장소 Secret에 직접 등록. 실제 참가자 권한은 미부여. | [준비 채널](https://discord.com/channels/1442030160311484416/1548251856549974136). 자격증명은 문서·로그에 보관하지 않음. |
| 2026-09-12 | 로컬 Python 3.9 | 단위·어댑터 테스트 29개 통과. 비활성, 역할 수락, 수동 분류, 기한, 위조 상태, 알림 실패, YAML·Fixture 등을 확인. | [해당 버전의 테스트](https://github.com/UMC-PRODUCT/proposal-routing-lab/tree/c1ca65d1027d197075ccf8d28aeb4fb63878aad5/tests) |
| 2026-09-12 | GitHub Actions, Python 3.12 | 최초 버전 28개, Fixture 회귀 테스트 추가 버전 29개 통과. | [최초 CI](https://github.com/UMC-PRODUCT/proposal-routing-lab/actions/runs/34683928299), [Fixture 추가 후 CI](https://github.com/UMC-PRODUCT/proposal-routing-lab/actions/runs/34684156939) |
| 2026-09-12 | 비활성 Pilot 워크플로 | `records` 성공, `discord` 건너뜀. | [실행 결과](https://github.com/UMC-PRODUCT/proposal-routing-lab/actions/runs/34683987968) |
| 2026-09-12 | API로 만든 합성 Issue | 제품·디자인 정상 입력은 오류 없음. 필수 정보 누락 건은 `needs:information`과 누락 목록 7개 표시. | [제품 #2](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/2), [디자인 #3](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/3), [누락 #4](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/4) |
| 2026-09-12 | 비활성 일반 제안 | 비활성 안내만 기록. 최초 승인 이전 생성 건이므로 향후 실제 접수 표본에도 포함되지 않음. | [비활성 #5](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/5) |
| 2026-09-12 | 합성 Issue 4개·Discord | 네 Issue 모두 Assignee·결정 기한·알림 큐 없음. Discord에는 준비 안내와 고정 시스템 메시지만 있고 Webhook 메시지는 0건. | 위 Issue들과 준비 채널의 당시 확인 결과 |
| 2026-09-13 | 호스트 `gh` | 저장소와 이슈 접근 성공. Project 목록 조회는 토큰에 `read:project`가 없어 실패. 두 운영 변수 `false` 확인. | 호스트 CLI 조회. 인증값은 보관하지 않음. |

`tests/fixtures`에는 위 합성 Issue의 API 왕복 본문을 보존했습니다. 실제 Issue Form 화면에서 생성한 본문이 아닙니다. 로컬 파싱·자동 테스트와 실제 Form 제출 검증은 구분합니다.

## 문서·표시 개선 검증

2026-09-13에 제안자·운영자별 안내, Form 설명과 입력 예시, 작업별 완료 확인, 자동 댓글의 한국어 항목명과 KST 표시를 보완했습니다. 검증 결과는 아래에 확인한 근거와 함께 기록합니다.

- 로컬: 기존 테스트 29개와 자동 댓글 표시 테스트 6개 통과. 숨김 상태 JSON 보존, KST 날짜 변경, 비활성·시나리오·보완·결정 상태별 다음 행동을 확인했습니다.
- Form: 두 양식의 필드 ID·제목·선택지·필수 여부·라벨이 이전 버전과 같음을 확인했습니다. 설명·예시·안내만 변경했습니다.
- 문서: Markdown 6개와 로컬 링크 22개를 확인했습니다. GitHub Markdown API로 제목·표·안내 경로의 렌더링을 확인했습니다. 실제 브라우저 Form 화면을 확인한 것은 아닙니다.
- 코드: 표시 함수와 표시용 보조 함수를 제외한 핵심 로직이 기존 버전과 같음을 AST 비교로 확인했습니다.
- 원격 반영과 변경 버전의 CI·댓글 확인 결과는 실제 확인한 뒤 추가합니다.

## 남은 검증과 확인 방법

| 아직 확인할 항목 | 다음 확인 방법 | 근거를 남길 위치 |
|---|---|---|
| 실제 역할·참가자 수락 | 합의한 계정을 설정에 반영하고 각자의 수락 댓글 작성자·ID를 대조합니다. | 활성화 이슈 |
| 실제 계정별 권한 | 참가자·결정권자·부총괄 계정으로 저장소·Project·Discord를 확인합니다. 비참가 계정과 관리자 예외도 비교합니다. | 활성화 이슈 |
| Project 필드·보기·자동 등록 | Project 권한이 있는 계정으로 설정한 뒤 새 제출의 자동 등록과 기본 상태, 보기별 표시를 확인합니다. | 활성화 이슈와 설정 화면·Issue 링크 |
| 실제 Form 표시와 제출 본문 | 로그인한 브라우저에서 두 양식의 설명·예시를 확인하고 승인된 테스트 조건에서 제출합니다. 생성된 본문의 필드 제목·필수 정보 판정을 Fixture와 대조합니다. | 검증 기록과 해당 테스트 Issue |
| 실제 알림의 수신·실패·중복 | 실제 전송을 허용한 검증 단계에서 Issue 기록과 Discord 수신 결과를 함께 확인합니다. 비활성 상태에서는 실제 제안 알림을 보내지 않습니다. | 해당 Issue 운영 메모 |
| 시작 이후 실제 접수 | 참가자가 승인·시작 이후 제출한 유효 제안에 유효 접수 시각과 첫 결정 기한이 기록되는지 확인합니다. | 활성화 이슈와 실제 제안 링크 |

접수 전 테스트는 `pilot:scenario`로 구분하고, 실제 참가자나 전송을 사용하는 검증은 담당자와 허용 범위를 합의한 뒤 수행합니다. 환경 준비, 운영 인계, 파일럿 효과는 각각 확인해야 합니다. 문서의 절차나 목표만으로 검증 완료를 표시하지 않습니다.
