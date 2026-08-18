#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_release_readiness import validate_release_readiness  # noqa: E402


def run(*args: str, cwd: Path) -> str:
    return subprocess.check_output(list(args), cwd=cwd, text=True).strip()


class ReleaseReadinessTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git") and shutil.which("openssl"), "需要 Git 與 OpenSSL")
    def test_accepts_complete_signed_release(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            release = base / "release"
            source.mkdir()
            release.mkdir()
            for repo in (source, release):
                run("git", "init", "-b", "main", cwd=repo)
                run("git", "config", "user.email", "test@example.invalid", cwd=repo)
                run("git", "config", "user.name", "Test", cwd=repo)
            (source / "product.txt").write_text("source", encoding="utf-8")
            run("git", "add", ".", cwd=source)
            run("git", "commit", "-m", "feat: source", cwd=source)
            commit = run("git", "rev-parse", "HEAD", cwd=source)

            artifact = base / "sample-1.0.0.bin"
            signature = base / "sample-1.0.0.bin.sig"
            private_key = base / "private.pem"
            public_key = base / "public.pem"
            sbom = base / "sample-1.0.0.spdx.json"
            provenance = base / "sample-1.0.0.provenance.json"
            artifact.write_bytes(b"release artifact")
            sbom.write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            provenance.write_text(json.dumps({"predicateType": "https://slsa.dev/provenance/v1"}), encoding="utf-8")
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(private_key), "-out", str(signature), str(artifact)], check=True)
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

            (release / "release-evidence").mkdir()
            (release / "release-notes").mkdir()
            evidence = {
                "schemaVersion": 2, "product": "sample", "version": "1.0.0",
                "source": {"repository": "https://example.invalid/sample.git", "commit": commit, "ref": "refs/heads/main"},
                "artifact": {
                    "uri": "artifact://sample/1.0.0/sample.bin", "sha256": digest(artifact),
                    "immutable": True, "signatureUri": "artifact://sample/1.0.0/sample.bin.sig",
                    "signatureSha256": digest(signature), "signatureAlgorithm": "openssl-sha256",
                },
                "verification": {"ciSystem": "test", "runId": "1", "checks": ["build", "test", "lint", "security", "package"]},
                "sbom": {"uri": "artifact://sample/1.0.0/sbom.json", "sha256": digest(sbom), "format": "spdx-json"},
                "provenance": {"uri": "artifact://sample/1.0.0/provenance.json", "sha256": digest(provenance), "predicateType": "https://slsa.dev/provenance/v1"},
                "approval": {"status": "approved", "approvedBy": "reviewer"},
                "release": {"publisher": "publisher"},
            }
            (release / "release-evidence/1.0.0.json").write_text(json.dumps(evidence), encoding="utf-8")
            (release / "release-notes/1.0.0.md").write_text("# Release Note v1.0.0\n", encoding="utf-8")
            run("git", "add", ".", cwd=release)
            run("git", "commit", "-m", "chore: release 1.0.0", cwd=release)
            run("git", "tag", "v1.0.0", cwd=release)
            errors = validate_release_readiness(
                release, source, artifact, signature, public_key, sbom, provenance, "1.0.0"
            )
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
