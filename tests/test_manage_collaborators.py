#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from manage_collaborators import (  # noqa: E402
    MAINTENANCE_PATTERNS,
    RELEASE_PATTERNS,
    canonical_codeowners,
    codeowner_errors,
    local_policy_errors,
    parse_github_repository,
    parse_gitlab_project,
    repository_context,
    validate_gitlab_api_url,
    validate_username,
)


class CollaboratorManagementTest(unittest.TestCase):
    def test_parses_supported_remotes(self):
        self.assertEqual(
            parse_github_repository("git@github.com:Owner/repository.git"),
            "Owner/repository",
        )
        self.assertEqual(
            parse_gitlab_project("https://gitlab.com/group/subgroup/repository.git"),
            "group/subgroup/repository",
        )

    def test_rejects_unsafe_values(self):
        for username in ("-prefix", "name with spaces", "user;rm", ""):
            with self.subTest(username=username), self.assertRaises(ValueError):
                validate_username(username)
        with self.assertRaises(ValueError):
            validate_gitlab_api_url("http://gitlab.example.test/api/v4", allow_insecure_http=False)
        with self.assertRaises(ValueError):
            validate_gitlab_api_url("https://user:secret@example.test/api/v4", allow_insecure_http=False)

    def test_adds_owner_and_missing_rules_idempotently(self):
        original = "# owners\n* @owner\n/governance/ @owner\n"
        first = canonical_codeowners(
            original,
            username="reviewer",
            primary_owner="owner",
            default_patterns=MAINTENANCE_PATTERNS,
        )
        second = canonical_codeowners(
            first,
            username="reviewer",
            primary_owner="owner",
            default_patterns=MAINTENANCE_PATTERNS,
        )
        self.assertEqual(first, second)
        self.assertEqual(codeowner_errors(first, required_patterns=MAINTENANCE_PATTERNS), [])
        for pattern in MAINTENANCE_PATTERNS:
            self.assertIn(f"{pattern} @owner @reviewer", first)

    def test_detects_release_repository_and_policy_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            (root / "release-evidence").mkdir()
            (root / "release-notes").mkdir()
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".gitlab").mkdir()
            (root / ".github/workflows/repository-policy.yml").write_text("name: test\n", encoding="utf-8")
            (root / ".gitlab-ci.yml").write_text("stages: [check]\n", encoding="utf-8")
            content = canonical_codeowners(
                "",
                username="reviewer",
                primary_owner="owner",
                default_patterns=RELEASE_PATTERNS,
            )
            (root / ".github/CODEOWNERS").write_text(content, encoding="utf-8")
            (root / ".gitlab/CODEOWNERS").write_text(content, encoding="utf-8")
            context = repository_context(root)
            self.assertEqual(context.kind, "release")
            self.assertEqual(local_policy_errors(context), [])


if __name__ == "__main__":
    unittest.main()
