#!/usr/bin/env python3
"""在 Git push 前檢查儲存庫邊界、忽略規則與高信心敏感資料樣式。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SECRET_PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "openai-project-key": re.compile(rb"sk-proj-[A-Za-z0-9_-]{30,}"),
    "aws-access-key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    # Google API key 固定為 AIza + 35 個字元。邊界條件可避免 notebook
    # 內嵌圖片的長 base64 字串剛好含 AIza 時產生偽陽性。
    "google-api-key": re.compile(
        rb"(?<![0-9A-Za-z_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])"
    ),
    "slack-token": re.compile(rb"xox[baprs]-[0-9A-Za-z-]{20,}"),
}
REQUIRED_IGNORE_RULES = {
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "dist/", "build/", "__pycache__/", "*.py[cod]", ".gradle/", "local.properties",
    ".idea/", ".vscode/", "/.ai/handoffs/",
}
FORBIDDEN_TRACKED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_TRACKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
SCAN_CHUNK_BYTES = 1024 * 1024
SCAN_OVERLAP_BYTES = 512
SAFE_REMOTE_PATTERN = re.compile(
    r"(?:(?:git@[A-Za-z0-9_.-]+:)"
    r"|(?:ssh://git@[A-Za-z0-9_.-]+(?::\d+)?/)"
    r"|(?:https://[A-Za-z0-9_.-]+(?::\d+)?/))"
    r"[A-Za-z0-9_.~/-]+(?:\.git)?"
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def repository_files(root: Path) -> list[str]:
    tracked = git(root, "ls-files", "-z").split("\0")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({path for path in tracked + untracked if path})


def is_safe_remote_url(remote: str) -> bool:
    """只接受不含內嵌密碼或 Token 的 Git SSH／HTTPS remote。"""
    return SAFE_REMOTE_PATTERN.fullmatch(remote) is not None


def find_secret_types(path: Path) -> list[str]:
    """分段掃描文字檔，避免大型 Notebook／CSV 因記憶體限制而未受檢查。"""
    try:
        with path.open("rb") as stream:
            first = stream.read(8192)
            if b"\0" in first:
                return []
            stream.seek(0)
            previous = b""
            found: set[str] = set()
            while chunk := stream.read(SCAN_CHUNK_BYTES):
                payload = previous + chunk
                for kind, pattern in SECRET_PATTERNS.items():
                    if kind not in found and pattern.search(payload):
                        found.add(kind)
                previous = payload[-SCAN_OVERLAP_BYTES:]
            return sorted(found)
    except OSError:
        return []


def inspect_git_identity(
    root: Path,
    *,
    required: bool,
) -> tuple[dict[str, str], list[str], list[str]]:
    """讀取本機 commit 身分；CI runner 不建立 commit，因此不要求此設定。"""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        identity = {
            "name": git(root, "config", "user.name"),
            "email": git(root, "config", "user.email"),
        }
    except subprocess.CalledProcessError:
        identity = {"name": "", "email": ""}
        if required:
            errors.append("Git user.name 與 user.email 必須先設定")
    if (
        required
        and identity["email"]
        and not identity["email"].lower().endswith("@users.noreply.github.com")
    ):
        warnings.append("Git commit 會公開目前的 user.email；公開儲存庫建議改用 GitHub noreply 信箱")
    return identity, errors, warnings


def audit_repository(root: Path, *, ci: bool = False) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        git_root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        return {"ok": False, "errors": [f"不是 Git 儲存庫：{error}"], "warnings": []}
    if git_root != root:
        errors.append(f"必須從儲存庫根目錄執行：{git_root}")
    if root.name == "ai-dev-platform":
        errors.append("不得推送無 .git 的 Work/ai-dev-platform 唯讀平台包")
    if root.name != "ai_dev_platform-cicd-platform":
        warnings.append(f"目錄名不是預期的維護儲存庫：{root.name}")

    try:
        remote = git(root, "remote", "get-url", "origin")
        if not is_safe_remote_url(remote):
            errors.append("origin 不是無內嵌憑證的 Git SSH／HTTPS URL")
    except (OSError, subprocess.CalledProcessError):
        errors.append("缺少 origin remote")
        remote = ""

    ignore_path = root / ".gitignore"
    if not ignore_path.is_file():
        errors.append("缺少 .gitignore")
    else:
        rules = {
            line.strip() for line in ignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if missing := sorted(REQUIRED_IGNORE_RULES - rules):
            errors.append(f".gitignore 缺少必要規則：{', '.join(missing)}")

    files = repository_files(root)
    sensitive_hits: list[dict[str, str]] = []
    for relative in files:
        path = root / relative
        parts = Path(relative).parts
        if any(part in FORBIDDEN_TRACKED_PARTS for part in parts):
            errors.append(f"不得準備推送快取目錄：{relative}")
        if path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
            errors.append(f"不得準備推送金鑰／憑證檔：{relative}")
        if not path.is_file():
            continue
        for kind in find_secret_types(path):
            sensitive_hits.append({"path": relative, "type": kind})
    for hit in sensitive_hits:
        errors.append(f"高信心敏感資料樣式：{hit['path']} ({hit['type']})")

    tracked = set(git(root, "ls-files").splitlines())
    for forbidden in ("dist", "build"):
        if any(path == forbidden or path.startswith(f"{forbidden}/") for path in tracked):
            errors.append(f"建置成品目錄不得被 Git 追蹤：{forbidden}/")
    if any(path.startswith(".ai/handoffs/") for path in tracked):
        errors.append(".ai/handoffs/ 可能包含對話上下文，不得推送")

    branch = git(root, "branch", "--show-current")
    if branch in {"main", "master"}:
        warnings.append("目前在預設分支；推送前應建立 agent/<description> 功能分支")
    identity, identity_errors, identity_warnings = inspect_git_identity(
        root,
        required=not ci,
    )
    errors.extend(identity_errors)
    warnings.extend(identity_warnings)
    return {
        "schemaVersion": 1,
        "auditMode": "ci" if ci else "local",
        "repository": str(root),
        "remote": remote,
        "branch": branch,
        "gitIdentity": identity,
        "gitIdentityRequired": not ci,
        "scannedFileCount": len(files),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI 驗證模式：不要求 runner 設定 Git commit 身分；其他檢查不變",
    )
    args = parser.parse_args()
    try:
        result = audit_repository(args.root, ci=args.ci)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"[FAIL] pre-push audit: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"[WARN] pre-push audit: {warning}")
        for error in result["errors"]:
            print(f"[FAIL] pre-push audit: {error}", file=sys.stderr)
        if result["ok"]:
            print(f"[OK] pre-push audit: {result['scannedFileCount']} files, {result['remote']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
