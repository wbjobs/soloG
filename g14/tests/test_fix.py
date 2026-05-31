"""测试修复功能"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from code_review.fixer import CodeFixer, FixPatch


def test_patch_application():
    """测试补丁应用"""
    print("🧪 测试补丁应用功能\n")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write("""def test_func():
    try:
        result = eval(user_input)
    except:
        pass
    return result
""")
        temp_file = f.name

    try:
        patches = [
            FixPatch(
                file_path=temp_file,
                issue_line=3,
                original_code="    result = eval(user_input)",
                fixed_code="    result = safe_eval(user_input)",
                description="替换 eval 为 safe_eval",
                confidence=0.9
            ),
            FixPatch(
                file_path=temp_file,
                issue_line=4,
                original_code="    except:\n        pass",
                fixed_code="    except Exception as e:\n        print(f\"错误: {e}\")",
                description="捕获具体异常",
                confidence=0.85
            )
        ]

        fixer = CodeFixer(backup=True)
        result = fixer.apply_and_save(temp_file, patches)

        print(f"✅ 总补丁数: {result.total_patches}")
        print(f"✅ 成功应用: {result.applied_count}")
        print(f"❌ 失败: {result.failed_count}")

        assert result.applied_count == 2, f"应该应用 2 个补丁，实际应用 {result.applied_count} 个"
        assert result.failed_count == 0, f"不应该有失败的补丁"

        with open(temp_file, "r", encoding="utf-8") as f:
            fixed_content = f.read()

        print("\n修复后的内容:")
        print(fixed_content)

        assert "safe_eval" in fixed_content, "应该包含 safe_eval"
        assert "except Exception as e:" in fixed_content, "应该包含具体异常捕获"
        assert "print(f\"错误: {e}\")" in fixed_content, "应该包含错误打印"

        backup_file = temp_file + ".bak"
        assert Path(backup_file).exists(), "应该创建备份文件"
        print(f"\n✅ 备份文件已创建: {backup_file}")

        with open(backup_file, "r", encoding="utf-8") as f:
            backup_content = f.read()
        assert "eval(user_input)" in backup_content, "备份应该包含原始代码"
        assert "except:" in backup_content, "备份应该包含原始 except"

        print("\n🎉 补丁应用测试通过！")
        return True

    finally:
        Path(temp_file).unlink(missing_ok=True)
        Path(temp_file + ".bak").unlink(missing_ok=True)


def test_patch_with_confidence_filter():
    """测试置信度过滤"""
    print("\n🧪 测试置信度过滤\n")

    patches = [
        FixPatch("test.py", 1, "a", "b", "测试1", confidence=0.9),
        FixPatch("test.py", 2, "c", "d", "测试2", confidence=0.5),
        FixPatch("test.py", 3, "e", "f", "测试3", confidence=0.7),
    ]

    min_confidence = 0.7
    filtered = [p for p in patches if p.confidence >= min_confidence]

    print(f"总补丁数: {len(patches)}")
    print(f"最小置信度: {min_confidence}")
    print(f"过滤后补丁数: {len(filtered)}")

    assert len(filtered) == 2, f"应该过滤后剩 2 个补丁，实际剩 {len(filtered)} 个"
    assert all(p.confidence >= min_confidence for p in filtered)

    print("🎉 置信度过滤测试通过！")
    return True


def test_patch_diff():
    """测试补丁差异生成"""
    print("\n🧪 测试补丁差异生成\n")

    patch = FixPatch(
        file_path="test.py",
        issue_line=1,
        original_code="x = 1 + 2\ny = 3 + 4",
        fixed_code="x = 1 + 2\nz = 3 + 4",
        description="修改变量名",
        confidence=0.8
    )

    diff = patch.get_diff()
    print("差异:")
    print(diff)

    assert "-y = 3 + 4" in diff, "应该包含删除的行"
    assert "+z = 3 + 4" in diff, "应该包含添加的行"

    print("🎉 差异生成测试通过！")
    return True


if __name__ == "__main__":
    success1 = test_patch_application()
    success2 = test_patch_with_confidence_filter()
    success3 = test_patch_diff()

    if success1 and success2 and success3:
        print("\n🎉 所有修复功能测试通过！")
        sys.exit(0)
    else:
        print("\n💔 部分测试失败")
        sys.exit(1)
