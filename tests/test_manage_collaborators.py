#!/usr/bin/env python3

import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from manage_collaborators import (  # noqa: E402
    GitLabApiError,
    MAINTENANCE_PATTERNS,
    RELEASE_PATTERNS,
    add_command,
    atomic_write,
    canonical_codeowners,
    codeowner_errors,
    configure_gitlab_policy,
    github_branch_protection_preflight,
    github_review_preflight,
    gitlab_access_updates,
    gitlab_preflight,
    gitlab_protected_branch_preflight,
    gitlab_review_preflight,
    local_policy_errors,
    parse_github_repository,
    parse_gitlab_project,
    repository_context,
    selected_branch,
    validate_gitlab_api_url,
    validate_username,
)


class CollaboratorManagementTest(unittest.TestCase):
    def test_parses_supported_remotes(self):
        self.assertEqual(
            parse_github_repository("git@github.com:Owner/repository.git"),
            "Owner/repository",
        )
        self.assertEqual(
            parse_gitlab_project("https://gitlab.com/group/subgroup/repository.git"),
            "group/subgroup/repository",
        )

    def test_rejects_unsafe_values(self):
        for username in ("-prefix", "name with spaces", "user;rm", ""):
            with self.subTest(username=username), self.assertRaises(ValueError):
                validate_username(username)
        with self.assertRaises(ValueError):
            validate_gitlab_api_url("http://gitlab.example.test/api/v4", allow_insecure_http=False)
        with self.assertRaises(ValueError):
            validate_gitlab_api_url("https://user:secret@example.test/api/v4", allow_insecure_http=False)

    def test_requires_explicit_branch_when_remote_omits_default(self):
        with self.assertRaisesRegex(RuntimeError, "default_branch"):
            selected_branch(None, {}, provider="GitHub")
        self.assertEqual(selected_branch("release", {}, provider="GitHub"), "release")

    def test_adds_owner_and_missing_rules_idempotently(self):
        original = "# owners\n* @owner\n/governance/ @owner\n"
        first = canonical_codeowners(
            original,
            username="reviewer",
            primary_owner="owner",
            default_patterns=MAINTENANCE_PATTERNS,
        )
        second = canonical_codeowners(
            first,
            username="reviewer",
            primary_owner="owner",
            default_patterns=MAINTENANCE_PATTERNS,
        )
        self.assertEqual(first, second)
        self.assertEqual(codeowner_errors(first, required_patterns=MAINTENANCE_PATTERNS), [])
        for pattern in MAINTENANCE_PATTERNS:
            self.assertIn(f"{pattern} @owner @reviewer", first)

    def test_detects_release_repository_and_policy_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            (root / "release-evidence").mkdir()
            (root / "release-notes").mkdir()
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".gitlab").mkdir()
            (root / ".github/workflows/repository-policy.yml").write_text("name: test\n", encoding="utf-8")
            (root / ".gitlab-ci.yml").write_text("stages: [check]\n", encoding="utf-8")
            content = canonical_codeowners(
                "",
                username="reviewer",
                primary_owner="owner",
                default_patterns=RELEASE_PATTERNS,
            )
            (root / ".github/CODEOWNERS").write_text(content, encoding="utf-8")
            (root / ".gitlab/CODEOWNERS").write_text(content, encoding="utf-8")
            context = repository_context(root)
            self.assertEqual(context.kind, "release")
            self.assertEqual(local_policy_errors(context), [])

    def test_atomic_write_preserves_existing_file_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "CODEOWNERS"
            path.write_text("* @owner\n", encoding="utf-8")
            path.chmod(0o644)

            atomic_write(path, "* @owner @reviewer\n")

            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_explains_private_plan_limit(self, run):
        run.side_effect = (
            mock.Mock(returncode=0, stdout='{"name":"main"}'),
            mock.Mock(
                returncode=1,
                stdout=(
                    '{"message":"Upgrade to GitHub Pro or make this repository public '
                    'to enable this feature.","status":"403"}\n'
                    "gh: Upgrade to GitHub Pro or make this repository public (HTTP 403)"
                ),
            ),
        )

        with self.assertRaisesRegex(RuntimeError, "GitHub Pro"):
            github_branch_protection_preflight("owner/repository", "main")

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_accepts_existing_unprotected_branch(self, run):
        run.side_effect = (
            mock.Mock(returncode=0, stdout='{"name":"main"}'),
            mock.Mock(returncode=1, stdout='{"message":"Branch not protected","status":"404"}'),
        )

        github_branch_protection_preflight("owner/repository", "main")

        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            run.call_args_list[0].args[0][-1],
            "repos/owner/repository/branches/main",
        )
        self.assertEqual(
            run.call_args_list[1].args[0][-1],
            "repos/owner/repository/branches/main/protection",
        )

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_rejects_missing_branch(self, run):
        run.return_value = mock.Mock(
            returncode=1,
            stdout='{"message":"Branch not found","status":"404"}',
        )

        with self.assertRaisesRegex(RuntimeError, "分支不存在或無法讀取"):
            github_branch_protection_preflight("owner/repository", "missing")

        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            run.call_args_list[0].args[0][-1],
            "repos/owner/repository/branches/missing",
        )

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_rejects_malformed_branch_response(self, run):
        run.return_value = mock.Mock(returncode=0, stdout="[]")

        with self.assertRaisesRegex(RuntimeError, "格式或名稱不一致"):
            github_branch_protection_preflight("owner/repository", "main")

        self.assertEqual(run.call_count, 1)

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_rejects_wrong_branch_name(self, run):
        run.return_value = mock.Mock(returncode=0, stdout='{"name":"develop"}')

        with self.assertRaisesRegex(RuntimeError, "格式或名稱不一致"):
            github_branch_protection_preflight("owner/repository", "main")

        self.assertEqual(run.call_count, 1)

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_rejects_non_json_branch_response(self, run):
        run.return_value = mock.Mock(returncode=0, stdout="not-json")

        with self.assertRaisesRegex(RuntimeError, "回應格式無效"):
            github_branch_protection_preflight("owner/repository", "main")

        self.assertEqual(run.call_count, 1)

    @mock.patch("manage_collaborators.subprocess.run")
    def test_branch_protection_preflight_rejects_unknown_forbidden_response(self, run):
        run.side_effect = (
            mock.Mock(returncode=0, stdout='{"name":"main"}'),
            mock.Mock(returncode=1, stdout='{"message":"Forbidden","status":"403"}'),
        )

        with self.assertRaisesRegex(RuntimeError, "Forbidden"):
            github_branch_protection_preflight("owner/repository", "main")

    @mock.patch("manage_collaborators.gh_api_json")
    def test_github_review_preflight_rejects_pr_author(self, api):
        api.side_effect = (
            {"login": "reviewer"},
            {
                "number": 12,
                "state": "open",
                "user": {"login": "reviewer"},
            },
        )

        with self.assertRaisesRegex(RuntimeError, "作者不可成為自己的 reviewer"):
            github_review_preflight("owner/repository", "reviewer", 12)

    def test_add_stops_before_local_or_remote_writes_when_policy_preflight_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository=None,
                gitlab_project=None,
                skip_github=False,
                skip_gitlab=True,
                local_only=False,
                request_review=None,
                request_merge_request_review=None,
                apply=True,
                owner=None,
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            with (
                mock.patch(
                    "manage_collaborators.git",
                    return_value="git@github.com:owner/repository.git",
                ),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value="write",
                ),
                mock.patch(
                    "manage_collaborators.github_branch_protection_preflight",
                    side_effect=RuntimeError("方案不支援"),
                ),
                mock.patch("manage_collaborators.atomic_write") as atomic_write_mock,
                mock.patch("manage_collaborators.github_add_collaborator") as add_mock,
                mock.patch("manage_collaborators.configure_github_policy") as policy_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "方案不支援"):
                    add_command(args, context)

            atomic_write_mock.assert_not_called()
            add_mock.assert_not_called()
            policy_mock.assert_not_called()

    def test_add_stops_before_writes_when_github_reviewer_preflight_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository="owner/repository",
                gitlab_project=None,
                skip_github=False,
                skip_gitlab=True,
                local_only=False,
                request_review=12,
                request_merge_request_review=None,
                apply=True,
                owner="owner",
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            with (
                mock.patch("manage_collaborators.git", return_value=""),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value="write",
                ),
                mock.patch("manage_collaborators.github_branch_protection_preflight"),
                mock.patch(
                    "manage_collaborators.github_review_preflight",
                    side_effect=RuntimeError("PR 已關閉"),
                ),
                mock.patch("manage_collaborators.atomic_write") as atomic_write_mock,
                mock.patch("manage_collaborators.github_add_collaborator") as add_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "PR 已關閉"):
                    add_command(args, context)

            atomic_write_mock.assert_not_called()
            add_mock.assert_not_called()

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_explains_paid_policy_limit(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "user"},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            {"name": "main"},
            GitLabApiError(404, "Protected Branch Not Found"),
            GitLabApiError(403, "Forbidden"),
        )

        with self.assertRaisesRegex(RuntimeError, "Premium.*Ultimate"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_rejects_missing_branch(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "user"},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            GitLabApiError(404, "Branch Not Found"),
        )

        with self.assertRaisesRegex(RuntimeError, "GitLab 分支不存在或無法讀取"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override="missing",
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_rejects_invalid_branch_response(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "user"},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            {},
        )

        with self.assertRaisesRegex(RuntimeError, "分支回應格式或名稱不一致"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_requires_maintainer_access(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 30}},
                "default_branch": "main",
            },
        )

        with self.assertRaisesRegex(RuntimeError, "Maintainer"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

        self.assertEqual(request.call_count, 2)

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_requires_api_scope(self, request):
        request.return_value = {
            "active": True,
            "revoked": False,
            "scopes": ["read_api"],
        }

        with self.assertRaisesRegex(RuntimeError, "api scope"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[1], "/personal_access_tokens/self")

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_rejects_blocked_user(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
            },
            [{"id": 17, "username": "reviewer", "state": "blocked"}],
        )

        with self.assertRaisesRegex(RuntimeError, "不是 active"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_rejects_membership_lock_for_new_member(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "group", "id": 9},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            {"id": 9, "membership_lock": True},
        )

        with self.assertRaisesRegex(RuntimeError, "membership lock"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_rejects_unknown_membership_lock_state(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "group", "id": 9},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            {"id": 9},
        )

        with self.assertRaisesRegex(RuntimeError, "無法確認.*membership lock"):
            gitlab_preflight(
                "https://gitlab.example.test/api/v4",
                "group/project",
                token="secret",
                username="reviewer",
                branch_override=None,
                configure_policy=True,
            )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_preflight_checks_expected_read_endpoints_in_order(self, request):
        request.side_effect = (
            {"active": True, "revoked": False, "scopes": ["api"]},
            {
                "permissions": {"project_access": {"access_level": 40}},
                "default_branch": "main",
                "namespace": {"kind": "user"},
            },
            [{"id": 17, "username": "reviewer", "state": "active"}],
            GitLabApiError(404, "Member Not Found"),
            {"name": "main"},
            GitLabApiError(404, "Protected Branch Not Found"),
            {},
            [],
        )

        gitlab_preflight(
            "https://gitlab.example.test/api/v4",
            "group/project",
            token="secret",
            username="reviewer",
            branch_override=None,
            configure_policy=True,
        )

        self.assertEqual(
            [call.args[1] for call in request.call_args_list],
            [
                "/personal_access_tokens/self",
                "/projects/group%2Fproject",
                "/users?username=reviewer&active=true",
                "/projects/group%2Fproject/members/17",
                "/projects/group%2Fproject/repository/branches/main",
                "/projects/group%2Fproject/protected_branches/main",
                "/projects/group%2Fproject/approvals",
                "/projects/group%2Fproject/approval_rules",
            ],
        )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_protected_branch_preflight_rejects_missing_access_lists(self, request):
        request.return_value = {
            "name": "main",
            "allow_force_push": False,
            "code_owner_approval_required": True,
        }

        with self.assertRaisesRegex(RuntimeError, "push_access_levels"):
            gitlab_protected_branch_preflight(
                "https://gitlab.example.test/api/v4",
                "/projects/group%2Fproject",
                token="secret",
                branch="main",
            )

    def test_gitlab_access_updates_remove_exceptions_and_set_required_level(self):
        records = [
            {"id": 1, "access_level": 30, "user_id": 17},
            {"id": 2, "access_level": 30},
            {"id": 3, "access_level": 40},
        ]

        self.assertEqual(
            gitlab_access_updates(records, 40),
            [
                {"id": 1, "_destroy": True},
                {"id": 2, "access_level": 40},
                {"id": 3, "_destroy": True},
            ],
        )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_configure_gitlab_policy_normalizes_all_branch_access(self, request):
        current = {
            "push_access_levels": [{"id": 1, "access_level": 30}],
            "merge_access_levels": [{"id": 2, "access_level": 40}],
            "unprotect_access_levels": [{"id": 3, "access_level": 30}],
        }

        configure_gitlab_policy(
            "https://gitlab.example.test/api/v4",
            "/projects/group%2Fproject",
            token="secret",
            branch="main",
            approvals=1,
            current_protection=current,
            approval_rules=[{"id": 7, "name": "Repository policy"}],
        )

        branch_call = request.call_args_list[1]
        self.assertEqual(branch_call.kwargs["method"], "PATCH")
        self.assertEqual(
            branch_call.kwargs["payload"]["allowed_to_push"],
            [{"id": 1, "access_level": 0}],
        )
        self.assertEqual(
            branch_call.kwargs["payload"]["allowed_to_merge"],
            [{"id": 2, "access_level": 30}],
        )
        self.assertEqual(
            branch_call.kwargs["payload"]["allowed_to_unprotect"],
            [{"id": 3, "access_level": 40}],
        )

    @mock.patch("manage_collaborators.gitlab_request")
    def test_gitlab_review_preflight_rejects_mr_author(self, request):
        request.return_value = {
            "iid": 12,
            "state": "opened",
            "author": {"id": 17},
            "reviewers": [],
        }

        with self.assertRaisesRegex(RuntimeError, "作者不可成為自己的 reviewer"):
            gitlab_review_preflight(
                "https://gitlab.example.test/api/v4",
                "/projects/group%2Fproject",
                token="secret",
                user_id=17,
                merge_request_iid=12,
            )

    def test_add_stops_before_writes_when_gitlab_preflight_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository="owner/repository",
                gitlab_project="group/project",
                skip_github=False,
                skip_gitlab=False,
                local_only=False,
                request_review=None,
                request_merge_request_review=None,
                apply=True,
                owner="owner",
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                gitlab_api_url="https://gitlab.example.test/api/v4",
                allow_insecure_gitlab_http=False,
                gitlab_access_level=30,
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            with (
                mock.patch.dict("os.environ", {"GITLAB_TOKEN": "secret"}),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value="write",
                ),
                mock.patch("manage_collaborators.github_branch_protection_preflight"),
                mock.patch(
                    "manage_collaborators.gitlab_preflight",
                    side_effect=RuntimeError("GitLab 方案不支援"),
                ),
                mock.patch("manage_collaborators.atomic_write") as atomic_write_mock,
                mock.patch("manage_collaborators.github_add_collaborator") as github_add_mock,
                mock.patch("manage_collaborators.configure_github_policy") as github_policy_mock,
                mock.patch("manage_collaborators.gitlab_add_member") as add_mock,
                mock.patch("manage_collaborators.configure_gitlab_policy") as policy_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "GitLab 方案不支援"):
                    add_command(args, context)

            atomic_write_mock.assert_not_called()
            github_add_mock.assert_not_called()
            github_policy_mock.assert_not_called()
            add_mock.assert_not_called()
            policy_mock.assert_not_called()

    def test_remote_policies_precede_permissions_and_local_codeowners(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository="owner/repository",
                gitlab_project="group/project",
                skip_github=False,
                skip_gitlab=False,
                local_only=False,
                request_review=None,
                request_merge_request_review=None,
                apply=True,
                owner="owner",
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                gitlab_api_url="https://gitlab.example.test/api/v4",
                allow_insecure_gitlab_http=False,
                gitlab_access_level=30,
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            events: list[str] = []
            gitlab_result = SimpleNamespace(
                user_id=17,
                branch="main",
                protected_branch=None,
                approval_rules=[],
                merge_request=None,
            )
            with (
                mock.patch.dict("os.environ", {"GITLAB_TOKEN": "secret"}),
                mock.patch("manage_collaborators.git", return_value=""),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value="write",
                ),
                mock.patch("manage_collaborators.github_branch_protection_preflight"),
                mock.patch("manage_collaborators.gitlab_preflight", return_value=gitlab_result),
                mock.patch(
                    "manage_collaborators.configure_github_policy",
                    side_effect=lambda *args, **kwargs: events.append("github-policy"),
                ),
                mock.patch(
                    "manage_collaborators.configure_gitlab_policy",
                    side_effect=lambda *args, **kwargs: events.append("gitlab-policy"),
                ),
                mock.patch(
                    "manage_collaborators.github_add_collaborator",
                    side_effect=lambda *args, **kwargs: events.append("github-permission"),
                ),
                mock.patch(
                    "manage_collaborators.gitlab_add_member",
                    side_effect=lambda *args, **kwargs: events.append("gitlab-permission"),
                ),
                mock.patch(
                    "manage_collaborators.atomic_write",
                    side_effect=lambda *args, **kwargs: events.append("codeowners"),
                ),
            ):
                self.assertEqual(add_command(args, context), 0)

            self.assertEqual(
                events,
                [
                    "github-policy",
                    "gitlab-policy",
                    "github-permission",
                    "gitlab-permission",
                    "codeowners",
                    "codeowners",
                ],
            )

    def test_new_github_collaborator_receives_read_only_invitation_first(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository="owner/repository",
                gitlab_project=None,
                skip_github=False,
                skip_gitlab=True,
                local_only=False,
                request_review=None,
                request_merge_request_review=None,
                apply=True,
                owner="owner",
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            with (
                mock.patch("manage_collaborators.git", return_value=""),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value=None,
                ),
                mock.patch("manage_collaborators.github_branch_protection_preflight"),
                mock.patch("manage_collaborators.configure_github_policy"),
                mock.patch("manage_collaborators.github_add_collaborator") as add_mock,
                mock.patch("manage_collaborators.atomic_write") as atomic_write_mock,
            ):
                self.assertEqual(add_command(args, context), 2)

            add_mock.assert_called_once_with("owner/repository", "reviewer", "pull")
            atomic_write_mock.assert_not_called()

    def test_preflight_only_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            context = repository_context(root)
            args = SimpleNamespace(
                username="reviewer",
                github_repository="owner/repository",
                gitlab_project=None,
                skip_github=False,
                skip_gitlab=True,
                local_only=False,
                preflight_only=True,
                request_review=None,
                request_merge_request_review=None,
                apply=False,
                owner="owner",
                required_check=None,
                gitlab_token_env="GITLAB_TOKEN",
                github_permission="push",
                configure_policy=True,
                branch=None,
                approvals=1,
            )
            with (
                mock.patch("manage_collaborators.git", return_value=""),
                mock.patch(
                    "manage_collaborators.github_preflight",
                    return_value={"default_branch": "main"},
                ),
                mock.patch(
                    "manage_collaborators.github_collaborator_permission",
                    return_value="write",
                ),
                mock.patch("manage_collaborators.github_branch_protection_preflight"),
                mock.patch("manage_collaborators.configure_github_policy") as policy_mock,
                mock.patch("manage_collaborators.github_add_collaborator") as add_mock,
                mock.patch("manage_collaborators.atomic_write") as atomic_write_mock,
            ):
                self.assertEqual(add_command(args, context), 0)

            policy_mock.assert_not_called()
            add_mock.assert_not_called()
            atomic_write_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
