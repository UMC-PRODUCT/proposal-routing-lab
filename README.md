# Proposal Routing Pilot

제안이 적절한 결정권자에게 도착하고, 제안자에게 다음 행동이 돌아오는지 확인하는 비공개 파일럿입니다.

**현재 준비 상태: 비활성.** 실제 접수는 Pilot DRI가 설정과 역할을 수락한 뒤 시작합니다. 현재 상태는 저장소 Actions Variables의 `PILOT_ACTIVE`와 활성화 Issue를 함께 확인하세요.

- [시작·운영 안내](START-HERE.md)
- [Proposal 제출](https://github.com/UMC-PRODUCT/proposal-routing-lab/issues/new/choose)
- [활성화 체크리스트 원본](docs/activation-checklist.md)
- [구축 및 실제 검증 기록](docs/verification.md)

제품·기능과 Design System Proposal만 대상으로 합니다. 팀 내부의 일상 작업은 기존 경로를 사용합니다. 첫 버전은 수동 Routing이며 실행·Outcome 측정과 조직 전체 확대는 포함하지 않습니다.

Issue가 기한·결정의 기준이고 Project는 조회용입니다. Discord에는 제안 번호·종류·Route·담당 GitHub 계정·기한·링크만 전송합니다. 실제 제목과 본문은 전송하지 않습니다.

## 로컬 확인

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pilot.runner check-config
```

Python 3.12와 PyYAML 6.0.3을 사용합니다. 테스트에는 합성 사용자·기록만 사용하며 네트워크 요청을 보내지 않습니다. 실제 GitHub 연결 검증은 별도로 기록합니다.
