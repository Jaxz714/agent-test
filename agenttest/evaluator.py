"""AI-powered evaluation engine for AgentTest."""

from __future__ import annotations

import re
from typing import Any

from agenttest.models import (
    AssertionResult,
    ExpectType,
    Expectation,
    TestStatus,
)


class Evaluator:
    """Evaluates agent output against expectations."""

    def __init__(self, anthropic_client: Any | None = None, model: str = "claude-sonnet-4-6"):
        self.client = anthropic_client
        self.model = model

    def evaluate(self, output: str, expectation: Expectation) -> AssertionResult:
        """Evaluate output against a single expectation."""
        handler = {
            ExpectType.EXACT: self._eval_exact,
            ExpectType.CONTAINS: self._eval_contains,
            ExpectType.NOT_CONTAINS: self._eval_not_contains,
            ExpectType.REGEX: self._eval_regex,
            ExpectType.LENGTH: self._eval_length,
            ExpectType.AI_JUDGE: self._eval_ai_judge,
            ExpectType.SEMANTIC: self._eval_semantic,
            ExpectType.STARTS_WITH: self._eval_starts_with,
            ExpectType.ENDS_WITH: self._eval_ends_with,
        }.get(expectation.type)

        if handler is None:
            return AssertionResult(
                expectation=expectation,
                status=TestStatus.ERROR,
                message=f"Unknown expectation type: {expectation.type}",
            )

        try:
            return handler(output, expectation)
        except Exception as e:
            return AssertionResult(
                expectation=expectation,
                status=TestStatus.ERROR,
                message=f"Evaluation error: {e}",
            )

    def evaluate_all(self, output: str, expectations: list[Expectation]) -> list[AssertionResult]:
        """Evaluate output against all expectations."""
        return [self.evaluate(output, exp) for exp in expectations]

    def _eval_exact(self, output: str, exp: Expectation) -> AssertionResult:
        """Check if output exactly matches expected value."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No value specified for exact match",
            )
        match = output.strip() == exp.value.strip()
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message="Exact match" if match else f"Expected exact match: {exp.value[:100]}",
        )

    def _eval_contains(self, output: str, exp: Expectation) -> AssertionResult:
        """Check if output contains the expected value (case-insensitive)."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No value specified for contains check",
            )
        match = exp.value.lower() in output.lower()
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message=f"Contains '{exp.value}'" if match else f"Missing expected content: '{exp.value}'",
        )

    def _eval_not_contains(self, output: str, exp: Expectation) -> AssertionResult:
        """Check that output does NOT contain the value."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No value specified for not_contains check",
            )
        match = exp.value.lower() not in output.lower()
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message=f"Does not contain '{exp.value}'" if match else f"Unexpectedly contains: '{exp.value}'",
        )

    def _eval_regex(self, output: str, exp: Expectation) -> AssertionResult:
        """Check if output matches a regex pattern."""
        if exp.pattern is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No pattern specified for regex check",
            )
        match = re.search(exp.pattern, output, re.IGNORECASE) is not None
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message=f"Matches pattern: {exp.pattern}" if match else f"Does not match pattern: {exp.pattern}",
        )

    def _eval_length(self, output: str, exp: Expectation) -> AssertionResult:
        """Check output length constraints."""
        length = len(output)
        word_count = len(output.split())

        if exp.max is not None and length > exp.max:
            return AssertionResult(
                expectation=exp,
                status=TestStatus.FAILED,
                message=f"Output too long: {length} chars (max {exp.max})",
                details={"length": length, "max": exp.max},
            )
        if exp.min is not None and length < exp.min:
            return AssertionResult(
                expectation=exp,
                status=TestStatus.FAILED,
                message=f"Output too short: {length} chars (min {exp.min})",
                details={"length": length, "min": exp.min},
            )

        parts = [f"{length} chars"]
        if exp.min is not None:
            parts.append(f"(min {exp.min})")
        if exp.max is not None:
            parts.append(f"(max {exp.max})")
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED,
            message=f"Length OK: {' '.join(parts)}",
            details={"length": length, "word_count": word_count},
        )

    def _eval_starts_with(self, output: str, exp: Expectation) -> AssertionResult:
        """Check if output starts with the expected value."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No value specified for starts_with check",
            )
        match = output.strip().lower().startswith(exp.value.lower())
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message=f"Starts with '{exp.value}'" if match else f"Does not start with '{exp.value}'",
        )

    def _eval_ends_with(self, output: str, exp: Expectation) -> AssertionResult:
        """Check if output ends with the expected value."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No value specified for ends_with check",
            )
        match = output.strip().lower().endswith(exp.value.lower())
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if match else TestStatus.FAILED,
            message=f"Ends with '{exp.value}'" if match else f"Does not end with '{exp.value}'",
        )

    def _eval_semantic(self, output: str, exp: Expectation) -> AssertionResult:
        """Semantic similarity check using AI judge."""
        if exp.value is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No reference value specified for semantic check",
            )
        if self.client is None:
            return self._fallback_semantic(output, exp)

        prompt = f"""You are evaluating an AI agent's output for semantic similarity.

Agent output:
\"\"\"
{output}
\"\"\"

Reference text:
\"\"\"
{exp.value}
\"\"\"

Rate the semantic similarity from 0.0 to 1.0, where:
- 1.0 means identical meaning
- 0.5 means partially similar
- 0.0 means completely different

Respond with ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            result = json.loads(response.content[0].text)
            score = result.get("score", 0.0)
            reason = result.get("reason", "")
            threshold = exp.threshold or 0.7
            passed = score >= threshold

            return AssertionResult(
                expectation=exp,
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                message=f"Semantic similarity: {score:.2f} (threshold: {threshold}) - {reason}",
                score=score,
                details={"score": score, "threshold": threshold, "reason": reason},
            )
        except Exception as e:
            return AssertionResult(
                expectation=exp,
                status=TestStatus.ERROR,
                message=f"Semantic evaluation failed: {e}",
            )

    def _fallback_semantic(self, output: str, exp: Expectation) -> AssertionResult:
        """Fallback semantic check using word overlap."""
        output_words = set(output.lower().split())
        ref_words = set(exp.value.lower().split())
        if not ref_words:
            return AssertionResult(
                expectation=exp, status=TestStatus.FAILED,
                message="Reference text is empty",
            )
        overlap = output_words & ref_words
        score = len(overlap) / len(ref_words)
        threshold = exp.threshold or 0.5
        return AssertionResult(
            expectation=exp,
            status=TestStatus.PASSED if score >= threshold else TestStatus.FAILED,
            message=f"Word overlap similarity: {score:.2f} (threshold: {threshold})",
            score=score,
        )

    def _eval_ai_judge(self, output: str, exp: Expectation) -> AssertionResult:
        """Use Claude to judge if output meets criteria."""
        if exp.criteria is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="No criteria specified for AI judge",
            )
        if self.client is None:
            return AssertionResult(
                expectation=exp, status=TestStatus.ERROR,
                message="AI judge requires an Anthropic API key (set ANTHROPIC_API_KEY)",
            )

        prompt = f"""You are an expert evaluator judging an AI agent's output.

Agent output:
\"\"\"
{output}
\"\"\"

Evaluation criteria:
{exp.criteria}

Respond with ONLY a JSON object in this exact format:
{{"passed": true/false, "score": <float 0.0-1.0>, "reason": "<brief explanation>"}}

Be strict but fair. Only pass if the output clearly meets the criteria."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            result = json.loads(response.content[0].text)
            passed = result.get("passed", False)
            score = result.get("score", 0.0)
            reason = result.get("reason", "")

            return AssertionResult(
                expectation=exp,
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                message=f"AI Judge: {'PASS' if passed else 'FAIL'} ({score:.2f}) - {reason}",
                score=score,
                details={"criteria": exp.criteria, "score": score, "reason": reason},
            )
        except json.JSONDecodeError:
            # Try to extract a pass/fail from raw text
            raw = response.content[0].text.lower()
            passed = '"passed": true' in raw or '"passed":true' in raw
            return AssertionResult(
                expectation=exp,
                status=TestStatus.PASSED if passed else TestStatus.FAILED,
                message=f"AI Judge (raw): {'PASS' if passed else 'FAIL'} - {response.content[0].text[:200]}",
            )
        except Exception as e:
            return AssertionResult(
                expectation=exp,
                status=TestStatus.ERROR,
                message=f"AI judge failed: {e}",
            )
