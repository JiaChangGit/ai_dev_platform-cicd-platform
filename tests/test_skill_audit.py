#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_skills import (  # noqa: E402
    audit_skills,
    load_yaml,
    local_reference_is_packaged,
    parse_skill,
)


class SkillAuditTest(unittest.TestCase):
    def test_all_packaged_skills_follow_routing_policy(self):
        result = audit_skills(ROOT)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["packagedSkillCount"], 62)
        self.assertEqual(result["descriptionAuditCount"], 62)
        self.assertEqual(result["catalogSourceCount"], 7)
        self.assertEqual(result["manualOnlyCount"], 16)
        self.assertEqual(result["collisionGroupCount"], 7)
        self.assertEqual(result["triggerTestCount"], 43)
        self.assertEqual(result["guardedRouteCount"], 34)

    def test_routing_yaml_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "routing.yaml"
            path.write_text("schemaVersion: 1\nschemaVersion: 2\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "重複 key"):
                load_yaml(path)

    def test_skill_frontmatter_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SKILL.md"
            path.write_text(
                "---\nname: sample\nname: duplicate\ndescription: sample\n---\n\n# Sample\n",
                encoding="utf-8",
            )

            _, _, errors = parse_skill(path)

            self.assertTrue(any("重複 key" in error for error in errors), errors)

    def test_local_skill_reference_must_be_in_distribution_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / "external/vendor/sample/SKILL.md"
            reference = skill.parent / "references/guide.md"
            reference.parent.mkdir(parents=True)
            skill.write_text("skill\n", encoding="utf-8")
            reference.write_text("guide\n", encoding="utf-8")

            self.assertFalse(
                local_reference_is_packaged(root, skill, "references/guide.md", {"external/vendor/sample/SKILL.md"})
            )
            self.assertTrue(
                local_reference_is_packaged(
                    root,
                    skill,
                    "references/guide.md",
                    {
                        "external/vendor/sample/SKILL.md",
                        "external/vendor/sample/references/guide.md",
                    },
                )
            )

    def test_current_routing_cases_do_not_repeat_expected_or_forbidden_paths(self):
        routing = load_yaml(ROOT / "registry/skill-routing.yaml")
        for case in routing["triggerTests"]:
            with self.subTest(prompt=case["prompt"]):
                self.assertEqual(len(case["expect"]), len(set(case["expect"])))
                self.assertEqual(len(case["forbid"]), len(set(case["forbid"])))


if __name__ == "__main__":
    unittest.main()
