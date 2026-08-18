#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pre_push_audit import (  # noqa: E402
    find_secret_types,
    inspect_git_identity,
    is_safe_remote_url,
)


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

    def test_local_mode_requires_git_identity(self):
        failure = subprocess.CalledProcessError(1, ["git", "config", "user.name"])
        with mock.patch("pre_push_audit.git", side_effect=failure):
            identity, errors, warnings = inspect_git_identity(ROOT, required=True)
        self.assertEqual(identity, {"name": "", "email": ""})
        self.assertEqual(errors, ["Git user.name 與 user.email 必須先設定"])
        self.assertEqual(warnings, [])

    def test_ci_mode_does_not_require_git_identity(self):
        failure = subprocess.CalledProcessError(1, ["git", "config", "user.name"])
        with mock.patch("pre_push_audit.git", side_effect=failure):
            identity, errors, warnings = inspect_git_identity(ROOT, required=False)
        self.assertEqual(identity, {"name": "", "email": ""})
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_ci_workflows_select_ci_mode_explicitly(self):
        github = (ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8")
        gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
        command = "python3 -B scripts/pre_push_audit.py --ci"
        self.assertIn(command, github)
        self.assertIn(command, gitlab)

    def test_accepts_git_hosts_without_embedded_credentials(self):
        for remote in (
            "git@github.com:owner/repository.git",
            "git@gitlab.example:group/repository.git",
            "ssh://git@git.internal.example:2222/group/repository.git",
            "https://github.com/owner/repository.git",
            "https://gitlab.example/group/repository.git",
        ):
            with self.subTest(remote=remote):
                self.assertTrue(is_safe_remote_url(remote))

    def test_rejects_remote_with_embedded_credentials(self):
        self.assertFalse(
            is_safe_remote_url("https://gitlab-ci-token:secret@gitlab.example/group/repository.git")
        )


if __name__ == "__main__":
    unittest.main()
