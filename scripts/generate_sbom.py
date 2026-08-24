#!/usr/bin/env python3
"""從已驗證的平台 ZIP 產生 SPDX 2.3 JSON SBOM。"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_archive_json(archive: ZipFile, suffix: str) -> dict:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"ZIP 內必須恰好有一份 {suffix}，實際為 {len(matches)} 份")
    value = json.loads(archive.read(matches[0]).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{suffix} root 必須是 object")
    return value


def spdx_id(prefix: str, value: str) -> str:
    safe = "".join(character if character.isalnum() or character in ".-" else "-" for character in value)
    return f"SPDXRef-{prefix}-{safe.strip('-') or 'item'}"


def generate_sbom(
    archive_path: Path,
    *,
    repository: str,
    created: str,
) -> dict:
    artifact_sha256 = sha256_file(archive_path)
    with ZipFile(archive_path) as archive:
        manifest = load_archive_json(archive, "/RELEASE-MANIFEST.json")

    platform_id = str(manifest["platformId"])
    version = str(manifest["version"])
    files = manifest.get("files")
    if not isinstance(files, list) or not all(isinstance(item, dict) for item in files):
        raise ValueError("RELEASE-MANIFEST.json 的 files 必須是 object 陣列")

    document_namespace = (
        f"{repository.rstrip('/')}/releases/tag/v{version}/"
        f"spdx-{artifact_sha256}"
    )
    platform_spdx_id = spdx_id("Package", platform_id)
    packages = [
        {
            "name": platform_id,
            "SPDXID": platform_spdx_id,
            "versionInfo": version,
            "downloadLocation": f"{repository.rstrip('/')}/releases/download/v{version}/{archive_path.name}",
            "filesAnalyzed": True,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "MIT",
            "copyrightText": "Copyright 2026 JiaChangGit contributors",
            "checksums": [{"algorithm": "SHA256", "checksumValue": artifact_sha256}],
        }
    ]
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": platform_spdx_id,
        }
    ]
    spdx_files = []
    for index, item in enumerate(files, start=1):
        path = str(item.get("path", ""))
        digest = str(item.get("sha256", ""))
        if not path or len(digest) != 64:
            raise ValueError("RELEASE-MANIFEST.json 含無效的檔案路徑或 SHA-256")
        file_id = f"SPDXRef-File-{index}-{digest[:12]}"
        spdx_files.append(
            {
                "fileName": f"./{path}",
                "SPDXID": file_id,
                "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": platform_spdx_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": file_id,
            }
        )

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{platform_id}-{version}",
        "documentNamespace": document_namespace,
        "creationInfo": {
            "created": created,
            "creators": ["Tool: ai-dev-platform/generate_sbom.py", "Organization: JiaChangGit"],
        },
        "documentDescribes": [platform_spdx_id],
        "packages": packages,
        "files": spdx_files,
        "relationships": relationships,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--repository",
        default="https://github.com/JiaChangGit/ai_dev_platform-cicd-platform",
    )
    parser.add_argument(
        "--created",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        help="SPDX creationInfo.created；正式 CI 建議傳入來源 commit 時間",
    )
    args = parser.parse_args()
    sbom = generate_sbom(
        args.archive.resolve(),
        repository=args.repository,
        created=args.created,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] SPDX SBOM: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
