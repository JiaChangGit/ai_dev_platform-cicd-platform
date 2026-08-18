#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pre_push_audit import find_secret_types  # noqa: E402


class PrePushConfigurationTest(unittest.TestCase):
    def test_sensitive_and_generated_files_are_ignored(self):
        rules = {
            line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for rule in (".env", ".env.*", "!.env.example", "*.pem", "*.key", "dist/", "build/", "/.ai/handoffs/"):
            self.assertIn(rule, rules)

    def test_scans_large_text_files_in_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.txt"
            with path.open("wb") as stream:
                for _ in range(21):
                    stream.write(b"a" * 1024 * 1024)
                stream.write(b"-----BEGIN " + b"PRIVATE KEY-----\n")
            self.assertEqual(find_secret_types(path), ["private-key"])


if __name__ == "__main__":
    unittest.main()
