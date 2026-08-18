#!/usr/bin/env python3
"""建立精簡、可離線使用且不含 Git 資料的發行 ZIP 與 SHA-256。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from verify_package import expected_payload_names, load_json, verify_archive


RELEASE_MANIFEST = "RELEASE-MANIFEST.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def source_ref(root: Path, requested: str | None) -> str:
    if requested:
        return requested
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def worktree_is_dirty(root: Path) -> bool:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        )
        return bool(output.strip())
    except (OSError, subprocess.CalledProcessError):
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_write(
    archive: zipfile.ZipFile,
    name: str,
    payload: bytes,
    mode: int = 0o100644,
) -> None:
    info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = mode << 16
    archive.writestr(info, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--source-ref", help="產生此發行包的不可變來源 commit 或 tag")
    parser.add_argument("--version", help="覆寫 distribution/manifest.json 的版本（供發行工作使用）")
    parser.add_argument("--dry-run", action="store_true", help="只驗證清單並顯示預計打包內容，不寫檔")
    parser.add_argument(
        "--allow-dirty", action="store_true", help="允許從有未 commit 變更的工作目錄打包（僅限本機診斷）"
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config = load_json(root / "distribution" / "manifest.json")
    version = args.version or config["version"]
    archive_name = config["archiveName"].replace("{version}", version)
    output_dir = args.output_dir.resolve()
    archive_path = output_dir / archive_name
    checksum_path = output_dir / f"{archive_name}.sha256"
    partial_archive_path = output_dir / f".{archive_name}.partial"
    partial_checksum_path = output_dir / f".{archive_name}.sha256.partial"
    expected = expected_payload_names(root, config)

    if args.dry_run:
        total_bytes = sum((root / relative).stat().st_size for relative in expected)
        print(f"[OK] package plan: {len(expected)} files, {total_bytes} bytes")
        print(f"[OK] target: {archive_path}")
        return 0

    if not args.allow_dirty and worktree_is_dirty(root):
        print("[FAIL] 維護儲存庫有未 commit 變更；正式發行包必須對應不可變 sourceRef", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    file_entries = []
    for relative in sorted(expected):
        payload = (root / relative).read_bytes()
        executable = bool((root / relative).stat().st_mode & 0o111)
        file_entries.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "mode": "0755" if executable else "0644",
            }
        )

    release_manifest = {
        "schemaVersion": 1,
        "platformId": config["platformId"],
        "version": version,
        "sourceRef": source_ref(root, args.source_ref),
        "files": file_entries,
    }
    archive_root = config.get("archiveRoot", config["platformId"]).strip("/")
    # 先寫入暫存檔，驗證通過後再以原子替換（atomic replace）發布。
    # 即使 CI 中斷或磁碟空間不足，上一份已驗證的發行包仍保持完整。
    partial_archive_path.unlink(missing_ok=True)
    partial_checksum_path.unlink(missing_ok=True)
    with zipfile.ZipFile(partial_archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(expected):
            source_path = root / relative
            mode = 0o100755 if source_path.stat().st_mode & 0o111 else 0o100644
            zip_write(archive, f"{archive_root}/{relative}", source_path.read_bytes(), mode)
        zip_write(
            archive,
            f"{archive_root}/{RELEASE_MANIFEST}",
            json.dumps(release_manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    digest = sha256_file(partial_archive_path)
    partial_checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    try:
        verify_archive(partial_archive_path, root)
    except Exception as error:  # 未通過驗證的發行包不得進入交接流程
        partial_archive_path.unlink(missing_ok=True)
        partial_checksum_path.unlink(missing_ok=True)
        print(f"[FAIL] package verification: {error}", file=sys.stderr)
        return 1
    partial_archive_path.replace(archive_path)
    partial_checksum_path.replace(checksum_path)
    print(f"[OK] created {archive_path}")
    print(f"[OK] created {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
