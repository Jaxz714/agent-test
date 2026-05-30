[English](README.md) | [中文](README_CN.md)

# AgentTest

Testing framework for AI agents -- define tests in YAML, evaluate with AI-powered assertions, track regressions.

## Installation

```bash
pip install agent-test
```

Or install from source:

```bash
git clone https://github.com/Jaxz714/agent-test.git
cd agent-test
pip install -e .
```

## Quick Start

### 1. Create a test file

```yaml
name: "My Agent Tests"
description: "Tests for my chatbot agent"
agent:
  type: cli
  command: "python my_agent.py"

tests:
  - name: "Basic greeting"
    input: "Hello, how are you?"
    expect:
      - type: contains
        value: "hello"
      - type: ai_judge
        criteria: "Response should be friendly and welcoming"
      - type: length
        max: 500
```

### 2. Run the tests

```bash
# Run a single test file
agenttest run tests/basic_tests.yaml

# Run all tests in a directory
agenttest run tests/

# Run specific suite by name
agenttest run tests/ --suite "greeting"

# Run with verbose output
agenttest run tests/basic_tests.yaml -v
```

### 3. View results

```bash
# List all saved runs
agenttest report

# Compare two runs for regressions
agenttest compare 20260531_143000 20260531_150000
```

## Evaluation Types

| Type | Description | Parameters |
|------|-------------|------------|
| `exact` | Exact string match | `value` |
| `contains` | Case-insensitive substring match | `value` |
| `not_contains` | Should not contain | `value` |
| `regex` | Regular expression match | `pattern` |
| `length` | Check output length | `min`, `max` |
| `ai_judge` | AI-powered evaluation | `criteria` |
| `semantic` | Semantic similarity | `value`, `threshold` |
| `starts_with` | Starts with string | `value` |
| `ends_with` | Ends with string | `value` |

## AI-Powered Assertions

The `ai_judge` evaluation type uses Claude to evaluate whether an agent's output meets specified criteria. This is useful for subjective or complex checks that can't be expressed with simple pattern matching.

```yaml
tests:
  - name: "Code generation"
    input: "Write a Python function to reverse a string"
    expect:
      - type: ai_judge
        criteria: "Should contain valid Python code with a function definition"
```

To use AI judge, set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Agent Types

### CLI Agent

Test agents that run as command-line programs:

```yaml
agent:
  type: cli
  command: "python my_agent.py"
```

### API Agent

Test agents accessible via HTTP API:

```yaml
agent:
  type: api
  endpoint: "http://localhost:8000/chat"
  headers:
    Authorization: "Bearer your-token"
```

## Configuration

Create a config file at `~/.agenttest/config.yaml`:

```yaml
model: "claude-sonnet-4-20250514"
results_dir: "~/.agenttest/results"
timeout: 60
evaluation:
  ai_judge_model: "claude-sonnet-4-20250514"
  semantic_threshold: 0.7
```

Or use a project-level `agenttest.yaml` in your working directory.

## CLI Commands

| Command | Description |
|---------|-------------|
| `agenttest run <path>` | Run test suites |
| `agenttest report` | List saved runs |
| `agenttest compare <run1> <run2>` | Compare two runs |
| `agenttest validate <path>` | Validate test YAML |
| `agenttest init` | Initialize configuration |

## License

MIT License - Copyright (c) 2026 Jaxz714
