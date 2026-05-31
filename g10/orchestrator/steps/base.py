from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StepResult:
    success: bool
    data: Any = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStep(ABC):
    def __init__(self, step_config: Dict[str, Any]):
        self.id = step_config["id"]
        self.type = step_config["type"]
        self.name = step_config.get("name", self.id)
        self.description = step_config.get("description", "")
        self.depends_on = step_config.get("depends_on", [])
        self.config = step_config.get("config", {})

    @abstractmethod
    def execute(self, context: Dict[str, Any], logger) -> StepResult:
        pass

    def _resolve_variables(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            if matches:
                result = value
                for var_path in matches:
                    resolved = self._get_nested_value(context, var_path)
                    if resolved is not None:
                        result = result.replace(f"${{{var_path}}}", str(resolved))
                return result
            return value
        elif isinstance(value, dict):
            return {k: self._resolve_variables(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_variables(item, context) for item in value]
        return value

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        try:
            safe_context = {"context": context}
            result = eval(condition, {"__builtins__": {}}, safe_context)
            return bool(result)
        except Exception as e:
            raise ValueError(f"Failed to evaluate condition '{condition}': {e}")
