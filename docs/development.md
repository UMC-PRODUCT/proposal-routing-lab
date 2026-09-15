# 개발과 검증


아래 명령은 저장소 루트에서 실행합니다. GitHub Actions는 Python 3.12에서 실행합니다. 테스트는 실제 API 호출 없이 합성 기록을 사용합니다.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m intake.runner check-config
python -m intake.generate --check
```

`registry/ownership.yml` 변경 후 `python -m intake.generate`로 양식과 읽기용 표를 갱신하세요. `check-config` 성공은 스키마가 유효하다는 뜻이며 운영 개시·실제 권한 검증을 대신하지 않습니다.

상태 계산은 `intake/core.py`, 계정·임기·영업일은 `intake/registry.py`, API 조회와 쓰기는 `intake/runner.py`에 있습니다. 기존 `pilot/runner.py`의 GitHub API 전송·페이지 처리만 재사용합니다. 옛 정책 코드·합성 테스트는 보존하지만 운영 워크플로는 `.github/workflows/intake.yml`입니다. 옛 양식·워크플로·안내는 [legacy](../legacy/README.md)에 보관합니다.

[구성원 사용 안내로 돌아가기](../README.md)
