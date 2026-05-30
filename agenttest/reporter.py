"""Results reporting for AgentTest."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agenttest.models import RunResult, SuiteResult, TestResult, TestStatus


class Reporter:
    """Formats and displays test results."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def report_run(self, run_result: RunResult) -> None:
        """Print a full run report."""
        self.console.print()
        self._print_header(run_result)

        for suite_result in run_result.suite_results:
            self._print_suite_result(suite_result)

        self._print_summary(run_result)

    def report_suite(self, suite_result: SuiteResult) -> None:
        """Print a single suite report."""
        self.console.print()
        self._print_suite_result(suite_result)
        self._print_suite_summary(suite_result)

    def report_comparison(self, run1: dict[str, Any], run2: dict[str, Any]) -> None:
        """Print a comparison between two runs."""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]Regression Comparison[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()

        table = Table(title="Run Comparison", show_lines=True)
        table.add_column("Metric", style="bold")
        table.add_column(f"Run 1 ({run1.get('run_id', '?')})", justify="center")
        table.add_column(f"Run 2 ({run2.get('run_id', '?')})", justify="center")
        table.add_column("Change", justify="center")

        # Overall metrics
        self._add_comparison_row(table, "Total Tests", run1.get("total", 0), run2.get("total", 0))
        self._add_comparison_row(table, "Passed", run1.get("passed", 0), run2.get("passed", 0))
        self._add_comparison_row(table, "Failed", run1.get("failed", 0), run2.get("failed", 0))
        self._add_comparison_row(table, "Errors", run1.get("errors", 0), run2.get("errors", 0))
        self._add_comparison_row(table, "Score", run1.get("score", 0), run2.get("score", 0), is_pct=True)
        self._add_comparison_row(table, "Duration", run1.get("duration", 0), run2.get("duration", 0), is_time=True)

        self.console.print(table)

        # Compare individual tests
        self._compare_tests(run1, run2)

    def _add_comparison_row(
        self,
        table: Table,
        metric: str,
        val1: float,
        val2: float,
        is_pct: bool = False,
        is_time: bool = False,
    ) -> None:
        """Add a row to the comparison table."""
        if is_pct:
            v1 = f"{val1:.1%}"
            v2 = f"{val2:.1%}"
            diff = val2 - val1
            if diff > 0:
                change = f"[green]+{diff:.1%}[/green]"
            elif diff < 0:
                change = f"[red]{diff:.1%}[/red]"
            else:
                change = "[dim]no change[/dim]"
        elif is_time:
            v1 = f"{val1:.2f}s"
            v2 = f"{val2:.2f}s"
            diff = val2 - val1
            if diff > 0:
                change = f"[red]+{diff:.2f}s[/red]"
            elif diff < 0:
                change = f"[green]{diff:.2f}s[/green]"
            else:
                change = "[dim]no change[/dim]"
        else:
            v1 = str(int(val1))
            v2 = str(int(val2))
            diff = int(val2) - int(val1)
            if diff > 0:
                change = f"[green]+{diff}[/green]"
            elif diff < 0:
                change = f"[red]{diff}[/red]"
            else:
                change = "[dim]no change[/dim]"

        table.add_row(metric, v1, v2, change)

    def _compare_tests(self, run1: dict[str, Any], run2: dict[str, Any]) -> None:
        """Compare individual test results between two runs."""
        tests1 = self._extract_test_map(run1)
        tests2 = self._extract_test_map(run2)

        all_names = sorted(set(tests1.keys()) | set(tests2.keys()))

        regressions = []
        improvements = []

        for name in all_names:
            t1 = tests1.get(name)
            t2 = tests2.get(name)

            if t1 and t2:
                s1 = t1.get("status", "unknown")
                s2 = t2.get("status", "unknown")
                if s1 == "passed" and s2 != "passed":
                    regressions.append((name, s1, s2))
                elif s1 != "passed" and s2 == "passed":
                    improvements.append((name, s1, s2))
            elif t2 is None:
                regressions.append((name, t1.get("status", "?"), "missing"))

        if regressions:
            self.console.print()
            self.console.print("[bold red]Regressions:[/bold red]")
            for name, old, new in regressions:
                self.console.print(f"  [red]FAIL[/red] {name}: {old} -> {new}")

        if improvements:
            self.console.print()
            self.console.print("[bold green]Improvements:[/bold green]")
            for name, old, new in improvements:
                self.console.print(f"  [green]PASS[/green] {name}: {old} -> {new}")

        if not regressions and not improvements:
            self.console.print()
            self.console.print("[dim]No test-level changes detected.[/dim]")

    def _extract_test_map(self, run_data: dict[str, Any]) -> dict[str, dict]:
        """Extract a flat map of test name -> test data from run results."""
        tests = {}
        for suite in run_data.get("suites", []):
            for test in suite.get("tests", []):
                tests[test["name"]] = test
        return tests

    def _print_header(self, run_result: RunResult) -> None:
        """Print the run header."""
        header = Text()
        header.append("AgentTest ", style="bold cyan")
        header.append("Run Report", style="bold")
        if run_result.run_id:
            header.append(f"  ({run_result.run_id})", style="dim")

        self.console.print(Panel.fit(header, border_style="cyan"))

    def _print_suite_result(self, suite_result: SuiteResult) -> None:
        """Print results for a single suite."""
        self.console.print()
        self.console.print(f"[bold]Suite: {suite_result.suite.name}[/bold]")
        if suite_result.suite.description:
            self.console.print(f"  [dim]{suite_result.suite.description}[/dim]")
        self.console.print()

        table = Table(show_lines=False, pad_edge=False)
        table.add_column("", width=3)
        table.add_column("Test", style="bold", min_width=30)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Score", justify="center", width=8)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Details", min_width=30)

        for result in suite_result.test_results:
            self._add_test_row(table, result)

        self.console.print(table)

    def _add_test_row(self, table: Table, result: TestResult) -> None:
        """Add a test result row to the table."""
        status_icon = {
            TestStatus.PASSED: "[green]PASS[/green]",
            TestStatus.FAILED: "[red]FAIL[/red]",
            TestStatus.ERROR: "[yellow]ERR[/yellow]",
            TestStatus.SKIPPED: "[dim]SKIP[/dim]",
        }.get(result.status, "?")

        icon = {
            TestStatus.PASSED: "[green]✓[/green]",
            TestStatus.FAILED: "[red]✗[/red]",
            TestStatus.ERROR: "[yellow]![/yellow]",
            TestStatus.SKIPPED: "[dim]-[/dim]",
        }.get(result.status, "?")

        # Collect assertion details
        details = []
        for ar in result.assertion_results:
            if ar.status == TestStatus.FAILED:
                details.append(f"[red]{ar.message}[/red]")
            elif ar.status == TestStatus.ERROR:
                details.append(f"[yellow]{ar.message}[/yellow]")

        if result.error:
            details.append(f"[red]Error: {result.error}[/red]")

        details_str = "\n".join(details) if details else "[dim]-[/dim]"
        score_str = f"{result.score:.0%}" if result.test_case.expectations else "-"
        duration_str = f"{result.duration:.2f}s"

        table.add_row(icon, result.test_case.name, status_icon, score_str, duration_str, details_str)

    def _print_summary(self, run_result: RunResult) -> None:
        """Print the run summary."""
        self.console.print()
        summary = Table(show_header=False, pad_edge=False, box=None)
        summary.add_column("Metric", style="bold")
        summary.add_column("Value", justify="right")

        summary.add_row("Total", str(run_result.total))
        summary.add_row("[green]Passed[/green]", str(run_result.passed))
        summary.add_row("[red]Failed[/red]", str(run_result.failed))
        summary.add_row("[yellow]Errors[/yellow]", str(run_result.errors))
        summary.add_row("[dim]Skipped[/dim]", str(run_result.skipped))
        summary.add_row("Score", f"{run_result.score:.1%}")
        summary.add_row("Duration", f"{run_result.duration:.2f}s")

        border = "green" if run_result.failed == 0 and run_result.errors == 0 else "red"
        self.console.print(Panel(summary, title="[bold]Summary[/bold]", border_style=border))

    def _print_suite_summary(self, suite_result: SuiteResult) -> None:
        """Print a single suite summary."""
        self.console.print()
        summary = Table(show_header=False, pad_edge=False, box=None)
        summary.add_column("Metric", style="bold")
        summary.add_column("Value", justify="right")

        summary.add_row("Total", str(suite_result.total))
        summary.add_row("[green]Passed[/green]", str(suite_result.passed))
        summary.add_row("[red]Failed[/red]", str(suite_result.failed))
        summary.add_row("Score", f"{suite_result.score:.1%}")
        summary.add_row("Duration", f"{suite_result.duration:.2f}s")

        border = "green" if suite_result.failed == 0 else "red"
        self.console.print(Panel(summary, title="[bold]Suite Summary[/bold]", border_style=border))

    def report_list(self, runs: list[str]) -> None:
        """Print a list of available runs."""
        if not runs:
            self.console.print("[dim]No saved runs found.[/dim]")
            return

        table = Table(title="Saved Runs")
        table.add_column("Run ID", style="bold")
        for run_id in runs:
            table.add_row(run_id)
        self.console.print(table)
