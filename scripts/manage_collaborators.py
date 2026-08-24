#!/usr/bin/env python3
"""安全地同步 CODEOWNERS、協作者與 repository 審查政策。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
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


@dataclass(frozen=True)
class GitLabPreflightResult:
    project: dict[str, object]
    user_id: int
    branch: str | None
    protected_branch: dict[str, object] | None
    approval_rules: list[object]
    merge_request: dict[str, object] | None


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
        required_checks=("repository-policy", "analyze-python")
        if is_release
        else ("self-check", "android-example", "analyze-actions", "analyze-python"),
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


def selected_branch(
    override: str | None,
    metadata: dict[str, object],
    *,
    provider: str,
) -> str:
    if override:
        return override
    branch = metadata.get("default_branch")
    if not isinstance(branch, str) or not branch.strip():
        raise RuntimeError(f"{provider} repository 缺少有效 default_branch；請用 --branch 明確指定")
    return branch


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
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.chmod(mode)
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


def github_branch_protection_preflight(repository: str, branch: str) -> None:
    """先確認方案可使用 branch protection，避免遠端只套用一半。"""
    encoded_branch = urllib.parse.quote(branch, safe="")
    branch_endpoint = f"repos/{repository}/branches/{encoded_branch}"
    branch_result = subprocess.run(
        ["gh", "api", "--method", "GET", branch_endpoint],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if branch_result.returncode != 0:
        detail = branch_result.stdout.strip()
        raise RuntimeError(
            f"GitHub 分支不存在或無法讀取：{repository}/{branch}"
            + (f"；{detail}" if detail else "")
        )
    try:
        branch_data = json.loads(branch_result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"GitHub 分支回應格式無效：{repository}/{branch}"
        ) from error
    if not isinstance(branch_data, dict) or branch_data.get("name") != branch:
        raise RuntimeError(
            f"GitHub 分支回應格式或名稱不一致：{repository}/{branch}"
        )

    endpoint = f"{branch_endpoint}/protection"
    result = subprocess.run(
        ["gh", "api", "--method", "GET", endpoint],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode == 0:
        return
    if any(marker in output for marker in ('"status":"404"', '"status":404', "HTTP 404")):
        return
    if "Upgrade to GitHub Pro" in output and "make this repository public" in output:
        raise RuntimeError(
            "GitHub branch protection 不可用：私人 repository 必須使用 GitHub Pro、"
            "GitHub Team 或 GitHub Enterprise，或將 repository 改為公開。"
            "branch protection 是阻擋條件，因此腳本不會自動改用 --no-configure-policy"
        )
    raise RuntimeError(output or f"無法確認 GitHub branch protection：{repository}/{branch}")


def github_review_preflight(repository: str, username: str, pr_number: int) -> None:
    """確認 reviewer 與開啟中的 PR，避免設定完成後才發現審查目標無效。"""
    user = gh_api_json(
        "GET",
        f"users/{urllib.parse.quote(username, safe='')}",
    )
    if not isinstance(user, dict) or str(user.get("login", "")).lower() != username.lower():
        raise RuntimeError(f"GitHub reviewer 無法解析：{username}")
    pull = gh_api_json("GET", f"repos/{repository}/pulls/{pr_number}")
    if (
        not isinstance(pull, dict)
        or pull.get("number") != pr_number
        or pull.get("state") != "open"
    ):
        raise RuntimeError(f"GitHub PR 不存在、未開啟或回應格式無效：#{pr_number}")
    author = pull.get("user")
    if isinstance(author, dict) and str(author.get("login", "")).lower() == username.lower():
        raise RuntimeError(f"GitHub PR 作者不可成為自己的 reviewer：#{pr_number}")


def github_add_collaborator(repository: str, username: str, permission: str) -> None:
    gh_api_json(
        "PUT",
        f"repos/{repository}/collaborators/{username}",
        {"permission": permission},
    )


def github_collaborator_permission(repository: str, username: str) -> str | None:
    """讀取已生效權限；尚未接受的邀請與非 collaborator 回傳 None。"""
    result = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "GET",
            f"repos/{repository}/collaborators/{username}/permission",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        if "HTTP 404" in output or "Not Found" in output:
            return None
        raise RuntimeError(output or "無法確認 GitHub collaborator 權限")
    try:
        data = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError("GitHub collaborator 權限回應格式無效") from error
    permission = data.get("permission") if isinstance(data, dict) else None
    if permission not in {"read", "triage", "write", "maintain", "admin"}:
        raise RuntimeError("GitHub collaborator 權限回應格式無效")
    return str(permission)


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
    query = urllib.parse.urlencode({"username": username, "active": "true"})
    users = gitlab_request(base_url, f"/users?{query}", token=token)
    exact = [
        item for item in users
        if isinstance(item, dict) and str(item.get("username", "")).lower() == username.lower()
    ] if isinstance(users, list) else []
    if len(exact) != 1 or not isinstance(exact[0].get("id"), int):
        raise RuntimeError(f"GitLab username 無法唯一解析：{username}")
    if exact[0].get("state") != "active":
        raise RuntimeError(f"GitLab username 不是 active 狀態：{username}")
    return int(exact[0]["id"])


def gitlab_effective_access_level(project: dict[str, object]) -> int:
    permissions = project.get("permissions")
    if not isinstance(permissions, dict):
        return 0
    levels = []
    for key in ("project_access", "group_access"):
        access = permissions.get(key)
        if isinstance(access, dict) and isinstance(access.get("access_level"), int):
            levels.append(int(access["access_level"]))
    return max(levels, default=0)


def gitlab_token_preflight(base_url: str, token: str) -> None:
    info = gitlab_request(base_url, "/personal_access_tokens/self", token=token)
    if not isinstance(info, dict):
        raise RuntimeError("GitLab Token 自我查詢回應格式無效")
    if info.get("active") is not True or info.get("revoked") is not False:
        raise RuntimeError("GitLab Token 已停用、撤銷或過期")
    scopes = info.get("scopes")
    if not isinstance(scopes, list) or "api" not in scopes:
        raise RuntimeError(
            "GitLab Token 缺少 api scope；read_api 與 write_repository 不足以管理 member 與 project policy"
        )


def gitlab_direct_member_exists(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    user_id: int,
) -> bool:
    try:
        member = gitlab_request(
            base_url,
            f"{project_endpoint}/members/{user_id}",
            token=token,
        )
    except GitLabApiError as error:
        if error.status == 404:
            return False
        raise
    if not isinstance(member, dict) or member.get("state") != "active":
        raise RuntimeError(f"GitLab direct member 回應格式或狀態無效：{user_id}")
    return True


def gitlab_membership_lock_preflight(
    base_url: str,
    project: dict[str, object],
    *,
    token: str,
) -> None:
    namespace = project.get("namespace")
    if not isinstance(namespace, dict):
        raise RuntimeError("GitLab project 缺少 namespace，無法確認 membership lock")
    kind = namespace.get("kind")
    if kind == "user":
        return
    if kind != "group":
        raise RuntimeError(f"GitLab project namespace kind 無法辨識：{kind}")
    group_id = namespace.get("id")
    if not isinstance(group_id, int):
        raise RuntimeError("GitLab project 缺少 immediate group id，無法確認 membership lock")
    group = gitlab_request(base_url, f"/groups/{group_id}", token=token)
    if not isinstance(group, dict):
        raise RuntimeError(f"GitLab group 回應格式無效：{group_id}")
    membership_lock = group.get("membership_lock")
    if not isinstance(membership_lock, bool):
        raise RuntimeError(
            f"無法確認 GitLab group membership lock：{group_id}；欄位缺少或型別無效"
        )
    if membership_lock:
        raise RuntimeError(
            f"GitLab group membership lock 已啟用，無法新增 project member：{group_id}"
        )


def gitlab_protected_branch_preflight(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    branch: str,
) -> dict[str, object] | None:
    endpoint = f"{project_endpoint}/protected_branches/{urllib.parse.quote(branch, safe='')}"
    try:
        current = gitlab_request(base_url, endpoint, token=token)
    except GitLabApiError as error:
        if error.status == 404:
            return None
        raise
    if not isinstance(current, dict) or current.get("name") != branch:
        raise RuntimeError(f"GitLab protected branch 回應格式或名稱不一致：{branch}")
    for field in ("push_access_levels", "merge_access_levels", "unprotect_access_levels"):
        records = current.get(field)
        if not isinstance(records, list):
            raise RuntimeError(f"GitLab protected branch 缺少 {field}：{branch}")
        for record in records:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("id"), int)
                or not isinstance(record.get("access_level"), int)
            ):
                raise RuntimeError(f"GitLab protected branch 的 {field} 格式無效：{branch}")
    for field in ("allow_force_push", "code_owner_approval_required"):
        if not isinstance(current.get(field), bool):
            raise RuntimeError(f"GitLab protected branch 缺少有效 {field}：{branch}")
    return current


def gitlab_review_preflight(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    user_id: int,
    merge_request_iid: int,
) -> dict[str, object]:
    merge_request = gitlab_request(
        base_url,
        f"{project_endpoint}/merge_requests/{merge_request_iid}",
        token=token,
    )
    if (
        not isinstance(merge_request, dict)
        or merge_request.get("iid") != merge_request_iid
        or merge_request.get("state") != "opened"
        or not isinstance(merge_request.get("reviewers"), list)
    ):
        raise RuntimeError(
            f"GitLab MR 不存在、未開啟或回應格式無效：!{merge_request_iid}"
        )
    author = merge_request.get("author")
    if isinstance(author, dict) and author.get("id") == user_id:
        raise RuntimeError(f"GitLab MR 作者不可成為自己的 reviewer：!{merge_request_iid}")
    for reviewer in merge_request["reviewers"]:
        if not isinstance(reviewer, dict) or not isinstance(reviewer.get("id"), int):
            raise RuntimeError(f"GitLab MR reviewer 回應格式無效：!{merge_request_iid}")
    return merge_request


def gitlab_preflight(
    base_url: str,
    project_name: str,
    *,
    token: str,
    username: str,
    branch_override: str | None,
    configure_policy: bool,
    merge_request_iid: int | None = None,
) -> GitLabPreflightResult:
    """唯讀確認 GitLab 權限、分支與付費政策 API，再允許任何寫入。"""
    gitlab_token_preflight(base_url, token)
    project_endpoint = f"/projects/{urllib.parse.quote(project_name, safe='')}"
    project = gitlab_request(base_url, project_endpoint, token=token)
    if not isinstance(project, dict):
        raise RuntimeError(f"GitLab project 回應格式無效：{project_name}")
    if gitlab_effective_access_level(project) < 40:
        raise RuntimeError(
            f"目前 GitLab Token 沒有 Maintainer 或 Owner 權限：{project_name}"
        )

    user_id = gitlab_user_id(base_url, token, username)
    direct_member = gitlab_direct_member_exists(
        base_url,
        project_endpoint,
        token=token,
        user_id=user_id,
    )
    if not direct_member:
        gitlab_membership_lock_preflight(base_url, project, token=token)

    branch = selected_branch(
        branch_override,
        project,
        provider="GitLab",
    ) if configure_policy else None
    protected_branch: dict[str, object] | None = None
    rules: list[object] = []
    if configure_policy:
        if branch is None:
            raise RuntimeError("GitLab 分支預檢狀態遺失")
        encoded_branch = urllib.parse.quote(branch, safe="")
        try:
            branch_data = gitlab_request(
                base_url,
                f"{project_endpoint}/repository/branches/{encoded_branch}",
                token=token,
            )
        except GitLabApiError as error:
            raise RuntimeError(
                f"GitLab 分支不存在或無法讀取：{project_name}/{branch}；{error}"
            ) from error
        if not isinstance(branch_data, dict) or branch_data.get("name") != branch:
            raise RuntimeError(
                f"GitLab 分支回應格式或名稱不一致：{project_name}/{branch}"
            )
        protected_branch = gitlab_protected_branch_preflight(
            base_url,
            project_endpoint,
            token=token,
            branch=branch,
        )
        try:
            approvals = gitlab_request(
                base_url,
                f"{project_endpoint}/approvals",
                token=token,
            )
            approval_rules = gitlab_request(
                base_url,
                f"{project_endpoint}/approval_rules",
                token=token,
            )
        except GitLabApiError as error:
            if error.status in (403, 404):
                raise RuntimeError(
                    "GitLab 必要核准政策不可用：Code Owner 與 required approval rule "
                    "需要 GitLab Premium／Ultimate，以及 Maintainer 或 Owner 權限"
                ) from error
            raise
        if not isinstance(approvals, dict) or not isinstance(approval_rules, list):
            raise RuntimeError(f"GitLab 核准政策回應格式無效：{project_name}")
        rules = approval_rules

    merge_request = None
    if merge_request_iid is not None:
        merge_request = gitlab_review_preflight(
            base_url,
            project_endpoint,
            token=token,
            user_id=user_id,
            merge_request_iid=merge_request_iid,
        )
    return GitLabPreflightResult(
        project=project,
        user_id=user_id,
        branch=branch,
        protected_branch=protected_branch,
        approval_rules=rules,
        merge_request=merge_request,
    )


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
    current_protection: dict[str, object] | None,
    approval_rules: list[object],
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
    if current_protection is None:
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
        payload: dict[str, object] = {
            "allow_force_push": False,
            "code_owner_approval_required": True,
            "allowed_to_push": gitlab_access_updates(
                current_protection["push_access_levels"], 0
            ),
            "allowed_to_merge": gitlab_access_updates(
                current_protection["merge_access_levels"], 30
            ),
            "allowed_to_unprotect": gitlab_access_updates(
                current_protection["unprotect_access_levels"], 40
            ),
        }
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
    named = [
        item
        for item in approval_rules
        if isinstance(item, dict) and item.get("name") == "Repository policy"
    ]
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


def gitlab_access_updates(records: object, access_level: int) -> list[dict[str, object]]:
    """保留一條一般層級規則，移除使用者、群組與 deploy key 例外。"""
    if not isinstance(records, list):
        raise RuntimeError("GitLab protected branch access level 預檢狀態遺失")
    updates: list[dict[str, object]] = []
    generic_seen = False
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), int):
            raise RuntimeError("GitLab protected branch access level 預檢狀態無效")
        special = any(
            record.get(field) is not None
            for field in ("user_id", "group_id", "deploy_key_id")
        )
        if special or generic_seen:
            updates.append({"id": record["id"], "_destroy": True})
        else:
            updates.append({"id": record["id"], "access_level": access_level})
            generic_seen = True
    if not generic_seen:
        updates.append({"access_level": access_level})
    return updates


def request_gitlab_review(
    base_url: str,
    project_endpoint: str,
    *,
    token: str,
    user_id: int,
    merge_request_iid: int,
    current: dict[str, object],
) -> None:
    endpoint = f"{project_endpoint}/merge_requests/{merge_request_iid}"
    reviewers = current["reviewers"]
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
    preflight_only = bool(getattr(args, "preflight_only", False))
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
    if preflight_only and (args.apply or args.local_only):
        raise ValueError("--preflight-only 不可搭配 --apply 或 --local-only")
    if args.request_review is not None and not github_repository:
        raise ValueError("--request-review 必須搭配可用的 GitHub repository")
    if args.request_merge_request_review is not None and not gitlab_project:
        raise ValueError("--request-merge-request-review 必須搭配可用的 GitLab project")
    if (args.apply or preflight_only) and not args.local_only and not github_repository and not gitlab_project:
        raise RuntimeError("沒有可處理的 GitHub／GitLab 目標；只改本機請加上 --local-only")
    if (args.apply or preflight_only) and not args.local_only and not args.configure_policy:
        raise ValueError("平台將分支保護列為阻擋條件，不接受 --no-configure-policy")

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
    if not args.apply and not preflight_only:
        print("[DRY-RUN] 未修改檔案或遠端設定；確認後加上 --apply")
        return 0

    github_metadata: dict[str, object] | None = None
    github_target_branch: str | None = None
    github_current_permission: str | None = None
    if github_repository and not args.local_only:
        github_metadata = github_preflight(github_repository)
        github_current_permission = github_collaborator_permission(
            github_repository,
            username,
        )
        if args.configure_policy:
            github_target_branch = selected_branch(
                args.branch,
                github_metadata,
                provider="GitHub",
            )
            github_branch_protection_preflight(github_repository, github_target_branch)
        if args.request_review is not None:
            github_review_preflight(github_repository, username, args.request_review)

    gitlab_base_url: str | None = None
    gitlab_token: str | None = None
    gitlab_preflight_result: GitLabPreflightResult | None = None
    if gitlab_project and not args.local_only:
        if not ENV_NAME_PATTERN.fullmatch(args.gitlab_token_env):
            raise ValueError("GitLab token 環境變數名稱格式無效")
        gitlab_token = os.environ.get(args.gitlab_token_env, "")
        if not gitlab_token:
            raise RuntimeError(f"缺少 GitLab token 環境變數：{args.gitlab_token_env}")
        gitlab_base_url = validate_gitlab_api_url(
            args.gitlab_api_url,
            allow_insecure_http=args.allow_insecure_gitlab_http,
        )
        gitlab_preflight_result = gitlab_preflight(
            gitlab_base_url,
            gitlab_project,
            token=gitlab_token,
            username=username,
            branch_override=args.branch,
            configure_policy=args.configure_policy,
            merge_request_iid=args.request_merge_request_review,
        )

    if preflight_only:
        print("[OK] GitHub／GitLab 遠端唯讀預檢通過；未修改檔案或遠端設定")
        return 0

    if args.local_only:
        atomic_write(context.root / ".github/CODEOWNERS", content)
        atomic_write(context.root / ".gitlab/CODEOWNERS", content)
        print("[OK] GitHub／GitLab CODEOWNERS 已同步")
        return 0

    # 先完成所有遠端保護政策，再授予可寫權限。後段失敗時，新成員不會
    # 留在未受保護的分支上。
    if github_repository:
        if github_target_branch is None:
            raise RuntimeError("GitHub 分支預檢狀態遺失；未設定 branch protection")
        configure_github_policy(
            github_repository,
            branch=github_target_branch,
            required_checks=checks,
            approvals=args.approvals,
        )
        print(f"[OK] GitHub PR／branch protection 已設定：{github_target_branch}")

    if gitlab_project:
        if (
            gitlab_token is None
            or gitlab_base_url is None
            or gitlab_preflight_result is None
        ):
            raise RuntimeError("GitLab 預檢狀態遺失；未執行任何 GitLab 寫入")
        token = gitlab_token
        base_url = gitlab_base_url
        project_endpoint = f"/projects/{urllib.parse.quote(gitlab_project, safe='')}"
        branch = gitlab_preflight_result.branch
        if branch is None:
            raise RuntimeError("GitLab 分支預檢狀態遺失；未設定 protected branch")
        configure_gitlab_policy(
            base_url,
            project_endpoint,
            token=token,
            branch=branch,
            approvals=args.approvals,
            current_protection=gitlab_preflight_result.protected_branch,
            approval_rules=gitlab_preflight_result.approval_rules,
        )
        print(f"[OK] GitLab MR／protected branch 已設定：{branch}")

    if github_repository and github_current_permission is None:
        github_add_collaborator(github_repository, username, "pull")
        print(
            f"[WAIT] GitHub 已送出唯讀邀請：{username}；接受後以相同參數重跑",
            file=sys.stderr,
        )
        print("[NEXT] 對方接受邀請後，以相同參數重跑一次 --apply", file=sys.stderr)
        return 2

    if github_repository:
        github_add_collaborator(github_repository, username, args.github_permission)
        print(f"[OK] GitHub collaborator 權限已設定：{username} ({args.github_permission})")

    if gitlab_project:
        if gitlab_preflight_result is None or gitlab_base_url is None or gitlab_token is None:
            raise RuntimeError("GitLab 預檢狀態遺失；未授予 member 權限")
        project_endpoint = f"/projects/{urllib.parse.quote(gitlab_project, safe='')}"
        gitlab_add_member(
            gitlab_base_url,
            project_endpoint,
            token=gitlab_token,
            user_id=gitlab_preflight_result.user_id,
            access_level=args.gitlab_access_level,
        )
        print(f"[OK] GitLab member 已設定：{username}")

    atomic_write(context.root / ".github/CODEOWNERS", content)
    atomic_write(context.root / ".gitlab/CODEOWNERS", content)
    print("[OK] GitHub／GitLab CODEOWNERS 已同步")

    if github_repository and args.request_review is not None:
        request_github_review(github_repository, username, args.request_review)
        print(f"[OK] GitHub PR #{args.request_review} 已加入 reviewer")

    if gitlab_project and args.request_merge_request_review is not None:
        if gitlab_preflight_result is None or gitlab_preflight_result.merge_request is None:
            raise RuntimeError("GitLab MR 預檢狀態遺失；未送出 reviewer 變更")
        request_gitlab_review(
            gitlab_base_url,
            f"/projects/{urllib.parse.quote(gitlab_project, safe='')}",
            token=gitlab_token,
            user_id=gitlab_preflight_result.user_id,
            merge_request_iid=args.request_merge_request_review,
            current=gitlab_preflight_result.merge_request,
        )
        print(f"[OK] GitLab MR !{args.request_merge_request_review} 已加入 reviewer")
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
    add.add_argument(
        "--preflight-only",
        action="store_true",
        help="執行 GitHub／GitLab 遠端唯讀預檢，不寫入設定",
    )
    add.add_argument("--local-only", action="store_true", help="只更新 CODEOWNERS，不呼叫 API")
    add.add_argument("--owner", help="既有 CODEOWNER；可用 user 或 organization/team")
    add.add_argument("--github-repository", help="owner/repository；GitHub origin 可自動判斷")
    add.add_argument("--skip-github", action="store_true", help="不呼叫 GitHub API")
    add.add_argument(
        "--github-permission",
        choices=("push", "maintain", "admin"),
        default="push",
        help="GitHub 權限；CODEOWNERS 至少需要 write（push）",
    )
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
