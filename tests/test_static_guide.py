#!/usr/bin/env python3

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "index.html"
GETTING_STARTED = ROOT / "docs" / "getting-started.md"


class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.scripts = 0
        self.external_resources: list[str] = []
        self.lang = ""
        self.csp = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if value := values.get("id"):
            self.ids.add(value)
        if tag == "html":
            self.lang = values.get("lang", "") or ""
        if tag == "script":
            self.scripts += 1
        if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
            self.csp = values.get("content", "") or ""
        for name in ("src", "href"):
            value = values.get(name) or ""
            if re.match(r"^(?:https?:)?//", value):
                self.external_resources.append(value)


class StaticGuideTest(unittest.TestCase):
    def test_is_private_offline_and_structurally_complete(self):
        text = GUIDE.read_text(encoding="utf-8")
        parser = GuideParser()
        parser.feed(text)

        self.assertEqual(parser.lang, "zh-Hant-TW")
        self.assertEqual(parser.scripts, 0)
        self.assertEqual(parser.external_resources, [])
        self.assertIn("default-src 'none'", parser.csp)
        self.assertIn("connect-src 'none'", parser.csp)
        self.assertTrue(
            {"main", "purpose", "architecture", "flow-section", "setup", "cases",
             "boundaries", "cleanup", "release", "github", "troubleshooting",
             "verify"}.issubset(parser.ids)
        )
        for private_marker in ("/home/", "\\Users\\", "@gmail.", "github.com/Jia"):
            self.assertNotIn(private_marker, text)

    def test_cites_executable_sources_for_key_claims(self):
        text = GUIDE.read_text(encoding="utf-8")
        for source in (
            "scripts/init_product.py",
            "scripts/package_release.py",
            "scripts/install_platform.py",
            "scripts/audit_workspace.py",
            "scripts/verify_release_layout.py",
            "scripts/verify_release_evidence.py",
            "scripts/verify_release_readiness.py",
        ):
            self.assertIn(source, text)

    def test_does_not_tell_products_to_modify_read_only_platform(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertNotIn("REPLACE_WITH_ACTUAL_MODEL_ID", text)
        self.assertIn("不修改唯讀平台", text)

    def test_distinguishes_evidence_contract_from_readiness(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("JSON 契約、必要 checks、SHA-256 格式", text)
        self.assertIn("實體 artifact／signature／SBOM／provenance", text)
        self.assertIn("不會連線查詢 CI run", text)

    def test_onboarding_commands_use_safe_paths_and_dry_run(self):
        text = GETTING_STARTED.read_text(encoding="utf-8")
        self.assertNotIn("cd <Work>", text)
        self.assertNotIn("目前 GitHub 尚未發布第一份正式 Release", text)
        self.assertIn("scripts/init_product.py", text)
        self.assertIn("--dry-run", text)
        for option in ("--product-type", "--target-platform", "--language-framework", "--with-example"):
            self.assertIn(option, text)


if __name__ == "__main__":
    unittest.main()
