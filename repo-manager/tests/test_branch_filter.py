from app.branch_filter import is_branch_allowed, load_ci_config


def test_branch_allowed() -> None:
    assert is_branch_allowed("main", ["main", "develop"]) is True


def test_branch_rejected() -> None:
    assert is_branch_allowed("feature/x", ["main", "develop"]) is False


def test_load_ci_config_uses_defaults_when_missing(tmp_path) -> None:
    config = load_ci_config(tmp_path)
    assert config["runtime"] == "python"
    assert config["branches"] == ["main", "develop"]
    assert config["image"] == "python:3.11-slim"
    assert "steps" in config
    assert config["steps"]["install"]["command"] == "pip install -r requirements.txt"
    assert config["steps"]["test"]["command"] == "pytest tests/ -v --tb=short"


def test_load_ci_config_reads_yaml(tmp_path) -> None:
    config_file = tmp_path / "ci-config.yaml"
    config_file.write_text(
        "\n".join(
            [
                "runtime: nodejs",
                "image: node:20-alpine",
                "branches:",
                "  - main",
                "  - release",
                "steps:",
                "  install:",
                "    command: npm install",
                "    timeout: 60",
                "  build:",
                "    command: npm run build",
                "    timeout: 90",
                "  test:",
                "    command: npm test",
                "    timeout: 120",
            ]
        ),
        encoding="utf-8",
    )

    config = load_ci_config(tmp_path)

    assert config["runtime"] == "nodejs"
    assert config["branches"] == ["main", "release"]
    assert config["image"] == "node:20-alpine"
    assert config["steps"]["install"]["command"] == "npm install"
    assert config["steps"]["install"]["timeout"] == 60
    assert config["steps"]["test"]["command"] == "npm test"
    assert config["steps"]["test"]["timeout"] == 120
