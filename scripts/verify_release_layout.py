#!/usr/bin/env python3
"""驗證 product-release 只保存允許的發行中繼資料。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from verify_release_evidence import validate_evidence


ROOT_FILES = {
    ".gitignore",
    ".gitlab-ci.yml",
    "AGENTS.md",
    "CLAUDE.md",
    "CODEOWNERS",
    "Jenkinsfile",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "opencode.json",
}
ROOT_DIRECTORIES = {".github", ".gitlab", "release-evidence", "release-notes", "scripts"}


def is_allowed_repository_file(relative: Path) -> bool:
    if len(relative.parts) == 1:
        return relative.name in ROOT_FILES
    if relative.parts[0] == "release-evidence":
        return len(relative.parts) == 2 and (
            relative.name == "README.md" or relative.suffix == ".json"
        )
    if relative.parts[0] == "release-notes":
        return len(relative.parts) == 2 and relative.suffix == ".md"
    if relative.parts[0] == ".github":
        if relative.as_posix() in {
            ".github/CODEOWNERS",
            ".github/dependabot.yml",
            ".github/pull_request_template.md",
        }:
            return True
        return (
            len(relative.parts) == 3
            and relative.parts[1] == "workflows"
            and relative.suffix in {".yml", ".yaml"}
        )
    if relative.parts[0] == ".gitlab":
        if relative.as_posix() == ".gitlab/CODEOWNERS":
            return True
        return (
            relative.as_posix() == ".gitlab/merge_request_templates/default.md"
        )
    if relative.parts[0] == "scripts":
        return relative.as_posix() == "scripts/manage_collaborators.py"
    return False


def is_allowed_repository_directory(relative: Path) -> bool:
    if len(relative.parts) == 1:
        return relative.name in ROOT_DIRECTORIES
    return relative.as_posix() in {
        ".github/workflows",
        ".gitlab/merge_request_templates",
    }


def validate_release_layout(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"發行儲存庫不存在：{root}"]

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            errors.append(f"不得使用符號連結：{relative.as_posix()}")
            continue
        if path.is_dir() and not is_allowed_repository_directory(relative):
            errors.append(f"不在發行儲存庫允許清單內的目錄：{relative.as_posix()}")
        elif path.is_file() and not is_allowed_repository_file(relative):
            errors.append(f"不在發行儲存庫允許清單內的檔案：{relative.as_posix()}")

    evidence_dir = root / "release-evidence"
    if evidence_dir.is_dir():
        for path in evidence_dir.iterdir():
            if path.name == "README.md":
                continue
            if not path.is_file() or path.suffix != ".json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"發行證據無法解析：{path.name}: {error}")
                continue
            errors.extend(f"{path.name}: {message}" for message in validate_evidence(data))
            if isinstance(data, dict) and data.get("version") != path.stem:
                errors.append(f"{path.name}: version 與檔名不一致")
            note = root / "release-notes" / f"{path.stem}.md"
            if not note.is_file():
                errors.append(f"{path.name}: 缺少同版本 Release Note")
            else:
                first = next(
                    (line.strip() for line in note.read_text(encoding="utf-8").splitlines() if line.strip()),
                    "",
                )
                if not first.startswith("# ") or f"v{path.stem}" not in first:
                    errors.append(f"{path.name}: Release Note 標題版本不一致")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="product-release 儲存庫路徑")
    args = parser.parse_args()
    errors = validate_release_layout(args.root.resolve())
    if errors:
        for error in errors:
            print(f"[FAIL] release layout: {error}", file=sys.stderr)
        return 1
    print(f"[OK] release layout: {args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
