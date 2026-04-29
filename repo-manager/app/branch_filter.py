from pathlib import Path

import yaml

DEFAULT_CI_CONFIG = {
    "runtime": "python",
    "branches": ["main", "develop"],
    "image": "python:3.11-slim",
    "steps": {
        "install": {
            "command": "pip install -r requirements.txt",
            "timeout": 120,
        },
        "build": {
            "command": "echo 'no build step'",
            "timeout": 180,
        },
        "test": {
            "command": "pytest tests/ -v --tb=short",
            "timeout": 300,
        },
    },
}


def is_branch_allowed(branch: str, allowed_branches: list[str]) -> bool:
    return branch in allowed_branches


def default_image_for_runtime(runtime: str) -> str:
    images = {
        "python": "python:3.11-slim",
        "nodejs": "node:20-alpine",
        "java": "maven:3.9-eclipse-temurin-17",
    }
    return images.get(runtime, "python:3.11-slim")


def normalize_step(data: dict | None, default_command: str, default_timeout: int) -> dict:
    step_data = data if isinstance(data, dict) else {}
    return {
        "command": str(step_data.get("command", default_command)),
        "timeout": int(step_data.get("timeout", default_timeout)),
    }


def load_ci_config(repo_path: str | Path) -> dict:
    config_path = Path(repo_path) / "ci-config.yaml"
    if not config_path.exists():
        return DEFAULT_CI_CONFIG.copy()

    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    runtime = str(data.get("runtime") or DEFAULT_CI_CONFIG["runtime"])
    branches = data.get("branches") or DEFAULT_CI_CONFIG["branches"]
    image = str(data.get("image") or default_image_for_runtime(runtime))
    steps_data = data.get("steps") if isinstance(data.get("steps"), dict) else {}
    default_steps = DEFAULT_CI_CONFIG["steps"]

    return {
        "runtime": runtime,
        "branches": [str(branch) for branch in branches],
        "image": image,
        "steps": {
            "install": normalize_step(
                steps_data.get("install"),
                default_steps["install"]["command"],
                default_steps["install"]["timeout"],
            ),
            "build": normalize_step(
                steps_data.get("build"),
                default_steps["build"]["command"],
                default_steps["build"]["timeout"],
            ),
            "test": normalize_step(
                steps_data.get("test"),
                default_steps["test"]["command"],
                default_steps["test"]["timeout"],
            ),
        },
    }


def load_allowed_branches(repo_path: str | Path) -> list[str]:
    return load_ci_config(repo_path)["branches"]
