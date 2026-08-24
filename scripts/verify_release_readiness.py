#!/usr/bin/env python3
"""驗證發行儲存庫、建置成品與供應鏈證據是否可以發布。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from verify_release_evidence import REQUIRED_CHECKS, validate_evidence
from verify_release_layout import validate_release_layout


MUTABLE_URI_WORDS = {"latest", "current", "snapshot", "nightly"}
GITHUB_SOURCE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def load_json(path: Path, errors: list[str], label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("root 不是 object")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"{label} 無法解析：{error}")
        return {}


def validate_sbom(path: Path, evidence: dict, errors: list[str]) -> None:
    data = load_json(path, errors, "SBOM")
    if not data:
        return
    if evidence.get("format") == "spdx-json" and not str(data.get("spdxVersion", "")).startswith("SPDX-2."):
        errors.append("SBOM 宣告 spdx-json，但內容不是 SPDX 2.x JSON")
    if evidence.get("format") == "cyclonedx-json" and data.get("bomFormat") != "CycloneDX":
        errors.append("SBOM 宣告 cyclonedx-json，但內容不是 CycloneDX JSON")


def verify_github_attestation(
    artifact_file: Path,
    bundle_file: Path,
    *,
    repository: str,
    workflow: str,
    source_commit: str,
    source_ref: str,
    predicate_type: str,
) -> str | None:
    if shutil.which("gh") is None:
        return "找不到 gh，無法驗證 GitHub artifact attestation"
    result = subprocess.run(
        [
            "gh", "attestation", "verify", str(artifact_file),
            "--repo", repository,
            "--bundle", str(bundle_file),
            "--signer-workflow", workflow,
            "--source-digest", source_commit,
            "--source-ref", source_ref,
            "--predicate-type", predicate_type,
            "--deny-self-hosted-runners",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        return "GitHub artifact attestation 驗證失敗"
    return None


def validate_release_readiness(
    release_root: Path,
    source_repo: Path,
    artifact_file: Path,
    signature_file: Path,
    public_key: Path | None,
    sbom_file: Path,
    provenance_file: Path,
    version: str | None = None,
) -> list[str]:
    release_root = release_root.resolve()
    errors = validate_release_layout(release_root)
    evidence_files = sorted((release_root / "release-evidence").glob("*.json"))
    if version is None:
        if len(evidence_files) != 1:
            errors.append("未指定 --version 時，release-evidence/ 必須恰好有一份版本 JSON")
            return errors
        version = evidence_files[0].stem
    evidence_path = release_root / "release-evidence" / f"{version}.json"
    note_path = release_root / "release-notes" / f"{version}.md"
    if not evidence_path.is_file():
        errors.append(f"缺少發行證據：release-evidence/{version}.json")
        return errors
    data = load_json(evidence_path, errors, "發行證據")
    errors.extend(validate_evidence(data))
    if not data:
        return errors
    if data.get("version") != version:
        errors.append("發行證據的 version 與檔名不一致")
    if not note_path.is_file():
        errors.append(f"缺少 Release Note：release-notes/{version}.md")
    else:
        first = next((line.strip() for line in note_path.read_text(encoding="utf-8").splitlines() if line.strip()), "")
        if not first.startswith("# ") or f"v{version}" not in first:
            errors.append("Release Note 的一級標題必須包含同一版本 v<version>")

    artifact = data.get("artifact", {})
    signature_algorithm = artifact.get("signatureAlgorithm")
    materials: list[tuple[Path, str]] = [
        (artifact_file, "建置成品"), (signature_file, "簽章"),
        (sbom_file, "SBOM"), (provenance_file, "SLSA 來源證明"),
    ]
    if signature_algorithm == "openssl-sha256":
        if public_key is None:
            errors.append("openssl-sha256 簽章需要 --public-key")
        else:
            materials.append((public_key, "公開金鑰"))
    for path, label in materials:
        if not path.is_file():
            errors.append(f"{label}檔不存在：{path}")
        elif inside(path, release_root):
            errors.append(f"{label}檔不得存在 product-release 內：{path.name}")

    uri = str(artifact.get("uri", ""))
    if any(word in {part.lower() for part in uri.replace(":", "/").split("/")} for word in MUTABLE_URI_WORDS):
        errors.append("artifact.uri 含 latest/current/snapshot/nightly 等可變路徑")
    if version not in uri and str(artifact.get("sha256", ""))[:12] not in uri:
        errors.append("artifact.uri 必須包含版本或 SHA-256 前 12 碼，以證明位置不可變")
    if artifact_file.is_file() and sha256_file(artifact_file) != artifact.get("sha256"):
        errors.append("建置成品 SHA-256 與發行證據不一致")
    if signature_file.is_file() and sha256_file(signature_file) != artifact.get("signatureSha256"):
        errors.append("簽章檔 SHA-256 與發行證據不一致")
    sbom = data.get("sbom", {})
    if sbom_file.is_file() and sha256_file(sbom_file) != sbom.get("sha256"):
        errors.append("SBOM SHA-256 與發行證據不一致")
    if sbom_file.is_file():
        validate_sbom(sbom_file, sbom, errors)
    provenance = data.get("provenance", {})
    if provenance_file.is_file() and sha256_file(provenance_file) != provenance.get("sha256"):
        errors.append("SLSA 來源證明 SHA-256 與發行證據不一致")
    if provenance_file.is_file() and signature_algorithm == "openssl-sha256":
        prov = load_json(provenance_file, errors, "SLSA 來源證明")
        if prov and prov.get("predicateType") != provenance.get("predicateType"):
            errors.append("SLSA predicateType 與發行證據不一致")

    if signature_algorithm == "openssl-sha256":
        if shutil.which("openssl") is None:
            errors.append("找不到 openssl，無法驗證建置成品簽章")
        elif (
            artifact_file.is_file()
            and signature_file.is_file()
            and public_key is not None
            and public_key.is_file()
        ):
            result = subprocess.run(
                ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature_file), str(artifact_file)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            if result.returncode != 0:
                errors.append("建置成品簽章驗證失敗")
    elif signature_algorithm == "github-attestation":
        identity = artifact.get("signatureIdentity", {})
        repository_name = str(identity.get("repository", ""))
        source_repository = str(data.get("source", {}).get("repository", ""))
        match = GITHUB_SOURCE.fullmatch(source_repository)
        if match is None or match.group("repository") != repository_name:
            errors.append("source.repository 必須與 GitHub attestation repository 相同")
        if artifact.get("signatureSha256") != provenance.get("sha256"):
            errors.append("GitHub attestation 的 signature 與 provenance 必須引用同一份 bundle")
        if signature_file.is_file() and provenance_file.is_file() and signature_file.read_bytes() != provenance_file.read_bytes():
            errors.append("GitHub attestation 的 signature 與 provenance 實體 bundle 不一致")
        if artifact_file.is_file() and signature_file.is_file():
            attestation_error = verify_github_attestation(
                artifact_file,
                signature_file,
                repository=repository_name,
                workflow=str(identity.get("workflow", "")),
                source_commit=str(data.get("source", {}).get("commit", "")),
                source_ref=str(identity.get("sourceRef", "")),
                predicate_type=str(provenance.get("predicateType", "")),
            )
            if attestation_error:
                errors.append(attestation_error)

    try:
        if git(release_root, "status", "--porcelain"):
            errors.append("product-release 工作目錄不乾淨")
        head = git(release_root, "rev-parse", "HEAD")
        tag_commit = git(release_root, "rev-list", "-n", "1", f"v{version}")
        if tag_commit != head:
            errors.append(f"發行 tag v{version} 必須指向 product-release HEAD")
    except (OSError, subprocess.CalledProcessError):
        errors.append(f"product-release 缺少可驗證的 tag v{version}")

    source = data.get("source", {})
    try:
        commit = git(source_repo.resolve(), "rev-parse", f"{source.get('commit')}^{{commit}}")
        if commit != source.get("commit"):
            errors.append("source.commit 不是來源儲存庫的完整 commit SHA")
        ref_commit = git(source_repo.resolve(), "rev-parse", f"{source.get('ref')}^{{commit}}")
        ancestor = subprocess.run(
            ["git", "-C", str(source_repo.resolve()), "merge-base", "--is-ancestor", commit, ref_commit]
        ).returncode == 0
        if not ancestor:
            errors.append("source.commit 不屬於 source.ref 的歷史")
    except (OSError, subprocess.CalledProcessError):
        errors.append("source.commit 或 source.ref 無法在來源儲存庫驗證")

    checks = set(data.get("verification", {}).get("checks", []))
    if missing := sorted(REQUIRED_CHECKS - checks):
        errors.append(f"缺少必要 CI 阻擋檢查：{', '.join(missing)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_root", type=Path)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--artifact-file", type=Path, required=True)
    parser.add_argument("--signature-file", type=Path, required=True)
    parser.add_argument("--public-key", type=Path)
    parser.add_argument("--sbom-file", type=Path, required=True)
    parser.add_argument("--provenance-file", type=Path, required=True)
    parser.add_argument("--version")
    args = parser.parse_args()
    errors = validate_release_readiness(
        args.release_root, args.source_repo, args.artifact_file, args.signature_file,
        args.public_key, args.sbom_file, args.provenance_file, args.version,
    )
    if errors:
        for error in errors:
            print(f"[FAIL] release readiness: {error}", file=sys.stderr)
        return 1
    print(f"[OK] release readiness: {args.release_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
