import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, asdict, field


@dataclass
class ExecutionSnapshot:
    workflow_name: str
    workflow_hash: str
    execution_id: str
    created_at: str
    updated_at: str
    completed_steps: list
    failed_steps: list
    context: Dict[str, Any]
    logs: list
    status: str = "running"
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionSnapshot":
        return cls(
            workflow_name=data.get("workflow_name", ""),
            workflow_hash=data.get("workflow_hash", ""),
            execution_id=data.get("execution_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            context=data.get("context", {}),
            logs=data.get("logs", []),
            status=data.get("status", "running"),
            error=data.get("error", None)
        )


class SnapshotManager:
    def __init__(self, snapshot_dir: str = ".snapshots"):
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _get_snapshot_path(self, workflow_name: str, execution_id: str) -> str:
        return os.path.join(self.snapshot_dir, f"{workflow_name}_{execution_id}.json")

    def _get_latest_snapshot_path(self, workflow_name: str) -> Optional[str]:
        pattern = f"{workflow_name}_"
        snapshots = []
        for filename in os.listdir(self.snapshot_dir):
            if filename.startswith(pattern) and filename.endswith(".json"):
                filepath = os.path.join(self.snapshot_dir, filename)
                snapshots.append((filepath, os.path.getmtime(filepath)))
        
        if not snapshots:
            return None
        
        snapshots.sort(key=lambda x: x[1], reverse=True)
        return snapshots[0][0]

    def _compute_workflow_hash(self, workflow: Dict[str, Any]) -> str:
        workflow_copy = {
            "name": workflow.get("name"),
            "version": workflow.get("version"),
            "steps": workflow.get("steps", [])
        }
        workflow_str = json.dumps(workflow_copy, sort_keys=True, default=str)
        return hashlib.sha256(workflow_str.encode("utf-8")).hexdigest()[:16]

    def create_snapshot(self, workflow: Dict[str, Any], execution_id: str,
                        completed_steps: Set[str], failed_steps: Set[str],
                        context: Dict[str, Any], logs: list,
                        status: str = "running", error: Optional[str] = None) -> ExecutionSnapshot:
        workflow_hash = self._compute_workflow_hash(workflow)
        now = datetime.now().isoformat()
        
        snapshot = ExecutionSnapshot(
            workflow_name=workflow.get("name", "unknown"),
            workflow_hash=workflow_hash,
            execution_id=execution_id,
            created_at=now,
            updated_at=now,
            completed_steps=list(completed_steps),
            failed_steps=list(failed_steps),
            context=context,
            logs=logs,
            status=status,
            error=error
        )
        
        filepath = self._get_snapshot_path(snapshot.workflow_name, execution_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(snapshot), f, indent=2, default=str, ensure_ascii=False)
        
        return snapshot

    def update_snapshot(self, workflow: Dict[str, Any], execution_id: str,
                        completed_steps: Set[str], failed_steps: Set[str],
                        context: Dict[str, Any], logs: list,
                        status: str = "running", error: Optional[str] = None) -> Optional[ExecutionSnapshot]:
        filepath = self._get_snapshot_path(workflow.get("name", "unknown"), execution_id)
        if not os.path.exists(filepath):
            return self.create_snapshot(workflow, execution_id, completed_steps, failed_steps, context, logs, status, error)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        existing_snapshot = ExecutionSnapshot.from_dict(data)
        
        existing_snapshot.updated_at = datetime.now().isoformat()
        existing_snapshot.completed_steps = list(completed_steps)
        existing_snapshot.failed_steps = list(failed_steps)
        existing_snapshot.context = context
        existing_snapshot.logs = logs
        existing_snapshot.status = status
        existing_snapshot.error = error
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(existing_snapshot), f, indent=2, default=str, ensure_ascii=False)
        
        return existing_snapshot

    def load_snapshot(self, workflow_name: str, execution_id: Optional[str] = None) -> Optional[ExecutionSnapshot]:
        if execution_id:
            filepath = self._get_snapshot_path(workflow_name, execution_id)
        else:
            filepath = self._get_latest_snapshot_path(workflow_name)
        
        if not filepath or not os.path.exists(filepath):
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return ExecutionSnapshot.from_dict(data)

    def load_snapshot_by_file(self, filepath: str) -> Optional[ExecutionSnapshot]:
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return ExecutionSnapshot.from_dict(data)

    def verify_workflow_compatible(self, snapshot: ExecutionSnapshot, current_workflow: Dict[str, Any]) -> bool:
        current_hash = self._compute_workflow_hash(current_workflow)
        return snapshot.workflow_hash == current_hash

    def delete_snapshot(self, workflow_name: str, execution_id: str) -> bool:
        filepath = self._get_snapshot_path(workflow_name, execution_id)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def delete_all_snapshots(self, workflow_name: Optional[str] = None) -> int:
        count = 0
        for filename in os.listdir(self.snapshot_dir):
            if filename.endswith(".json"):
                if workflow_name is None or filename.startswith(f"{workflow_name}_"):
                    filepath = os.path.join(self.snapshot_dir, filename)
                    os.remove(filepath)
                    count += 1
        return count

    def list_snapshots(self, workflow_name: Optional[str] = None) -> list:
        snapshots = []
        for filename in os.listdir(self.snapshot_dir):
            if filename.endswith(".json"):
                if workflow_name is None or filename.startswith(f"{workflow_name}_"):
                    filepath = os.path.join(self.snapshot_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        snapshots.append({
                            "workflow_name": data.get("workflow_name"),
                            "execution_id": data.get("execution_id"),
                            "status": data.get("status"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "completed_steps": len(data.get("completed_steps", [])),
                            "failed_steps": len(data.get("failed_steps", []))
                        })
                    except Exception:
                        pass
        
        snapshots.sort(key=lambda x: x["updated_at"], reverse=True)
        return snapshots
