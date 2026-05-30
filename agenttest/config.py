"""Configuration management for AgentTest."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_DIR = Path.home() / ".agenttest"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_RESULTS_DIR = DEFAULT_CONFIG_DIR / "results"


def get_config_dir() -> Path:
    """Get the configuration directory."""
    return Path(os.environ.get("AGENTTEST_CONFIG_DIR", DEFAULT_CONFIG_DIR))


def get_results_dir() -> Path:
    """Get the results directory."""
    return Path(os.environ.get("AGENTTEST_RESULTS_DIR", DEFAULT_RESULTS_DIR))


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from file."""
    if config_path is None:
        # Try project-level config first
        project_config = Path.cwd() / "agenttest.yaml"
        if project_config.exists():
            config_path = project_config
        else:
            config_path = get_config_dir() / "config.yaml"

    path = Path(config_path)
    if not path.exists():
        return get_default_config()

    with open(path) as f:
        config = yaml.safe_load(f) or {}

    # Merge with defaults
    defaults = get_default_config()
    return _deep_merge(defaults, config)


def get_default_config() -> dict[str, Any]:
    """Get default configuration."""
    return {
        "model": "claude-sonnet-4-20250514",
        "results_dir": str(get_results_dir()),
        "timeout": 60,
        "agent": {
            "type": "cli",
            "timeout": 60,
        },
        "evaluation": {
            "ai_judge_model": "claude-sonnet-4-20250514",
            "semantic_threshold": 0.7,
        },
    }


def save_config(config: dict[str, Any], config_path: str | Path | None = None) -> None:
    """Save configuration to file."""
    if config_path is None:
        config_path = get_config_dir() / "config.yaml"

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def init_config() -> Path:
    """Initialize configuration directory and default config."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    results_dir = get_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    if not config_path.exists():
        save_config(get_default_config(), config_path)

    return config_dir


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
