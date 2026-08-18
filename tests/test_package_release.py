#!/usr/bin/env python3

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_release import sha256_file, zip_write  # noqa: E402


class PackageReleaseTest(unittest.TestCase):
    def test_sha256_file_streams_expected_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "payload.bin"
            payload = b"ai-dev-platform" * 1000
            path.write_bytes(payload)
            self.assertEqual(sha256_file(path), hashlib.sha256(payload).hexdigest())

    def test_zip_write_preserves_executable_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "package.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                zip_write(archive, "scripts/check.sh", b"#!/bin/sh\n", 0o100755)
            with zipfile.ZipFile(archive_path) as archive:
                info = archive.getinfo("scripts/check.sh")
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()
