"""代码分析引擎"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .fixer import FixPatch
from .llm_client import LLMClient
from .rules import Rule, RuleCategory, Severity, get_rules_for_language
from .scanner import CodeFile


@dataclass
class Issue:
    """代码问题"""
    file_path: str
    line: int
    severity: Severity
    category: RuleCategory
    message: str
    suggestion: str = ""
    rule_id: Optional[str] = None
    code_snippet: str = ""
    original_code: str = ""
    fixed_code: str = ""
    fix_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
            "code_snippet": self.code_snippet,
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "fix_confidence": self.fix_confidence,
        }

    def to_patch(self) -> Optional[FixPatch]:
        """转换为修复补丁"""
        if not self.original_code or not self.fixed_code:
            return None
        return FixPatch(
            file_path=self.file_path,
            issue_line=self.line,
            original_code=self.original_code,
            fixed_code=self.fixed_code,
            description=self.message,
            confidence=self.fix_confidence,
        )


@dataclass
class FileAnalysisResult:
    """单个文件的分析结果"""
    file_path: str
    language: str
    issues: List[Issue] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.LOW)

    def get_patches(self) -> List[FixPatch]:
        """获取所有可应用的修复补丁"""
        patches = []
        for issue in self.issues:
            patch = issue.to_patch()
            if patch:
                patches.append(patch)
        return patches

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "issues": [issue.to_dict() for issue in self.issues],
            "patches": [patch.to_dict() for patch in self.get_patches()],
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "summary": {
                "total": len(self.issues),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "fixable": len(self.get_patches()),
            }
        }


@dataclass
class AnalysisSummary:
    """分析摘要"""
    total_files: int = 0
    files_with_issues: int = 0
    total_issues: int = 0
    total_fixable_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "files_with_issues": self.files_with_issues,
            "total_issues": self.total_issues,
            "total_fixable_issues": self.total_fixable_issues,
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "low": self.low_count,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_latency_ms": self.total_latency_ms,
        }


@dataclass
class AnalysisReport:
    """完整的分析报告"""
    files: List[FileAnalysisResult] = field(default_factory=list)
    summary: AnalysisSummary = field(default_factory=AnalysisSummary)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "files": [f.to_dict() for f in self.files],
            "errors": self.errors,
        }


class CodeAnalyzer:
    """代码分析引擎"""

    def __init__(
        self,
        llm_client: LLMClient,
        enabled_rulesets: Optional[List[str]] = None,
        custom_rules: Optional[List[Rule]] = None,
        generate_fixes: bool = True,
    ) -> None:
        self.llm_client = llm_client
        self.enabled_rulesets = enabled_rulesets or ["pep8", "eslint"]
        self.custom_rules = custom_rules or []
        self.generate_fixes = generate_fixes

    def _build_system_prompt(self, language: str, rules: List[Rule]) -> str:
        """构建系统提示词"""
        rule_descriptions = "\n".join(
            f"- [{rule.id}] {rule.name}: {rule.description} (严重程度: {rule.severity.value})"
            for rule in rules
        )

        fix_instructions = ""
        if self.generate_fixes:
            fix_instructions = """
对于每个问题，如果可以提供自动修复，请额外提供：
- original_code: 问题所在的原始代码片段（完整的几行代码）
- fixed_code: 修复后的代码片段
- fix_confidence: 修复的置信度 (0.0-1.0)

确保 original_code 可以精确匹配到文件中的代码（包括缩进）。
"""

        json_format = self._get_json_format()

        return f"""你是一个专业的代码审查助手，负责分析 {language} 代码的质量。

请根据以下规则集检查代码：
{rule_descriptions}

你的任务是：
1. 识别潜在的 Bug 和逻辑错误
2. 发现代码异味（如重复代码、过长函数、命名不当等）
3. 检测安全漏洞（如 SQL 注入、XSS、代码注入等）
4. 指出不符合编码规范的地方
{fix_instructions}

对于每个问题，请提供：
- 问题所在的行号
- 问题的严重程度（critical/high/medium/low/info）
- 问题的类别（bug/code_smell/security/style/performance）
- 问题的详细描述
- 修复建议
{'- original_code: 原始代码片段' if self.generate_fixes else ''}
{'- fixed_code: 修复后的代码片段' if self.generate_fixes else ''}
{'- fix_confidence: 修复置信度 (0.0-1.0)' if self.generate_fixes else ''}

{json_format}
"""

    def _get_json_format(self) -> str:
        """获取 JSON 格式说明"""
        if self.generate_fixes:
            return """请严格按照 JSON 格式输出，格式如下：
{
  "issues": [
    {
      "line": 1,
      "severity": "high",
      "category": "bug",
      "message": "问题描述",
      "suggestion": "修复建议",
      "rule_id": "规则ID",
      "original_code": "原始代码\\n第二行代码",
      "fixed_code": "修复后的代码\\n第二行代码",
      "fix_confidence": 0.9
    }
  ]
}

如果没有发现问题，请返回：
{
  "issues": []
}"""
        else:
            return """请严格按照 JSON 格式输出，格式如下：
{
  "issues": [
    {
      "line": 1,
      "severity": "high",
      "category": "bug",
      "message": "问题描述",
      "suggestion": "修复建议",
      "rule_id": "规则ID"
    }
  ]
}

如果没有发现问题，请返回：
{
  "issues": []
}"""

    def _build_user_prompt(self, code_file: CodeFile) -> str:
        """构建用户提示词"""
        return f"""以下是文件 `{code_file.path}` 的代码：

```
{code_file.content}
```

请分析上述代码，找出所有潜在的问题。"""

    def _parse_llm_response(
        self,
        response: Dict[str, Any],
        code_file: CodeFile,
    ) -> List[Issue]:
        """解析 LLM 响应为 Issue 列表"""
        issues = []
        lines = code_file.get_lines()

        raw_issues = response.get("issues", [])
        for raw_issue in raw_issues:
            try:
                line = int(raw_issue.get("line", 0))
                severity = Severity(raw_issue.get("severity", "low"))
                category = RuleCategory(raw_issue.get("category", "code_smell"))
                message = raw_issue.get("message", "")
                suggestion = raw_issue.get("suggestion", "")
                rule_id = raw_issue.get("rule_id")
                original_code = raw_issue.get("original_code", "")
                fixed_code = raw_issue.get("fixed_code", "")
                fix_confidence = float(raw_issue.get("fix_confidence", 0.0))

                code_snippet = ""
                if 1 <= line <= len(lines):
                    start = max(0, line - 3)
                    end = min(len(lines), line + 2)
                    code_snippet = "\n".join(lines[start:end])

                issues.append(Issue(
                    file_path=str(code_file.path),
                    line=line,
                    severity=severity,
                    category=category,
                    message=message,
                    suggestion=suggestion,
                    rule_id=rule_id,
                    code_snippet=code_snippet,
                    original_code=original_code,
                    fixed_code=fixed_code,
                    fix_confidence=fix_confidence,
                ))
            except (ValueError, TypeError) as e:
                print(f"警告: 解析问题时出错: {e}")
                continue

        return issues

    def _get_expected_json_schema(self) -> Dict[str, Any]:
        """获取期望的 JSON 结构示例"""
        if self.generate_fixes:
            return {
                "issues": [
                    {
                        "line": 1,
                        "severity": "high",
                        "category": "bug",
                        "message": "问题描述",
                        "suggestion": "修复建议",
                        "rule_id": "E722",
                        "original_code": "原始代码",
                        "fixed_code": "修复后的代码",
                        "fix_confidence": 0.9
                    }
                ]
            }
        return {
            "issues": [
                {
                    "line": 1,
                    "severity": "high",
                    "category": "bug",
                    "message": "问题描述",
                    "suggestion": "修复建议",
                    "rule_id": "E722"
                }
            ]
        }

    def analyze_file(self, code_file: CodeFile) -> FileAnalysisResult:
        """分析单个文件"""
        result = FileAnalysisResult(
            file_path=str(code_file.path),
            language=code_file.language,
        )

        try:
            rules = get_rules_for_language(code_file.language)
            rules.extend(self.custom_rules)

            if not rules:
                result.error = f"没有找到语言 {code_file.language} 的规则"
                return result

            system_prompt = self._build_system_prompt(code_file.language, rules)
            user_prompt = self._build_user_prompt(code_file)

            parsed_response = self.llm_client.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expected_schema=self._get_expected_json_schema(),
            )

            result.prompt_tokens = 0
            result.completion_tokens = 0
            result.latency_ms = 0

            result.issues = self._parse_llm_response(parsed_response, code_file)

        except Exception as e:
            result.error = f"分析文件时出错: {str(e)}"

        return result

    def analyze_files(self, code_files: List[CodeFile]) -> AnalysisReport:
        """分析多个文件"""
        report = AnalysisReport()

        for code_file in code_files:
            file_result = self.analyze_file(code_file)
            report.files.append(file_result)

            if file_result.error:
                report.errors.append(file_result.error)
                continue

            report.summary.total_prompt_tokens += file_result.prompt_tokens
            report.summary.total_completion_tokens += file_result.completion_tokens
            report.summary.total_latency_ms += file_result.latency_ms

            if file_result.has_issues:
                report.summary.files_with_issues += 1
                report.summary.total_issues += len(file_result.issues)
                report.summary.total_fixable_issues += len(file_result.get_patches())
                report.summary.critical_count += file_result.critical_count
                report.summary.high_count += file_result.high_count
                report.summary.medium_count += file_result.medium_count
                report.summary.low_count += file_result.low_count

        report.summary.total_files = len(code_files)

        return report
