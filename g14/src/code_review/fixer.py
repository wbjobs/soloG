"""代码修复补丁生成和应用"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FixPatch:
    """修复补丁"""
    file_path: str
    issue_line: int
    original_code: str
    fixed_code: str
    description: str
    confidence: float = 0.0

    @property
    def is_valid(self) -> bool:
        """检查补丁是否有效"""
        return bool(self.original_code and self.fixed_code)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "issue_line": self.issue_line,
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "description": self.description,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixPatch":
        return cls(
            file_path=data["file_path"],
            issue_line=data["issue_line"],
            original_code=data["original_code"],
            fixed_code=data["fixed_code"],
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.0),
        )

    def get_diff(self) -> str:
        """获取差异对比"""
        original_lines = self.original_code.splitlines(keepends=True)
        fixed_lines = self.fixed_code.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{Path(self.file_path).name}",
            tofile=f"b/{Path(self.file_path).name}",
            n=3,
        )
        return "".join(diff)


@dataclass
class FileFixResult:
    """文件修复结果"""
    file_path: str
    patches: List[FixPatch] = field(default_factory=list)
    applied_patches: List[FixPatch] = field(default_factory=list)
    failed_patches: List[Tuple[FixPatch, str]] = field(default_factory=list)
    original_content: str = ""
    fixed_content: str = ""

    @property
    def total_patches(self) -> int:
        return len(self.patches)

    @property
    def applied_count(self) -> int:
        return len(self.applied_patches)

    @property
    def failed_count(self) -> int:
        return len(self.failed_patches)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "patches": [p.to_dict() for p in self.patches],
            "applied_patches": [p.to_dict() for p in self.applied_patches],
            "failed_patches": [
                {"patch": p[0].to_dict(), "error": p[1]}
                for p in self.failed_patches
            ],
            "original_content": self.original_content,
            "fixed_content": self.fixed_content,
        }


class CodeFixer:
    """代码修复器"""

    def __init__(self, backup: bool = True) -> None:
        self.backup = backup
        self.backup_suffix = ".bak"

    def _read_file(self, file_path: str) -> str:
        """读取文件内容"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, file_path: str, content: str) -> None:
        """写入文件内容"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _create_backup(self, file_path: str, content: str) -> str:
        """创建文件备份"""
        if not self.backup:
            return ""
        backup_path = file_path + self.backup_suffix
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)
        return backup_path

    def _find_code_in_content(self, content: str, code: str, line_number: Optional[int] = None) -> Optional[int]:
        """在文件内容中查找代码片段的起始行

        Args:
            content: 文件内容
            code: 要查找的代码片段
            line_number: 预期的行号（用于优先搜索附近）

        Returns:
            找到的起始行号（从 0 开始），未找到返回 None
        """
        lines = content.splitlines()
        code_lines = code.strip().splitlines()

        if not code_lines:
            return None

        search_range = range(len(lines) - len(code_lines) + 1)

        if line_number is not None:
            search_start = max(0, line_number - 5)
            search_end = min(len(lines), line_number + 5)
            preferred_range = range(search_start, min(search_end, len(lines) - len(code_lines) + 1))
            for i in preferred_range:
                if self._lines_match(lines[i:i + len(code_lines)], code_lines):
                    return i

        for i in search_range:
            if self._lines_match(lines[i:i + len(code_lines)], code_lines):
                return i

        return None

    def _lines_match(self, lines1: List[str], lines2: List[str]) -> bool:
        """比较两行代码是否匹配（忽略首尾空白）"""
        if len(lines1) != len(lines2):
            return False

        for l1, l2 in zip(lines1, lines2):
            if l1.strip() != l2.strip():
                return False
        return True

    def apply_patch(self, content: str, patch: FixPatch) -> Tuple[str, bool, str]:
        """应用单个补丁

        Args:
            content: 文件原始内容
            patch: 修复补丁

        Returns:
            (修复后的内容, 是否成功, 错误信息)
        """
        if not patch.is_valid:
            return content, False, "补丁无效：original_code 或 fixed_code 为空"

        start_line = self._find_code_in_content(content, patch.original_code, patch.issue_line - 1)

        if start_line is None:
            return content, False, f"在文件中未找到原始代码（行 {patch.issue_line}）"

        lines = content.splitlines(keepends=True)
        original_lines = patch.original_code.strip().splitlines()
        fixed_lines = patch.fixed_code.splitlines(keepends=True)

        end_line = start_line + len(original_lines)

        if end_line > len(lines):
            return content, False, "代码片段超出文件范围"

        original_line_endings = [line.endswith("\n") for line in lines[start_line:end_line]]
        for i, line in enumerate(fixed_lines):
            if i < len(original_line_endings) and original_line_endings[i] and not line.endswith("\n"):
                fixed_lines[i] = line + "\n"

        new_lines = lines[:start_line] + fixed_lines + lines[end_line:]
        new_content = "".join(new_lines)

        return new_content, True, ""

    def apply_patches(self, file_path: str, patches: List[FixPatch]) -> FileFixResult:
        """应用多个补丁到文件

        Args:
            file_path: 文件路径
            patches: 补丁列表

        Returns:
            修复结果
        """
        result = FileFixResult(file_path=file_path, patches=patches)

        try:
            original_content = self._read_file(file_path)
            result.original_content = original_content
        except Exception as e:
            result.failed_patches = [(p, f"读取文件失败: {e}") for p in patches]
            return result

        current_content = original_content

        sorted_patches = sorted(patches, key=lambda p: p.issue_line, reverse=True)

        for patch in sorted_patches:
            new_content, success, error = self.apply_patch(current_content, patch)
            if success:
                current_content = new_content
                result.applied_patches.append(patch)
            else:
                result.failed_patches.append((patch, error))

        result.fixed_content = current_content

        return result

    def apply_and_save(self, file_path: str, patches: List[FixPatch]) -> FileFixResult:
        """应用补丁并保存到文件

        Args:
            file_path: 文件路径
            patches: 补丁列表

        Returns:
            修复结果
        """
        result = self.apply_patches(file_path, patches)

        if result.applied_count > 0:
            try:
                self._create_backup(file_path, result.original_content)
                self._write_file(file_path, result.fixed_content)
            except Exception as e:
                result.failed_patches.extend(
                    [(p, f"保存文件失败: {e}") for p in result.applied_patches]
                )
                result.applied_patches = []

        return result

    def preview_patch(self, patch: FixPatch) -> str:
        """预览补丁的差异

        Args:
            patch: 修复补丁

        Returns:
            差异预览字符串
        """
        return patch.get_diff()

    def preview_file_patches(self, file_path: str, patches: List[FixPatch]) -> str:
        """预览文件的所有补丁

        Args:
            file_path: 文件路径
            patches: 补丁列表

        Returns:
            差异预览字符串
        """
        try:
            original_content = self._read_file(file_path)
        except Exception as e:
            return f"无法读取文件: {e}"

        current_content = original_content
        all_diffs = []

        sorted_patches = sorted(patches, key=lambda p: p.issue_line, reverse=True)

        for patch in sorted_patches:
            new_content, success, error = self.apply_patch(current_content, patch)
            if success:
                diff = patch.get_diff()
                if diff:
                    all_diffs.append(diff)
                current_content = new_content

        return "\n".join(all_diffs)


def parse_fix_patches_from_llm_response(response: Dict[str, Any], file_path: str) -> List[FixPatch]:
    """从 LLM 响应中解析修复补丁

    Args:
        response: LLM 的 JSON 响应
        file_path: 文件路径

    Returns:
        补丁列表
    """
    patches = []
    issues = response.get("issues", [])

    for issue in issues:
        original_code = issue.get("original_code", "").strip()
        fixed_code = issue.get("fixed_code", "").strip()

        if not original_code or not fixed_code:
            continue

        patch = FixPatch(
            file_path=file_path,
            issue_line=issue.get("line", 0),
            original_code=original_code,
            fixed_code=fixed_code,
            description=issue.get("message", ""),
            confidence=issue.get("confidence", 0.8),
        )
        patches.append(patch)

    return patches
