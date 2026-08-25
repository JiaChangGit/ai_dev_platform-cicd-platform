#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMOTION = ROOT / ".github" / "workflows" / "promote-release.yml"


class ReleaseWorkflowTest(unittest.TestCase):
    def test_promotion_replaces_candidate_title_and_notes(self):
        workflow = PROMOTION.read_text(encoding="utf-8")

        self.assertIn('--prerelease=false', workflow)
        self.assertIn('--title "AI Dev Platform v${VERSION}"', workflow)
        self.assertIn('--notes-file formal-release-notes.md', workflow)
        self.assertIn('release-notes/${VERSION}.md', workflow)
        self.assertIn('release-evidence/${VERSION}.json', workflow)


if __name__ == "__main__":
    unittest.main()
