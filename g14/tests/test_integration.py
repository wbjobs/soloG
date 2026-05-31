"""集成测试：验证完整的代码审查流程"""

import sys
sys.path.insert(0, "src")

from code_review.scanner import CodeScanner
from code_review.llm_client import MockLLMClient, _extract_json_from_text
from code_review.analyzer import CodeAnalyzer
from code_review.reporter import get_reporter


def test_full_workflow():
    """测试完整的工作流"""
    print("🧪 测试完整代码审查工作流\n")

    # 1. 扫描文件
    print("📁 步骤 1: 扫描文件...")
    scanner = CodeScanner()
    scan_result = scanner.scan("examples")
    print(f"   扫描到 {scan_result.total_files} 个文件")
    assert scan_result.total_files > 0, "应该扫描到文件"

    # 2. 创建分析器
    print("🤖 步骤 2: 创建分析器...")
    llm_client = MockLLMClient()
    analyzer = CodeAnalyzer(llm_client=llm_client)

    # 3. 分析文件
    print("🔍 步骤 3: 分析文件...")
    report = analyzer.analyze_files(scan_result.files)
    print(f"   分析完成，发现 {report.summary.total_issues} 个问题")
    assert report.summary.total_issues > 0, "应该发现问题"

    # 4. 生成各种格式的报告
    print("📊 步骤 4: 生成报告...")

    # 控制台报告
    console_reporter = get_reporter("console")
    console_report = console_reporter.generate(report)
    assert "代码审查结果" in console_report
    print("   ✅ 控制台报告生成成功")

    # JSON 报告
    json_reporter = get_reporter("json")
    json_report = json_reporter.generate(report)
    import json
    json_data = json.loads(json_report)
    assert "summary" in json_data
    assert "files" in json_data
    print("   ✅ JSON 报告生成成功")

    # Markdown 报告
    md_reporter = get_reporter("markdown")
    md_report = md_reporter.generate(report)
    assert "# 代码审查报告" in md_report
    assert "## 审查摘要" in md_report
    print("   ✅ Markdown 报告生成成功")

    print("\n🎉 完整工作流测试通过！")
    return True


def test_llm_json_parsing_edge_cases():
    """测试 LLM 返回的各种边缘 JSON 格式"""
    print("\n🧪 测试 LLM JSON 解析边缘场景\n")

    # 模拟 LLM 可能返回的各种格式
    llm_responses = [
        # 场景 1: 纯 JSON
        '{"issues": [{"line": 1, "message": "test"}]}',

        # 场景 2: JSON 前后有自然语言
        '好的，我分析了代码，发现以下问题：\n{"issues": [{"line": 15, "severity": "high", "message": "空的 except 块"}]}\n以上是我的分析结果。',

        # 场景 3: JSON 在代码块中
        '这是分析结果：\n```json\n{"issues": [{"line": 1, "message": "问题"}]}\n```\n请查看。',

        # 场景 4: JSON 在通用代码块中
        '```\n{"issues": [{"line": 1, "message": "问题"}]}\n```',

        # 场景 5: 有多段解释和 JSON
        '让我逐步分析...\n\n首先，我发现了一些问题...\n\n具体来说：\n{"issues": [{"line": 10, "severity": "medium", "message": "变量名不规范"}]}\n\n希望这些建议对你有帮助！',

        # 场景 6: JSON 被 Markdown 格式包裹
        '## 分析结果\n\n{"issues": [{"line": 5, "message": "问题"}]}\n\n---',

        # 场景 7: 包含中文的 JSON
        '{"issues": [{"line": 1, "message": "这是一个中文问题描述", "suggestion": "这是修复建议"}]}',

        # 场景 8: 空结果（没有问题）
        '分析完成，没有发现问题。\n{"issues": []}',
    ]

    all_passed = True
    for i, response in enumerate(llm_responses, 1):
        result = _extract_json_from_text(response)
        if result is not None and "issues" in result:
            print(f"✅ 场景 {i}: 解析成功，找到 {len(result['issues'])} 个问题")
        else:
            print(f"❌ 场景 {i}: 解析失败")
            print(f"   输入: {response[:100]}...")
            all_passed = False

    if all_passed:
        print("\n🎉 所有边缘场景解析测试通过！")
    else:
        print("\n💔 部分场景解析失败")

    return all_passed


def test_json_format_prompt():
    """测试 JSON 格式提示词"""
    print("\n🧪 测试 JSON 格式提示词\n")

    from code_review.llm_client import LLMClient

    # 检查格式指示是否存在
    assert hasattr(LLMClient, "JSON_FORMAT_INSTRUCTIONS")
    instructions = LLMClient.JSON_FORMAT_INSTRUCTIONS

    # 检查关键内容
    assert "JSON" in instructions
    assert "双引号" in instructions
    assert "不要包含任何其他文本" in instructions

    print("✅ JSON 格式提示词已正确定义")
    print(f"   提示词长度: {len(instructions)} 字符")

    return True


if __name__ == "__main__":
    success1 = test_full_workflow()
    success2 = test_llm_json_parsing_edge_cases()
    success3 = test_json_format_prompt()

    if success1 and success2 and success3:
        print("\n🎉 所有集成测试通过！")
        sys.exit(0)
    else:
        print("\n💔 部分集成测试失败")
        sys.exit(1)
