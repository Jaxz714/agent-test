"""YAML test file loaders for AgentTest."""

from __future__ import annotations

from pathlib import Path

import yaml

from agenttest.models import TestSuite


def load_test_suite(file_path: str | Path) -> TestSuite:
    """Load a single test suite from a YAML file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid test file format: {path}")

    return TestSuite.from_dict(data, file_path=str(path))


def load_test_suites(path: str | Path, suite_name: str | None = None) -> list[TestSuite]:
    """Load test suites from a file or directory."""
    path = Path(path)

    if path.is_file():
        suite = load_test_suite(path)
        return [suite]

    if path.is_dir():
        suites = []
        for yaml_file in sorted(path.glob("**/*.yaml")):
            try:
                suite = load_test_suite(yaml_file)
                if suite_name is None or suite_name.lower() in suite.name.lower():
                    suites.append(suite)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

        for yml_file in sorted(path.glob("**/*.yml")):
            try:
                suite = load_test_suite(yml_file)
                if suite_name is None or suite_name.lower() in suite.name.lower():
                    suites.append(suite)
            except Exception as e:
                print(f"Warning: Failed to load {yml_file}: {e}")

        return suites

    raise FileNotFoundError(f"Path not found: {path}")


def save_test_suite(suite: TestSuite, file_path: str | Path) -> None:
    """Save a test suite to a YAML file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "name": suite.name,
        "description": suite.description,
        "agent": {
            "type": suite.agent.type,
        },
        "tests": [],
    }

    if suite.agent.command:
        data["agent"]["command"] = suite.agent.command
    if suite.agent.endpoint:
        data["agent"]["endpoint"] = suite.agent.endpoint

    for test in suite.tests:
        test_data: dict = {
            "name": test.name,
            "input": test.input,
            "expect": [],
        }
        for exp in test.expectations:
            exp_data: dict = {"type": exp.type.value}
            if exp.value is not None:
                exp_data["value"] = exp.value
            if exp.criteria is not None:
                exp_data["criteria"] = exp.criteria
            if exp.min is not None:
                exp_data["min"] = exp.min
            if exp.max is not None:
                exp_data["max"] = exp.max
            if exp.pattern is not None:
                exp_data["pattern"] = exp.pattern
            if exp.threshold is not None:
                exp_data["threshold"] = exp.threshold
            test_data["expect"].append(exp_data)
        data["tests"].append(test_data)

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
