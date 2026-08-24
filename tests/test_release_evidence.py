#!/usr/bin/env python3

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_release_evidence import ROOT_FIELDS, validate_evidence  # noqa: E402


def valid_evidence() -> dict:
    return {
        "schemaVersion": 2,
        "product": "example",
        "version": "1.0.0",
        "source": {"repository": "repo", "commit": "a" * 40, "ref": "refs/heads/main"},
        "artifact": {
            "uri": "artifact://immutable/example/1.0.0", "sha256": "0" * 64,
            "immutable": True, "signatureUri": "artifact://immutable/example/1.0.0.sig",
            "signatureSha256": "1" * 64, "signatureAlgorithm": "openssl-sha256",
        },
        "verification": {
            "ciSystem": "internal-ci", "runId": "run-1",
            "checks": ["build", "test", "lint", "security", "package"],
        },
        "sbom": {"uri": "artifact://immutable/example/1.0.0.sbom.json", "sha256": "2" * 64, "format": "spdx-json"},
        "provenance": {
            "uri": "artifact://immutable/example/1.0.0.provenance.json", "sha256": "3" * 64,
            "predicateType": "https://slsa.dev/provenance/v1",
        },
        "approval": {"status": "approved", "approvedBy": "reviewer@example"},
        "release": {"publisher": "publisher@example"},
    }


class ReleaseEvidenceTest(unittest.TestCase):
    def test_validator_required_fields_match_json_schema(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / "distribution" / "release-evidence.schema.json").read_text())
        self.assertEqual(set(schema["required"]), set(ROOT_FIELDS))
        expected_nested = {
            "source": {"repository", "commit", "ref"},
            "artifact": {"uri", "sha256", "immutable", "signatureUri", "signatureSha256", "signatureAlgorithm"},
            "verification": {"ciSystem", "runId", "checks"},
            "sbom": {"uri", "sha256", "format"},
            "provenance": {"uri", "sha256", "predicateType"},
            "approval": {"status", "approvedBy"},
            "release": {"publisher"},
        }
        for name, required in expected_nested.items():
            self.assertEqual(set(schema["properties"][name]["required"]), required)
            self.assertFalse(schema["properties"][name]["additionalProperties"])
        self.assertEqual(schema["properties"]["verification"]["properties"]["checks"]["items"]["type"], "string")

    def test_accepts_provider_neutral_evidence(self):
        self.assertEqual(validate_evidence(valid_evidence()), [])

    def test_rejects_bad_digest_and_missing_approval(self):
        evidence = valid_evidence()
        evidence["artifact"]["sha256"] = "bad"
        evidence["approval"]["approvedBy"] = ""
        errors = validate_evidence(evidence)
        self.assertTrue(any("artifact.sha256" in error for error in errors))
        self.assertTrue(any("approval.approvedBy" in error for error in errors))

    def test_rejects_missing_blocker_and_same_approver(self):
        evidence = valid_evidence()
        evidence["verification"]["checks"].remove("security")
        evidence["release"]["publisher"] = evidence["approval"]["approvedBy"]
        errors = validate_evidence(evidence)
        self.assertTrue(any("security" in error for error in errors))
        self.assertTrue(any("publisher" in error for error in errors))

    def test_accepts_github_keyless_attestation_identity(self):
        evidence = valid_evidence()
        evidence["source"]["repository"] = "https://github.com/example/platform"
        evidence["source"]["ref"] = "refs/tags/v1.0.0"
        evidence["artifact"]["signatureAlgorithm"] = "github-attestation"
        evidence["artifact"]["signatureIdentity"] = {
            "repository": "example/platform",
            "workflow": "example/platform/.github/workflows/release.yml",
            "sourceRef": "refs/tags/v1.0.0",
        }
        self.assertEqual(validate_evidence(evidence), [])

    def test_rejects_mismatched_github_attestation_identity(self):
        evidence = valid_evidence()
        evidence["artifact"]["signatureAlgorithm"] = "github-attestation"
        evidence["artifact"]["signatureIdentity"] = {
            "repository": "example/platform",
            "workflow": "other/platform/.github/workflows/release.yml",
            "sourceRef": "refs/tags/v2.0.0",
        }
        errors = validate_evidence(evidence)
        self.assertTrue(any("同一個 repository" in error for error in errors))
        self.assertTrue(any("source.ref" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
