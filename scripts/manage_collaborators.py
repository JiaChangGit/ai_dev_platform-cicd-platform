#!/usr/bin/env python3
"""安全地同步 CODEOWNERS、協作者與 repository 審查政策。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


USERNAME_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
OWNER_PATTERN = re.compile(
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)"
    r"(?:/[A-Za-z0-9_.-]+)?"
)
PROJECT_PATTERN = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+")
ENV_NAME_PATTERN = re.compile(r"[A-Z_][A-Z0-9_]*")

MAINTENANCE_PATTERNS = (
    "*",
    "/governance/",
    "/distribution/",
    "/external/",
    "/scripts/",
    "/.github/",
    "/.gitlab/",
)
RELEASE_PATTERNS = (
    "*",
    "/release-evidence/",
    "/release-notes/",
    "/scripts/",
    "/.github/",
    "/.gitlab/",
)


@dataclass(frozen=True)
class RepositoryContext:
    root: Path
    kind: str
    patterns: tuple[str, ...]
    required_checks: tuple[str, ...]


class GitLabApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitLab API HTTP {status}: {message}")
        self.status = status


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def repository_context(root: Path) -> RepositoryContext:
    resolved = root.resolve()
    if not (resolved / ".git").exists():
        raise ValueError(f"不是 Git repository：{resolved}")
    is_release = (resolved / "release-evidence").is_dir() and (resolved / "release-notes").is_dir()
    return RepositoryContext(
        root=resolved,
        kind="release" if is_release else "maintenance",
        patterns=RELEASE_PATTERNS if is_release else MAINTENANCE_PATTERNS,
        required_checks=("repository-policy",) if is_release else ("self-check", "android-example"),
    )


def validate_username(username: str) -> str:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(f"username 格式無效：{username}")
    return username


def validate_owner(owner: str) -> str:
    value = owner.removeprefix("@")
    if not OWNER_PATTERN.fullmatch(value):
        raise ValueError(f"CODEOWNER 格式無效：{owner}")
    return value


def validate_project(project: str) -> str:
    value = project.removesuffix(".git")
    if not PROJECT_PATTERN.fullmatch(value) or ".." in value.split("/"):
        raise ValueError(f"repository／project 路徑無效：{project}")
    return value


def parse_github_repository(remote: str) -> str | None:
    prefixes = ("git@github.com:", "https://github.com/", "ssh://git@github.com/")
    for prefix in prefixes:
        if remote.startswith(prefix):
            return validate_project(remote[len(prefix) :])
    return None


def parse_gitlab_project(remote: str) -> str | None:
    prefixes = ("git@gitlab.com:", "https://gitlab.com/", "ssh://git@gitlab.com/")
    for prefix in prefixes:
        if remote.startswith(prefix):
            return validate_project(remote[len(prefix) :])
    return None


def existing_primary_owner(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for item in stripped.split()[1:]:
            if item.startswith("@"):
                return validate_owner(item)
    return None


def canonical_codeowners(
    text: str,
    *,
    username: str,
    primary_owner: str,
    default_patterns: tuple[str, ...],
) -> str:
    """加入協作者並補齊必要規則；既有註解與規則順序保持不變。"""
    collaborator = f"@{validate_username(username)}"
    owner = f"@{validate_owner(primary_owner)}"
    result: list[str] = []
    seen_patterns: set[str] = set()

    if not text.strip():
        result.append("# GitHub／GitLab 共用 CODEOWNERS；由 manage_collaborators.py 維護。")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            result.append(line)
            continue
        parts = stripped.split()
        if len(parts) < 2:
            raise ValueError(f"CODEOWNERS 規則缺少 owner：{line}")
        seen_patterns.add(parts[0])
        owners_lower = {item.lower() for item in parts[1:]}
        if owner.lower() not in owners_lower:
            parts.append(owner)
        if collaborator.lower() not in owners_lower:
            parts.append(collaborator)
        result.append(" ".join(parts))

    if result and result[-1] != "" and seen_patterns:
        result.append("")
    for pattern in default_patterns:
        if pattern not in seen_patterns:
            result.append(f"{pattern} {owner} {collaborator}")
    return "\n".join(result).rstrip() + "\n"


def codeowner_errors(
    text: str,
    *,
    required_patterns: tuple[str, ...],
    minimum_owners: int = 2,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        seen.add(parts[0])
        owners = {item.lower() for item in parts[1:] if item.startswith("@")}
        if len(owners) < minimum_owners:
            errors.append(f"第 {number} 行少於 {minimum_owners} 位不同 owner：{line}")
    for pattern in required_patterns:
        if pattern not in seen:
            errors.append(f"缺少規則：{pattern}")
    return errors


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def local_policy_errors(context: RepositoryContext) -> list[str]:
    github = context.root / ".github/CODEOWNERS"
    gitlab = context.root / ".gitlab/CODEOWNERS"
    errors: list[str] = []
    if not github.is_file():
        errors.append("缺少 .github/CODEOWNERS")
    if not gitlab.is_file():
        errors.append("缺少 .gitlab/CODEOWNERS")
    if errors:
        return errors
    github_text = github.read_text(encoding="utf-8")
    gitlab_text = gitlab.read_text(encoding="utf-8")
    if github_text != gitlab_text:
        errors.append("GitHub／GitLab CODEOWNERS 不同步")
    errors.extend(codeowner_errors(github_text, required_patterns=context.patterns))

    required_files = (
        (".github/workflows/repository-policy.yml", ".gitlab-ci.yml")
        if context.kind == "release"
        else (".github/workflows/check.yml", ".gitlab-ci.yml")
    )
    for relative in required_files:
        if not (context.root / relative).is_file():
            errors.append(f"缺少 CI 設定：{relative}")
    return errors


def run_gh(args: list[str], *, payload: object | None = None) -> str:
    result = subprocess.run(
        ["gh", *args],
        input=None if payload is None else json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or f"gh {' '.join(args)} 失敗")
    return result.stdout.strip()


def gh_api_json(method: str, endpoint: str, payload: object | None = None) -> object:
    args = ["api", "--method", method, endpoint]
    if payload is not None:
        args.extend(["--input", "-"])
    output = run_gh(args, payload=payload)
    return json.loads(output) if output else {}


def github_preflight(repository: str) -> dict[str, object]:
    if shutil.which("gh") is None:
        raise RuntimeError("找不到 gh；請安裝 GitHub CLI 並執行 gh auth login")
    run_gh(["auth", "status"])
    data = gh_api_json("GET", f"repos/{repository}")
    if not isinstance(data, dict) or str(data.get("full_name", "")).lower() != repository.lower():
        raise RuntimeError(f"GitHub repository 不一致：{repository}")
    permissions = data.get("permissions")
    if not isinstance(permissions, dict) or permissions.get("admin") is not True:
        raise RuntimeError(f"目前 gh 身分沒有 repository 管理權限：{repository}")
    return data


def github_add_collaborator(repository: str, username: str, permission: str) -> None:
    gh_api_json(
        "PUT",
        f"repos/{repository}/collaborators/{username}",
        {"permission": permission},
    )


def github_collaborator_is_active(repository: str, username: str) -> bool:
    result = subprocess.run(
        ["gh", "api", "--silent", f"repos/{repository}/collaborators/{username}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0:
        return True
    if "HTTP 404" in result.stdout or "Not Found" in result.stdout:
        return False
    raise RuntimeError(result.stdout.strip() or "無法確認 GitHub collaborator 狀態")


def configure_github_policy(
    repository: str,
    *,
    branch: str,
    required_checks: list[str],
    approvals: int,
) -> None:
    gh_api_json(
        "PATCH",
        f"repos/{repository}",
        {
            "allow_squash_merge": True,
            "allow_merge_commit": False,
            "allow_rebase_merge": False,
            "delete_branch_on_merge": True,
        },
    )
    status_checks: object = None
    if required_checks:
        status_checks = {
            "strict": True,
            "checks": [{"context": name} for name in required_checks],
        }
    gh_api_json(
        "PUT",
        f"repos/{repository}/branches/{urllib.parse.quote(branch, safe='')}/protection",
        {
            "required_status_checks": status_checks,
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
                "required_approving_review_count": approvals,
                "require_last_push_approval": True,
            },
            "restrictions": None,
            "required_linear_history": True,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "block_creations": False,
            "required_conversation_resolution": True,
            "lock_branch": False,
            "allow_fork_syncing": True,
        },
    )


def request_github_review(repository: str, username: str, pr_number: int) -> None:
    gh_api_json(
        "POST",
        f"repos/{repository}/pulls/{pr_number}/requested_reviewers",
        {"reviewers": [username]},
    )


def validate_gitlab_api_url(value: str, *, allow_insecure_http: bool) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" and not (allow_insecure_http and parsed.scheme == "http"):
        raise ValueError("GitLab API URL 必須使用 HTTPS；測試環境才可明確允許 HTTP")
    if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("GitLab API URL 格式無效")
    return value.rstrip("/")


def gitlab_request(
    base_url: str,
    endpoint: str,
    *,
    token: str,
    method: str = "GET",
    payload: object | None = None,
) -> object:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{endpoint}",
        data=body,
        method=method,
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise GitLabApiError(error.code, detail or error.reason) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"無法連線 GitLab API：{error.reason}") from error
    return json.loads(data) if data else {}


def gitlab_user_id(base_url: str, token: str, username: str) -> int:
    query = urllib.parse.urlencode({"username": username})
    users = gitlab_request(base_url, f"/users?{query}", token=token)
    exact = [
        item for item in users
        if isinstance(item, dict) and str(item.get("username", "")).lower() == username.lower()
    ] if isinstance(users, list) else []
    if len(exact) != 1 or not isinstance(exact[0].get("id"), int):
        raise RuntimeError(f"GitLab username 無法唯一解析：{username}")
    return int(exact[0]["id"])


def gitlab_add_member(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    user_id: int,
    access_level: int,
) -> None:
    try:
        gitlab_request(
            base_url,
            f"{project_endpoint}/members",
            token=token,
            method="POST",
            payload={"user_id": user_id, "access_level": access_level},
        )
    except GitLabApiError as error:
        if error.status != 409:
            raise
        gitlab_request(
            base_url,
            f"{project_endpoint}/members/{user_id}",
            token=token,
            method="PUT",
            payload={"access_level": access_level},
        )


def configure_gitlab_policy(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    branch: str,
    approvals: int,
) -> None:
    gitlab_request(
        base_url,
        project_endpoint,
        token=token,
        method="PUT",
        payload={
            "only_allow_merge_if_pipeline_succeeds": True,
            "only_allow_merge_if_all_discussions_are_resolved": True,
            "remove_source_branch_after_merge": True,
        },
    )

    branch_endpoint = f"{project_endpoint}/protected_branches/{urllib.parse.quote(branch, safe='')}"
    try:
        current = gitlab_request(base_url, branch_endpoint, token=token)
    except GitLabApiError as error:
        if error.status != 404:
            raise
        current = None
    if current is None:
        gitlab_request(
            base_url,
            f"{project_endpoint}/protected_branches",
            token=token,
            method="POST",
            payload={
                "name": branch,
                "push_access_level": 0,
                "merge_access_level": 30,
                "unprotect_access_level": 40,
                "allow_force_push": False,
                "code_owner_approval_required": True,
            },
        )
    else:
        push_updates: list[dict[str, object]] = []
        if isinstance(current, dict):
            for record in current.get("push_access_levels", []):
                if not isinstance(record, dict) or not isinstance(record.get("id"), int):
                    continue
                if record.get("deploy_key_id") is not None:
                    push_updates.append({"id": record["id"], "_destroy": True})
                else:
                    push_updates.append({"id": record["id"], "access_level": 0})
        payload: dict[str, object] = {
            "allow_force_push": False,
            "code_owner_approval_required": True,
        }
        if push_updates:
            payload["allowed_to_push"] = push_updates
        gitlab_request(base_url, branch_endpoint, token=token, method="PATCH", payload=payload)

    gitlab_request(
        base_url,
        f"{project_endpoint}/approvals",
        token=token,
        method="POST",
        payload={
            "reset_approvals_on_push": True,
            "disable_overriding_approvers_per_merge_request": True,
            "merge_requests_author_approval": False,
            "merge_requests_disable_committers_approval": True,
        },
    )
    rules = gitlab_request(base_url, f"{project_endpoint}/approval_rules", token=token)
    named = [item for item in rules if isinstance(item, dict) and item.get("name") == "Repository policy"] \
        if isinstance(rules, list) else []
    rule_payload = {
        "name": "Repository policy",
        "approvals_required": approvals,
        "applies_to_all_protected_branches": True,
    }
    if named and isinstance(named[0].get("id"), int):
        gitlab_request(
            base_url,
            f"{project_endpoint}/approval_rules/{named[0]['id']}",
            token=token,
            method="PUT",
            payload=rule_payload,
        )
    else:
        gitlab_request(
            base_url,
            f"{project_endpoint}/approval_rules",
            token=token,
            method="POST",
            payload=rule_payload,
        )


def request_gitlab_review(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    user_id: int,
    merge_request_iid: int,
) -> None:
    endpoint = f"{project_endpoint}/merge_requests/{merge_request_iid}"
    current = gitlab_request(base_url, endpoint, token=token)
    reviewers = current.get("reviewers", []) if isinstance(current, dict) else []
    reviewer_ids = {
        item["id"] for item in reviewers
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    }
    reviewer_ids.add(user_id)
    gitlab_request(
        base_url,
        endpoint,
        token=token,
        method="PUT",
        payload={"reviewer_ids": sorted(reviewer_ids)},
    )


def source_codeowners(context: RepositoryContext) -> str:
    github = context.root / ".github/CODEOWNERS"
    gitlab = context.root / ".gitlab/CODEOWNERS"
    if github.is_file():
        return github.read_text(encoding="utf-8")
    if gitlab.is_file():
        return gitlab.read_text(encoding="utf-8")
    return ""


def add_command(args: argparse.Namespace, context: RepositoryContext) -> int:
    username = validate_username(args.username)
    try:
        remote = git(context.root, "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        remote = ""
    github_repository = args.github_repository or parse_github_repository(remote)
    gitlab_project = args.gitlab_project or parse_gitlab_project(remote)
    if args.skip_github:
        github_repository = None
    if args.skip_gitlab:
        gitlab_project = None
    if github_repository:
        github_repository = validate_project(github_repository)
    if gitlab_project:
        gitlab_project = validate_project(gitlab_project)
    if args.local_only and (
        args.request_review is not None or args.request_merge_request_review is not None
    ):
        raise ValueError("--local-only 不可搭配遠端 reviewer 參數")
    if args.apply and not args.local_only and not github_repository and not gitlab_project:
        raise RuntimeError("沒有可處理的 GitHub／GitLab 目標；只改本機請加上 --local-only")

    current = source_codeowners(context)
    inferred_owner = existing_primary_owner(current)
    if args.owner:
        primary_owner = validate_owner(args.owner)
    elif inferred_owner:
        primary_owner = inferred_owner
    elif github_repository:
        primary_owner = validate_owner(github_repository.split("/", 1)[0])
    else:
        raise ValueError("新的 CODEOWNERS 必須用 --owner 指定既有負責人或 team")
    content = canonical_codeowners(
        current,
        username=username,
        primary_owner=primary_owner,
        default_patterns=context.patterns,
    )

    checks = list(args.required_check) if args.required_check is not None else list(context.required_checks)
    print(f"[PLAN] repository: {context.root}")
    print(f"[PLAN] CODEOWNERS: @{primary_owner} + @{username}")
    if github_repository:
        print(f"[PLAN] GitHub: {github_repository}; required checks={','.join(checks) or '(none)'}")
    if gitlab_project:
        print(f"[PLAN] GitLab: {gitlab_project}; token env={args.gitlab_token_env}")
    if not args.apply:
        print("[DRY-RUN] 未修改檔案或遠端設定；確認後加上 --apply")
        return 0

    atomic_write(context.root / ".github/CODEOWNERS", content)
    atomic_write(context.root / ".gitlab/CODEOWNERS", content)
    print("[OK] GitHub／GitLab CODEOWNERS 已同步")
    if args.local_only:
        return 0
    pending_github_invitation = False
    if github_repository:
        metadata = github_preflight(github_repository)
        github_add_collaborator(github_repository, username, args.github_permission)
        active = github_collaborator_is_active(github_repository, username)
        print(f"[OK] GitHub collaborator 已存在或邀請已送出：{username}")
        if active:
            if args.configure_policy:
                branch = args.branch or str(metadata.get("default_branch") or "main")
                configure_github_policy(
                    github_repository,
                    branch=branch,
                    required_checks=checks,
                    approvals=args.approvals,
                )
                print(f"[OK] GitHub PR／branch protection 已設定：{branch}")
            if args.request_review is not None:
                request_github_review(github_repository, username, args.request_review)
                print(f"[OK] GitHub PR #{args.request_review} 已加入 reviewer")
        else:
            pending_github_invitation = True
            print(
                "[WAIT] GitHub 邀請尚未接受；為避免鎖住預設分支，暫不啟用 branch protection 或指定 reviewer",
                file=sys.stderr,
            )

    if gitlab_project:
        if not ENV_NAME_PATTERN.fullmatch(args.gitlab_token_env):
            raise ValueError("GitLab token 環境變數名稱格式無效")
        token = os.environ.get(args.gitlab_token_env, "")
        if not token:
            raise RuntimeError(f"缺少 GitLab token 環境變數：{args.gitlab_token_env}")
        base_url = validate_gitlab_api_url(
            args.gitlab_api_url,
            allow_insecure_http=args.allow_insecure_gitlab_http,
        )
        project_endpoint = f"/projects/{urllib.parse.quote(gitlab_project, safe='')}"
        project = gitlab_request(base_url, project_endpoint, token=token)
        if not isinstance(project, dict):
            raise RuntimeError(f"GitLab project 回應格式無效：{gitlab_project}")
        user_id = gitlab_user_id(base_url, token, username)
        gitlab_add_member(
            base_url,
            project_endpoint,
            token=token,
            user_id=user_id,
            access_level=args.gitlab_access_level,
        )
        print(f"[OK] GitLab member 已設定：{username}")
        if args.configure_policy:
            branch = args.branch or str(project.get("default_branch") or "main")
            configure_gitlab_policy(
                base_url,
                project_endpoint,
                token=token,
                branch=branch,
                approvals=args.approvals,
            )
            print(f"[OK] GitLab MR／protected branch 已設定：{branch}")
        if args.request_merge_request_review is not None:
            request_gitlab_review(
                base_url,
                project_endpoint,
                token=token,
                user_id=user_id,
                merge_request_iid=args.request_merge_request_review,
            )
            print(f"[OK] GitLab MR !{args.request_merge_request_review} 已加入 reviewer")

    if pending_github_invitation:
        print("[NEXT] 對方接受邀請後，以相同參數重跑一次 --apply", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="目前 repository 根目錄",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="驗證 CODEOWNERS 與 CI 政策檔")

    add = subparsers.add_parser("add", help="新增 collaborator／member 並設定審查政策")
    add.add_argument("username")
    add.add_argument("--apply", action="store_true", help="實際修改；預設只顯示計畫")
    add.add_argument("--local-only", action="store_true", help="只更新 CODEOWNERS，不呼叫 API")
    add.add_argument("--owner", help="既有 CODEOWNER；可用 user 或 organization/team")
    add.add_argument("--github-repository", help="owner/repository；GitHub origin 可自動判斷")
    add.add_argument("--skip-github", action="store_true", help="不呼叫 GitHub API")
    add.add_argument("--github-permission", choices=("pull", "triage", "push", "maintain", "admin"), default="push")
    add.add_argument("--request-review", type=int, metavar="PR_NUMBER")
    add.add_argument("--gitlab-project", help="group/project；GitLab origin 可自動判斷")
    add.add_argument("--skip-gitlab", action="store_true", help="不呼叫 GitLab API")
    add.add_argument("--gitlab-api-url", default="https://gitlab.com/api/v4")
    add.add_argument("--gitlab-token-env", default="GITLAB_TOKEN")
    add.add_argument("--gitlab-access-level", choices=(30, 40), type=int, default=30, help="30=Developer；40=Maintainer")
    add.add_argument("--request-merge-request-review", type=int, metavar="MR_IID")
    add.add_argument("--allow-insecure-gitlab-http", action="store_true", help="只供隔離測試環境")
    add.add_argument("--branch", help="要保護的分支；預設讀取遠端 default branch")
    add.add_argument("--required-check", action="append", help="GitHub 必要狀態檢查；可重複")
    add.add_argument("--approvals", choices=range(1, 7), type=int, default=1)
    add.add_argument(
        "--configure-policy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="設定 PR／MR、必要 CI 與分支保護",
    )

    args = parser.parse_args()
    try:
        context = repository_context(args.root)
        if args.command == "check":
            errors = local_policy_errors(context)
            if errors:
                for error in errors:
                    print(f"[FAIL] collaborator policy: {error}", file=sys.stderr)
                return 1
            print(f"[OK] collaborator policy: {context.kind}")
            return 0
        return add_command(args, context)
    except (
        GitLabApiError,
        OSError,
        ValueError,
        RuntimeError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        print(f"[FAIL] collaborator management: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
