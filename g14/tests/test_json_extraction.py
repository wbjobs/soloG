"""测试鲁棒的 JSON 提取逻辑"""

import sys
sys.path.insert(0, "src")

from code_review.llm_client import _extract_json_from_text, _clean_json_text


def test_json_extraction():
    """测试各种 JSON 提取场景"""

    test_cases = [
        # 1. 纯 JSON
        ('{"issues": [{"line": 1, "message": "test"}]}', True),

        # 2. JSON 被自然语言包裹
        ('好的，我来分析这段代码。以下是结果：\n{"issues": [{"line": 1, "message": "test"}]}\n希望对你有帮助！', True),

        # 3. JSON 在 ```json 代码块中
        ('```json\n{"issues": [{"line": 1, "message": "test"}]}\n```', True),

        # 4. JSON 在 ``` 代码块中
        ('```\n{"issues": [{"line": 1, "message": "test"}]}\n```', True),

        # 5. 有多行解释和 JSON
        ("我发现了以下问题：\n\n1. 问题1\n2. 问题2\n\nJSON 结果：\n{\"issues\": [{\"line\": 15, \"severity\": \"high\", \"category\": \"bug\", \"message\": \"空的 except 块可能会隐藏错误\", \"suggestion\": \"指定具体的异常类型\"}]}\n\n以上是分析结果。", True),

        # 6. JSON 前有文本，后有解释
        ('分析完成！\n{"issues": []}\n如有疑问请告诉我。', True),

        # 7. 单引号的 JSON（需要修复）
        ("{'issues': [{'line': 1, 'message': 'test'}]}", True),

        # 8. 没有双引号的键名
        ('{issues: [{line: 1, message: "test"}]}', True),

        # 9. 有尾随逗号的 JSON
        ('{"issues": [{"line": 1, "message": "test",}]}', True),

        # 10. 包含 // 注释的 JSON
        ('{"issues": [{"line": 1, // 这是行号\n"message": "test"}]}', True),

        # 11. 包含 /* */ 注释的 JSON
        ('{"issues": [{"line": 1, /* 这是行号 */ "message": "test"}]}', True),

        # 12. 混合场景：自然语言 + 代码块 + JSON
        ('以下是分析结果：\n\n```json\n{"issues": [{"line": 15, "severity": "high", "message": "空的 except 块"}]}\n```\n\n请注意这些问题。', True),

        # 13. JSON 被 Markdown 表格和文本包裹
        ('## 分析结果\n\n| 行号 | 问题 |\n|------|------|\n| 15 | 空 except |\n\n```\n{"issues": [{"line": 15, "message": "空的 except 块"}]}\n```', True),

        # 14. 无效的 JSON（应该返回 None）
        ("这不是 JSON", False),

        # 15. 空字符串
        ("", False),
    ]

    print("🧪 测试 JSON 提取逻辑\n")

    passed = 0
    failed = 0

    for i, (input_text, should_succeed) in enumerate(test_cases, 1):
        result = _extract_json_from_text(input_text)
        success = result is not None if should_succeed else result is None

        status = "✅" if success else "❌"
        if success:
            passed += 1
        else:
            failed += 1

        preview = input_text[:80].replace("\n", "\\n")
        if len(input_text) > 80:
            preview += "..."

        print(f"{status} 测试 {i}: {preview}")
        if not success:
            print(f"   期望: {'成功' if should_succeed else '失败'}, 实际: {'成功' if result is not None else '失败'}")
            if result:
                print(f"   提取结果: {str(result)[:100]}")

    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")

    return failed == 0


def test_clean_json_text():
    """测试 JSON 文本清理功能"""

    print("\n🧪 测试 JSON 文本清理\n")

    test_cases = [
        # 移除尾随逗号
        ('{"a": 1, "b": 2,}', '{"a": 1, "b": 2}'),
        # 修复单引号
        ("{'a': 'test'}", '{"a": "test"}'),
        # 修复未加引号的键
        ('{a: "test", b: 123}', '{"a": "test", "b": 123}'),
        # 移除单行注释
        ('{"a": 1, // comment\n"b": 2}', '{"a": 1, "b": 2}'),
        # 移除多行注释
        ('{"a": 1, /* comment */ "b": 2}', '{"a": 1, "b": 2}'),
        # 移除前后的非 JSON 文本
        ('前缀文本 {"a": 1} 后缀文本', '{"a": 1}'),
    ]

    passed = 0
    failed = 0

    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = _clean_json_text(input_text)

        import json
        try:
            json.loads(result)
            success = True
        except json.JSONDecodeError:
            success = False

        status = "✅" if success else "❌"
        if success:
            passed += 1
        else:
            failed += 1

        print(f"{status} 测试 {i}: {input_text[:60]}")
        if not success:
            print(f"   清理后: {result}")

    print(f"\n📊 清理测试结果: {passed} 通过, {failed} 失败")

    return failed == 0


if __name__ == "__main__":
    success1 = test_json_extraction()
    success2 = test_clean_json_text()

    if success1 and success2:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n💔 部分测试失败")
        sys.exit(1)
