import os
import tempfile
import textwrap

import pytest
import yaml

from app.image_resolver import ImageResolver


def make_workspace(config: dict) -> str:
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "ci-config.yaml"), "w") as f:
        yaml.dump(config, f)
    return tmp


# ── resolve_image ──────────────────────────────────────────────────────────

def test_resolve_explicit_image():
    ws = make_workspace({"image": "python:3.12", "steps": {"install": {"command": "pip install ."}}})
    assert ImageResolver(ws).resolve_image() == "python:3.12"


def test_resolve_python_runtime():
    ws = make_workspace({"runtime": "python", "steps": {"install": {"command": "pip install ."}}})
    assert ImageResolver(ws).resolve_image() == "python:3.11"


def test_resolve_nodejs_runtime():
    ws = make_workspace({"runtime": "nodejs", "steps": {"install": {"command": "npm ci"}}})
    assert ImageResolver(ws).resolve_image() == "node:18-slim"


def test_resolve_unknown_runtime_falls_back_to_default():
    ws = make_workspace({"runtime": "rust", "steps": {"install": {"command": "cargo build"}}})
    assert ImageResolver(ws).resolve_image() == "ubuntu:22.04"


# ── get_step_image ─────────────────────────────────────────────────────────

def test_step_image_override():
    ws = make_workspace({
        "image": "python:3.11-slim",
        "steps": {
            "install": {"command": "pip install .", "image": "python:3.12-slim"},
        },
    })
    assert ImageResolver(ws).get_step_image("install") == "python:3.12-slim"


def test_step_image_falls_back_to_global():
    ws = make_workspace({
        "image": "python:3.11-slim",
        "steps": {"install": {"command": "pip install ."}},
    })
    assert ImageResolver(ws).get_step_image("install") == "python:3.11-slim"


# ── get_commands ───────────────────────────────────────────────────────────

def test_get_commands_returns_all_steps():
    ws = make_workspace({
        "runtime": "python",
        "steps": {
            "install": {"command": "pip install -r requirements.txt"},
            "test":    {"command": "pytest tests/"},
        },
    })
    cmds = ImageResolver(ws).get_commands()
    assert cmds["install"] == "pip install -r requirements.txt"
    assert cmds["test"] == "pytest tests/"


def test_get_commands_missing_steps_raises():
    ws = make_workspace({"runtime": "python"})
    with pytest.raises(ValueError, match="steps"):
        ImageResolver(ws).get_commands()


def test_get_commands_missing_command_raises():
    ws = make_workspace({"runtime": "python", "steps": {"install": {"timeout": 120}}})
    with pytest.raises(ValueError, match="command"):
        ImageResolver(ws).get_commands()


# ── get_timeout ────────────────────────────────────────────────────────────

def test_get_timeout_explicit():
    ws = make_workspace({
        "runtime": "python",
        "steps": {"install": {"command": "pip install .", "timeout": 300}},
    })
    assert ImageResolver(ws).get_timeout("install") == 300


def test_get_timeout_default_when_missing():
    ws = make_workspace({
        "runtime": "python",
        "steps": {"install": {"command": "pip install ."}},
    })
    assert ImageResolver(ws).get_timeout("install") == 120


def test_get_timeout_default_for_unknown_step():
    ws = make_workspace({"runtime": "python", "steps": {"install": {"command": "pip install ."}}})
    assert ImageResolver(ws).get_timeout("nonexistent") == 120


# ── error cases ────────────────────────────────────────────────────────────

def test_missing_config_file_raises():
    with pytest.raises(FileNotFoundError):
        ImageResolver("/nonexistent/path").resolve_image()


def test_invalid_yaml_raises():
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "ci-config.yaml"), "w") as f:
        f.write("key: [unclosed")
    with pytest.raises(ValueError, match="Invalid YAML"):
        ImageResolver(tmp).resolve_image()


def test_config_caching(mocker=None):
    ws = make_workspace({"image": "python:3.11", "steps": {"install": {"command": "pip install ."}}})
    resolver = ImageResolver(ws)
    resolver.resolve_image()
    # Second call should use cache, not re-read file
    os.remove(os.path.join(ws, "ci-config.yaml"))
    assert resolver.resolve_image() == "python:3.11"
