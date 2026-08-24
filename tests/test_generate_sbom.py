#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_sbom import generate_sbom  # noqa: E402


class GenerateSbomTest(unittest.TestCase):
    def test_generates_spdx_for_files_and_third_party_components(self):
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "ai-dev-platform-1.4.0.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "ai-dev-platform/RELEASE-MANIFEST.json",
                    json.dumps(
                        {
                            "platformId": "ai-dev-platform",
                            "version": "1.4.0",
                            "files": [{"path": "README.md", "sha256": "a" * 64}],
                        }
                    ),
                )
                archive.writestr(
                    "ai-dev-platform/distribution/third-party-notices.json",
                    json.dumps(
                        {
                            "entries": [
                                {
                                    "id": "example-skill",
                                    "snapshotTree": "b" * 40,
                                    "syncRepository": "https://github.com/example/skill.git",
                                    "licenseEvidence": "external/example/LICENSE",
                                }
                            ]
                        }
                    ),
                )

            result = generate_sbom(
                archive_path,
                repository="https://github.com/example/platform",
                created="2026-08-24T00:00:00Z",
            )

            self.assertEqual(result["spdxVersion"], "SPDX-2.3")
            self.assertEqual(result["creationInfo"]["created"], "2026-08-24T00:00:00Z")
            self.assertEqual(len(result["files"]), 1)
            self.assertEqual({item["name"] for item in result["packages"]}, {"ai-dev-platform", "example-skill"})
            self.assertIn("/releases/tag/v1.4.0/spdx-", result["documentNamespace"])
            self.assertTrue(
                any(item["relationshipType"] == "DEPENDS_ON" for item in result["relationships"])
            )


if __name__ == "__main__":
    unittest.main()
