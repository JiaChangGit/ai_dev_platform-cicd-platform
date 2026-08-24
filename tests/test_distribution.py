#!/usr/bin/env python3

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_package import RELEASE_MANIFEST, verify_archive  # noqa: E402
from package_release import zip_write  # noqa: E402


class DistributionVerifierTest(unittest.TestCase):
    def make_fixture(
        self,
        base: Path,
        prefixed: bool = True,
        unexpected: bool = False,
        wrong_mode: bool = False,
    ) -> tuple[Path, Path]:
        root = base / "source"
        (root / "distribution").mkdir(parents=True)
        (root / "docs").mkdir(parents=True)
        for name in ("AGENTS.md", "CLAUDE.md", "README.md", "opencode.json"):
            (root / name).write_text(name, encoding="utf-8")
        (root / "docs" / "guide.md").write_text("guide", encoding="utf-8")
        config = {
            "schemaVersion": 1,
            "platformId": "ai-dev-platform",
            "archiveRoot": "ai-dev-platform",
            "include": ["AGENTS.md", "CLAUDE.md", "README.md", "opencode.json", "docs"],
            "excludeNames": [".git"],
        }
        (root / "distribution" / "manifest.json").write_text(json.dumps(config), encoding="utf-8")

        payload_paths = ["AGENTS.md", "CLAUDE.md", "README.md", "opencode.json", "docs/guide.md"]
        entries = []
        archive_path = base / "package.zip"
        prefix = "ai-dev-platform/" if prefixed else ""
        with zipfile.ZipFile(archive_path, "w") as archive:
            for relative in payload_paths:
                payload = (root / relative).read_bytes()
                entries.append({
                    "path": relative, "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload), "mode": "0644",
                })
                mode = 0o100755 if wrong_mode and relative == "README.md" else 0o100644
                zip_write(archive, f"{prefix}{relative}", payload, mode)
            zip_write(archive, f"{prefix}{RELEASE_MANIFEST}", json.dumps({"files": entries}).encode())
            if unexpected:
                zip_write(archive, f"{prefix}unexpected.bin", b"not declared")
        return archive_path, root

    def test_accepts_prefixed_archive_and_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, root = self.make_fixture(Path(temp))
            verify_archive(archive, root)

    def test_rejects_files_outside_archive_root(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, root = self.make_fixture(Path(temp), prefixed=False)
            with self.assertRaisesRegex(ValueError, "頂層|不在 ai-dev-platform/"):
                verify_archive(archive, root)

    def test_rejects_undeclared_archive_content(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, root = self.make_fixture(Path(temp), unexpected=True)
            with self.assertRaisesRegex(ValueError, "不一致|未宣告內容"):
                verify_archive(archive, root)

    def test_rejects_mode_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            archive, root = self.make_fixture(Path(temp), wrong_mode=True)
            with self.assertRaisesRegex(ValueError, "權限"):
                verify_archive(archive, root)


if __name__ == "__main__":
    unittest.main()
