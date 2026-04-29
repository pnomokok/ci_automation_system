import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse, urlunparse

from git import GitCommandError, Repo


def _inject_token(repo_url: str) -> str:
    """GitHub token varsa HTTPS URL'ye ekle."""
    token = os.getenv("GITHUB_TOKEN", "")
    if token and "github.com" in repo_url and repo_url.startswith("https://"):
        parsed = urlparse(repo_url)
        authed = parsed._replace(netloc=f"{token}@{parsed.netloc}")
        return urlunparse(authed)
    return repo_url


class GitOperationError(Exception):
    def __init__(self, step: str, detail: str) -> None:
        self.step = step
        self.detail = detail
        super().__init__(f"Git step '{step}' failed: {detail}")


def run_git_command(step: str, operation) -> str:
    try:
        return operation()
    except GitCommandError as exc:
        detail = str(exc).strip() or "unknown git error"
        raise GitOperationError(step, detail) from exc


def repo_name_from_url(repo_url: str) -> str:
    repo_path = urlparse(repo_url).path.rstrip("/")
    repo_name = Path(repo_path).name
    return repo_name.removesuffix(".git") or "repository"


def clone_repository(repo_url: str, destination: str) -> str:
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    auth_url = _inject_token(repo_url)
    run_git_command("clone", lambda: Repo.clone_from(auth_url, destination))
    return destination


def checkout_branch(repo_path: str, branch: str) -> None:
    repo = Repo(repo_path)
    run_git_command("checkout", lambda: repo.git.checkout(branch))


def pull_latest(repo_path: str) -> None:
    repo = Repo(repo_path)
    run_git_command("pull", lambda: repo.remotes.origin.pull())


def checkout_commit(repo_path: str, commit_hash: str) -> None:
    repo = Repo(repo_path)
    run_git_command("checkout-commit", lambda: repo.git.checkout(commit_hash))


def ensure_repository_state(repo_url: str, branch: str, workspace: str) -> str:
    workspace_path = Path(workspace)
    if not workspace_path.exists():
        clone_repository(repo_url, workspace)

    checkout_branch(workspace, branch)
    pull_latest(workspace)
    return str(workspace_path)


def get_latest_commit_info(repo_path: str) -> dict[str, str]:
    repo = Repo(repo_path)
    commit = repo.head.commit
    return {
        "commit_hash": commit.hexsha,
        "commit_msg": commit.message.strip(),
        "commit_author": str(commit.author),
    }


def create_temp_workspace(root: str | None = None) -> str:
    workspace_root = root or "/shared/workspaces"
    return str(Path(workspace_root) / f"tmp-{uuid4()}")
