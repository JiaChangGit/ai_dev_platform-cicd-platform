#!/usr/bin/env python3
"""依 CI 供應商無關契約驗證發行證據（release evidence）。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SHA256 = re.compile(r"^[a-f0-9]{64}$")
COMMIT = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
SOURCE_REF = re.compile(r"^refs/(?:heads/(?:main|release/.+)|tags/v.+)$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_WORKFLOW = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml$"
)
REQUIRED_CHECKS = frozenset({"build", "test", "lint", "security", "package"})
ROOT_FIELDS = {
    "schemaVersion", "product", "version", "source", "artifact", "verification",
    "sbom", "provenance", "approval", "release",
}


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_object(
    value: object, name: str, required: set[str], allowed: set[str], errors: list[str]
) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{name} 必須是 object")
        return {}
    for key in sorted(required - set(value)):
        errors.append(f"缺少必要欄位: {name}.{key}")
    for key in sorted(set(value) - allowed):
        errors.append(f"不允許的欄位: {name}.{key}")
    return value


def require_text(data: dict, key: str, errors: list[str], prefix: str = "") -> None:
    if not nonempty_string(data.get(key)):
        errors.append(f"{prefix}{key} 必須是非空字串")


def require_sha(data: dict, key: str, errors: list[str], prefix: str) -> None:
    if not isinstance(data.get(key), str) or not SHA256.fullmatch(data[key]):
        errors.append(f"{prefix}{key} 必須是 64 位小寫十六進位")


def validate_evidence(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["root 必須是 JSON object"]
    errors: list[str] = []
    for key in sorted(ROOT_FIELDS - set(data)):
        errors.append(f"缺少必要欄位: {key}")
    for key in sorted(set(data) - ROOT_FIELDS):
        errors.append(f"不允許的欄位: {key}")
    if errors:
        return errors
    if data["schemaVersion"] != 2:
        errors.append("schemaVersion 必須是 2")
    require_text(data, "product", errors)
    if not isinstance(data.get("version"), str) or not SEMVER.fullmatch(data["version"]):
        errors.append("version 必須是有效的語意化版本")

    source = validate_object(data["source"], "source", {"repository", "commit", "ref"}, {"repository", "commit", "ref"}, errors)
    require_text(source, "repository", errors, "source.")
    if not isinstance(source.get("commit"), str) or not COMMIT.fullmatch(source["commit"]):
        errors.append("source.commit 必須是完整 Git commit SHA")
    if not isinstance(source.get("ref"), str) or not SOURCE_REF.fullmatch(source["ref"]):
        errors.append("source.ref 只允許 main、release/* 或 v* tag 的完整 ref")

    artifact_required = {"uri", "sha256", "immutable", "signatureUri", "signatureSha256", "signatureAlgorithm"}
    artifact_allowed = artifact_required | {"signatureIdentity"}
    artifact = validate_object(data["artifact"], "artifact", artifact_required, artifact_allowed, errors)
    require_text(artifact, "uri", errors, "artifact.")
    require_text(artifact, "signatureUri", errors, "artifact.")
    require_sha(artifact, "sha256", errors, "artifact.")
    require_sha(artifact, "signatureSha256", errors, "artifact.")
    if artifact.get("immutable") is not True:
        errors.append("artifact.immutable 必須是 true")
    signature_algorithm = artifact.get("signatureAlgorithm")
    if signature_algorithm not in {"openssl-sha256", "github-attestation"}:
        errors.append("artifact.signatureAlgorithm 必須是 openssl-sha256 或 github-attestation")
    signature_identity = artifact.get("signatureIdentity")
    if signature_algorithm == "github-attestation":
        identity = validate_object(
            signature_identity,
            "artifact.signatureIdentity",
            {"repository", "workflow", "sourceRef"},
            {"repository", "workflow", "sourceRef"},
            errors,
        )
        repository = identity.get("repository")
        workflow = identity.get("workflow")
        source_ref = identity.get("sourceRef")
        if not isinstance(repository, str) or not GITHUB_REPOSITORY.fullmatch(repository):
            errors.append("artifact.signatureIdentity.repository 必須是 owner/repository")
        if not isinstance(workflow, str) or not GITHUB_WORKFLOW.fullmatch(workflow):
            errors.append("artifact.signatureIdentity.workflow 必須是 owner/repository/.github/workflows/<file>.yml")
        elif isinstance(repository, str) and not workflow.startswith(f"{repository}/"):
            errors.append("artifact.signatureIdentity.workflow 必須位於同一個 repository")
        if source_ref != source.get("ref"):
            errors.append("artifact.signatureIdentity.sourceRef 必須與 source.ref 相同")
    elif signature_identity is not None:
        errors.append("openssl-sha256 不得包含 artifact.signatureIdentity")

    verification = validate_object(data["verification"], "verification", {"ciSystem", "runId", "checks"}, {"ciSystem", "runId", "checks"}, errors)
    require_text(verification, "ciSystem", errors, "verification.")
    require_text(verification, "runId", errors, "verification.")
    checks = verification.get("checks")
    if not isinstance(checks, list) or not checks or not all(nonempty_string(item) for item in checks):
        errors.append("verification.checks 必須是非空字串陣列")
    elif len(checks) != len(set(checks)):
        errors.append("verification.checks 不得重複")
    elif missing := sorted(REQUIRED_CHECKS - set(checks)):
        errors.append(f"verification.checks 缺少阻擋檢查: {', '.join(missing)}")

    sbom = validate_object(data["sbom"], "sbom", {"uri", "sha256", "format"}, {"uri", "sha256", "format"}, errors)
    require_text(sbom, "uri", errors, "sbom.")
    require_sha(sbom, "sha256", errors, "sbom.")
    if sbom.get("format") not in {"spdx-json", "cyclonedx-json"}:
        errors.append("sbom.format 必須是 spdx-json 或 cyclonedx-json")

    provenance = validate_object(data["provenance"], "provenance", {"uri", "sha256", "predicateType"}, {"uri", "sha256", "predicateType"}, errors)
    require_text(provenance, "uri", errors, "provenance.")
    require_sha(provenance, "sha256", errors, "provenance.")
    if provenance.get("predicateType") != "https://slsa.dev/provenance/v1":
        errors.append("provenance.predicateType 必須是 SLSA provenance v1")

    approval = validate_object(data["approval"], "approval", {"status", "approvedBy"}, {"status", "approvedBy"}, errors)
    if approval.get("status") != "approved":
        errors.append("approval.status 必須是 approved")
    require_text(approval, "approvedBy", errors, "approval.")
    release = validate_object(data["release"], "release", {"publisher"}, {"publisher"}, errors)
    require_text(release, "publisher", errors, "release.")
    if approval.get("approvedBy") == release.get("publisher") and nonempty_string(approval.get("approvedBy")):
        errors.append("approval.approvedBy 不得與 release.publisher 相同")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] release evidence: {error}", file=sys.stderr)
        return 1
    errors = validate_evidence(data)
    if errors:
        for error in errors:
            print(f"[FAIL] release evidence: {error}", file=sys.stderr)
        return 1
    print(f"[OK] release evidence: {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
