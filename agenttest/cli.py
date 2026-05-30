"""CLI interface for AgentTest."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from agenttest.config import init_config, load_config
from agenttest.loaders import load_test_suites
from agenttest.reporter import Reporter
from agenttest.runner import TestRunner

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="agenttest")
def main() -> None:
    """AgentTest - Testing framework for AI agents.

    Define tests in YAML, evaluate with AI-powered assertions, track regressions.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--suite", "-s", default=None, help="Run only suites matching this name")
@click.option("--tag", "-t", multiple=True, help="Run only tests with these tags")
@click.option("--model", "-m", default=None, help="Claude model for AI judge")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", default=None, help="Anthropic API key")
@click.option("--config", "-c", default=None, type=click.Path(), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(
    path: str,
    suite: str | None,
    tag: tuple[str, ...],
    model: str | None,
    api_key: str | None,
    config: str | None,
    verbose: bool,
) -> None:
    """Run test suites from a YAML file or directory.

    PATH is the path to a test YAML file or directory containing test files.
    """
    init_config()
    cfg = load_config(config)

    model = model or cfg.get("model", "claude-sonnet-4-20250514")

    if verbose:
        console.print(f"[dim]Loading tests from: {path}[/dim]")
        console.print(f"[dim]Model: {model}[/dim]")
        if not api_key:
            console.print("[dim]No API key - AI judge evaluations will be skipped[/dim]")

    # Load test suites
    try:
        suites = load_test_suites(path, suite_name=suite)
    except Exception as e:
        console.print(f"[red]Error loading tests: {e}[/red]")
        sys.exit(1)

    if not suites:
        console.print("[yellow]No test suites found.[/yellow]")
        sys.exit(0)

    if verbose:
        total_tests = sum(len(s.tests) for s in suites)
        console.print(f"[dim]Found {len(suites)} suite(s) with {total_tests} test(s)[/dim]")

    # Run tests
    runner = TestRunner(api_key=api_key, model=model)
    tags = list(tag) if tag else None

    with console.status("[bold cyan]Running tests..."):
        run_result = runner.run_suites(suites, suite_name=suite, tags=tags)

    # Report results
    reporter = Reporter(console)
    reporter.report_run(run_result)

    # Exit with appropriate code
    if run_result.failed > 0 or run_result.errors > 0:
        sys.exit(1)


@main.command()
@click.option("--config", "-c", default=None, type=click.Path(), help="Config file path")
@click.option("--latest", "-l", is_flag=True, help="Show latest run only")
def report(config: str | None, latest: bool) -> None:
    """Show results from the last test run."""
    cfg = load_config(config)
    runner = TestRunner(results_dir=cfg.get("results_dir"))
    reporter = Reporter(console)

    if latest:
        try:
            data = runner.load_latest_result()
            console.print_json(data)
        except FileNotFoundError as e:
            console.print(f"[yellow]{e}[/yellow]")
            sys.exit(1)
    else:
        runs = runner.list_runs()
        reporter.report_list(runs)


@main.command()
@click.argument("run1")
@click.argument("run2")
@click.option("--config", "-c", default=None, type=click.Path(), help="Config file path")
def compare(run1: str, run2: str, config: str | None) -> None:
    """Compare two test runs to detect regressions.

    RUN1 and RUN2 are run IDs (use 'agenttest report' to list available runs).
    """
    cfg = load_config(config)
    runner = TestRunner(results_dir=cfg.get("results_dir"))
    reporter = Reporter(console)

    try:
        data1 = runner.load_result(run1)
        data2 = runner.load_result(run2)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    reporter.report_comparison(data1, data2)


@main.command()
def init() -> None:
    """Initialize AgentTest configuration and directory structure."""
    config_dir = init_config()
    console.print(f"[green]AgentTest initialized![/green]")
    console.print(f"  Config dir: {config_dir}")
    console.print(f"  Results dir: {config_dir / 'results'}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Create a test YAML file (see 'agenttest --help' for format)")
    console.print("  2. Set ANTHROPIC_API_KEY for AI-powered assertions")
    console.print("  3. Run: agenttest run your_tests.yaml")


@main.command()
@click.argument("path", type=click.Path(exists=True))
def validate(path: str) -> None:
    """Validate a test YAML file without running it."""
    try:
        suites = load_test_suites(path)
        for suite in suites:
            console.print(f"[green]OK[/green] {suite.name}: {len(suite.tests)} test(s)")
            for test in suite.tests:
                n_expect = len(test.expectations)
                console.print(f"  - {test.name} ({n_expect} expectation(s))")
    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        sys.exit(1)

    console.print()
    console.print("[green]All test files are valid.[/green]")


if __name__ == "__main__":
    main()
