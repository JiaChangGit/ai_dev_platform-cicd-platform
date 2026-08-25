#!/usr/bin/env python3

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class DocumentationContractTest(unittest.TestCase):
    def test_offline_guide_matches_manifest_version(self):
        manifest = json.loads(read("distribution/manifest.json"))
        self.assertIn(f"平台版本 {manifest['version']}", read("docs/index.html"))

    def test_android_documentation_matches_build_files(self):
        root_build = read("examples/android-app/build.gradle.kts")
        app_build = read("examples/android-app/app/build.gradle.kts")
        guide = read("examples/android-app/SAMPLE.md")

        agp = re.search(r'com\.android\.application"\) version "([^"]+)"', root_build)
        self.assertIsNotNone(agp)
        self.assertIn(f"Android Gradle Plugin | {agp.group(1)}", guide)
        for name, pattern in (
            ("compileSdk", r"compileSdk = ([0-9]+)"),
            ("targetSdk", r"targetSdk = ([0-9]+)"),
            ("minSdk", r"minSdk = ([0-9]+)"),
        ):
            value = re.search(pattern, app_build)
            self.assertIsNotNone(value)
            self.assertIn(f"{name} | {value.group(1)}", guide)

        self.assertIn("Gradle | 9.4.1", guide)
        self.assertIn("JDK | 17", guide)
        self.assertIn("案例不含 wrapper", guide)
        self.assertIn("本機未重新執行 Android build", read("docs/documentation-validation.md"))

    def test_generated_actions_use_repository_pins(self):
        generator = read("scripts/init_product.py")
        check_workflow = read(".github/workflows/check.yml")
        setup_gradle = re.search(
            r"gradle/actions/setup-gradle@([0-9a-f]{40}) # v6\.3\.0",
            check_workflow,
        )
        self.assertIsNotNone(setup_gradle)
        self.assertIn(
            f"gradle/actions/setup-gradle@{setup_gradle.group(1)} # v6.3.0",
            generator,
        )
        for action in ("actions/checkout", "actions/setup-java", "gradle/actions/setup-gradle"):
            self.assertNotRegex(generator, rf"{re.escape(action)}@v[0-9]")

    def test_ssd_documentation_matches_header_and_makefile(self):
        header = read("examples/ssd-pcie-fw/include/fw_core.h")
        makefile = read("examples/ssd-pcie-fw/Makefile")
        guide = read("examples/ssd-pcie-fw/SAMPLE.md")

        capacity = re.search(r"#define FW_TRACE_CAPACITY ([0-9]+)U", header)
        self.assertIsNotNone(capacity)
        self.assertIn(f"容量 {capacity.group(1)}", guide)
        for event in (
            "FW_TRACE_READ_RECEIVED",
            "FW_TRACE_READ_ACCEPTED",
            "FW_TRACE_READ_REJECTED",
        ):
            self.assertIn(event, header)
            self.assertIn(event, guide)
        for target in ("clean", "lint", "test", "all", "package"):
            self.assertRegex(makefile, rf"(?m)^(?:\.PHONY:.*\b{target}\b|{target}:)")
            self.assertIn(f"make {target}", guide)
        for boundary in ("不能燒錄", "不實作 PCIe", "uint32_t next_sequence"):
            self.assertIn(boundary, guide)

    def test_spec_documentation_matches_validator_contract(self):
        guide = read("examples/spec-notes/SAMPLE.md")
        validator = read("examples/spec-notes/validate.py")
        for name in (
            "source-register.md",
            "sample-spec.md",
            "reading-notes.md",
            "index.html",
            "validate.py",
        ):
            self.assertIn(name, guide)
        for marker in (
            "SAMPLE-EVENT-EXPORT 1.0",
            "出現規格未定義的識別字",
            "index.html 不得包含 script",
            "index.html 不得載入外部資源",
        ):
            self.assertIn(marker, validator)
        self.assertIn("不能判斷摘要是否正確", guide)

    def test_onboarding_covers_download_config_sync_and_removal(self):
        guide = read("docs/getting-started.md")
        for heading in (
            "下載並驗證唯讀平台",
            "建立產品：先 dry-run",
            "把案例改成實際產品",
            "建立遠端與保護規則",
            "日常開發步驟",
            "更新既有 dev project",
            "要下載、同步、設定與移除的項目",
        ):
            self.assertIn(heading, guide)
        for option in (
            "--product-type",
            "--target-platform",
            "--language-framework",
            "--build-command",
            "--test-command",
            "--lint-command",
            "--package-command",
            "--artifact-path",
            "--with-example",
            "--dry-run",
        ):
            self.assertIn(option, guide)
        self.assertIn("source-register.md", guide)
        self.assertIn("commit-lint.sh --range origin/main..HEAD", guide)
        self.assertIn("gh pr create --base main", guide)
        self.assertIn("gh pr review <number> --approve", guide)
        self.assertIn("gh pr merge <number> --rebase --delete-branch", guide)

    def test_update_guide_targets_manifest_and_preserves_backup(self):
        manifest = json.loads(read("distribution/manifest.json"))
        guide = read("docs/update-existing-product.md")
        self.assertIn(f"PLATFORM_VERSION={manifest['version']}", guide)
        self.assertIn("--json isDraft --jq .isDraft", guide)
        self.assertIn("--json isPrerelease --jq .isPrerelease", guide)
        self.assertIn("--keep-backup", guide)
        self.assertIn("previous platform backup retained", guide)

    def test_case_guides_include_diagrams_and_product_boundaries(self):
        required = {
            "examples/ssd-pcie-fw/SAMPLE.md": ("flowchart", "sequenceDiagram", "產品端要提供"),
            "examples/android-app/SAMPLE.md": ("flowchart", "sequenceDiagram", "正式簽章與發布邊界"),
            "examples/spec-notes/SAMPLE.md": ("flowchart", "sequenceDiagram", "授權與機密邊界"),
        }
        for relative, markers in required.items():
            with self.subTest(relative=relative):
                text = read(relative)
                for marker in markers:
                    self.assertIn(marker, text)

    def test_primary_guides_avoid_promotional_or_conversational_phrases(self):
        banned = (
            "你只要",
            "神奇地",
            "輕鬆搞定",
            "無縫接軌",
            "一鍵完成",
            "革命性",
            "最佳體驗",
            "強大功能",
            "智能地",
            "智慧化",
            "身為 AI",
            "我是 AI",
        )
        paths = [ROOT / "README.md"]
        paths.extend(
            path for path in (ROOT / "docs").glob("*.md")
            if path.name != "terminology.md"
        )
        paths.extend((ROOT / "examples").glob("*/SAMPLE.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for phrase in banned:
                with self.subTest(path=path.relative_to(ROOT), phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_current_external_claims_have_dates_and_primary_sources(self):
        evidence = read("docs/documentation-validation.md")
        operations = read("docs/repository-operations.md")
        self.assertIn("2026-08-25", evidence)
        self.assertIn("2026-08-25", operations)
        for url in (
            "https://developer.android.com/build/releases/agp-9-2-0-release-notes",
            "https://developer.android.com/build/migrate-to-built-in-kotlin",
            "https://pcisig.com/specification-overview/pci-express-base",
            "https://nvmexpress.org/specifications/",
            "https://docs.github.com/en/actions/concepts/security/artifact-attestations",
            "https://docs.gitlab.com/user/project/repository/mirror/pull/",
            "https://docs.gitlab.com/user/project/merge_requests/approvals/",
        ):
            self.assertIn(url, evidence)


if __name__ == "__main__":
    unittest.main()
