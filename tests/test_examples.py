#!/usr/bin/env python3

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExampleValidationTest(unittest.TestCase):
    def test_spec_notes_are_traceable_and_offline(self):
        root = ROOT / "examples/spec-notes"
        result = subprocess.run(
            [sys.executable, "-B", "validate.py"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertIn("3 個需求識別字", result.stdout)

    def test_android_sample_has_build_test_and_app_entrypoint(self):
        root = ROOT / "examples/android-app"
        build = (root / "build.gradle.kts").read_text(encoding="utf-8")
        app_build = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('version "9.2.0"', build)
        self.assertNotIn("org.jetbrains.kotlin.android", build + app_build)
        self.assertIn("compileSdk = 36", app_build)
        self.assertTrue((root / "app/src/main/AndroidManifest.xml").is_file())
        self.assertTrue((root / "app/src/test/java/dev/aiplatform/sample/BuildStatusTest.kt").is_file())

    @unittest.skipUnless(shutil.which("make") and shutil.which("cc"), "需要 make 與 C 編譯器")
    def test_firmware_sample_builds_tests_lints_and_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ssd-pcie-fw"
            shutil.copytree(ROOT / "examples/ssd-pcie-fw", root)
            subprocess.run(
                ["make", "all", "test", "lint", "package"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            artifact = root / "dist/ssd-pcie-fw-sample.elf"
            self.assertTrue(artifact.is_file())
            self.assertGreater(artifact.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
