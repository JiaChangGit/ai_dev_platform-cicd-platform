#!/usr/bin/env python3
"""以唯讀方式稽核 Work 中的共用平台、產品與發行儲存庫。"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from verify_release_layout import validate_release_layout  # noqa: E402


def audit_workspace(work_root: Path) -> dict:
    work_root = work_root.resolve()
    platform = work_root / "ai-dev-platform"
    errors: list[str] = []
    products: list[str] = []
    releases: list[str] = []
    if not platform.is_dir():
        errors.append("Work/ai-dev-platform 不存在")
    else:
        if (platform / ".git").exists():
            errors.append("Work/ai-dev-platform 不得包含 .git")
        for entry in ("AGENTS.md", "CLAUDE.md", "opencode.json", "scripts/check.sh"):
            if not (platform / entry).is_file():
                errors.append(f"共用平台缺少 {entry}")
        writable = [
            path.relative_to(platform).as_posix() for path in platform.rglob("*")
            if path.is_file() and stat.S_IMODE(path.stat().st_mode) & 0o222
        ]
        if writable:
            errors.append(f"唯讀平台仍有可寫檔案：{', '.join(writable[:3])}")

    for child in sorted(path for path in work_root.iterdir() if path.is_dir()):
        metadata_path = child / ".ai" / "product.json"
        if not metadata_path.is_file():
            continue
        products.append(child.name)
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{child.name}: .ai/product.json 無法解析：{error}")
            continue
        if metadata.get("platform") != "../ai-dev-platform":
            errors.append(f"{child.name}: platform 必須是 ../ai-dev-platform")
        if metadata.get("platformVersionPolicy") != "always-current":
            errors.append(f"{child.name}: platformVersionPolicy 必須是 always-current")
        agents = child / "AGENTS.md"
        if not agents.is_file() or "../ai-dev-platform/AGENTS.md" not in agents.read_text(encoding="utf-8"):
            errors.append(f"{child.name}: AGENTS.md 未讀取穩定共用平台")
        for lock in (child / ".ai/platform.lock", child / ".ai/platform-version.json"):
            if lock.exists():
                errors.append(f"{child.name}: 不得鎖定平台版本：{lock.name}")
        if not (child / ".git").exists():
            errors.append(f"{child.name}: 產品開發目錄必須是獨立 Git 儲存庫")
        release_value = metadata.get("releaseRepository")
        if isinstance(release_value, str):
            release = (child / release_value).resolve()
            try:
                release.relative_to(work_root)
            except ValueError:
                errors.append(f"{child.name}: releaseRepository 超出 Work 範圍")
                continue
            releases.append(release.name)
            if not (release / ".git").exists():
                errors.append(f"{release.name}: 發行目錄必須是獨立 Git 儲存庫")
            errors.extend(f"{release.name}: {message}" for message in validate_release_layout(release))
    return {
        "workRoot": str(work_root), "platform": str(platform),
        "products": sorted(set(products)), "releaseRepositories": sorted(set(releases)),
        "errors": errors, "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_root", type=Path, nargs="?", default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_workspace(args.work_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print(f"[OK] workspace audit: {result['workRoot']} ({len(result['products'])} products)")
    else:
        for error in result["errors"]:
            print(f"[FAIL] workspace audit: {error}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
