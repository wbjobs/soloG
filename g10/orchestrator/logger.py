import logging
from datetime import datetime
from typing import Dict, Any, Optional


class ExecutionLogger:
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.logs = []
        self.logger = logging.getLogger(f"orchestrator.{workflow_name}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_step_start(self, step_id: str, step_type: str):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": step_type,
            "event": "START",
            "status": "RUNNING"
        }
        self.logs.append(log_entry)
        self.logger.info(f"Step [{step_id}] ({step_type}) started")

    def log_step_complete(self, step_id: str, step_type: str, result: Any = None):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": step_type,
            "event": "COMPLETE",
            "status": "SUCCESS",
            "result": str(result)[:200] if result else None
        }
        self.logs.append(log_entry)
        self.logger.info(f"Step [{step_id}] ({step_type}) completed successfully")

    def log_step_failed(self, step_id: str, step_type: str, error: Exception):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": step_type,
            "event": "FAILED",
            "status": "FAILED",
            "error": str(error)
        }
        self.logs.append(log_entry)
        self.logger.error(f"Step [{step_id}] ({step_type}) failed: {error}")

    def log_step_retry(self, step_id: str, step_type: str, attempt: int, max_attempts: int):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": step_type,
            "event": "RETRY",
            "status": "RETRYING",
            "attempt": attempt,
            "max_attempts": max_attempts
        }
        self.logs.append(log_entry)
        self.logger.warning(f"Step [{step_id}] ({step_type}) retrying (attempt {attempt}/{max_attempts})")

    def log_condition_branch(self, step_id: str, condition: str, result: bool, branch_taken: str):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": "condition",
            "event": "BRANCH",
            "condition": condition,
            "result": result,
            "branch_taken": branch_taken
        }
        self.logs.append(log_entry)
        self.logger.info(f"Step [{step_id}] condition '{condition}' evaluated to {result}, taking branch: {branch_taken}")

    def log_parallel_start(self, step_id: str, branches: int):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step_id": step_id,
            "step_type": "parallel",
            "event": "PARALLEL_START",
            "branches": branches
        }
        self.logs.append(log_entry)
        self.logger.info(f"Step [{step_id}] parallel execution started with {branches} branches")

    def get_logs(self) -> list:
        return self.logs

    def print_summary(self):
        print("\n" + "=" * 80)
        print(f"WORKFLOW EXECUTION SUMMARY: {self.workflow_name}")
        print("=" * 80)
        for log in self.logs:
            status_icon = {
                "RUNNING": "⏳",
                "SUCCESS": "✅",
                "FAILED": "❌",
                "RETRYING": "🔄",
                "BRANCH": "🔀",
                "PARALLEL_START": "🚀"
            }.get(log.get("status", log.get("event", "")), "•")
            
            timestamp = log.get("timestamp", "N/A")
            step_id = log.get("step_id", "unknown")
            event = log.get("event", "UNKNOWN")
            status = log.get("status", "")
            print(f"{status_icon} [{timestamp}] {step_id:20} {event:15} {status}")
            if "error" in log:
                print(f"     Error: {log['error']}")
            if "result" in log and log["result"]:
                print(f"     Result: {log['result']}")
            if "branch_taken" in log:
                print(f"     Branch: {log['branch_taken']}")
        print("=" * 80 + "\n")
