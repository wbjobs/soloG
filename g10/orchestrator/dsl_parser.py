import yaml
from typing import Dict, Any, List
import os


class DSLParser:
    def __init__(self):
        self.supported_step_types = {
            "http": "HttpStep",
            "condition": "ConditionStep",
            "parallel": "ParallelStep",
            "retry": "RetryStep",
            "noop": "NoopStep"
        }

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"YAML file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return self.parse(data)

    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_schema(data)
        
        workflow = {
            "name": data.get("name", "unnamed_workflow"),
            "version": data.get("version", "1.0"),
            "description": data.get("description", ""),
            "steps": self._parse_steps(data.get("steps", [])),
            "variables": data.get("variables", {})
        }
        
        return workflow

    def _validate_schema(self, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("YAML root must be a dictionary")
        
        if "steps" not in data:
            raise ValueError("YAML must contain a 'steps' section")
        
        if not isinstance(data["steps"], list):
            raise ValueError("'steps' must be a list")

    def _parse_steps(self, steps_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_steps = []
        for step_data in steps_data:
            parsed_step = self._parse_step(step_data)
            parsed_steps.append(parsed_step)
        return parsed_steps

    def _parse_step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in step_data:
            raise ValueError("Each step must have an 'id' field")
        
        if "type" not in step_data:
            raise ValueError(f"Step '{step_data.get('id', 'unknown')}' must have a 'type' field")
        
        step_type = step_data["type"]
        if step_type not in self.supported_step_types:
            raise ValueError(f"Unsupported step type: {step_type}. Supported types: {list(self.supported_step_types.keys())}")
        
        step = {
            "id": step_data["id"],
            "type": step_type,
            "name": step_data.get("name", step_data["id"]),
            "description": step_data.get("description", ""),
            "depends_on": step_data.get("depends_on", []),
            "config": self._parse_step_config(step_type, step_data)
        }
        
        return step

    def _parse_step_config(self, step_type: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        config = {}
        
        if step_type == "http":
            config = {
                "method": step_data.get("method", "GET").upper(),
                "url": step_data.get("url", ""),
                "headers": step_data.get("headers", {}),
                "body": step_data.get("body", None),
                "timeout": step_data.get("timeout", 30),
                "query_params": step_data.get("query_params", {}),
                "idempotency_key": step_data.get("idempotency_key", None)
            }
        elif step_type == "condition":
            config = {
                "condition": step_data.get("condition", ""),
                "then": self._parse_steps(step_data.get("then", [])),
                "else": self._parse_steps(step_data.get("else", []))
            }
        elif step_type == "parallel":
            config = {
                "branches": []
            }
            for branch in step_data.get("branches", []):
                branch_data = {
                    "name": branch.get("name", f"branch_{len(config['branches'])}"),
                    "steps": self._parse_steps(branch.get("steps", []))
                }
                config["branches"].append(branch_data)
        elif step_type == "retry":
            config = {
                "max_attempts": step_data.get("max_attempts", 3),
                "delay_seconds": step_data.get("delay_seconds", 1),
                "retry_on_status_codes": step_data.get("retry_on_status_codes", [408, 429, 500, 502, 503, 504]),
                "retry_on_exceptions": step_data.get("retry_on_exceptions", ["connection_error", "timeout", "request_exception"]),
                "allow_unsafe_retries": step_data.get("allow_unsafe_retries", False),
                "step": self._parse_step(step_data["step"]) if "step" in step_data else None
            }
        
        return config
