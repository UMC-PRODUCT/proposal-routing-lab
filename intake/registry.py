"""Registry validation, role consent, and the business calendar.

Validation deliberately separates an incomplete registration from a malformed file.
No GitHub I/O occurs here: linked comments must come from the control issue API.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

import yaml

KST = ZoneInfo("Asia/Seoul")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def stamp(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp requires an explicit timezone")
    return result


def iso(value: datetime) -> str:
    return stamp(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class _RegistryLoader(yaml.SafeLoader):
    """Reject duplicate keys, which would silently replace an owner or permission."""


def _mapping(loader: _RegistryLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError("registry keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_RegistryLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_registry(path: str | Path) -> dict:
    cfg = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_RegistryLoader)
    errors = validate_registry(cfg)
    if errors:
        raise ValueError("invalid registry: " + "; ".join(errors))
    return cfg


def _id(value: Any) -> bool:
    return type(value) is int and value > 0


def validate_registry(cfg: Any) -> list[str]:
    """Return schema errors; null IDs and false readiness are valid pending setup."""
    errors = []
    if not isinstance(cfg, dict):
        return ["registry must be a mapping"]
    if type(cfg.get("version")) is not int or cfg.get("version") != 1:
        errors.append("version must be 1")

    def obj(value: Any, path: str) -> dict:
        if not isinstance(value, dict):
            errors.append(f"{path} must be a mapping")
            return {}
        return value

    def sequence(value: Any, path: str) -> list:
        if not isinstance(value, list):
            errors.append(f"{path} must be a list")
            return []
        return value

    def nullable_id(value: Any, path: str) -> None:
        if value is not None and not _id(value):
            errors.append(f"{path} must be a positive integer or null")

    def nullable_time(value: Any, path: str) -> datetime | None:
        if value is None:
            return None
        try:
            return stamp(value)
        except (ValueError, TypeError, AttributeError):
            errors.append(f"{path} must be a quoted ISO timestamp with timezone or null")
            return None

    def day(value: Any, path: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            errors.append(f"{path} must be a quoted ISO date")
            return None

    repo = obj(cfg.get("repository"), "repository")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(repo.get("full_name", ""))):
        errors.append("repository.full_name must be owner/repository")
    nullable_time(repo.get("intake_opened_at"), "repository.intake_opened_at")
    for key in ("dashboard_issue", "control_issue"):
        nullable_id(repo.get(key), f"repository.{key}")
    if not _id(repo.get("control_issue")):
        errors.append("repository.control_issue is required")
    excluded = sequence(repo.get("excluded_issue_numbers"), "repository.excluded_issue_numbers")
    if any(not _id(x) for x in excluded) or len(set(str(x) for x in excluded)) != len(excluded):
        errors.append("repository.excluded_issue_numbers must contain unique positive integers")
    if repo.get("control_issue") not in excluded:
        errors.append("repository.control_issue must be excluded from intake")
    if repo.get("dashboard_issue") is not None and repo["dashboard_issue"] not in excluded:
        errors.append("repository.dashboard_issue must be excluded from intake")
    if repo.get("dashboard_issue") == repo.get("control_issue"):
        errors.append("dashboard and control issues must be distinct")

    readiness = obj(cfg.get("readiness"), "readiness")
    for key in ("protection_verified", "usability_verified"):
        if type(readiness.get(key)) is not bool:
            errors.append(f"readiness.{key} must be boolean")

    members = sequence(cfg.get("members"), "members")
    seen_ids, seen_logins = set(), set()
    for index, item in enumerate(members):
        entry = obj(item, f"members[{index}]")
        user_id, login = entry.get("id"), entry.get("login")
        if not _id(user_id) or str(user_id) in seen_ids:
            errors.append(f"members[{index}].id must be a unique positive integer")
        seen_ids.add(str(user_id))
        if not isinstance(login, str) or not _LOGIN.fullmatch(login) or login.lower() in seen_logins:
            errors.append(f"members[{index}].login must be a unique GitHub login")
        seen_logins.add(str(login).lower())
        if type(entry.get("active")) is not bool:
            errors.append(f"members[{index}].active must be boolean")
        registered = nullable_time(entry.get("registered_at"), f"members[{index}].registered_at")
        if entry.get("active") is True and registered is None:
            errors.append(f"members[{index}].registered_at is required for active members")

    reviewers = obj(cfg.get("reviewers"), "reviewers")
    for key in ("registry", "automation"):
        values = sequence(reviewers.get(key), f"reviewers.{key}")
        if any(not _id(x) for x in values) or len(set(str(x) for x in values)) != len(values):
            errors.append(f"reviewers.{key} must contain unique positive integer IDs")

    coordinators = obj(cfg.get("coordination"), "coordination")
    if set(coordinators) - {"primary", "backup"}:
        errors.append("coordination only supports primary and backup")
    for name in ("primary", "backup"):
        entry = obj(coordinators.get(name), f"coordination.{name}")
        for field in ("user_id", "acceptance_comment_id"):
            nullable_id(entry.get(field), f"coordination.{name}.{field}")

    routes = obj(cfg.get("routes"), "routes")
    products, labels = set(), set()
    for route_id, raw in routes.items():
        path = f"routes.{route_id}"
        route = obj(raw, path)
        if not isinstance(route_id, str) or not _SLUG.fullmatch(route_id):
            errors.append("route IDs must be lowercase hyphenated slugs")
        for key in ("name", "scope"):
            if not isinstance(route.get(key), str) or not route[key].strip():
                errors.append(f"{path}.{key} must be nonempty text")
        if route.get("type") not in ("Purpose", "Standing"):
            errors.append(f"{path}.type must be Purpose or Standing")
        if route.get("display_name") is not None and not isinstance(route["display_name"], str):
            errors.append(f"{path}.display_name must be text or null")
        for key in ("owner_id", "acceptance_comment_id", "handoff_comment_id"):
            nullable_id(route.get(key), f"{path}.{key}")
        for key in ("enabled", "acting"):
            if type(route.get(key)) is not bool:
                errors.append(f"{path}.{key} must be boolean")
        start = nullable_time(route.get("starts_at"), f"{path}.starts_at")
        end = nullable_time(route.get("ends_at"), f"{path}.ends_at")
        review = day(route["review_on"], f"{path}.review_on") if route.get("review_on") is not None else None
        if start and end and start >= end:
            errors.append(f"{path}.ends_at must follow starts_at")
        if review and start and review < start.astimezone(KST).date():
            errors.append(f"{path}.review_on precedes starts_at")
        if review and end and review >= end.astimezone(KST).date():
            errors.append(f"{path}.review_on must precede ends_at")
        for item in sequence(route.get("products"), f"{path}.products"):
            product = obj(item, f"{path}.products[]")
            product_id, label = product.get("id"), product.get("label")
            if not isinstance(product_id, str) or not _SLUG.fullmatch(product_id) or product_id in products:
                errors.append(f"{path}.products IDs must be unique slugs")
            products.add(str(product_id))
            if not isinstance(label, str) or not label.strip() or label in labels or "\n" in label or label == "모르겠음 / 여러 영역에 해당":
                errors.append(f"{path}.products labels must be unique nonempty lines")
            labels.add(str(label))

    calendar = obj(cfg.get("calendar"), "calendar")
    if calendar.get("timezone") != "Asia/Seoul":
        errors.append("calendar.timezone must be Asia/Seoul")
    for value in sequence(calendar.get("non_working_dates"), "calendar.non_working_dates"):
        day(value, "calendar.non_working_dates[]")
    for value in sequence(calendar.get("quiet_periods"), "calendar.quiet_periods"):
        period = obj(value, "calendar.quiet_periods[]")
        first = day(period.get("start"), "quiet_period.start")
        last = day(period.get("end"), "quiet_period.end")
        if first and last and first > last:
            errors.append("quiet period end must not precede start")
    policy = obj(cfg.get("policy"), "policy")
    for key in ("first_response_business_days", "routing_business_days"):
        if not _id(policy.get(key)):
            errors.append(f"policy.{key} must be a positive integer")
    return errors


def member(cfg: dict, user_id: int) -> dict | None:
    if not _id(user_id):
        return None
    return next((x for x in cfg.get("members", []) if x.get("id") == user_id and x.get("active") is True), None)


def route_version(route: dict) -> str:
    content = {k: v for k, v in route.items() if k not in {"acceptance_comment_id", "handoff_comment_id", "enabled", "display_name"}}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _consent(comments: list[dict], comment_id: int | None, user_id: int | None, command: str, now: datetime) -> bool:
    if not _id(comment_id) or not _id(user_id):
        return False
    matches = [x for x in comments if x.get("id") == comment_id]
    if len(matches) != 1:
        return False
    comment = matches[0]
    author = comment.get("user", {})
    if author.get("type") != "User" or author.get("id") != user_id:
        return False
    body = comment.get("body")
    if not isinstance(body, str):
        return False
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or lines[0] != command:
        return False
    try:
        return stamp(comment["created_at"]) <= stamp(now) and stamp(comment.get("updated_at", comment["created_at"])) <= stamp(now)
    except (ValueError, TypeError, KeyError):
        return False


def _member_consent(cfg: dict, comments: list[dict], comment_id: int | None, user_id: int | None, command: str, now: datetime) -> bool:
    owner = member(cfg, user_id)
    if owner is None or not owner.get("registered_at"):
        return False
    if not _consent(comments, comment_id, user_id, command, now):
        return False
    consent = next(x for x in comments if x.get("id") == comment_id)
    return stamp(owner["registered_at"]) <= stamp(consent["created_at"])


def route_errors(cfg: dict, route_id: str, role_comments: list[dict], now: datetime) -> list[str]:
    route = cfg.get("routes", {}).get(route_id)
    if route is None:
        return [f"{route_id}: 등록되지 않은 책임"]
    errors = []
    if route.get("enabled") is not True:
        errors.append(f"{route_id}: 접수 비활성")
    if member(cfg, route.get("owner_id")) is None:
        errors.append(f"{route_id}: 담당자 계정 미등록 또는 비활성")
    else:
        registered_at = member(cfg, route["owner_id"]).get("registered_at")
        if registered_at is None or stamp(registered_at) > now:
            errors.append(f"{route_id}: 구성원 등록 전")
    start = stamp(route["starts_at"]) if route.get("starts_at") else None
    end = stamp(route["ends_at"]) if route.get("ends_at") else None
    if start is None or now < start:
        errors.append(f"{route_id}: 역할 시작 전 또는 시작일 미등록")
    if end and now >= end:
        errors.append(f"{route_id}: 임기 종료·인계 필요")
    if route.get("acting") and (end is None or not route.get("review_on")):
        errors.append(f"{route_id}: Acting 종료일·재검토일 미등록")
    command = f"/역할수락 {route_id} {route_version(route)}"
    if not _member_consent(cfg, role_comments, route.get("acceptance_comment_id"), route.get("owner_id"), command, now):
        errors.append(f"{route_id}: 현재 책임 버전의 본인 수락 필요")
    return errors


def coordinator_ids(cfg: dict, role_comments: list[dict], now: datetime) -> set[int]:
    result = set()
    for name, data in cfg.get("coordination", {}).items():
        owner = member(cfg, data.get("user_id"))
        if owner and owner.get("registered_at") and stamp(owner["registered_at"]) <= now and _member_consent(cfg, role_comments, data.get("acceptance_comment_id"), data.get("user_id"), f"/역할수락 coordination.{name}", now):
            result.add(data["user_id"])
    return result


def activation_errors(cfg: dict, role_comments: list[dict], now: datetime, require_ready_route: bool = True) -> list[str]:
    errors = validate_registry(cfg)
    if errors:
        return errors
    for name, verified in cfg["readiness"].items():
        if verified is not True:
            errors.append(f"readiness.{name}: 검증 미완료")
    opened = cfg["repository"].get("intake_opened_at")
    if opened is None or stamp(opened) > now:
        errors.append("운영 개시일 미등록 또는 개시 전")
    if cfg["repository"].get("dashboard_issue") is None:
        errors.append("운영 현황 Issue 미등록")
    reviewers = cfg["reviewers"]
    for area in ("registry", "automation"):
        if not reviewers[area] or any(member(cfg, x) is None or stamp(member(cfg, x)["registered_at"]) > now for x in reviewers[area]):
            errors.append(f"reviewers.{area}: 등록된 검토자 필요")
        if len(set(reviewers[area])) < 2:
            errors.append(f"reviewers.{area}: 작성자 외 승인을 위해 서로 다른 검토자 2명 필요")
    if len(set(reviewers["registry"] + reviewers["automation"])) < 2:
        errors.append("서로 다른 검토자 최소 2명 필요")
    coordinators = coordinator_ids(cfg, role_comments, now)
    for name, data in cfg["coordination"].items():
        if data.get("user_id") not in coordinators or not _member_consent(cfg, role_comments, data.get("acceptance_comment_id"), data.get("user_id"), f"/역할수락 coordination.{name}", now):
            errors.append(f"coordination.{name}: 등록과 본인 수락 필요")
    if cfg["coordination"]["primary"].get("user_id") == cfg["coordination"]["backup"].get("user_id"):
        errors.append("예외 담당자와 부재 시 대행자는 서로 다른 구성원이어야 함")
    if require_ready_route and not any(not route_errors(cfg, route_id, role_comments, now) for route_id in cfg["routes"]):
        errors.append("활성화 가능한 책임이 하나 이상 필요")
    return errors


def quiet(cfg: dict, when: datetime) -> bool:
    today = stamp(when).astimezone(KST).date()
    return any(date.fromisoformat(x["start"]) <= today <= date.fromisoformat(x["end"]) for x in cfg["calendar"]["quiet_periods"])


def business_day(cfg: dict, day: date) -> bool:
    return day.weekday() < 5 and day.isoformat() not in cfg["calendar"]["non_working_dates"] and not quiet(cfg, datetime.combine(day, time.min, KST))


def effective_check_date(cfg: dict, day: date) -> date:
    while not business_day(cfg, day):
        day += timedelta(days=1)
    return day


def add_business_days(cfg: dict, start: datetime, count: int) -> datetime:
    if type(count) is not int or count < 1:
        raise ValueError("business-day count must be a positive integer")
    cursor = stamp(start).astimezone(KST).date()
    while count:
        cursor += timedelta(days=1)
        if business_day(cfg, cursor):
            count -= 1
    return datetime.combine(cursor, time(23, 59, 59), KST)
