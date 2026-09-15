"""Generate public registry views and the two issue forms from ownership.yml."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from intake.registry import load_registry, member, route_version

UNKNOWN = "모르겠음 / 여러 영역에 해당"
ROOT = Path(__file__).resolve().parents[1]


def _registered(cfg: dict, route: dict) -> bool:
    return bool(route.get("enabled") and member(cfg, route.get("owner_id")) and route.get("acceptance_comment_id") and route.get("starts_at"))


def _form(cfg: dict, design: bool) -> dict:
    routes = {k: v for k, v in cfg["routes"].items() if (k == "design-platform") == design}
    labels = [product["label"] for route in routes.values() for product in route["products"]]
    if not design:
        labels.append(UNKNOWN)
    registered = [route["name"] for route in routes.values() if _registered(cfg, route)]
    pending = [route["name"] for route in routes.values() if not _registered(cfg, route)]
    repo = cfg["repository"]["full_name"]
    readiness = "\n".join([
        "이 저장소의 제목·본문·댓글·첨부는 공개됩니다. 실제 사용자 개인정보나 민감한 원본 자료는 기존 비공개 작업에 보관해주세요.",
        "등록된 구성원의 제품·기능 개선과 Design System 제안만 접수합니다. 조직의 인사·회의·운영 제도 변경과 일상 개발 작업은 기존 경로를 사용해주세요.",
        f"[접수 상태와 사용 안내](https://github.com/{repo}/blob/main/START-HERE.md)를 먼저 확인해주세요.",
    ])
    if pending:
        readiness += "\n\n담당자 등록 준비 중: " + ", ".join(pending) + ". 이 영역은 현재 정상 자동 접수를 시작하지 않았습니다. 제출하더라도 임의의 PM에게 배정하지 않습니다."
    if registered:
        readiness += "\n\n등록된 영역: " + ", ".join(registered) + ". 실제 처리 여부는 운영 모드·역할 수락·현재 임기 확인 결과에 따릅니다."
    if not design:
        readiness += "\n\n대상이 불명확하면 '모르겠음 / 여러 영역에 해당'을 선택하세요. 연결 담당자가 책임 범위를 확인합니다."
    return {
        "name": "Design System 제안" if design else "제품·기능 개선 제안",
        "description": "공통 컴포넌트·토큰·패턴과 플랫폼 간 계약의 개선" if design else "사용자가 겪는 문제와 필요한 도움을 남겨주세요.",
        "title": "[Design System] " if design else "[제품 제안] ",
        "labels": ["intake", "intake:design-system" if design else "intake:product"],
        "body": [
            {"type": "markdown", "attributes": {"value": readiness}},
            {"type": "dropdown", "id": "target", "attributes": {"label": "대상", "options": labels}, "validations": {"required": True}},
            {"type": "textarea", "id": "problem", "attributes": {"label": "문제", "description": "누가 어떤 상황에서 무엇을 어려워하나요?", "placeholder": "관찰한 문제와 아직 확인하지 못한 내용을 구분해주세요."}, "validations": {"required": True}},
            {"type": "textarea", "id": "help", "attributes": {"label": "원하는 도움", "description": "함께 확인하거나 결정해주었으면 하는 내용. 완성된 해결책이 없어도 됩니다."}, "validations": {"required": True}},
            {"type": "textarea", "id": "evidence", "attributes": {"label": "근거·스크린샷·Figma 링크", "description": "선택 사항입니다. 공개 가능한 자료만 첨부하고 민감한 원본은 비공개 작업에서 관리해주세요."}, "validations": {"required": False}},
        ],
    }


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ") if value is not None else "미등록"


def _registry_doc(cfg: dict) -> str:
    rows = [
        "# 제안 접수 Ownership Registry",
        "",
        "> 이 문서는 `python -m intake.generate`로 생성합니다. 배정 변경은 [registry/ownership.yml](../registry/ownership.yml)의 PR로 기록합니다.",
        "",
        "제품·기능 개선 및 Design System 제안의 연결·결정 책임만 포함합니다. 조직의 전체 임명권·인사·배치 평가 자료는 이 공개 문서에 포함하지 않습니다.",
        "등록된 계정·본인 수락·운영 개시·보호 설정을 확인해야 자동화가 활성화됩니다. 아래 등록 표만으로 운영 중이거나 본인이 수락했다고 판단하지 않습니다.",
        "",
        "| 책임 | Type | 확정 배치 | GitHub 계정 | 등록 상태 | 시작 | 임기 종료 | 재검토 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for route in cfg["routes"].values():
        owner = member(cfg, route.get("owner_id"))
        account = f"@{owner['login']} (ID {owner['id']})" if owner else "미등록"
        title = f"{route['display_name']} — Acting Lead" if route.get("acting") and route.get("display_name") else route.get("display_name") or "미정"
        fields = [route["name"], route["type"], title, account, "설정 등록·실시간 검증 필요" if _registered(cfg, route) else "준비 중", route.get("starts_at"), route.get("ends_at"), route.get("review_on")]
        rows.append("| " + " | ".join(_cell(value) for value in fields) + " |")
    rows += ["", "## 제품 연결과 범위", "", "제품 이름은 조직 운영 모델의 제품·도메인 Ownership Map을 따릅니다. 계정이 미등록된 영역은 정상 자동 접수를 시작하지 않습니다.", ""]
    for route_id, route in cfg["routes"].items():
        rows += [f"### {route['name']} (`{route_id}`)", "", route["scope"], ""]
        rows += [f"- {product['label']} (`{product['id']}`)" for product in route["products"]]
        rows += ["", f"현재 책임 버전: `{route_version(route)}`", ""]
    rows += [
        "## 등록과 변경",
        "",
        "구성원 등록 시 GitHub의 숫자 사용자 ID·현재 사용자명·실제 등록 시각(`registered_at`)을 기록합니다. 사용자명이 바뀌어도 ID로 본인을 확인하며, 등록 전 행동을 소급 인정하지 않습니다.",
        "역할자는 운영 제어 Issue에서 첫 줄이 `/역할수락 <책임 ID> <현재 책임 버전>`인 댓글을 직접 작성합니다. 그 댓글 ID를 해당 책임의 `acceptance_comment_id`에 등록합니다.",
        "부총괄·총괄의 연결 역할 수락은 각각 `/역할수락 coordination.primary`, `/역할수락 coordination.backup`으로 기록합니다. 연결 역할은 제품 채택 결정권을 대신하지 않습니다.",
        "후임자는 자신의 역할 수락과 `/인계수락 <책임 ID> <현재 책임 버전>` 댓글로 미결 요청의 인수를 확인하고, 해당 댓글 ID를 `handoff_comment_id`에 연결합니다.",
        "책임별 버전은 범위·담당자·임기·제품 연결을 포함합니다. 다른 팀의 변경이나 같은 담당자의 닉네임 표기 변경만으로 기존 책임의 수락이 무효화되지 않습니다.",
        "",
        "## 일정과 운영 준비",
        "",
        "책임별 시작·임기 종료·재검토일은 위 표를 따릅니다. 종료 시각부터 신규 자동 배정과 새 결정권을 인정하지 않으며, 임기는 자동 연장되지 않습니다.",
        "기한 계산·독촉 알림 휴식 기간(KST, 양 끝 날짜 포함): " + ", ".join(f"{x['start']} ~ {x['end']}" for x in cfg["calendar"]["quiet_periods"]) + ". 접수·배정·결정·수락은 계속 처리합니다.",
        "운영 개시일·구성원 계정·리뷰어·예외 담당자 수락·보호 설정·사용성 검증이 준비되어야 활성화합니다. 비활성 상태의 문서는 실제 운영 완료를 뜻하지 않습니다.",
        "",
    ]
    return "\n".join(rows)


def generated_files(cfg: dict) -> dict[str, str]:
    def dump(value: dict) -> str:
        return "# Generated by python -m intake.generate; edit registry/ownership.yml or intake/generate.py.\n" + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000)
    repo = cfg["repository"]["full_name"]
    owners = ['# Generated by python -m intake.generate; edit registry/ownership.yml.',
              '# Pending reviewer registration means activation must remain blocked.']
    groups = {area: [f"@{member(cfg, uid)['login']}" for uid in cfg['reviewers'][area] if member(cfg, uid)]
              for area in ('registry', 'automation')}
    all_owners = sorted(set(groups['registry'] + groups['automation']))
    if all_owners:
        owners.append('* ' + ' '.join(all_owners))
    for pattern, area in [('/registry/', 'registry'), ('/docs/ownership-registry.md', 'registry'),
                          ('/intake/', 'automation'), ('/pilot/', 'automation'), ('/tests/', 'automation'),
                          ('/requirements.txt', 'automation'), ('/.github/workflows/', 'automation'),
                          ('/.github/ISSUE_TEMPLATE/', 'automation')]:
        if groups[area]:
            owners.append(pattern + ' ' + ' '.join(groups[area]))
    if all_owners:
        owners.append('/.github/CODEOWNERS ' + ' '.join(all_owners))
    return {
        '.github/CODEOWNERS': '\n'.join(owners) + '\n',
        ".github/ISSUE_TEMPLATE/product.yml": dump(_form(cfg, False)),
        ".github/ISSUE_TEMPLATE/design-system.yml": dump(_form(cfg, True)),
        ".github/ISSUE_TEMPLATE/config.yml": dump({"blank_issues_enabled": False, "contact_links": [
            {"name": "접수 상태와 제안 안내", "url": f"https://github.com/{repo}/blob/main/START-HERE.md", "about": "제안 범위와 현재 운영 상태, 제출 후 다음 행동을 확인합니다."},
            {"name": "담당 책임과 등록 상태", "url": f"https://github.com/{repo}/blob/main/docs/ownership-registry.md", "about": "제품별 책임과 담당자 등록 준비 상태를 확인합니다."},
        ]}),
        "docs/ownership-registry.md": _registry_doc(cfg),
    }


def generate(root: Path, cfg: dict, check: bool = False) -> list[str]:
    changed = []
    for relative, content in generated_files(cfg).items():
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report generated-file drift without writing")
    parser.add_argument("--registry", default=str(ROOT / "registry/ownership.yml"))
    args = parser.parse_args()
    changed = generate(ROOT, load_registry(args.registry), args.check)
    for path in changed:
        print(("out of date: " if args.check else "generated: ") + path)
    if args.check and changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
