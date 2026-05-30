"""Data models for AgentTest."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExpectType(str, Enum):
    """Supported evaluation types."""

    EXACT = "exact"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    LENGTH = "length"
    AI_JUDGE = "ai_judge"
    SEMANTIC = "semantic"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class TestStatus(str, Enum):
    """Status of a test result."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class Expectation:
    """A single expectation for a test case."""

    type: ExpectType
    value: str | None = None
    criteria: str | None = None
    min: int | None = None
    max: int | None = None
    pattern: str | None = None
    threshold: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Expectation:
        """Create an Expectation from a dictionary."""
        return cls(
            type=ExpectType(data["type"]),
            value=data.get("value"),
            criteria=data.get("criteria"),
            min=data.get("min"),
            max=data.get("max"),
            pattern=data.get("pattern"),
            threshold=data.get("threshold"),
        )


@dataclass
class AgentConfig:
    """Configuration for the agent under test."""

    type: str = "cli"
    command: str | None = None
    endpoint: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 60

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """Create an AgentConfig from a dictionary."""
        return cls(
            type=data.get("type", "cli"),
            command=data.get("command"),
            endpoint=data.get("endpoint"),
            headers=data.get("headers", {}),
            timeout=data.get("timeout", 60),
        )


@dataclass
class TestCase:
    """A single test case."""

    name: str
    input: str
    expectations: list[Expectation] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timeout: int | None = None
    skip: bool = False
    skip_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        """Create a TestCase from a dictionary."""
        expectations = [
            Expectation.from_dict(e) for e in data.get("expect", [])
        ]
        return cls(
            name=data["name"],
            input=data.get("input", ""),
            expectations=expectations,
            tags=data.get("tags", []),
            timeout=data.get("timeout"),
            skip=data.get("skip", False),
            skip_reason=data.get("skip_reason"),
        )


@dataclass
class TestSuite:
    """A collection of test cases."""

    name: str
    tests: list[TestCase] = field(default_factory=list)
    description: str = ""
    agent: AgentConfig = field(default_factory=AgentConfig)
    tags: list[str] = field(default_factory=list)
    file_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], file_path: str | None = None) -> TestSuite:
        """Create a TestSuite from a dictionary."""
        agent = AgentConfig.from_dict(data.get("agent", {}))
        tests = [TestCase.from_dict(t) for t in data.get("tests", [])]
        return cls(
            name=data.get("name", "Unnamed Suite"),
            tests=tests,
            description=data.get("description", ""),
            agent=agent,
            tags=data.get("tags", []),
            file_path=file_path,
        )


@dataclass
class AssertionResult:
    """Result of a single assertion."""

    expectation: Expectation
    status: TestStatus
    message: str = ""
    score: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of running a single test case."""

    test_case: TestCase
    status: TestStatus
    output: str = ""
    assertion_results: list[AssertionResult] = field(default_factory=list)
    duration: float = 0.0
    error: str | None = None

    @property
    def score(self) -> float:
        """Calculate score as ratio of passed assertions."""
        if not self.assertion_results:
            return 0.0
        passed = sum(1 for r in self.assertion_results if r.status == TestStatus.PASSED)
        return passed / len(self.assertion_results)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED


@dataclass
class SuiteResult:
    """Result of running a test suite."""

    suite: TestSuite
    test_results: list[TestResult] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def total(self) -> int:
        return len(self.test_results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.test_results if r.status == TestStatus.PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.test_results if r.status == TestStatus.FAILED)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.test_results if r.status == TestStatus.ERROR)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)

    @property
    def score(self) -> float:
        """Overall score as ratio of passed tests."""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for saving."""
        return {
            "suite_name": self.suite.name,
            "suite_description": self.suite.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "score": self.score,
            "tests": [
                {
                    "name": r.test_case.name,
                    "status": r.status.value,
                    "output": r.output[:500],
                    "score": r.score,
                    "duration": r.duration,
                    "error": r.error,
                    "assertions": [
                        {
                            "type": a.expectation.type.value,
                            "status": a.status.value,
                            "message": a.message,
                            "score": a.score,
                        }
                        for a in r.assertion_results
                    ],
                }
                for r in self.test_results
            ],
        }


@dataclass
class RunResult:
    """Result of an entire run (one or more suites)."""

    suite_results: list[SuiteResult] = field(default_factory=list)
    run_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def total(self) -> int:
        return sum(sr.total for sr in self.suite_results)

    @property
    def passed(self) -> int:
        return sum(sr.passed for sr in self.suite_results)

    @property
    def failed(self) -> int:
        return sum(sr.failed for sr in self.suite_results)

    @property
    def errors(self) -> int:
        return sum(sr.errors for sr in self.suite_results)

    @property
    def skipped(self) -> int:
        return sum(sr.skipped for sr in self.suite_results)

    @property
    def score(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for saving."""
        return {
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "score": self.score,
            "suites": [sr.to_dict() for sr in self.suite_results],
        }
