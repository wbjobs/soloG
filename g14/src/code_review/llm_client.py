"""LLM 客户端封装"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    """LLM 配置"""
    model_path: str
    n_ctx: int = 4096
    n_threads: int = 4
    n_gpu_layers: int = 0
    temperature: float = 0.1
    max_tokens: int = 2048
    top_p: float = 0.95
    stop: List[str] = field(default_factory=lambda: ["```", "</s>"])
    verbose: bool = False


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    raw_response: Any
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """从文本中鲁棒地提取 JSON 对象

    尝试多种策略从包含自然语言的文本中提取 JSON:
    1. 直接解析整个文本
    2. 提取 ```json ... ``` 块
    3. 提取第一个 { 到最后一个 } 之间的内容
    4. 使用正则表达式匹配 JSON 对象
    5. 尝试修复常见的 JSON 格式错误
    """
    if not text or not text.strip():
        return None

    strategies = [
        lambda t: t,
        lambda t: t[t.find("{"):t.rfind("}") + 1] if "{" in t and "}" in t else t,
        lambda t: re.search(r"```json\s*(.*?)\s*```", t, re.DOTALL).group(1) if re.search(r"```json\s*(.*?)\s*```", t, re.DOTALL) else t,
        lambda t: re.search(r"```\s*(.*?)\s*```", t, re.DOTALL).group(1) if re.search(r"```\s*(.*?)\s*```", t, re.DOTALL) else t,
        lambda t: re.search(r"\{[\s\S]*\}", t).group(0) if re.search(r"\{[\s\S]*\}", t) else t,
    ]

    for strategy in strategies:
        try:
            extracted = strategy(text)
            if extracted:
                return json.loads(extracted)
        except (json.JSONDecodeError, AttributeError):
            continue

    cleaned_text = _clean_json_text(text)
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    return None


def _clean_json_text(text: str) -> str:
    """清理文本中的常见 JSON 格式问题"""
    cleaned = text.strip()

    cleaned = re.sub(r"^[^{]*", "", cleaned)
    cleaned = re.sub(r"[^}]*$", "", cleaned)

    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    cleaned = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', cleaned)

    cleaned = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    cleaned = _fix_single_quotes(cleaned)

    return cleaned


def _fix_single_quotes(text: str) -> str:
    """将 JSON 中的单引号替换为双引号"""
    result = []
    in_string = False
    string_char = None
    i = 0

    while i < len(text):
        char = text[i]

        if not in_string:
            if char in ('"', "'"):
                in_string = True
                string_char = char
                result.append('"')
            else:
                result.append(char)
        else:
            if char == "\\" and i + 1 < len(text):
                result.append(char)
                result.append(text[i + 1])
                i += 1
            elif char == string_char:
                in_string = False
                string_char = None
                result.append('"')
            else:
                result.append(char)

        i += 1

    return "".join(result)


class LLMClient:
    """LLM 客户端封装"""

    JSON_FORMAT_INSTRUCTIONS = """
重要：你的输出必须只包含一个有效的 JSON 对象，不要包含任何其他文本、解释、注释或代码块标记。

JSON 格式要求：
- 所有字符串必须使用双引号
- 键名必须使用双引号
- 不要有尾随逗号
- 不要添加任何自然语言说明
- 不要使用 ``` 或 ```json 包裹 JSON

直接输出 JSON 对象，例如：
{"key": "value"}
"""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llama = None
        self._initialized = False

    def _initialize(self) -> None:
        """初始化 llama-cpp-python"""
        if self._initialized:
            return

        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python 未安装，请运行: pip install llama-cpp-python"
            )

        self._llama = Llama(
            model_path=self.config.model_path,
            n_ctx=self.config.n_ctx,
            n_threads=self.config.n_threads,
            n_gpu_layers=self.config.n_gpu_layers,
            verbose=self.config.verbose,
        )
        self._initialized = True

    def _build_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """构建提示词"""
        return f"""<s>[INST] <<SYS>>
{system_prompt}
<</SYS>>

{user_prompt} [/INST]"""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """生成文本"""
        self._initialize()

        prompt = self._build_prompt(system_prompt, user_prompt)

        start_time = time.time()

        output = self._llama.create_completion(
            prompt=prompt,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            top_p=self.config.top_p,
            stop=self.config.stop,
            echo=False,
        )

        latency_ms = (time.time() - start_time) * 1000

        content = output["choices"][0]["text"].strip()
        usage = output.get("usage", {})

        return LLMResponse(
            content=content,
            raw_response=output,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 2,
        expected_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成 JSON 格式的响应

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            max_tokens: 最大生成 token 数
            temperature: 生成温度
            max_retries: 最大重试次数
            expected_schema: 期望的 JSON 结构示例，用于帮助模型理解输出格式
        """
        schema_instruction = ""
        if expected_schema:
            schema_json = json.dumps(expected_schema, ensure_ascii=False, indent=2)
            schema_instruction = f"\n\n期望的 JSON 结构示例：\n```json\n{schema_json}\n```\n\n请严格按照此结构输出。"

        system_prompt_with_json = (
            system_prompt
            + "\n\n"
            + self.JSON_FORMAT_INSTRUCTIONS.strip()
            + schema_instruction
        )

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.generate(
                    system_prompt=system_prompt_with_json,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                parsed_json = _extract_json_from_text(response.content)
                if parsed_json is not None:
                    return parsed_json

                raise json.JSONDecodeError(
                    "无法从响应中提取有效的 JSON",
                    response.content[:200],
                    0
                )

            except (json.JSONDecodeError, RuntimeError) as e:
                last_error = e
                if attempt < max_retries:
                    retry_instruction = (
                        f"\n\n上一次尝试生成的 JSON 格式不正确，请重新输出。"
                        f"错误信息: {str(e)}。"
                        f"\n请确保只输出 JSON 对象，不要包含任何其他文本。"
                    )
                    user_prompt = user_prompt + retry_instruction
                    continue

        raise RuntimeError(f"达到最大重试次数 ({max_retries})，无法获取有效的 JSON 响应。最后错误: {last_error}")


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端，用于测试"""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        if config is None:
            config = LLMConfig(model_path="mock")
        super().__init__(config)
        self._initialized = True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """模拟生成响应"""
        mock_content = """
我已分析了提供的代码。以下是发现的问题：

1. **潜在 Bug**:
   - 第 15 行: 空的 except 块可能会隐藏错误
   - 第 42 行: 未对用户输入进行验证

2. **代码异味**:
   - 第 8 行: 函数名 `f` 不够描述性
   - 第 20-35 行: 函数过长，考虑拆分

3. **安全漏洞**:
   - 第 58 行: 使用了 `eval()` 可能导致代码注入
   - 第 72 行: SQL 查询中直接拼接字符串，存在 SQL 注入风险
"""

        return LLMResponse(
            content=mock_content,
            raw_response={"choices": [{"text": mock_content}]},
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            latency_ms=50.0,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 2,
        expected_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """模拟生成 JSON 响应"""
        return {
            "issues": [
                {
                    "severity": "high",
                    "category": "bug",
                    "line": 15,
                    "message": "空的 except 块可能会隐藏错误",
                    "suggestion": "指定具体的异常类型，或至少记录错误日志",
                    "rule_id": "E722",
                    "original_code": "    except:\n        pass",
                    "fixed_code": "    except Exception as e:\n        print(f\"错误: {e}\")",
                    "fix_confidence": 0.9
                },
                {
                    "severity": "critical",
                    "category": "security",
                    "line": 11,
                    "message": "使用了 eval() 可能导致代码注入",
                    "suggestion": "避免使用 eval()，使用更安全的替代方案",
                    "rule_id": "SEC001",
                    "original_code": "    result = eval(user_input)",
                    "fixed_code": "    result = safe_eval(user_input)",
                    "fix_confidence": 0.85
                }
            ]
        }
