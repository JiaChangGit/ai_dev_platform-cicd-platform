#!/usr/bin/env python3

import json
import shutil
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
            self.assertEqual(validate_release_layout(release), [])
            self.assertFalse((release / "external").exists())
            self.assertFalse((release / "app").exists())

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
