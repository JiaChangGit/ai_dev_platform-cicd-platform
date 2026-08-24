#!/usr/bin/env python3
"""在離線環境驗證可發行的 ai-dev-platform ZIP。"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath


RELEASE_MANIFEST = "RELEASE-MANIFEST.json"
REQUIRED_ROOT_FILES = {"AGENTS.md", "CLAUDE.md", "README.md", "opencode.json"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"無法讀取 JSON：{path}: {error}")


def safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and ".git" not in path.parts


def expected_payload_names(root: Path, config: dict) -> set[str]:
    excluded = set(config.get("excludeNames", []))
    excluded_globs = config.get("excludeGlobs", [])
    names: set[str] = set()
    for relative in config["include"]:
        target = root / relative
        if not target.exists():
            fail(f"distribution/manifest.json 指向不存在的內容：{relative}")
        if target.is_file():
            names.add(target.relative_to(root).as_posix())
            continue
        for item in target.rglob("*"):
            item_relative = item.relative_to(root)
            item_name = item_relative.as_posix()
            if not item.is_file() or any(part in excluded for part in item_relative.parts):
                continue
            if any(fnmatch.fnmatch(item_name, pattern) for pattern in excluded_globs):
                continue
            names.add(item_name)
    return names


def archive_file_mode(info: zipfile.ZipInfo) -> str:
    """Return the portable permission bits recorded in a ZIP member."""
    return f"{(info.external_attr >> 16) & 0o777:04o}"


def verify_archive_contents(archive_path: Path) -> dict:
    """Verify path safety, hashes, sizes and modes without needing the source tree."""
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = {name for name in archive.namelist() if not name.endswith("/")}
        unsafe = sorted(name for name in archive_names if not safe_archive_name(name))
        if unsafe:
            fail(f"壓縮檔含不安全或 Git 內部路徑：{', '.join(unsafe[:3])}")
        manifest_members = [
            name for name in archive_names
            if name == RELEASE_MANIFEST or name.endswith(f"/{RELEASE_MANIFEST}")
        ]
        if len(manifest_members) != 1:
            fail(f"壓縮檔必須恰好包含一份 {RELEASE_MANIFEST}")
        manifest_member = manifest_members[0]
        prefix = manifest_member[: -len(RELEASE_MANIFEST)]
        archive_root = prefix.rstrip("/")
        if not archive_root or "/" in archive_root:
            fail("壓縮檔頂層必須是單一安全目錄")
        outside_root = sorted(name for name in archive_names if not name.startswith(prefix))
        if outside_root:
            fail(f"壓縮檔內容不在 {archive_root}/ 下：{', '.join(outside_root[:3])}")
        names = {name.removeprefix(prefix) for name in archive_names}
        missing_root = sorted(REQUIRED_ROOT_FILES - names)
        if missing_root:
            fail(f"壓縮檔缺少開發工具入口檔：{', '.join(missing_root)}")

        release_manifest = json.loads(archive.read(manifest_member).decode("utf-8"))
        files = release_manifest.get("files")
        if not isinstance(files, list) or not files:
            fail(f"{RELEASE_MANIFEST} 沒有 files 清單")
        declared = {entry.get("path"): entry for entry in files if isinstance(entry, dict)}
        if len(declared) != len(files) or None in declared:
            fail(f"{RELEASE_MANIFEST} 含無效或重複的檔案路徑")
        actual_payload = names - {RELEASE_MANIFEST}
        if set(declared) != actual_payload:
            fail(f"{RELEASE_MANIFEST} 的檔案清單與 ZIP 實際內容不一致")
        for path, entry in declared.items():
            if not safe_archive_name(path):
                fail(f"{RELEASE_MANIFEST} 含不安全路徑：{path}")
            member = f"{prefix}{path}"
            payload = archive.read(member)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != entry.get("sha256") or len(payload) != entry.get("size"):
                fail(f"檔案 hash 或大小不符：{path}")
            if entry.get("mode") not in {"0644", "0755"}:
                fail(f"檔案權限未宣告或不安全：{path}")
            if archive_file_mode(archive.getinfo(member)) != entry["mode"]:
                fail(f"檔案權限與 manifest 不一致：{path}")
        return release_manifest


def verify_archive(archive_path: Path, root: Path) -> None:
    config = load_json(root / "distribution" / "manifest.json")
    expected = expected_payload_names(root, config)
    archive_root = config.get("archiveRoot", config["platformId"]).strip("/")
    prefix = f"{archive_root}/"
    release_manifest_path = f"{prefix}{RELEASE_MANIFEST}"

    verify_archive_contents(archive_path)

    with zipfile.ZipFile(archive_path) as archive:
        archive_names = {name for name in archive.namelist() if not name.endswith("/")}
        unsafe = sorted(name for name in archive_names if not safe_archive_name(name))
        if unsafe:
            fail(f"壓縮檔含不安全或 Git 內部路徑：{', '.join(unsafe[:3])}")
        outside_root = sorted(name for name in archive_names if not name.startswith(prefix))
        if outside_root:
            fail(f"壓縮檔內容不在 {archive_root}/ 下：{', '.join(outside_root[:3])}")
        names = {name.removeprefix(prefix) for name in archive_names}
        missing = sorted(expected - names)
        if missing:
            fail(f"壓縮檔缺少 manifest 指定內容：{', '.join(missing[:5])}")
        unexpected = sorted(names - expected - {RELEASE_MANIFEST})
        if unexpected:
            fail(f"壓縮檔含 manifest 未宣告內容：{', '.join(unexpected[:5])}")
        missing_root = sorted(REQUIRED_ROOT_FILES - names)
        if missing_root:
            fail(f"壓縮檔缺少開發工具入口檔：{', '.join(missing_root)}")
        if RELEASE_MANIFEST not in names:
            fail(f"壓縮檔缺少 {RELEASE_MANIFEST}")

        release_manifest = json.loads(archive.read(release_manifest_path).decode("utf-8"))
        files = release_manifest.get("files")
        if not isinstance(files, list) or not files:
            fail(f"{RELEASE_MANIFEST} 沒有 files 清單")
        declared = {entry.get("path"): entry for entry in files}
        if set(declared) != expected:
            fail(f"{RELEASE_MANIFEST} 的檔案清單與實際 distribution manifest 不一致")
        for path, entry in declared.items():
            payload = archive.read(f"{prefix}{path}")
            digest = hashlib.sha256(payload).hexdigest()
            source_mode = "0755" if (root / path).stat().st_mode & 0o111 else "0644"
            if digest != entry.get("sha256") or len(payload) != entry.get("size"):
                fail(f"檔案 hash 或大小不符：{path}")
            if entry.get("mode") != source_mode:
                fail(f"檔案權限與來源工作樹不一致：{path}")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="待驗證的 ZIP 檔")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1], help="Git 維護儲存庫根目錄"
    )
    args = parser.parse_args()
    try:
        verify_archive(args.archive.resolve(), args.root.resolve())
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"[FAIL] package verification: {error}", file=sys.stderr)
        return 1
    print(f"[OK] package verification: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
