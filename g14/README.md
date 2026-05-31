# code-review-cli

本地代码审查 CLI 工具，使用 Python + Click + llama-cpp-python 构建，调用本地大模型分析代码质量。

## 功能特性

- 🔍 **智能代码分析**：基于本地 LLM 模型，分析代码中的潜在 bug、代码异味和安全漏洞
- 📁 **多源输入支持**：支持单个文件或整个目录的递归扫描
- 📋 **规则集配置**：内置 PEP8（Python）和 ESLint（JavaScript/TypeScript）规则集
- 📊 **多种输出格式**：支持 JSON、Markdown 和控制台三种报告格式
- 🚀 **本地隐私保护**：所有分析在本地完成，代码不会上传到外部服务器
- ⚙️ **高度可配置**：支持自定义忽略模式、模型参数、规则集等

## 支持的语言

- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)

## 安装

### 前置要求

- Python 3.9+
- C/C++ 编译器（用于编译 llama-cpp-python）

### 安装步骤

1. 克隆或下载项目代码
2. 安装依赖：

```bash
pip install -r requirements.txt
```

或者使用 pip 安装：

```bash
pip install -e .
```

### 安装 llama-cpp-python（可选）

如果你需要 GPU 加速或特定配置，可以手动安装 llama-cpp-python：

```bash
# CPU 版本
pip install llama-cpp-python

# NVIDIA GPU 版本（CUDA）
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# Apple Silicon 版本
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```

## 快速开始

### 1. 生成配置文件（可选）

```bash
code-review init-config
```

### 2. 查看可用规则

```bash
# 查看所有规则
code-review list-rules

# 查看 PEP8 规则
code-review list-rules -r pep8

# 导出规则为 Markdown
code-review list-rules -f markdown -o rules.md
```

### 3. 运行代码审查

使用模拟模式（无需模型文件，用于测试）：

```bash
# 审查单个文件
code-review review path/to/file.py --mock

# 审查整个目录
code-review review path/to/project --mock

# 输出 JSON 报告
code-review review path/to/project --mock -f json -o report.json

# 输出 Markdown 报告
code-review review path/to/project --mock -f markdown -o report.md
```

使用真实模型：

```bash
code-review review path/to/project -m /path/to/model.gguf
```

## 命令详解

### review 命令

审查代码文件或目录。

```bash
code-review review [OPTIONS] TARGET
```

**参数：**

- `TARGET`: 要审查的文件或目录路径

**选项：**

- `-m, --model PATH`: LLM 模型文件路径 (.gguf 格式)
- `--mock`: 使用模拟 LLM 客户端（测试用）
- `-r, --ruleset TEXT`: 启用的规则集，可重复指定（默认: pep8, eslint）
- `-f, --format [json|markdown|md|console]`: 输出格式（默认: console）
- `-o, --output PATH`: 输出文件路径
- `-i, --ignore TEXT`: 忽略的文件模式（glob 格式），可重复指定
- `--n-ctx INTEGER`: 上下文窗口大小（默认: 4096）
- `--n-threads INTEGER`: 线程数（默认: 4）
- `--n-gpu-layers INTEGER`: GPU 层数量（默认: 0）
- `--temperature FLOAT`: 生成温度（默认: 0.1）
- `--max-tokens INTEGER`: 最大生成 token 数（默认: 2048）
- `--verbose`: 显示详细日志

### list-rules 命令

列出可用的审查规则。

```bash
code-review list-rules [OPTIONS]
```

**选项：**

- `-f, --format [json|markdown|md]`: 输出格式，不指定则输出到控制台
- `-r, --ruleset TEXT`: 显示指定规则集的规则，可重复指定

### init-config 命令

生成默认配置文件。

```bash
code-review init-config [OPTIONS]
```

**选项：**

- `-o, --output PATH`: 配置文件输出路径（默认: code-review-config.yaml）

## 规则集说明

### PEP8 规则集

包含 30+ 条 Python 代码规范规则，涵盖：

- 缩进规范（E101, E111）
- 空白字符（E201, E202, E225, E231）
- 空行规范（E301, E302）
- 导入规范（E401, E402）
- 行长度（E501）
- 语句规范（E701, E711, E712, E722）
- 导入检查（F401, F403）
- 变量使用（F811, F821, F841）
- 空白检查（W191, W291, W292, W293, W391, W503, W504）
- 已弃用特性（W601, W603）

### ESLint 规则集

包含 30+ 条 JavaScript/TypeScript 代码规范规则，涵盖：

- 变量使用（no-undef, no-unused-vars, no-use-before-define, no-redeclare）
- 调试代码（no-console, no-alert, no-debugger）
- 安全漏洞（no-eval, no-implied-eval, no-new-func, no-script-url）
- 比较规范（eqeqeq, no-eq-null）
- 代码简洁（no-extra-boolean-cast, no-extra-semi, no-empty, no-constant-condition）
- 代码风格（semi, quotes, indent, max-len, no-trailing-spaces, no-multiple-empty-lines, camelcase）
- 最佳实践（no-var, prefer-const, no-dupe-keys, no-dupe-args）

## 项目结构

```
code-review-cli/
├── src/
│   └── code_review/
│       ├── __init__.py          # 包初始化
│       ├── cli.py               # CLI 入口
│       ├── rules.py             # 规则集定义
│       ├── scanner.py           # 代码文件扫描器
│       ├── llm_client.py        # LLM 客户端封装
│       ├── analyzer.py          # 代码分析引擎
│       └── reporter.py          # 报告生成器
├── pyproject.toml               # 项目配置
├── requirements.txt             # 依赖列表
└── README.md                    # 项目文档
```

## 模块说明

### [rules.py](file:///e:/soloG/g14/src/code_review/rules.py)
定义了规则、规则集数据结构，以及内置的 PEP8 和 ESLint 规则。

### [scanner.py](file:///e:/soloG/g14/src/code_review/scanner.py)
负责扫描文件系统，识别支持的代码文件，自动忽略 .gitignore 和默认忽略模式。

### [llm_client.py](file:///e:/soloG/g14/src/code_review/llm_client.py)
封装 llama-cpp-python，提供统一的文本生成和 JSON 生成接口，包含 Mock 客户端用于测试。

### [analyzer.py](file:///e:/soloG/g14/src/code_review/analyzer.py)
核心分析引擎，构建提示词、调用 LLM、解析响应、生成分析报告。

### [reporter.py](file:///e:/soloG/g14/src/code_review/reporter.py)
报告生成器，支持 JSON、Markdown 和控制台三种输出格式。

### [cli.py](file:///e:/soloG/g14/src/code_review/cli.py)
命令行接口，基于 Click 构建，提供 review、list-rules、init-config 三个子命令。

## 模型推荐

以下是一些适合代码审查的开源 LLM 模型（需要转换为 GGUF 格式）：

- CodeLlama
- StarCoder
- CodeLlama-Python
- DeepSeek-Coder
- CodeLlama-Instruct

你可以在 Hugging Face 上下载这些模型的 GGUF 版本。

## 示例

### 审查 Python 文件

```bash
code-review review my_script.py --mock -f markdown -o report.md
```

### 审查 JavaScript 项目

```bash
code-review review ./my-js-project -m ./models/codellama-7b.gguf -f json -o report.json
```

### 在 CI/CD 中使用

```yaml
# .github/workflows/code-review.yml
name: Code Review
on: [push, pull_request]

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: code-review review . --mock -f json -o report.json
      - uses: actions/upload-artifact@v4
        with:
          name: code-review-report
          path: report.json
```

## 开发指南

### 运行测试

```bash
# 安装开发依赖
pip install pytest

# 运行测试
pytest tests/
```

### 添加新规则

在 `rules.py` 中添加新的规则定义：

```python
MY_RULES: Dict[str, Rule] = {
    "MY001": Rule(
        id="MY001",
        name="my-custom-rule",
        description="自定义规则描述",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
}
```

### 自定义报告格式

继承 `ReportGenerator` 基类，实现 `generate` 方法：

```python
class HTMLReporter(ReportGenerator):
    def generate(self, report: AnalysisReport, output_path: Optional[str] = None) -> str:
        # 实现 HTML 报告生成逻辑
        pass
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
