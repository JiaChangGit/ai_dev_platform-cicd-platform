#!/usr/bin/env python3
"""驗證並原子安裝／更新 Work/ai-dev-platform 唯讀平台包。"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

from verify_package import (  # noqa: E402
    OPTIONAL_PACK_MANIFEST,
    RELEASE_MANIFEST,
    safe_archive_name,
    verify_archive_contents,
    verify_optional_archive_contents,
)


SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(archive: Path, checksum: Path) -> None:
    fields = checksum.read_text(encoding="utf-8").strip().split()
    if len(fields) != 2 or fields[1].lstrip("*") != archive.name:
        raise ValueError("SHA-256 sidecar 格式或檔名不正確")
    if fields[0].lower() != sha256_file(archive):
        raise ValueError("平台 ZIP 的 SHA-256 與 sidecar 不一致")


def extract_verified(archive_path: Path, staging_parent: Path) -> Path:
    manifest = verify_archive_contents(archive_path)
    declared_modes = {entry["path"]: entry["mode"] for entry in manifest["files"]}
    with zipfile.ZipFile(archive_path) as archive:
        manifest_member = next(name for name in archive.namelist() if name.endswith(f"/{RELEASE_MANIFEST}"))
        prefix = manifest_member[: -len(RELEASE_MANIFEST)]
        archive_root = prefix.rstrip("/")
        target_root = staging_parent / archive_root
        target_root.mkdir()
        for info in archive.infolist():
            if info.is_dir():
                continue
            if not safe_archive_name(info.filename) or not info.filename.startswith(prefix):
                raise ValueError(f"壓縮檔含不安全路徑：{info.filename}")
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode):
                raise ValueError(f"壓縮檔不得包含符號連結：{info.filename}")
            relative = PurePosixPath(info.filename.removeprefix(prefix))
            if relative.name == RELEASE_MANIFEST:
                continue
            destination = target_root.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(destination, int(declared_modes[relative.as_posix()], 8))
    return target_root


def overlay_optional_pack(pack_path: Path, target_root: Path, platform_version: str) -> None:
    manifest = verify_optional_archive_contents(pack_path)
    if manifest.get("platformVersion") != platform_version:
        raise ValueError(
            f"選用套件 {pack_path.name} 的平台版本與預設包不一致"
        )
    declared_modes = {entry["path"]: entry["mode"] for entry in manifest["files"]}
    with zipfile.ZipFile(pack_path) as archive:
        manifest_member = next(
            name for name in archive.namelist() if name.endswith(f"/{OPTIONAL_PACK_MANIFEST}")
        )
        prefix = manifest_member[: -len(OPTIONAL_PACK_MANIFEST)]
        for info in archive.infolist():
            if info.is_dir() or info.filename == manifest_member:
                continue
            relative = PurePosixPath(info.filename.removeprefix(prefix))
            destination = target_root.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(destination, int(declared_modes[relative.as_posix()], 8))


def set_tree_read_only(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            current = stat.S_IMODE(path.stat().st_mode)
            os.chmod(path, 0o555 if current & 0o111 else 0o444)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        os.chmod(path, 0o555)
    os.chmod(root, 0o555)


def make_tree_writable(root: Path) -> None:
    if not root.exists():
        return
    os.chmod(root, 0o755)
    for path in root.rglob("*"):
        if path.is_dir():
            os.chmod(path, 0o755)
        elif path.is_file():
            current = stat.S_IMODE(path.stat().st_mode)
            os.chmod(path, 0o755 if current & 0o111 else 0o644)


def remove_tree(root: Path) -> None:
    make_tree_writable(root)
    shutil.rmtree(root)


def install_platform(
    archive: Path,
    checksum: Path,
    work_root: Path,
    platform_name: str = "ai-dev-platform",
    read_only: bool = True,
    keep_backup: bool = False,
    optional_packs: tuple[Path, ...] = (),
) -> Path:
    if not SAFE_NAME.fullmatch(platform_name):
        raise ValueError("平台目錄名稱不安全")
    archive, checksum, work_root = archive.resolve(), checksum.resolve(), work_root.resolve()
    if not work_root.is_dir():
        raise ValueError(f"Work 目錄不存在：{work_root}")
    verify_checksum(archive, checksum)
    platform_manifest = verify_archive_contents(archive)
    resolved_packs: list[Path] = []
    for pack in optional_packs:
        resolved = pack.resolve()
        verify_checksum(resolved, resolved.with_name(f"{resolved.name}.sha256"))
        resolved_packs.append(resolved)
    target = work_root / platform_name
    if target.exists() and (target / ".git").exists():
        raise ValueError("目標是 Git 儲存庫，拒絕當作唯讀平台包替換")
    backup = work_root / f".{platform_name}-backup-{uuid.uuid4().hex[:10]}"
    moved_old = False
    installed_new = False
    with tempfile.TemporaryDirectory(prefix=f".{platform_name}-install-", dir=work_root) as temp:
        staged = extract_verified(archive, Path(temp))
        for pack in resolved_packs:
            overlay_optional_pack(pack, staged, str(platform_manifest.get("version")))
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            ["bash", "scripts/check.sh"], cwd=staged, env=env, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            if target.exists():
                os.replace(target, backup)
                moved_old = True
            os.replace(staged, target)
            installed_new = True
            if read_only:
                set_tree_read_only(target)
        except Exception:
            if installed_new and target.exists():
                remove_tree(target)
            if moved_old and not target.exists():
                os.replace(backup, target)
            raise
    if moved_old and not keep_backup:
        remove_tree(backup)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--checksum", type=Path, help="預設為 <archive>.sha256")
    parser.add_argument("--work-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--platform-dir-name", default="ai-dev-platform")
    parser.add_argument("--writable", action="store_true", help="只供調試；安裝後保留可寫")
    parser.add_argument("--keep-backup", action="store_true")
    parser.add_argument(
        "--optional-pack", type=Path, action="append", default=[],
        help="要在同一次安裝疊加的選用 ZIP；其 .sha256 必須放在旁邊",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    checksum = args.checksum or args.archive.with_name(f"{args.archive.name}.sha256")
    try:
        verify_checksum(args.archive.resolve(), checksum.resolve())
        manifest = verify_archive_contents(args.archive.resolve())
        for pack in args.optional_pack:
            resolved_pack = pack.resolve()
            verify_checksum(
                resolved_pack, resolved_pack.with_name(f"{resolved_pack.name}.sha256")
            )
            pack_manifest = verify_optional_archive_contents(resolved_pack)
            if pack_manifest.get("platformVersion") != manifest.get("version"):
                raise ValueError(f"選用套件版本不一致：{pack.name}")
        if args.dry_run:
            print(f"[OK] install plan: {manifest.get('version')} -> {(args.work_root / args.platform_dir_name).resolve()}")
            return 0
        target = install_platform(
            args.archive, checksum, args.work_root, args.platform_dir_name,
            not args.writable, args.keep_backup, tuple(args.optional_pack),
        )
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        print(f"[FAIL] platform install: {error}", file=sys.stderr)
        return 1
    print(f"[OK] platform installed: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
