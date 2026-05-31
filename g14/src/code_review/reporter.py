"""报告生成器"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import AnalysisReport, FileAnalysisResult, Issue
from .rules import RuleCategory, Severity


SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🟢",
    Severity.INFO: "🔵",
}

SEVERITY_LABEL = {
    Severity.CRITICAL: "严重",
    Severity.HIGH: "高",
    Severity.MEDIUM: "中",
    Severity.LOW: "低",
    Severity.INFO: "信息",
}

CATEGORY_LABEL = {
    RuleCategory.BUG: "Bug",
    RuleCategory.CODE_SMELL: "代码异味",
    RuleCategory.SECURITY: "安全漏洞",
    RuleCategory.STYLE: "代码风格",
    RuleCategory.PERFORMANCE: "性能问题",
}


class ReportGenerator:
    """报告生成器基类"""

    def generate(self, report: AnalysisReport, output_path: Optional[str] = None) -> str:
        """生成报告"""
        raise NotImplementedError

    def save(self, content: str, output_path: str) -> None:
        """保存报告到文件"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class JSONReporter(ReportGenerator):
    """JSON 报告生成器"""

    def generate(self, report: AnalysisReport, output_path: Optional[str] = None) -> str:
        """生成 JSON 格式报告"""
        report_data = report.to_dict()
        report_data["generated_at"] = datetime.now().isoformat()

        json_content = json.dumps(report_data, ensure_ascii=False, indent=2)

        if output_path:
            self.save(json_content, output_path)

        return json_content


class MarkdownReporter(ReportGenerator):
    """Markdown 报告生成器"""

    def _format_summary(self, report: AnalysisReport) -> str:
        """格式化摘要部分"""
        summary = report.summary
        lines = [
            "# 代码审查报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 审查摘要",
            "",
            "| 指标 | 数量 |",
            "|------|------|",
            f"| 总文件数 | {summary.total_files} |",
            f"| 有问题的文件 | {summary.files_with_issues} |",
            f"| 总问题数 | {summary.total_issues} |",
            "",
            "### 问题分布",
            "",
            "| 严重程度 | 数量 |",
            "|----------|------|",
            f"| {SEVERITY_EMOJI[Severity.CRITICAL]} 严重 | {summary.critical_count} |",
            f"| {SEVERITY_EMOJI[Severity.HIGH]} 高 | {summary.high_count} |",
            f"| {SEVERITY_EMOJI[Severity.MEDIUM]} 中 | {summary.medium_count} |",
            f"| {SEVERITY_EMOJI[Severity.LOW]} 低 | {summary.low_count} |",
            "",
            "### Token 使用统计",
            "",
            f"- 输入 Token: {summary.total_prompt_tokens}",
            f"- 输出 Token: {summary.total_completion_tokens}",
            f"- 总 Token: {summary.total_prompt_tokens + summary.total_completion_tokens}",
            f"- 总耗时: {summary.total_latency_ms / 1000:.2f} 秒",
            "",
        ]
        return "\n".join(lines)

    def _format_issue(self, issue: Issue) -> str:
        """格式化单个问题"""
        lines = []

        severity_emoji = SEVERITY_EMOJI.get(issue.severity, "⚪")
        severity_label = SEVERITY_LABEL.get(issue.severity, issue.severity.value)
        category_label = CATEGORY_LABEL.get(issue.category, issue.category.value)

        lines.append(f"#### {severity_emoji} [{severity_label}] {category_label}: {issue.message}")
        lines.append("")
        lines.append(f"- **文件**: `{issue.file_path}`")
        lines.append(f"- **行号**: {issue.line}")
        if issue.rule_id:
            lines.append(f"- **规则**: `{issue.rule_id}`")
        lines.append("")

        if issue.suggestion:
            lines.append("**修复建议**:")
            lines.append("")
            lines.append(f"> {issue.suggestion}")
            lines.append("")

        if issue.code_snippet:
            lines.append("**相关代码**:")
            lines.append("")
            lines.append("```")
            lines.append(issue.code_snippet)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _format_file_result(self, file_result: FileAnalysisResult) -> str:
        """格式化单个文件的分析结果"""
        lines = []

        lines.append(f"## 📄 {file_result.file_path}")
        lines.append("")
        lines.append(f"- **语言**: {file_result.language}")
        lines.append(f"- **问题数**: {len(file_result.issues)}")
        lines.append("")

        if file_result.error:
            lines.append(f"⚠️ **错误**: {file_result.error}")
            lines.append("")
            return "\n".join(lines)

        if not file_result.issues:
            lines.append("✅ 未发现问题")
            lines.append("")
            return "\n".join(lines)

        severity_counts = {
            Severity.CRITICAL: file_result.critical_count,
            Severity.HIGH: file_result.high_count,
            Severity.MEDIUM: file_result.medium_count,
            Severity.LOW: file_result.low_count,
        }

        lines.append("### 问题统计")
        lines.append("")
        for severity, count in severity_counts.items():
            if count > 0:
                lines.append(f"- {SEVERITY_EMOJI[severity]} {SEVERITY_LABEL[severity]}: {count}")
        lines.append("")

        lines.append("### 问题详情")
        lines.append("")
        for issue in sorted(file_result.issues, key=lambda x: (
            list(Severity).index(x.severity),
            x.line
        )):
            lines.append(self._format_issue(issue))

        return "\n".join(lines)

    def _format_errors(self, errors: List[str]) -> str:
        """格式化错误信息"""
        if not errors:
            return ""

        lines = [
            "## ⚠️ 错误信息",
            "",
        ]
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")
        return "\n".join(lines)

    def generate(self, report: AnalysisReport, output_path: Optional[str] = None) -> str:
        """生成 Markdown 格式报告"""
        parts = []

        parts.append(self._format_summary(report))

        parts.append("## 详细结果")
        parts.append("")

        for file_result in sorted(report.files, key=lambda x: (
            -len(x.issues),
            x.file_path
        )):
            parts.append(self._format_file_result(file_result))

        errors_section = self._format_errors(report.errors)
        if errors_section:
            parts.append(errors_section)

        md_content = "\n".join(parts)

        if output_path:
            self.save(md_content, output_path)

        return md_content


class ConsoleReporter(ReportGenerator):
    """控制台报告生成器"""

    def generate(self, report: AnalysisReport, output_path: Optional[str] = None) -> str:
        """生成控制台格式报告"""
        summary = report.summary
        lines = []

        lines.append("=" * 60)
        lines.append("📋 代码审查结果")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"总文件数: {summary.total_files}")
        lines.append(f"有问题的文件: {summary.files_with_issues}")
        lines.append(f"总问题数: {summary.total_issues}")
        lines.append("")

        if summary.total_issues > 0:
            lines.append("问题分布:")
            lines.append(f"  {SEVERITY_EMOJI[Severity.CRITICAL]} 严重: {summary.critical_count}")
            lines.append(f"  {SEVERITY_EMOJI[Severity.HIGH]} 高: {summary.high_count}")
            lines.append(f"  {SEVERITY_EMOJI[Severity.MEDIUM]} 中: {summary.medium_count}")
            lines.append(f"  {SEVERITY_EMOJI[Severity.LOW]} 低: {summary.low_count}")
            lines.append("")

        for file_result in report.files:
            if file_result.has_issues:
                lines.append(f"📄 {file_result.file_path} ({len(file_result.issues)} 个问题)")
                for issue in sorted(file_result.issues, key=lambda x: list(Severity).index(x.severity)):
                    severity_emoji = SEVERITY_EMOJI.get(issue.severity, "⚪")
                    lines.append(f"  {severity_emoji} L{issue.line}: {issue.message}")
                lines.append("")

        if report.errors:
            lines.append("⚠️ 错误:")
            for error in report.errors:
                lines.append(f"  - {error}")
            lines.append("")

        lines.append(f"⏱️  总耗时: {summary.total_latency_ms / 1000:.2f} 秒")
        lines.append("=" * 60)

        console_content = "\n".join(lines)

        if output_path:
            self.save(console_content, output_path)

        return console_content


def get_reporter(format_type: str) -> ReportGenerator:
    """根据格式类型获取报告生成器"""
    reporters = {
        "json": JSONReporter(),
        "markdown": MarkdownReporter(),
        "md": MarkdownReporter(),
        "console": ConsoleReporter(),
    }

    reporter = reporters.get(format_type.lower())
    if not reporter:
        raise ValueError(f"不支持的报告格式: {format_type}")

    return reporter
