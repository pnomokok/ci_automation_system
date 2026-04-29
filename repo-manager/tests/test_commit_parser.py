from app.commit_parser import parse_push_payload


def test_parse_push_payload_extracts_expected_fields() -> None:
    payload = {
        "ref": "refs/heads/main",
        "after": "abc123456789",
        "repository": {
            "name": "sample-repo",
            "clone_url": "https://github.com/org/sample-repo.git",
        },
        "head_commit": {
            "id": "abc123456789",
            "message": "Add CI config",
            "timestamp": "2026-04-28T10:00:00Z",
            "author": {"name": "Zeynep"},
        },
    }

    parsed = parse_push_payload(payload)

    assert parsed["branch"] == "main"
    assert parsed["commit_hash"] == "abc123456789"
    assert parsed["commit_msg"] == "Add CI config"
    assert parsed["commit_author"] == "Zeynep"
    assert parsed["repo_url"] == "https://github.com/org/sample-repo.git"
    assert parsed["trigger_type"] == "webhook"
