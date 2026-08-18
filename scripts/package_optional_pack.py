#!/usr/bin/env python3
"""建立可疊加到唯讀平台包的選用離線套件。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from package_release import sha256_file, source_ref, worktree_is_dirty, zip_write
from verify_package import expected_payload_names, load_json, verify_optional_archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack_id", choices=["openai-cookbook"])
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--source-ref")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    platform = load_json(root / "distribution/manifest.json")
    packs = load_json(root / "distribution/optional-packs.json")["packs"]
    config = next(item for item in packs if item["id"] == args.pack_id)
    version = platform["version"]
    expected = expected_payload_names(root, config)
    archive_name = config["archiveName"].replace("{version}", version)
    output = args.output_dir.resolve() / archive_name
    partial = output.with_name(f".{output.name}.partial")
    if args.dry_run:
        size = sum((root / path).stat().st_size for path in expected)
        print(f"[OK] optional pack plan: {len(expected)} files, {size} bytes")
        return 0
    if not args.allow_dirty and worktree_is_dirty(root):
        print("[FAIL] 正式選用套件不得從未 commit 工作目錄建立", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{config['archiveRoot'].strip('/')}/"
    entries = []
    partial.unlink(missing_ok=True)
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(expected):
            path = root / relative
            payload = path.read_bytes()
            mode = 0o100755 if path.stat().st_mode & 0o111 else 0o100644
            zip_write(archive, f"{prefix}{relative}", payload, mode)
            entries.append({
                "path": relative,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "mode": "0755" if mode & 0o111 else "0644",
            })
        pack_manifest = {
            "schemaVersion": 1,
            "packId": config["id"],
            "platformVersion": version,
            "sourceRef": source_ref(root, args.source_ref),
            "files": entries,
        }
        zip_write(
            archive,
            f"{prefix}OPTIONAL-PACK-MANIFEST.json",
            json.dumps(pack_manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    try:
        verify_optional_archive(partial, root, args.pack_id)
    except Exception as error:
        partial.unlink(missing_ok=True)
        print(f"[FAIL] optional pack verification: {error}", file=sys.stderr)
        return 1
    partial.replace(output)
    digest = sha256_file(output)
    output.with_name(f"{output.name}.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"[OK] created {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
