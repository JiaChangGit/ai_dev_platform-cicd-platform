#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_skills import audit_skills  # noqa: E402


class SkillAuditTest(unittest.TestCase):
    def test_all_packaged_skills_follow_routing_policy(self):
        result = audit_skills(ROOT)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["packagedSkillCount"], 62)
        self.assertGreaterEqual(result["triggerTestCount"], 15)


if __name__ == "__main__":
    unittest.main()
