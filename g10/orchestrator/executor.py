from typing import Dict, Any, List, Set, Optional
from celery import group
from .dag import DAG
from .logger import ExecutionLogger
from .tasks import execute_step_task, execute_with_retry
from .steps import STEP_REGISTRY
from .snapshot import SnapshotManager, ExecutionSnapshot
import time
import uuid


class Executor:
    def __init__(self, workflow: Dict[str, Any], use_celery: bool = True,
                 enable_snapshot: bool = False, snapshot_dir: str = ".snapshots",
                 execution_id: Optional[str] = None):
        self.workflow = workflow
        self.workflow_name = workflow.get("name", "unnamed_workflow")
        self.steps = workflow.get("steps", [])
        self.variables = workflow.get("variables", {})
        self.use_celery = use_celery
        self.enable_snapshot = enable_snapshot
        self.execution_id = execution_id or str(uuid.uuid4())[:8]
        self.dag = DAG(self.steps)
        self.logger = ExecutionLogger(self.workflow_name)
        self.context: Dict[str, Any] = {
            "variables": self.variables,
            "results": {}
        }
        self.completed_steps: Set[str] = set()
        self.failed_steps: Set[str] = set()
        
        self.snapshot_manager = SnapshotManager(snapshot_dir) if enable_snapshot else None
        self._resumed_from_snapshot = False

    def validate(self) -> bool:
        try:
            self.dag.topological_sort()
            return True
        except ValueError as e:
            self.logger.logger.error(f"Workflow validation failed: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        if not self.validate():
            return {"success": False, "error": "Workflow validation failed"}

        if self._resumed_from_snapshot:
            self.logger.logger.info(
                f"Resuming workflow execution: {self.workflow_name} (execution_id: {self.execution_id})"
            )
            self.logger.logger.info(
                f"Resumed from snapshot: {len(self.completed_steps)} steps already completed"
            )
        else:
            self.logger.logger.info(
                f"Starting workflow execution: {self.workflow_name} (execution_id: {self.execution_id})"
            )
        
        if self.enable_snapshot and not self._resumed_from_snapshot:
            self._save_snapshot(status="running")
        
        try:
            self._execute_steps(self.steps)
            
            success = len(self.failed_steps) == 0
            result = {
                "success": success,
                "workflow_name": self.workflow_name,
                "execution_id": self.execution_id,
                "completed_steps": list(self.completed_steps),
                "failed_steps": list(self.failed_steps),
                "context": self.context,
                "logs": self.logger.get_logs(),
                "resumed_from_snapshot": self._resumed_from_snapshot
            }
            
            if self.enable_snapshot:
                self._save_snapshot(status="completed" if success else "failed")
            
            self.logger.print_summary()
            return result
            
        except Exception as e:
            self.logger.logger.error(f"Workflow execution failed: {e}")
            if self.enable_snapshot:
                self._save_snapshot(status="crashed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "execution_id": self.execution_id,
                "completed_steps": list(self.completed_steps),
                "failed_steps": list(self.failed_steps),
                "logs": self.logger.get_logs(),
                "resumed_from_snapshot": self._resumed_from_snapshot
            }

    def resume_from_snapshot(self, snapshot: ExecutionSnapshot) -> bool:
        if not self.snapshot_manager:
            self.logger.logger.error("Snapshot is not enabled. Cannot resume.")
            return False
        
        if not self.snapshot_manager.verify_workflow_compatible(snapshot, self.workflow):
            self.logger.logger.error(
                "Workflow has changed since snapshot was taken. Cannot resume safely."
            )
            return False
        
        self.execution_id = snapshot.execution_id
        self.completed_steps = set(snapshot.completed_steps)
        self.failed_steps = set(snapshot.failed_steps)
        self.context = snapshot.context
        self.logger.logs = snapshot.logs
        self._resumed_from_snapshot = True
        
        self.logger.logger.info(
            f"Loaded snapshot for execution: {self.execution_id}"
        )
        self.logger.logger.info(
            f"Snapshot status: {snapshot.status}, completed steps: {len(self.completed_steps)}"
        )
        
        return True

    def _save_snapshot(self, status: str = "running", error: Optional[str] = None):
        if not self.snapshot_manager:
            return
        
        self.snapshot_manager.update_snapshot(
            workflow=self.workflow,
            execution_id=self.execution_id,
            completed_steps=self.completed_steps,
            failed_steps=self.failed_steps,
            context=self.context,
            logs=self.logger.get_logs(),
            status=status,
            error=error
        )
        
        self.logger.logger.debug(
            f"Snapshot saved: status={status}, completed_steps={len(self.completed_steps)}"
        )

    def _execute_steps(self, steps: List[Dict[str, Any]]):
        local_dag = DAG(steps)
        local_completed: Set[str] = set()
        
        while len(local_completed) < len(steps):
            ready_steps = local_dag.get_ready_steps(local_completed)
            
            if not ready_steps:
                break
            
            for step_id in ready_steps:
                step_config = local_dag.get_step(step_id)
                self._execute_single_step(step_config, local_completed)

    def _execute_single_step(self, step_config: Dict[str, Any], local_completed: Set[str]):
        step_type = step_config["type"]
        
        if step_type == "parallel":
            self._execute_parallel_step(step_config, local_completed)
        elif step_type == "condition":
            self._execute_condition_step(step_config, local_completed)
        elif step_type == "retry":
            self._execute_retry_step(step_config, local_completed)
        else:
            self._execute_normal_step(step_config, local_completed)

    def _execute_normal_step(self, step_config: Dict[str, Any], local_completed: Set[str]):
        if step_config["id"] in self.completed_steps:
            self.logger.logger.info(f"Step [{step_config['id']}] already completed, skipping")
            local_completed.add(step_config["id"])
            return
        
        result = self._run_step(step_config)
        
        if result["success"]:
            self.context["results"][step_config["id"]] = result.get("data", {})
            local_completed.add(step_config["id"])
            self.completed_steps.add(step_config["id"])
            
            if self.enable_snapshot:
                self._save_snapshot(status="running")
        else:
            self.failed_steps.add(step_config["id"])
            raise Exception(f"Step {step_config['id']} failed: {result.get('error', 'Unknown error')}")

    def _execute_parallel_step(self, step_config: Dict[str, Any], local_completed: Set[str]):
        if step_config["id"] in self.completed_steps:
            self.logger.logger.info(f"Step [{step_config['id']}] already completed, skipping")
            local_completed.add(step_config["id"])
            return
        
        branches = step_config["config"]["branches"]
        self.logger.log_parallel_start(step_config["id"], len(branches))
        
        branch_tasks = []
        steps_to_execute = []
        for branch in branches:
            branch_steps = branch.get("steps", [])
            for branch_step in branch_steps:
                if branch_step["id"] in self.completed_steps:
                    self.logger.logger.info(f"Parallel branch step [{branch_step['id']}] already completed, skipping")
                    continue
                steps_to_execute.append(branch_step)
        
        for branch_step in steps_to_execute:
            if self.use_celery:
                task = execute_step_task.s(branch_step, self.context, self.workflow_name)
                branch_tasks.append(task)
            else:
                result = self._run_step(branch_step)
                if result["success"]:
                    self.context["results"][branch_step["id"]] = result.get("data", {})
                    self.completed_steps.add(branch_step["id"])
                else:
                    self.failed_steps.add(branch_step["id"])
                    raise Exception(f"Parallel branch step {branch_step['id']} failed")
        
        if self.use_celery and branch_tasks:
            job = group(branch_tasks)
            async_result = job.apply_async()
            results = async_result.get(timeout=300)
            
            for result in results:
                if result["success"]:
                    step_id = result["step_id"]
                    self.context["results"][step_id] = result.get("data", {})
                    self.completed_steps.add(step_id)
                else:
                    self.failed_steps.add(result["step_id"])
                    raise Exception(f"Parallel step failed: {result.get('error')}")
        
        local_completed.add(step_config["id"])
        self.completed_steps.add(step_config["id"])
        self.logger.log_step_complete(step_config["id"], "parallel", {"branches_executed": len(branches)})
        
        if self.enable_snapshot:
            self._save_snapshot(status="running")

    def _execute_condition_step(self, step_config: Dict[str, Any], local_completed: Set[str]):
        if step_config["id"] in self.completed_steps:
            self.logger.logger.info(f"Step [{step_config['id']}] already completed, skipping")
            local_completed.add(step_config["id"])
            return
        
        result = self._run_step(step_config)
        
        if result["success"]:
            data = result.get("data", {})
            branch_steps = data.get("branch_steps", [])
            
            self._execute_steps(branch_steps)
            
            self.context["results"][step_config["id"]] = data
            local_completed.add(step_config["id"])
            self.completed_steps.add(step_config["id"])
            
            if self.enable_snapshot:
                self._save_snapshot(status="running")
        else:
            self.failed_steps.add(step_config["id"])
            raise Exception(f"Condition step {step_config['id']} failed: {result.get('error')}")

    def _execute_retry_step(self, step_config: Dict[str, Any], local_completed: Set[str]):
        if step_config["id"] in self.completed_steps:
            self.logger.logger.info(f"Step [{step_config['id']}] already completed, skipping")
            local_completed.add(step_config["id"])
            return
        
        max_attempts = step_config["config"].get("max_attempts", 3)
        delay_seconds = step_config["config"].get("delay_seconds", 1)
        retry_on_status_codes = step_config["config"].get("retry_on_status_codes", [408, 429, 500, 502, 503, 504])
        retry_on_exceptions = step_config["config"].get("retry_on_exceptions", ["connection_error", "timeout", "request_exception"])
        allow_unsafe_retries = step_config["config"].get("allow_unsafe_retries", False)
        wrapped_step = step_config["config"].get("step")
        
        if self.use_celery:
            result = execute_with_retry.delay(
                step_config, self.context, self.workflow_name, 
                max_attempts, delay_seconds,
                retry_on_status_codes, retry_on_exceptions, allow_unsafe_retries
            ).get(timeout=300)
        else:
            result = self._run_with_retry_sync(
                wrapped_step, max_attempts, delay_seconds,
                retry_on_status_codes, retry_on_exceptions, allow_unsafe_retries
            )
        
        if result["success"]:
            self.context["results"][step_config["id"]] = result.get("data", {})
            local_completed.add(step_config["id"])
            self.completed_steps.add(step_config["id"])
            
            if self.enable_snapshot:
                self._save_snapshot(status="running")
        else:
            self.failed_steps.add(step_config["id"])
            raise Exception(f"Retry step {step_config['id']} failed after {max_attempts} attempts")

    def _run_step(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_step_start(step_config["id"], step_config["type"])
        
        if self.use_celery:
            try:
                result = execute_step_task.delay(step_config, self.context, self.workflow_name).get(timeout=300)
                for log_entry in result.get("logs", []):
                    self.logger.logs.append(log_entry)
                return result
            except Exception as e:
                self.logger.log_step_failed(step_config["id"], step_config["type"], e)
                return {"success": False, "error": str(e), "step_id": step_config["id"]}
        else:
            try:
                step_class = STEP_REGISTRY.get(step_config["type"])
                if not step_class:
                    raise ValueError(f"Unknown step type: {step_config['type']}")
                
                step = step_class(step_config)
                result = step.execute(self.context, self.logger)
                
                if result.success:
                    self.logger.log_step_complete(step_config["id"], step_config["type"], result.data)
                    return {
                        "success": True,
                        "data": result.data,
                        "step_id": step_config["id"]
                    }
                else:
                    self.logger.log_step_failed(step_config["id"], step_config["type"], result.error or Exception("Unknown error"))
                    return {
                        "success": False,
                        "error": str(result.error) if result.error else "Unknown error",
                        "step_id": step_config["id"]
                    }
            except Exception as e:
                self.logger.log_step_failed(step_config["id"], step_config["type"], e)
                return {
                    "success": False,
                    "error": str(e),
                    "step_id": step_config["id"]
                }

    def _run_with_retry_sync(self, step_config: Dict[str, Any], max_attempts: int, delay_seconds: int,
                             retry_on_status_codes: list, retry_on_exceptions: list, allow_unsafe_retries: bool) -> Dict[str, Any]:
        last_result = None
        for attempt in range(1, max_attempts + 1):
            result = self._run_step(step_config)
            last_result = result
            
            if result["success"]:
                return result
            
            if attempt < max_attempts:
                safe_to_retry = self._is_safe_to_retry(result, retry_on_status_codes, retry_on_exceptions)
                
                if not safe_to_retry and not allow_unsafe_retries:
                    self.logger.logger.warning(
                        f"Step [{step_config['id']}] failed but is not safe to retry. "
                        f"Skipping remaining retries to avoid duplicate execution on idempotent interface."
                    )
                    break
                
                self.logger.log_step_retry(step_config["id"], step_config["type"], attempt, max_attempts)
                time.sleep(delay_seconds)
        
        return last_result

    def _is_safe_to_retry(self, result: Dict[str, Any], retry_on_status_codes: list, retry_on_exceptions: list) -> bool:
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
        
        if "safe_to_retry" in data:
            return data["safe_to_retry"]
        
        if "status_code" in data:
            return data["status_code"] in retry_on_status_codes
        
        if "error_type" in data:
            return data["error_type"] in retry_on_exceptions
        
        return True
