[English](README.md) | [中文](README_CN.md)

# AgentTest

AI 智能体测试框架 -- 使用 YAML 定义测试，通过 AI 驱动的断言进行评估，追踪回归问题。

## 安装

```bash
pip install agent-test
```

或从源码安装：

```bash
git clone https://github.com/Jaxz714/agent-test.git
cd agent-test
pip install -e .
```

## 快速开始

### 1. 创建测试文件

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

### 2. 运行测试

```bash
# 运行单个测试文件
agenttest run tests/basic_tests.yaml

# 运行目录下的所有测试
agenttest run tests/

# 按名称运行指定测试套件
agenttest run tests/ --suite "greeting"

# 以详细输出模式运行
agenttest run tests/basic_tests.yaml -v
```

### 3. 查看结果

```bash
# 列出所有已保存的运行记录
agenttest report

# 比较两次运行记录以检测回归问题
agenttest compare 20260531_143000 20260531_150000
```

## 评估类型

| 类型 | 描述 | 参数 |
|------|------|------|
| `exact` | 精确字符串匹配 | `value` |
| `contains` | 不区分大小写的子串匹配 | `value` |
| `not_contains` | 不应包含指定内容 | `value` |
| `regex` | 正则表达式匹配 | `pattern` |
| `length` | 检查输出长度 | `min`、`max` |
| `ai_judge` | AI 驱动的评估 | `criteria` |
| `semantic` | 语义相似度 | `value`、`threshold` |
| `starts_with` | 以指定字符串开头 | `value` |
| `ends_with` | 以指定字符串结尾 | `value` |

## AI 驱动的断言

`ai_judge` 评估类型使用 Claude 来评估智能体的输出是否满足指定标准。这对于无法通过简单模式匹配表达的主观或复杂检查非常有用。

```yaml
tests:
  - name: "Code generation"
    input: "Write a Python function to reverse a string"
    expect:
      - type: ai_judge
        criteria: "Should contain valid Python code with a function definition"
```

要使用 AI 评估功能，请设置你的 Anthropic API 密钥：

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## 智能体类型

### CLI 智能体

测试以命令行程序运行的智能体：

```yaml
agent:
  type: cli
  command: "python my_agent.py"
```

### API 智能体

测试通过 HTTP API 访问的智能体：

```yaml
agent:
  type: api
  endpoint: "http://localhost:8000/chat"
  headers:
    Authorization: "Bearer your-token"
```

## 配置

在 `~/.agenttest/config.yaml` 创建配置文件：

```yaml
model: "claude-sonnet-4-20250514"
results_dir: "~/.agenttest/results"
timeout: 60
evaluation:
  ai_judge_model: "claude-sonnet-4-20250514"
  semantic_threshold: 0.7
```

或在工作目录中使用项目级别的 `agenttest.yaml` 配置文件。

## CLI 命令

| 命令 | 描述 |
|------|------|
| `agenttest run <path>` | 运行测试套件 |
| `agenttest report` | 列出已保存的运行记录 |
| `agenttest compare <run1> <run2>` | 比较两次运行记录 |
| `agenttest validate <path>` | 验证测试 YAML 文件 |
| `agenttest init` | 初始化配置 |

## 许可证

MIT License - Copyright (c) 2026 Jaxz714
