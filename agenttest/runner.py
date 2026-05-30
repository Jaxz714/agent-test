"""Test runner for AgentTest."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import anthropic

from agenttest.evaluator import Evaluator
from agenttest.models import (
    AgentConfig,
    RunResult,
    SuiteResult,
    TestCase,
    TestResult,
    TestStatus,
    TestSuite,
)


class AgentClient:
    """Client for communicating with the agent under test."""

    def __init__(self, config: AgentConfig):
        self.config = config

    def send(self, prompt: str, timeout: int | None = None) -> str:
        """Send a prompt to the agent and return the response."""
        timeout = timeout or self.config.timeout

        if self.config.type == "cli":
            return self._send_cli(prompt, timeout)
        elif self.config.type == "api":
            return self._send_api(prompt, timeout)
        else:
            raise ValueError(f"Unknown agent type: {self.config.type}")

    def _send_cli(self, prompt: str, timeout: int) -> str:
        """Send prompt via CLI command."""
        if not self.config.command:
            raise ValueError("No command specified for CLI agent")

        try:
            result = subprocess.run(
                self.config.command,
                shell=True,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0 and not result.stdout:
                raise RuntimeError(
                    f"Agent command failed (exit {result.returncode}): {result.stderr}"
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Agent command timed out after {timeout}s")

    def _send_api(self, prompt: str, timeout: int) -> str:
        """Send prompt via HTTP API."""
        if not self.config.endpoint:
            raise ValueError("No endpoint specified for API agent")

        try:
            import urllib.request
            import urllib.error

            headers = {"Content-Type": "application/json"}
            headers.update(self.config.headers)

            payload = json.dumps({"prompt": prompt, "input": prompt, "message": prompt}).encode()
            req = urllib.request.Request(
                self.config.endpoint,
                data=payload,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                # Try common response keys
                return data.get("response") or data.get("output") or data.get("message") or str(data)
        except Exception as e:
            raise RuntimeError(f"API request failed: {e}")


class TestRunner:
    """Runs test suites and collects results."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        results_dir: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.results_dir = Path(results_dir or os.path.expanduser("~/.agenttest/results"))
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Anthropic client if API key is available
        self.anthropic_client = None
        if self.api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)

        self.evaluator = Evaluator(
            anthropic_client=self.anthropic_client,
            model=self.model,
        )

    def run_suite(self, suite: TestSuite, tags: list[str] | None = None) -> SuiteResult:
        """Run a single test suite."""
        result = SuiteResult(suite=suite)

        agent = AgentClient(suite.agent)

        for test_case in suite.tests:
            # Filter by tags if specified
            if tags and not any(t in test_case.tags for t in tags):
                continue

            test_result = self._run_test(test_case, agent)
            result.test_results.append(test_result)

        result.end_time = time.time()
        return result

    def run_suites(
        self,
        suites: list[TestSuite],
        suite_name: str | None = None,
        tags: list[str] | None = None,
    ) -> RunResult:
        """Run multiple test suites."""
        run_result = RunResult()
        run_result.run_id = time.strftime("%Y%m%d_%H%M%S")

        for suite in suites:
            # Filter by suite name if specified
            if suite_name and suite_name.lower() not in suite.name.lower():
                continue

            suite_result = self.run_suite(suite, tags=tags)
            run_result.suite_results.append(suite_result)

        run_result.end_time = time.time()

        # Save results
        self._save_results(run_result)

        return run_result

    def _run_test(self, test_case: TestCase, agent: AgentClient) -> TestResult:
        """Run a single test case."""
        # Handle skipped tests
        if test_case.skip:
            return TestResult(
                test_case=test_case,
                status=TestStatus.SKIPPED,
                error=test_case.skip_reason or "Test skipped",
            )

        start_time = time.time()
        try:
            # Send prompt to agent
            output = agent.send(test_case.input, timeout=test_case.timeout)

            # Evaluate all expectations
            assertion_results = self.evaluator.evaluate_all(output, test_case.expectations)

            # Determine overall status
            all_passed = all(
                a.status == TestStatus.PASSED for a in assertion_results
            )
            has_error = any(a.status == TestStatus.ERROR for a in assertion_results)

            if has_error:
                status = TestStatus.ERROR
            elif all_passed:
                status = TestStatus.PASSED
            else:
                status = TestStatus.FAILED

            duration = time.time() - start_time
            return TestResult(
                test_case=test_case,
                status=status,
                output=output,
                assertion_results=assertion_results,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_case=test_case,
                status=TestStatus.ERROR,
                duration=duration,
                error=str(e),
            )

    def _save_results(self, run_result: RunResult) -> Path:
        """Save run results to disk."""
        filename = f"run_{run_result.run_id}.json"
        filepath = self.results_dir / filename

        with open(filepath, "w") as f:
            json.dump(run_result.to_dict(), f, indent=2)

        # Also update the "latest" symlink
        latest = self.results_dir / "latest.json"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(filepath)

        return filepath

    def load_result(self, run_id: str) -> dict[str, Any]:
        """Load a saved run result."""
        filepath = self.results_dir / f"run_{run_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"No results found for run: {run_id}")
        with open(filepath) as f:
            return json.load(f)

    def load_latest_result(self) -> dict[str, Any]:
        """Load the latest run result."""
        filepath = self.results_dir / "latest.json"
        if not filepath.exists():
            raise FileNotFoundError("No results found. Run a test suite first.")
        with open(filepath) as f:
            return json.load(f)

    def list_runs(self) -> list[str]:
        """List all saved run IDs."""
        runs = []
        for f in sorted(self.results_dir.glob("run_*.json")):
            run_id = f.stem.replace("run_", "")
            runs.append(run_id)
        return runs
