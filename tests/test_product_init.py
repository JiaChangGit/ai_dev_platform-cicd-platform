#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from init_product import ProductConfig, create_product_workspace, validate_product_name  # noqa: E402
from verify_release_layout import validate_release_layout  # noqa: E402


def config(domain: str = "android", ci: str = "github-actions") -> ProductConfig:
    if domain == "android":
        return ProductConfig(
            name="sample-product",
            display_name="Sample Product",
            domain=domain,
            ci=ci,
            product_type="Android App",
            target_platform="Android 23 以上",
            language_framework="Kotlin、Gradle、Android SDK",
            build_command="gradle --no-daemon :app:assembleDebug",
            test_command="gradle --no-daemon :app:testDebugUnitTest",
            lint_command="gradle --no-daemon :app:lintDebug",
            package_command="gradle --no-daemon :app:assembleRelease",
            artifact_path="app/build/outputs/apk/release/app-release-unsigned.apk",
        )
    if domain == "ssd-pcie-fw":
        return ProductConfig(
            name="sample-product",
            display_name="Sample Product",
            domain=domain,
            ci=ci,
            product_type="SSD PCIe 韌體",
            target_platform="測試控制器",
            language_framework="C11、Make",
            build_command="make all",
            test_command="make test",
            lint_command="make lint",
            package_command="make package",
            artifact_path="dist/ssd-pcie-fw-sample.elf",
        )
    return ProductConfig(
        name="sample-product",
        display_name="Sample Product",
        domain=domain,
        ci=ci,
        product_type="規格閱讀手冊",
        target_platform="虛構規格",
        language_framework="Markdown、HTML、Python 3",
        build_command="python3 -B validate.py",
        test_command="python3 -B validate.py",
        lint_command="python3 -B validate.py",
        package_command=(
            "mkdir -p dist && python3 -m zipfile -c dist/spec-handbook.zip "
            "SAMPLE.md source-register.md sample-spec.md reading-notes.md index.html validate.py"
        ),
        artifact_path="dist/spec-handbook.zip",
    )


class ProductInitTest(unittest.TestCase):
    def prepare_platform(self, output_root: Path) -> Path:
        platform = output_root / "ai-dev-platform"
        platform.mkdir()
        for relative in ("AGENTS.md", "templates/product-entrypoint", "adapters/ci", "examples"):
            source = ROOT / relative
            target = platform / relative
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        return platform

    def test_creates_parallel_product_and_metadata_only_release(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            platform = self.prepare_platform(output_root)
            product, release = create_product_workspace(
                platform,
                output_root,
                config(),
                with_example=True,
                initialize_git=False,
            )

            self.assertEqual(product.parent, platform.parent)
            self.assertEqual(release.parent, platform.parent)
            self.assertIn("../ai-dev-platform/AGENTS.md", (product / "AGENTS.md").read_text())
            metadata = json.loads((product / ".ai/product.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["platformVersionPolicy"], "always-current")
            self.assertFalse((product / "external").exists())
            self.assertTrue((product / "app/src/main/AndroidManifest.xml").is_file())
            product_guide = (product / "README.md").read_text(encoding="utf-8")
            self.assertIn("../ai-dev-platform/docs/getting-started.md", product_guide)
            self.assertNotIn("第三方 skill", product_guide)
            self.assertNotIn("external/", product_guide)
            self.assertIn("gradle --no-daemon :app:assembleRelease", product_guide)
            self.assertIn("基本 CI 只執行 lint、test 與 build", product_guide)
            self.assertEqual(validate_release_layout(release), [])
            self.assertFalse((release / "external").exists())
            self.assertFalse((release / "app").exists())
            release_ignore = (release / ".gitignore").read_text(encoding="utf-8")
            for rule in (".env", "*.pem", "*.key", "credentials/", "/.ai/handoffs/", "*.zip"):
                self.assertIn(rule, release_ignore)
            self.assertIn("獨立 `.git`", (release / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertNotIn("docs/release-evidence.md", (release / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn(
                "verify_release_readiness.py",
                (release / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "verify_release_readiness.py",
                (release / "README.md").read_text(encoding="utf-8"),
            )
            release_guide = (release / "README.md").read_text(encoding="utf-8")
            self.assertIn("RELEASE_VERSION=1.0.0", release_guide)
            self.assertIn("不會連線到 CI", release_guide)
            self.assertLess(
                release_guide.index('git push -u origin "$RELEASE_BRANCH"'),
                release_guide.index('git tag -a "v${RELEASE_VERSION}"'),
            )
            tag_index = release_guide.index('git tag -a "v${RELEASE_VERSION}"')
            readiness_index = release_guide.index(
                "python3 -B ../ai-dev-platform/scripts/verify_release_readiness.py",
                tag_index,
            )
            self.assertLess(tag_index, readiness_index)

    def test_supports_every_ci_adapter(self):
        expected = {
            "github-actions": ".github/workflows/check.yml",
            "gitlab-ci": ".gitlab-ci.yml",
            "jenkins": "Jenkinsfile",
            "internal-ci": ".ci/internal-ci.json",
        }
        for ci, ci_path in expected.items():
            with self.subTest(ci=ci), tempfile.TemporaryDirectory() as temp:
                output_root = Path(temp)
                platform = self.prepare_platform(output_root)
                product, _ = create_product_workspace(
                    platform,
                    output_root,
                    config(domain="ssd-pcie-fw", ci=ci),
                    initialize_git=False,
                )
                self.assertTrue((product / ci_path).is_file())
                self.assertTrue(any((product / ".ci/release").iterdir()))

    def test_generic_domain_can_copy_spec_notes_example(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            platform = self.prepare_platform(output_root)
            product, _ = create_product_workspace(
                platform,
                output_root,
                config(domain="generic"),
                with_example=True,
                initialize_git=False,
            )

            for relative in (
                "SAMPLE.md",
                "source-register.md",
                "sample-spec.md",
                "reading-notes.md",
                "index.html",
                "validate.py",
            ):
                self.assertTrue((product / relative).is_file(), relative)
            self.assertIn("python3 -B validate.py", (product / "README.md").read_text(encoding="utf-8"))
            validation = subprocess.run(
                [sys.executable, "-B", "validate.py"],
                cwd=product,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout)

            if shutil.which("bash"):
                package = subprocess.run(
                    ["bash", "-lc", config(domain="generic").package_command],
                    cwd=product,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(package.returncode, 0, package.stdout)
                self.assertTrue((product / "dist/spec-handbook.zip").is_file())

    def test_generated_github_ci_pins_actions_and_uses_required_order(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            platform = self.prepare_platform(output_root)
            product, _ = create_product_workspace(
                platform,
                output_root,
                config(),
                initialize_git=False,
            )

            workflow = (product / ".github/workflows/check.yml").read_text(encoding="utf-8")
            self.assertNotIn("actions/checkout@v", workflow)
            self.assertNotIn("actions/setup-java@v", workflow)
            self.assertNotIn("gradle/actions/setup-gradle@v", workflow)
            self.assertLess(workflow.index("- name: Lint"), workflow.index("- name: Test"))
            self.assertLess(workflow.index("- name: Test"), workflow.index("- name: Build"))

    @unittest.skipUnless(shutil.which("git"), "需要 Git")
    def test_initializes_two_independent_git_repositories(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            platform = self.prepare_platform(output_root)
            product, release = create_product_workspace(
                platform,
                output_root,
                config(domain="ssd-pcie-fw", ci="gitlab-ci"),
                initialize_git=True,
            )
            self.assertTrue((product / ".git").is_dir())
            self.assertTrue((release / ".git").is_dir())
            self.assertEqual(validate_release_layout(release), [])

    def test_refuses_existing_target_without_partial_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            platform = self.prepare_platform(output_root)
            existing = output_root / "sample-product-cicd-platform"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                create_product_workspace(platform, output_root, config(), initialize_git=False)
            self.assertFalse((output_root / "sample-product-release").exists())

    def test_rejects_unsafe_product_name(self):
        for value in ("../escape", "UpperCase", "name with spaces", "-prefix"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_product_name(value)


if __name__ == "__main__":
    unittest.main()
