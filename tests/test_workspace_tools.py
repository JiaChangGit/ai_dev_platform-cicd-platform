#!/usr/bin/env python3

import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_workspace import audit_workspace  # noqa: E402
from install_platform import install_platform  # noqa: E402
from package_release import zip_write  # noqa: E402


class WorkspaceToolTest(unittest.TestCase):
    def make_archive(self, base: Path) -> tuple[Path, Path]:
        payloads = {
            "AGENTS.md": b"# Rules\n",
            "CLAUDE.md": b"# Claude\n",
            "README.md": b"# Platform\n",
            "opencode.json": b"{}\n",
            "scripts/check.sh": b"#!/usr/bin/env bash\nset -e\ntest -f AGENTS.md\n",
        }
        entries = []
        archive = base / "platform.zip"
        with zipfile.ZipFile(archive, "w") as package:
            for relative, payload in payloads.items():
                mode = "0755" if relative.endswith(".sh") else "0644"
                entries.append({
                    "path": relative, "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload), "mode": mode,
                })
                zip_write(package, f"ai-dev-platform/{relative}", payload, 0o100755 if mode == "0755" else 0o100644)
            manifest = {"schemaVersion": 1, "platformId": "ai-dev-platform", "version": "test", "files": entries}
            zip_write(package, "ai-dev-platform/RELEASE-MANIFEST.json", json.dumps(manifest).encode())
        checksum = base / "platform.zip.sha256"
        checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="utf-8")
        return archive, checksum

    @unittest.skipUnless(os.name == "posix", "需要 POSIX 檔案權限")
    def test_installer_replaces_target_and_preserves_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            target = work / "ai-dev-platform"
            target.mkdir()
            (target / "obsolete.txt").write_text("old", encoding="utf-8")
            archive, checksum = self.make_archive(work)
            result = install_platform(archive, checksum, work)
            self.assertEqual(result, target)
            self.assertFalse((target / "obsolete.txt").exists())
            self.assertTrue(stat.S_IMODE((target / "scripts/check.sh").stat().st_mode) & 0o111)
            self.assertEqual(stat.S_IMODE((target / "AGENTS.md").stat().st_mode) & 0o222, 0)

    @unittest.skipUnless(os.name == "posix", "需要 POSIX 檔案權限")
    def test_audit_accepts_always_current_product(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            platform = work / "ai-dev-platform"
            (platform / "scripts").mkdir(parents=True)
            for relative, content in (
                ("AGENTS.md", "# rules"), ("CLAUDE.md", "# claude"),
                ("opencode.json", "{}"), ("scripts/check.sh", "#!/bin/sh"),
            ):
                path = platform / relative
                path.write_text(content, encoding="utf-8")
                os.chmod(path, 0o444)
            product = work / "sample-cicd-platform"
            (product / ".ai").mkdir(parents=True)
            (product / ".git").mkdir()
            (product / "AGENTS.md").write_text("../ai-dev-platform/AGENTS.md", encoding="utf-8")
            (product / ".ai/product.json").write_text(json.dumps({
                "platform": "../ai-dev-platform", "platformVersionPolicy": "always-current",
                "releaseRepository": "../sample-release",
            }), encoding="utf-8")
            release = work / "sample-release"
            (release / ".git").mkdir(parents=True)
            result = audit_workspace(work)
            self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
