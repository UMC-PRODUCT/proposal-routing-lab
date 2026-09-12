from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from intake.generate import generate, generated_files, UNKNOWN
from intake.registry import (
    activation_errors, add_business_days, business_day, coordinator_ids,
    effective_check_date, iso, load_registry, member, quiet, route_errors,
    route_version, stamp, validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = stamp("2026-09-15T12:00:00+09:00")


def prepared():
    cfg = load_registry(ROOT / "registry/ownership.yml")
    cfg["members"] = [
        {"id": value, "login": f"test-user-{value}", "active": True, "registered_at": "2026-09-13T00:00:00+09:00"}
        for value in (10, 11, 12, 13)
    ]
    cfg["reviewers"] = {"registry": [10, 11], "automation": [11, 12]}
    cfg["repository"].update({"dashboard_issue": 6, "intake_opened_at": "2026-09-15T00:00:00+09:00"})
    cfg["repository"]["excluded_issue_numbers"] = [1, 2, 3, 4, 5, 6]
    cfg["readiness"] = {"protection_verified": True, "usability_verified": True}
    route = cfg["routes"]["brand-and-growth"]
    route.update({"owner_id": 10, "enabled": True, "acceptance_comment_id": 100})
    cfg["coordination"] = {
        "primary": {"user_id": 11, "acceptance_comment_id": 101},
        "backup": {"user_id": 12, "acceptance_comment_id": 102},
    }
    comments = [
        comment(100, 10, f"/역할수락 brand-and-growth {route_version(route)}"),
        comment(101, 11, "/역할수락 coordination.primary"),
        comment(102, 12, "/역할수락 coordination.backup"),
    ]
    return cfg, comments


def comment(comment_id, author, body):
    return {
        "id": comment_id,
        "user": {"id": author, "login": f"renamed-{author}", "type": "User"},
        "body": body,
        "created_at": "2026-09-14T09:00:00+09:00",
        "updated_at": "2026-09-14T09:00:00+09:00",
    }


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.comments = prepared()

    def test_initial_registry_is_valid_but_cannot_activate(self):
        cfg = load_registry(ROOT / "registry/ownership.yml")
        self.assertEqual([], validate_registry(cfg))
        self.assertTrue(activation_errors(cfg, [], NOW))
        self.assertEqual(9, sum(len(route["products"]) for route in cfg["routes"].values()))
        self.assertEqual({"돌민", "조이", "모루", "루씨"}, {r["display_name"] for r in cfg["routes"].values() if r["type"] == "Purpose"})

    def test_registry_can_activate_only_with_all_common_gates(self):
        self.assertEqual([], activation_errors(self.cfg, self.comments, NOW))
        for section, field, value in [
            ("readiness", "protection_verified", False),
            ("readiness", "usability_verified", False),
            ("repository", "intake_opened_at", None),
            ("repository", "dashboard_issue", None),
            ("reviewers", "automation", []),
        ]:
            cfg = deepcopy(self.cfg)
            cfg[section][field] = value
            with self.subTest(field=field):
                self.assertTrue(activation_errors(cfg, self.comments, NOW))

    def test_registration_clock_prevents_retroactive_consent(self):
        self.cfg["members"][0]["registered_at"] = "2026-09-15T01:00:00+09:00"
        self.assertTrue(route_errors(self.cfg, "brand-and-growth", self.comments, NOW))

    def test_numeric_identity_survives_username_change(self):
        self.assertEqual(10, member(self.cfg, 10)["id"])
        self.assertEqual([], route_errors(self.cfg, "brand-and-growth", self.comments, NOW))
        self.comments[0]["user"]["id"] = 999
        self.comments[0]["user"]["login"] = self.cfg["members"][0]["login"]
        self.assertTrue(route_errors(self.cfg, "brand-and-growth", self.comments, NOW))
        self.assertIsNone(member(self.cfg, "10"))
        self.assertIsNone(member(self.cfg, True))

    def test_bot_quoted_deleted_and_wrong_version_consent_rejected(self):
        for mutate in [
            lambda c: c[0]["user"].update(type="Bot"),
            lambda c: c[0].update(body="```\n" + c[0]["body"] + "\n```"),
            lambda c: c[0].update(body=c[0]["body"] + " extra"),
            lambda c: c[0].update(body="/역할수락 brand-and-growth stale"),
            lambda c: c[0].update(body=None),
            lambda c: c.pop(0),
            lambda c: c.append(deepcopy(c[0])),
        ]:
            comments = deepcopy(self.comments)
            mutate(comments)
            self.assertTrue(route_errors(self.cfg, "brand-and-growth", comments, NOW))

    def test_consent_cannot_authorize_actions_before_creation_or_edit(self):
        self.assertTrue(route_errors(self.cfg, "brand-and-growth", self.comments, stamp("2026-09-13T12:00:00+09:00")))
        self.comments[0]["updated_at"] = "2026-09-16T00:00:00+09:00"
        self.assertTrue(route_errors(self.cfg, "brand-and-growth", self.comments, NOW))

    def test_route_version_is_per_responsibility(self):
        route = self.cfg["routes"]["brand-and-growth"]
        version = route_version(route)
        for name in ("acceptance_comment_id", "handoff_comment_id", "enabled", "display_name"):
            edited = deepcopy(route)
            edited[name] = "a new value"
            self.assertEqual(version, route_version(edited))
        for name in ("owner_id", "scope", "starts_at", "ends_at", "review_on", "products"):
            edited = deepcopy(route)
            edited[name] = "a new value"
            self.assertNotEqual(version, route_version(edited))
        self.cfg["routes"]["learning-and-activity"]["scope"] = "changed scope"
        self.assertEqual([], route_errors(self.cfg, "brand-and-growth", self.comments, NOW))

    def test_expiry_is_exclusive_and_does_not_auto_extend(self):
        self.assertEqual([], route_errors(self.cfg, "brand-and-growth", self.comments, stamp("2026-11-07T23:59:59+09:00")))
        self.assertTrue(route_errors(self.cfg, "brand-and-growth", self.comments, stamp("2026-11-08T00:00:00+09:00")))
        self.assertTrue(route_errors(self.cfg, "unknown-route", self.comments, NOW))

    def test_distinct_coordinators_need_own_linked_acceptance(self):
        self.assertEqual({11, 12}, coordinator_ids(self.cfg, self.comments, NOW))
        self.cfg["coordination"]["backup"]["user_id"] = 11
        self.assertTrue(activation_errors(self.cfg, self.comments, NOW))
        self.cfg["coordination"]["backup"]["user_id"] = 12
        self.comments[2]["user"]["id"] = 11
        self.assertEqual({11}, coordinator_ids(self.cfg, self.comments, NOW))

    def test_each_review_area_can_be_approved_by_someone_other_than_author(self):
        self.cfg['reviewers']['registry'] = [10]
        self.assertTrue(activation_errors(self.cfg, self.comments, NOW))

    def test_drain_omits_ready_route_gate_but_keeps_protection_gate(self):
        later = stamp('2026-11-09T00:00:00+09:00')
        self.assertTrue(activation_errors(self.cfg, self.comments, later))
        self.assertEqual([], activation_errors(self.cfg, self.comments, later, require_ready_route=False))
        self.cfg['readiness']['protection_verified'] = False
        self.assertTrue(activation_errors(self.cfg, self.comments, later, require_ready_route=False))

    def test_schema_does_not_treat_truthy_values_as_permissions(self):
        cases = [
            lambda c: c["members"][0].update(id=True),
            lambda c: c["members"][0].update(active="true"),
            lambda c: c["members"][0].pop("registered_at"),
            lambda c: c["routes"]["brand-and-growth"].update(enabled="true"),
            lambda c: c["repository"].update(control_issue=0),
            lambda c: c["calendar"].update(quiet_periods=[{"start": "2026-10-24", "end": "2026-10-19"}]),
            lambda c: c["routes"]["brand-and-growth"].update(ends_at="2026-09-12T00:00:00+09:00"),
            lambda c: c["reviewers"].update(registry=[True]),
        ]
        for mutate in cases:
            cfg = deepcopy(self.cfg)
            mutate(cfg)
            self.assertTrue(validate_registry(cfg))
        for malformed in (None, [], {"version": 1}, {"routes": []}):
            self.assertTrue(validate_registry(malformed))

    def test_duplicate_keys_and_product_labels_are_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.yml"
            path.write_text("version: 1\nversion: 1\n")
            with self.assertRaisesRegex(ValueError, "unique"):
                load_registry(path)
        route = self.cfg["routes"]["brand-and-growth"]
        route["products"].append(deepcopy(route["products"][0]))
        self.assertTrue(validate_registry(self.cfg))


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_registry(ROOT / "registry/ownership.yml")

    def test_october_exam_period_excludes_days_from_deadline(self):
        due = add_business_days(self.cfg, stamp("2026-10-16T12:00:00+09:00"), 3)
        self.assertEqual("2026-10-28T23:59:59+09:00", due.isoformat())
        self.assertEqual("2026-10-28T14:59:59Z", iso(due))
        self.assertEqual(date(2026, 10, 26), effective_check_date(self.cfg, date(2026, 10, 19)))

    def test_exam_is_inclusive_and_timezone_aware(self):
        self.assertTrue(quiet(self.cfg, stamp("2026-10-18T15:00:00Z")))
        self.assertTrue(quiet(self.cfg, stamp("2026-10-24T14:59:59Z")))
        self.assertFalse(quiet(self.cfg, stamp("2026-10-24T15:00:00Z")))
        self.assertFalse(business_day(self.cfg, date(2026, 10, 23)))
        self.assertFalse(business_day(self.cfg, date(2026, 10, 25)))
        self.assertTrue(business_day(self.cfg, date(2026, 10, 26)))

    def test_holidays_and_submission_day_are_excluded(self):
        self.assertEqual(date(2026, 10, 6), add_business_days(self.cfg, stamp("2026-10-02T00:00:00+09:00"), 1).date())
        self.assertEqual(date(2026, 9, 28), add_business_days(self.cfg, stamp("2026-09-23T18:00:00+09:00"), 1).date())
        self.assertEqual(date(2026, 10, 13), effective_check_date(self.cfg, date(2026, 10, 13)))

    def test_naive_datetime_and_invalid_day_count_are_rejected(self):
        with self.assertRaises(ValueError):
            stamp("2026-09-13T12:00:00")
        with self.assertRaises(ValueError):
            iso(datetime(2026, 9, 13))
        for count in (0, -1, True, "3"):
            with self.assertRaises(ValueError):
                add_business_days(self.cfg, datetime.now(timezone.utc), count)


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_registry(ROOT / "registry/ownership.yml")

    def test_forms_have_only_three_required_inputs_and_two_choices(self):
        outputs = generated_files(self.cfg)
        forms = [yaml.safe_load(outputs[f".github/ISSUE_TEMPLATE/{name}.yml"]) for name in ("product", "design-system")]
        for form in forms:
            required = [item["id"] for item in form["body"] if item.get("validations", {}).get("required")]
            self.assertEqual(["target", "problem", "help"], required)
            self.assertNotIn("assignees", form)
            self.assertIn("공개", form["body"][0]["attributes"]["value"])
        targets = forms[0]["body"][1]["attributes"]["options"]
        self.assertEqual(9, len(targets))
        self.assertIn(UNKNOWN, targets)
        self.assertIn("기수·조직·구성원·역할·상벌점·운영 승인", targets)
        self.assertIn("Design Platform", forms[1]["body"][0]["attributes"]["value"])
        self.assertIn("현재 정상 자동 접수를 시작하지 않았습니다", forms[1]["body"][0]["attributes"]["value"])
        self.assertEqual(5, len(outputs))

    def test_generation_is_deterministic_and_check_is_read_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(5, len(generate(root, self.cfg, check=True)))
            self.assertEqual([], list(root.iterdir()))
            self.assertEqual(5, len(generate(root, self.cfg)))
            self.assertEqual([], generate(root, self.cfg, check=True))
            target = root / "docs/ownership-registry.md"
            target.write_text("stale")
            self.assertEqual(["docs/ownership-registry.md"], generate(root, self.cfg, check=True))
            self.assertEqual("stale", target.read_text())

    def test_codeowners_separates_registry_and_automation_from_verified_accounts(self):
        cfg, _ = prepared()
        text = generated_files(cfg)['.github/CODEOWNERS']
        self.assertIn('/registry/ @test-user-10 @test-user-11', text)
        self.assertIn('/intake/ @test-user-11 @test-user-12', text)
        self.assertIn('/.github/CODEOWNERS @test-user-10 @test-user-11 @test-user-12', text)
        self.assertFalse(any(line and not line.startswith('#') for line in generated_files(self.cfg)['.github/CODEOWNERS'].splitlines()))

    def test_generated_files_match_registry_and_no_sensitive_rationale(self):
        self.assertEqual([], generate(ROOT, self.cfg, check=True))
        text = generated_files(self.cfg)["docs/ownership-registry.md"]
        self.assertNotIn("인원-배치", text)
        self.assertNotIn("커피챗", text)
        self.assertIn("registered_at", text)

    def test_generated_calendar_comes_from_registry(self):
        self.cfg["calendar"]["quiet_periods"] = [{"start": "2027-01-01", "end": "2027-01-02"}]
        text = generated_files(self.cfg)["docs/ownership-registry.md"]
        self.assertIn("2027-01-01 ~ 2027-01-02", text)
        self.assertNotIn("2026-10-19", text)


if __name__ == "__main__":
    unittest.main()
