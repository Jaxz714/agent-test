# AgentTest Examples

This directory contains example test suites to help you get started with AgentTest.

## Files

- `basic_tests.yaml` - Simple test suite demonstrating all evaluation types

## Running Examples

```bash
# Run the basic tests
agenttest run examples/basic_tests.yaml

# Validate the test file without running
agenttest validate examples/basic_tests.yaml
```

## Creating Your Own Tests

1. Copy `basic_tests.yaml` as a starting point
2. Update the `agent` section with your agent's details
3. Add test cases with appropriate expectations
4. Run with `agenttest run your_tests.yaml`

## Agent Types

### CLI Agent
```yaml
agent:
  type: cli
  command: "python my_agent.py"
```

### API Agent
```yaml
agent:
  type: api
  endpoint: "http://localhost:8000/chat"
  headers:
    Authorization: "Bearer your-token"
```
