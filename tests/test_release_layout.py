#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_release_layout import validate_release_layout  # noqa: E402


def valid_evidence() -> dict:
    return {
        "schemaVersion": 2,
        "product": "sample-product",
        "version": "1.0.0",
        "source": {"repository": "https://example.invalid/product.git", "commit": "a" * 40, "ref": "refs/heads/main"},
        "artifact": {
            "uri": "artifact://immutable/sample/1.0.0", "sha256": "0" * 64,
            "immutable": True, "signatureUri": "artifact://immutable/sample/1.0.0.sig",
            "signatureSha256": "1" * 64, "signatureAlgorithm": "openssl-sha256",
        },
        "verification": {"ciSystem": "internal-ci", "runId": "run-1", "checks": ["build", "test", "lint", "security", "package"]},
        "sbom": {"uri": "artifact://immutable/sample/1.0.0.sbom.json", "sha256": "2" * 64, "format": "spdx-json"},
        "provenance": {"uri": "artifact://immutable/sample/1.0.0.provenance.json", "sha256": "3" * 64, "predicateType": "https://slsa.dev/provenance/v1"},
        "approval": {"status": "approved", "approvedBy": "independent-reviewer"},
        "release": {"publisher": "publisher"},
    }


class ReleaseLayoutTest(unittest.TestCase):
    def test_accepts_release_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "release-evidence").mkdir()
            (root / "release-notes").mkdir()
            (root / "release-evidence/1.0.0.json").write_text(
                json.dumps(valid_evidence()), encoding="utf-8"
            )
            (root / "release-notes/1.0.0.md").write_text("# v1.0.0\n", encoding="utf-8")
            self.assertEqual(validate_release_layout(root), [])

    def test_rejects_artifacts_source_and_external_skills(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in (
                "firmware.bin",
                "main.c",
                "app/src/Main.kt",
                "external/vendor/SKILL.md",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("not allowed", encoding="utf-8")
            errors = validate_release_layout(root)
            self.assertTrue(any("firmware.bin" in error for error in errors))
            self.assertTrue(any("main.c" in error for error in errors))
            self.assertTrue(any("external" in error for error in errors))

    def test_rejects_invalid_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "release-evidence").mkdir()
            (root / "release-evidence/bad.json").write_text("{}", encoding="utf-8")
            self.assertTrue(validate_release_layout(root))

    def test_rejects_version_and_note_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "release-evidence").mkdir()
            (root / "release-notes").mkdir()
            evidence = valid_evidence()
            evidence["version"] = "2.0.0"
            (root / "release-evidence/1.0.0.json").write_text(json.dumps(evidence), encoding="utf-8")
            (root / "release-notes/1.0.0.md").write_text("# v9.9.9\n", encoding="utf-8")
            errors = validate_release_layout(root)
            self.assertTrue(any("version" in error for error in errors))
            self.assertTrue(any("Release Note" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
