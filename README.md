# UMC PRODUCT 제안 접수

제품·기능 개선과 Design System 제안을 작성하면, 등록된 Ownership에 따라 결정 담당자와 다음 행동을 안내합니다. 제안·결정·실행 수락의 정본은 같은 GitHub Issue입니다.

**현재: v1 도입 준비 · 자동 운영 미개시.** 구성원 계정·담당자의 본인 수락·검토자·실제 권한과 사용성 확인이 끝나야 시작합니다. 저장소의 공개 여부와 자동 접수 활성화는 별개입니다.

- 제안 작성: [시작 안내](START-HERE.md)
- 담당 범위·준비 상태: [Ownership Registry](docs/ownership-registry.md)
- 결정·수락·인계·실패 대응: [운영 안내](docs/operator-guide.md)
- 운영 개시 준비: [활성화 체크리스트](docs/activation-checklist.md)
- 구현·검증 근거: [검증 기록](docs/verification.md)

조직의 인사·회의·운영 제도 변경과 일상 개발 작업은 기존 경로에서 다룹니다. 공지·출석·승인 등 운영을 지원하는 **제품 기능 개선**은 접수 대상입니다. Discord·Spring·별도 DB·GitHub App은 v1에 포함하지 않습니다.

## 개발과 검증

GitHub Actions는 Python 3.12에서 실행합니다. 테스트는 실제 API 호출 없이 합성 기록을 사용합니다.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m intake.runner check-config
python -m intake.generate --check
```

`registry/ownership.yml` 변경 후 `python -m intake.generate`로 양식과 읽기용 표를 갱신하세요. `check-config` 성공은 스키마가 유효하다는 뜻이며 운영 개시·실제 권한 검증을 대신하지 않습니다.

상태 계산은 `intake/core.py`, 계정·임기·영업일은 `intake/registry.py`, API 조회와 쓰기는 `intake/runner.py`에 있습니다. 기존 `pilot/runner.py`의 GitHub API 전송·페이지 처리만 재사용합니다. 옛 정책 코드·합성 테스트는 보존하지만 운영 워크플로는 `.github/workflows/intake.yml`입니다. 옛 양식·워크플로·안내는 [legacy](legacy/README.md)에 보관합니다.
