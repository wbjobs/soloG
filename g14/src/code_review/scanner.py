"""代码文件扫描器"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import pathspec

from .rules import LANGUAGE_EXTENSIONS


DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "node_modules/",
    "dist/",
    "build/",
    ".venv/",
    "venv/",
    ".idea/",
    ".vscode/",
    "*.min.js",
    "*.bundle.js",
]


@dataclass
class CodeFile:
    """代码文件"""
    path: Path
    language: str
    content: str = ""
    size: int = 0

    def read_content(self, max_size: int = 10 * 1024 * 1024) -> None:
        """读取文件内容"""
        if self.path.stat().st_size > max_size:
            raise ValueError(f"文件 {self.path} 超过最大限制 {max_size} 字节")
        self.content = self.path.read_text(encoding="utf-8", errors="replace")
        self.size = len(self.content)

    def get_lines(self) -> List[str]:
        """获取文件的所有行"""
        return self.content.splitlines()


@dataclass
class ScanResult:
    """扫描结果"""
    files: List[CodeFile] = field(default_factory=list)
    ignored: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)


class CodeScanner:
    """代码扫描器"""

    def __init__(
        self,
        extra_ignore_patterns: Optional[List[str]] = None,
        use_default_ignores: bool = True,
        max_file_size: int = 10 * 1024 * 1024,
    ) -> None:
        self.max_file_size = max_file_size
        self.ignore_patterns: List[str] = []

        if use_default_ignores:
            self.ignore_patterns.extend(DEFAULT_IGNORE_PATTERNS)

        if extra_ignore_patterns:
            self.ignore_patterns.extend(extra_ignore_patterns)

        self.gitignore_spec: Optional[pathspec.PathSpec] = None
        self.custom_spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            self.ignore_patterns
        )

    def _load_gitignore(self, base_path: Path) -> None:
        """加载 .gitignore 文件"""
        gitignore_path = base_path / ".gitignore"
        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                self.gitignore_spec = pathspec.PathSpec.from_lines(
                    pathspec.patterns.GitWildMatchPattern,
                    lines
                )
            except Exception as e:
                print(f"警告: 无法读取 .gitignore: {e}")

    def _is_ignored(self, file_path: Path, base_path: Path) -> bool:
        """检查文件是否被忽略"""
        try:
            rel_path = file_path.relative_to(base_path).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        if self.custom_spec.match_file(rel_path):
            return True

        if self.gitignore_spec and self.gitignore_spec.match_file(rel_path):
            return True

        return False

    def _get_language(self, file_path: Path) -> Optional[str]:
        """根据文件扩展名获取语言"""
        ext = file_path.suffix.lower()
        return LANGUAGE_EXTENSIONS.get(ext)

    def _scan_directory(self, dir_path: Path, base_path: Path) -> ScanResult:
        """扫描目录"""
        result = ScanResult()

        if not dir_path.exists():
            result.errors.append(f"目录不存在: {dir_path}")
            return result

        if not dir_path.is_dir():
            result.errors.append(f"不是目录: {dir_path}")
            return result

        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not self._is_ignored(root_path / d, base_path)
            ]

            for filename in files:
                file_path = root_path / filename

                if self._is_ignored(file_path, base_path):
                    result.ignored.append(file_path)
                    continue

                language = self._get_language(file_path)
                if language is None:
                    continue

                try:
                    code_file = CodeFile(path=file_path, language=language)
                    code_file.read_content(self.max_file_size)
                    result.files.append(code_file)
                except Exception as e:
                    result.errors.append(f"读取文件失败 {file_path}: {e}")

        return result

    def _scan_file(self, file_path: Path, base_path: Path) -> ScanResult:
        """扫描单个文件"""
        result = ScanResult()

        if not file_path.exists():
            result.errors.append(f"文件不存在: {file_path}")
            return result

        if not file_path.is_file():
            result.errors.append(f"不是文件: {file_path}")
            return result

        if self._is_ignored(file_path, base_path):
            result.ignored.append(file_path)
            return result

        language = self._get_language(file_path)
        if language is None:
            result.errors.append(f"不支持的文件类型: {file_path.suffix}")
            return result

        try:
            code_file = CodeFile(path=file_path, language=language)
            code_file.read_content(self.max_file_size)
            result.files.append(code_file)
        except Exception as e:
            result.errors.append(f"读取文件失败 {file_path}: {e}")

        return result

    def scan(self, target_path: str | Path) -> ScanResult:
        """扫描文件或目录"""
        path = Path(target_path).resolve()

        base_path = path if path.is_dir() else path.parent
        self._load_gitignore(base_path)

        if path.is_dir():
            return self._scan_directory(path, base_path)
        else:
            return self._scan_file(path, base_path)
