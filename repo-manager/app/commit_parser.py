from typing import Any

def extract_branch(ref: str) -> str:
    return ref.removeprefix("refs/heads/")


def parse_push_payload(payload: dict[str, Any]) -> dict[str, Any]:
    repository = payload.get("repository") or {}
    head_commit = payload.get("head_commit") or {}
    pusher = payload.get("pusher") or {}

    branch = extract_branch(payload.get("ref", ""))
    commit_hash = head_commit.get("id") or payload.get("after") or ""
    repo_name = repository.get("name", "repo")
    repo_url = repository.get("clone_url") or repository.get("html_url") or ""

    return {
        "event": "push",
        "repo_url": repo_url,
        "repo_name": repo_name,
        "branch": branch,
        "commit_hash": commit_hash,
        "commit_msg": head_commit.get("message", ""),
        "commit_author": (head_commit.get("author") or {}).get("name") or pusher.get("name", ""),
        "timestamp": head_commit.get("timestamp", ""),
        "trigger_type": "webhook",
    }
