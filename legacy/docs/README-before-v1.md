# Proposal Routing Pilot

제품·기능 개선과 Design System 제안을 GitHub Issue로 받고, 결정과 다음 행동을 남기는 비공개 저장소입니다. 초기 접수·처리·기록은 **GitHub만 사용**하며, Discord 연계는 실제 필요를 확인한 뒤 검토합니다.

## 초기 수동 접수 준비

[수동 접수 양식](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/new?template=manual.yml)으로 직접 제안하고 같은 Issue에서 보완·결정·본인 수락을 기록합니다. 현재 양식의 `Discord 원글 링크`는 비워도 됩니다. 조직의 운영 규칙·역할·회의 방식 제안은 이 접수 경로의 대상이 아닙니다. 공지·출석·승인처럼 운영을 지원하는 **제품 기능의 개선**은 대상입니다.

수동 접수는 `manual-intake` 라벨로 구분하며, 담당자가 연결·결정·본인 수락을 확인합니다. **담당자 자동 지정, 3영업일 자동 기한, 결정·수락 자동 검증은 적용되지 않습니다.** [수동 접수 운영 안내](docs/manual-operations.md)에서 한국어 양식과 다음 행동을 확인하세요.

목적팀 PM은 Acting Lead로 임시 지정해 해당 기간 Purpose DRI 책임을 맡습니다. 정확한 임기·시작일·Review일은 아직 정하지 않았으며, 6~8주는 후보입니다. 정상 목적팀 제안을 PM에게 직접 연결하고 예외만 부총괄에게 연결하는 절차와 응답 주기는 운영 권고입니다. 전체 운영 정본은 워크스페이스의 **`제안-접수-GitHub-초기운영-가이드.md`**입니다.

이 문서의 완성은 운영 시작을 뜻하지 않습니다. 담당 계정·본인 수락·접근권한·라벨 준비를 확인하고 시작 시점을 별도로 안내합니다. 현재 수동 양식 하나를 사용하며, 제품·기능과 Design System용 **수동 간소 양식 두 개는 권고안으로 아직 구현되지 않았습니다.**

**기존 자동 접수 파일럿은 실제 접수를 시작하기 전입니다.** 아래 파일럿 안내는 제품·기능 Proposal / Design System Proposal에 해당합니다. [활성화 이슈 #1](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1)의 담당자 수락과 준비 확인을 마친 뒤 별도로 시작합니다. 수동 접수를 위해 기존 활성화 설정이나 역할 수락을 대신 채우지 않습니다.

## 하려는 일에 따라 시작하기

| 하려는 일 | 읽을 문서 |
|---|---|
| 초기 제안 접수 경로와 시작 준비 확인 | [수동 접수와 결정 방법](docs/manual-operations.md), [수동 접수 양식](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/new?template=manual.yml) |
| 기존 자동 접수 파일럿의 제출 방법 알아보기 | [파일럿 제출 대상과 작성 방법](START-HERE.md#submit) |
| 수동 접수에서 결정권자를 연결하고 결정·수락 기록하기 | [수동 접수 운영 안내](docs/manual-operations.md) |
| 기존 자동 파일럿에서 결정권자를 지정하기 | [담당자 지정 절차](docs/operator-guide.md#route) |
| 기존 자동 파일럿의 결정과 수락을 기록하기 | [첫 결정 작성과 책임 수락](docs/operator-guide.md#decision) |
| 파일럿을 시작하기 | [운영 준비와 활성화](docs/operator-guide.md#activate), [이번 파일럿의 준비 기록](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/1) |
| 구현과 검증 결과를 확인하기 | [로컬 확인](#local-checks), [구축 및 검증 기록](docs/verification.md) |

## 기존 자동 접수 파일럿의 범위와 기록 위치

팀 내부의 일상 작업은 기존 경로를 사용합니다. 이 파일럿은 제안 접수부터 첫 결정과 다음 행동 안내까지 확인합니다. 실행 결과의 측정과 조직 전체 확대는 별도 판단이 필요합니다. 첫 파일럿에서는 운영 담당자가 직접 결정권자를 선택하며, 자동 분류는 사용하지 않습니다.

제안별 기한·결정·담당자는 **해당 Issue의 운영 기록**을 기준으로 확인합니다. Project는 그 기록을 모아 보는 용도입니다. [Discord 준비 채널](https://discord.com/channels/1442030160311484416/1548251856549974136)에는 제안 번호·종류·분류 경로·담당 GitHub 계정·기한·링크만 알립니다. 제안의 실제 제목과 본문은 전송하지 않습니다.

시작 준비와 승인 근거는 활성화 이슈에 기록합니다. 실제 접수 동작은 설정·본인 수락·Actions 변수까지 함께 검사하므로, 이슈의 체크박스나 Actions의 성공 표시만으로 활성화를 판단하지 않습니다. [확인 방법](docs/operator-guide.md#ready-check)을 따르세요.

<a id="local-checks"></a>
## 개발자가 로컬에서 확인하기

저장소를 내려받은 뒤 저장소 루트에서 실행합니다. GitHub Actions의 검증 환경은 Python 3.12이며, 의존성은 PyYAML 6.0.3입니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pilot.runner check-config
```

테스트가 끝나면 `OK`와 실행한 테스트 수를 확인합니다. 테스트는 합성 사용자와 기록을 사용하며 네트워크 요청을 보내지 않습니다.

`check-config`는 설정의 승인용 식별값(`Config approval fingerprint`)과 미완료 항목을 출력합니다. 초기 설정에서는 미완료 항목이 나오는 것이 정상이며, 명령의 종료 성공은 활성화 완료를 뜻하지 않습니다. 이 명령은 GitHub의 수락 댓글을 조회하지 않습니다. 실제 계정·Form·Project·알림 검증은 [검증 기록](docs/verification.md)에서 구분해 확인합니다.
