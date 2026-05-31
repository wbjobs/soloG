"""CLI 入口"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

import click

from .analyzer import CodeAnalyzer
from .llm_client import LLMClient, LLMConfig, MockLLMClient
from .reporter import get_reporter
from .scanner import CodeScanner
from . import __version__


def _get_llm_client(
    model_path: Optional[str],
    use_mock: bool,
    n_ctx: int,
    n_threads: int,
    n_gpu_layers: int,
    temperature: float,
    max_tokens: int,
    verbose: bool,
) -> LLMClient:
    """获取 LLM 客户端"""
    if use_mock:
        return MockLLMClient()

    if not model_path:
        raise click.UsageError(
            "请指定模型路径 (--model) 或使用模拟模式 (--mock)"
        )

    config = LLMConfig(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        temperature=temperature,
        max_tokens=max_tokens,
        verbose=verbose,
    )
    return LLMClient(config)


@click.group()
@click.version_option(__version__, "-v", "--version")
def main() -> None:
    """本地代码审查 CLI 工具"""
    pass


@main.command()
@click.argument(
    "target",
    type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True),
)
@click.option(
    "--model",
    "-m",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True),
    help="LLM 模型文件路径 (.gguf)",
)
@click.option(
    "--mock",
    is_flag=True,
    default=False,
    help="使用模拟 LLM 客户端（测试用）",
)
@click.option(
    "--ruleset",
    "-r",
    multiple=True,
    default=["pep8", "eslint"],
    help="启用的规则集，可重复指定",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "markdown", "md", "console"], case_sensitive=False),
    default="console",
    help="输出格式",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    help="输出文件路径",
)
@click.option(
    "--ignore",
    "-i",
    multiple=True,
    help="忽略的文件模式（glob 格式），可重复指定",
)
@click.option(
    "--n-ctx",
    type=int,
    default=4096,
    help="上下文窗口大小",
)
@click.option(
    "--n-threads",
    type=int,
    default=4,
    help="线程数",
)
@click.option(
    "--n-gpu-layers",
    type=int,
    default=0,
    help="GPU 层数量",
)
@click.option(
    "--temperature",
    type=float,
    default=0.1,
    help="生成温度",
)
@click.option(
    "--max-tokens",
    type=int,
    default=2048,
    help="最大生成 token 数",
)
@click.option(
    "--with-fixes/--no-fixes",
    is_flag=True,
    default=True,
    help="是否生成修复建议",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="显示详细日志",
)
def review(
    target: str,
    model: Optional[str],
    mock: bool,
    ruleset: List[str],
    output_format: str,
    output: Optional[str],
    ignore: List[str],
    with_fixes: bool,
    n_ctx: int,
    n_threads: int,
    n_gpu_layers: int,
    temperature: float,
    max_tokens: int,
    verbose: bool,
) -> None:
    """审查代码文件或目录"""
    try:
        if verbose:
            click.echo(f"🔍 开始扫描: {target}")

        scanner = CodeScanner(extra_ignore_patterns=list(ignore))
        scan_result = scanner.scan(target)

        if scan_result.errors:
            for error in scan_result.errors:
                click.echo(f"⚠️  {error}", err=True)

        if not scan_result.files:
            click.echo("❌ 没有找到可分析的文件")
            sys.exit(1)

        if verbose:
            click.echo(f"📁 找到 {scan_result.total_files} 个文件，"
                       f"共 {scan_result.total_size / 1024:.1f} KB")

        llm_client = _get_llm_client(
            model_path=model,
            use_mock=mock,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=verbose,
        )

        analyzer = CodeAnalyzer(
            llm_client=llm_client,
            enabled_rulesets=list(ruleset),
            generate_fixes=with_fixes,
        )

        if verbose:
            click.echo("🤖 开始分析代码...")

        with click.progressbar(scan_result.files, label="分析中") as files:
            report = analyzer.analyze_files(list(files))

        reporter = get_reporter(output_format)
        report_content = reporter.generate(report, output)

        if not output:
            click.echo(report_content)

        if output:
            click.echo(f"✅ 报告已保存到: {output}")

        if report.summary.total_issues > 0:
            click.echo(f"\n💡 发现 {report.summary.total_fixable_issues} 个可自动修复的问题")
            click.echo("   运行 'code-review fix' 来应用修复")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "markdown", "md"], case_sensitive=False),
    default=None,
    help="输出格式，不指定则输出到控制台",
)
@click.option(
    "--ruleset",
    "-r",
    multiple=True,
    help="显示指定规则集的规则，不指定则显示所有",
)
def list_rules(output_format: Optional[str], ruleset: List[str]) -> None:
    """列出可用的审查规则"""
    from .rules import get_all_rulesets, Rule, Severity, RuleCategory

    rulesets = get_all_rulesets()

    if ruleset:
        rulesets = {name: rs for name, rs in rulesets.items() if name in ruleset}

    if not rulesets:
        click.echo("❌ 没有找到规则集")
        sys.exit(1)

    if output_format in ("json",):
        import json
        result = {}
        for name, rs in rulesets.items():
            result[name] = {
                "description": rs.description,
                "rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "description": rule.description,
                        "category": rule.category.value,
                        "severity": rule.severity.value,
                        "language": rule.language,
                    }
                    for rule in rs.get_enabled_rules()
                ],
            }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif output_format in ("markdown", "md"):
        lines = ["# 审查规则列表", ""]
        for name, rs in rulesets.items():
            lines.append(f"## {name}")
            lines.append("")
            lines.append(rs.description)
            lines.append("")
            lines.append("| ID | 名称 | 描述 | 类别 | 严重程度 | 语言 |")
            lines.append("|----|------|------|------|----------|------|")
            for rule in sorted(rs.get_enabled_rules(), key=lambda r: r.id):
                lines.append(
                    f"| {rule.id} | {rule.name} | {rule.description} | "
                    f"{rule.category.value} | {rule.severity.value} | {rule.language} |"
                )
            lines.append("")
        click.echo("\n".join(lines))
    else:
        for name, rs in rulesets.items():
            click.echo(f"\n📋 {name}: {rs.description}")
            click.echo("-" * 60)
            for rule in sorted(rs.get_enabled_rules(), key=lambda r: r.id):
                severity_emoji = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢",
                    Severity.INFO: "🔵",
                }.get(rule.severity, "⚪")
                click.echo(
                    f"  {severity_emoji} [{rule.id}] {rule.name} - {rule.description}"
                )


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default="code-review-config.yaml",
    help="配置文件输出路径",
)
def init_config(output: str) -> None:
    """生成默认配置文件"""
    config_content = """# code-review-cli 配置文件

# LLM 模型配置
llm:
  # 模型文件路径 (.gguf 格式)
  model_path: ./models/code-review-model.gguf
  # 上下文窗口大小
  n_ctx: 4096
  # 线程数
  n_threads: 4
  # GPU 层数量 (0 表示使用 CPU)
  n_gpu_layers: 0
  # 生成温度
  temperature: 0.1
  # 最大生成 token 数
  max_tokens: 2048
  # 显示详细日志
  verbose: false

# 规则集配置
rulesets:
  # 启用的规则集
  enabled:
    - pep8
    - eslint
  # 自定义规则
  custom: []

# 扫描配置
scanner:
  # 忽略的文件模式
  ignore_patterns:
    - .git/
    - __pycache__/
    - node_modules/
    - dist/
    - build/
    - "*.min.js"
  # 最大文件大小 (字节)
  max_file_size: 10485760

# 输出配置
output:
  # 默认输出格式: console, json, markdown
  default_format: console
  # 默认输出目录
  output_dir: ./reports
"""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(config_content, encoding="utf-8")
    click.echo(f"✅ 配置文件已生成: {output}")


@main.command()
@click.argument(
    "target",
    type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True),
)
@click.option(
    "--model",
    "-m",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True),
    help="LLM 模型文件路径 (.gguf)",
)
@click.option(
    "--mock",
    is_flag=True,
    default=False,
    help="使用模拟 LLM 客户端（测试用）",
)
@click.option(
    "--ruleset",
    "-r",
    multiple=True,
    default=["pep8", "eslint"],
    help="启用的规则集，可重复指定",
)
@click.option(
    "--ignore",
    "-i",
    multiple=True,
    help="忽略的文件模式（glob 格式），可重复指定",
)
@click.option(
    "--preview",
    is_flag=True,
    default=False,
    help="只预览修复补丁，不应用",
)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="交互式选择要应用的补丁",
)
@click.option(
    "--no-backup",
    is_flag=True,
    default=False,
    help="不创建文件备份",
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.0,
    help="只应用置信度大于等于此值的修复 (0.0-1.0)",
)
@click.option(
    "--n-ctx",
    type=int,
    default=4096,
    help="上下文窗口大小",
)
@click.option(
    "--n-threads",
    type=int,
    default=4,
    help="线程数",
)
@click.option(
    "--n-gpu-layers",
    type=int,
    default=0,
    help="GPU 层数量",
)
@click.option(
    "--temperature",
    type=float,
    default=0.1,
    help="生成温度",
)
@click.option(
    "--max-tokens",
    type=int,
    default=2048,
    help="最大生成 token 数",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="显示详细日志",
)
def fix(
    target: str,
    model: Optional[str],
    mock: bool,
    ruleset: List[str],
    ignore: List[str],
    preview: bool,
    interactive: bool,
    no_backup: bool,
    min_confidence: float,
    n_ctx: int,
    n_threads: int,
    n_gpu_layers: int,
    temperature: float,
    max_tokens: int,
    verbose: bool,
) -> None:
    """分析并自动修复代码问题"""
    from .fixer import CodeFixer

    try:
        if verbose:
            click.echo(f"🔍 开始扫描: {target}")

        scanner = CodeScanner(extra_ignore_patterns=list(ignore))
        scan_result = scanner.scan(target)

        if scan_result.errors:
            for error in scan_result.errors:
                click.echo(f"⚠️  {error}", err=True)

        if not scan_result.files:
            click.echo("❌ 没有找到可分析的文件")
            sys.exit(1)

        if verbose:
            click.echo(f"📁 找到 {scan_result.total_files} 个文件")

        llm_client = _get_llm_client(
            model_path=model,
            use_mock=mock,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=verbose,
        )

        analyzer = CodeAnalyzer(
            llm_client=llm_client,
            enabled_rulesets=list(ruleset),
            generate_fixes=True,
        )

        if verbose:
            click.echo("🤖 开始分析代码并生成修复...")

        with click.progressbar(scan_result.files, label="分析中") as files:
            report = analyzer.analyze_files(list(files))

        all_patches = []
        for file_result in report.files:
            patches = file_result.get_patches()
            patches = [p for p in patches if p.confidence >= min_confidence]
            all_patches.extend(patches)

        if not all_patches:
            click.echo("✅ 没有发现可自动修复的问题")
            sys.exit(0)

        click.echo(f"\n🔧 发现 {len(all_patches)} 个可自动修复的问题\n")

        fixer = CodeFixer(backup=not no_backup)

        patches_by_file: Dict[str, List] = {}
        for patch in all_patches:
            if patch.file_path not in patches_by_file:
                patches_by_file[patch.file_path] = []
            patches_by_file[patch.file_path].append(patch)

        if preview:
            for file_path, patches in patches_by_file.items():
                click.echo(f"\n📄 {file_path} ({len(patches)} 个修复)")
                click.echo("-" * 60)
                diff = fixer.preview_file_patches(file_path, patches)
                if diff:
                    click.echo(diff)
            return

        if interactive:
            selected_patches = []
            for file_path, patches in patches_by_file.items():
                click.echo(f"\n📄 {file_path}")
                for i, patch in enumerate(patches, 1):
                    click.echo(f"\n  [{i}] 行 {patch.issue_line}: {patch.description}")
                    click.echo(f"      置信度: {patch.confidence:.2f}")
                    if click.confirm("      应用此修复?", default=True):
                        selected_patches.append(patch)
            all_patches = selected_patches

        if not all_patches:
            click.echo("⚠️  没有选择任何修复")
            sys.exit(0)

        click.echo("\n🔨 应用修复...")

        total_applied = 0
        total_failed = 0

        patches_by_file = {}
        for patch in all_patches:
            if patch.file_path not in patches_by_file:
                patches_by_file[patch.file_path] = []
            patches_by_file[patch.file_path].append(patch)

        for file_path, patches in patches_by_file.items():
            result = fixer.apply_and_save(file_path, patches)
            total_applied += result.applied_count
            total_failed += result.failed_count

            if result.applied_count > 0:
                click.echo(f"  ✅ {file_path}: 应用了 {result.applied_count} 个修复")
                if not no_backup:
                    click.echo(f"     备份: {file_path}.bak")

            for patch, error in result.failed_patches:
                click.echo(f"  ❌ {file_path} 行 {patch.issue_line}: {error}")

        click.echo(f"\n📊 修复完成: 成功 {total_applied} 个, 失败 {total_failed} 个")

        if total_failed > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
