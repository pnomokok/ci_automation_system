import pytest
from unittest.mock import MagicMock, patch
from git import GitCommandError

from app.git_client import (
    _inject_token,
    repo_name_from_url,
    run_git_command,
    GitOperationError,
    create_temp_workspace,
    checkout_branch,
    pull_latest,
    checkout_commit,
    get_latest_commit_info,
    ensure_repository_state,
)


# ── _inject_token ─────────────────────────────────────────────────────────────

def test_inject_token_adds_token_to_github_url(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken")
    result = _inject_token("https://github.com/org/repo")
    assert "ghp_testtoken@github.com" in result


def test_inject_token_no_token_unchanged(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    url = "https://github.com/org/repo"
    assert _inject_token(url) == url


def test_inject_token_non_github_unchanged():
    assert _inject_token("https://gitlab.com/org/repo") == "https://gitlab.com/org/repo"


def test_inject_token_non_https_unchanged(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    assert _inject_token("git@github.com:org/repo.git") == "git@github.com:org/repo.git"


# ── repo_name_from_url ────────────────────────────────────────────────────────

def test_repo_name_strips_git_suffix():
    assert repo_name_from_url("https://github.com/org/my-repo.git") == "my-repo"


def test_repo_name_without_suffix():
    assert repo_name_from_url("https://github.com/org/my-repo") == "my-repo"


def test_repo_name_trailing_slash():
    assert repo_name_from_url("https://github.com/org/my-repo/") == "my-repo"


# ── run_git_command ───────────────────────────────────────────────────────────

def test_run_git_command_returns_result():
    assert run_git_command("test", lambda: "output") == "output"


def test_run_git_command_wraps_git_error():
    def fail():
        raise GitCommandError("git clone", "fatal: repo not found")

    with pytest.raises(GitOperationError) as exc:
        run_git_command("clone", fail)
    assert exc.value.step == "clone"
    assert "clone" in str(exc.value)


# ── GitOperationError ─────────────────────────────────────────────────────────

def test_git_operation_error_attributes():
    err = GitOperationError("checkout", "branch not found")
    assert err.step == "checkout"
    assert err.detail == "branch not found"
    assert "checkout" in str(err)


# ── create_temp_workspace ─────────────────────────────────────────────────────

def test_create_temp_workspace_uses_provided_root(tmp_path):
    root = str(tmp_path)
    ws = create_temp_workspace(root=root)
    assert ws.startswith(root)
    assert "tmp-" in ws


def test_create_temp_workspace_default_root():
    ws = create_temp_workspace()
    assert "workspaces" in ws


# ── checkout_branch ───────────────────────────────────────────────────────────

def test_checkout_branch_calls_git_checkout(tmp_path):
    mock_repo = MagicMock()
    with patch("app.git_client.Repo", return_value=mock_repo):
        checkout_branch(str(tmp_path), "feature/xyz")
    mock_repo.git.checkout.assert_called_with("feature/xyz")


def test_checkout_branch_raises_on_git_error(tmp_path):
    mock_repo = MagicMock()
    mock_repo.git.checkout.side_effect = GitCommandError("checkout", "not found")
    with patch("app.git_client.Repo", return_value=mock_repo):
        with pytest.raises(GitOperationError):
            checkout_branch(str(tmp_path), "nonexistent")


# ── pull_latest ───────────────────────────────────────────────────────────────

def test_pull_latest_calls_origin_pull(tmp_path):
    mock_repo = MagicMock()
    with patch("app.git_client.Repo", return_value=mock_repo):
        pull_latest(str(tmp_path))
    mock_repo.remotes.origin.pull.assert_called_once()


# ── checkout_commit ───────────────────────────────────────────────────────────

def test_checkout_commit_calls_git_checkout(tmp_path):
    mock_repo = MagicMock()
    with patch("app.git_client.Repo", return_value=mock_repo):
        checkout_commit(str(tmp_path), "abc123def")
    mock_repo.git.checkout.assert_called_with("abc123def")


# ── get_latest_commit_info ────────────────────────────────────────────────────

def test_get_latest_commit_info_returns_dict(tmp_path):
    mock_commit = MagicMock()
    mock_commit.hexsha = "deadbeef1234"
    mock_commit.message = "  Fix bug\n"
    mock_commit.author = "Alice <alice@example.com>"
    mock_repo = MagicMock()
    mock_repo.head.commit = mock_commit

    with patch("app.git_client.Repo", return_value=mock_repo):
        info = get_latest_commit_info(str(tmp_path))

    assert info["commit_hash"] == "deadbeef1234"
    assert info["commit_msg"] == "Fix bug"
    assert "Alice" in info["commit_author"]


# ── ensure_repository_state ───────────────────────────────────────────────────

def test_ensure_repository_state_clones_if_not_exists(tmp_path):
    workspace = str(tmp_path / "new_workspace")
    with patch("app.git_client.clone_repository") as mock_clone:
        mock_clone.return_value = workspace
        result = ensure_repository_state("https://github.com/org/repo", "main", workspace)
    mock_clone.assert_called_once()
    assert result == workspace


def test_ensure_repository_state_pulls_if_exists(tmp_path):
    workspace = str(tmp_path)
    with patch("app.git_client.checkout_branch") as mock_checkout, \
         patch("app.git_client.pull_latest") as mock_pull:
        result = ensure_repository_state("https://github.com/org/repo", "main", workspace)
    mock_checkout.assert_called_once_with(workspace, "main")
    mock_pull.assert_called_once_with(workspace)
    assert result == workspace
