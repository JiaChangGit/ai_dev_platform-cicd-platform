#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_ci_adapters import validate_ci_adapters  # noqa: E402


class CiAdapterTest(unittest.TestCase):
    def test_repository_adapters_follow_contract(self):
        self.assertEqual(validate_ci_adapters(ROOT), [])


if __name__ == "__main__":
    unittest.main()
