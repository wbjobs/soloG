import time
from typing import Dict, Any
from celery import shared_task
from celery.utils.log import get_task_logger
from .steps import STEP_REGISTRY
from .logger import ExecutionLogger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=0)
def execute_step_task(self, step_config: Dict[str, Any], context: Dict[str, Any], workflow_name: str):
    exec_logger = ExecutionLogger(workflow_name)
    exec_logger.log_step_start(step_config["id"], step_config["type"])
    
    try:
        step_class = STEP_REGISTRY.get(step_config["type"])
        if not step_class:
            raise ValueError(f"Unknown step type: {step_config['type']}")
        
        step = step_class(step_config)
        result = step.execute(context, exec_logger)
        
        if result.success:
            exec_logger.log_step_complete(step_config["id"], step_config["type"], result.data)
        else:
            exec_logger.log_step_failed(step_config["id"], step_config["type"], result.error or Exception("Unknown error"))
        
        return {
            "success": result.success,
            "data": result.data,
            "error": str(result.error) if result.error else None,
            "step_id": step_config["id"],
            "step_type": step_config["type"],
            "logs": exec_logger.get_logs()
        }
        
    except Exception as e:
        exec_logger.log_step_failed(step_config["id"], step_config["type"], e)
        return {
            "success": False,
            "error": str(e),
            "step_id": step_config["id"],
            "step_type": step_config["type"],
            "logs": exec_logger.get_logs()
        }


@shared_task(bind=True)
def execute_with_retry(self, step_config: Dict[str, Any], context: Dict[str, Any], 
                       workflow_name: str, max_attempts: int = 3, delay_seconds: int = 1,
                       retry_on_status_codes: list = None, retry_on_exceptions: list = None,
                       allow_unsafe_retries: bool = False):
    if retry_on_status_codes is None:
        retry_on_status_codes = [408, 429, 500, 502, 503, 504]
    if retry_on_exceptions is None:
        retry_on_exceptions = ["connection_error", "timeout", "request_exception"]
    
    wrapped_step = step_config["config"]["step"]
    exec_logger = ExecutionLogger(workflow_name)
    last_result = None
    
    for attempt in range(1, max_attempts + 1):
        exec_logger.log_step_start(wrapped_step["id"], wrapped_step["type"])
        
        try:
            step_class = STEP_REGISTRY.get(wrapped_step["type"])
            if not step_class:
                raise ValueError(f"Unknown step type: {wrapped_step['type']}")
            
            step = step_class(wrapped_step)
            result = step.execute(context, exec_logger)
            last_result = result
            
            if result.success:
                exec_logger.log_step_complete(wrapped_step["id"], wrapped_step["type"], result.data)
                return {
                    "success": True,
                    "data": result.data,
                    "step_id": step_config["id"],
                    "wrapped_step_id": wrapped_step["id"],
                    "attempts": attempt,
                    "logs": exec_logger.get_logs()
                }
            else:
                if attempt < max_attempts:
                    safe_to_retry = _is_safe_to_retry(result, retry_on_status_codes, retry_on_exceptions)
                    
                    if not safe_to_retry and not allow_unsafe_retries:
                        exec_logger.logger.warning(
                            f"Step [{wrapped_step['id']}] failed but is not safe to retry. "
                            f"Skipping remaining retries to avoid duplicate execution on idempotent interface."
                        )
                        break
                    
                    exec_logger.log_step_retry(wrapped_step["id"], wrapped_step["type"], attempt, max_attempts)
                    time.sleep(delay_seconds)
                else:
                    exec_logger.log_step_failed(wrapped_step["id"], wrapped_step["type"], 
                                                result.error or Exception("Max retries exceeded"))
                    return {
                        "success": False,
                        "error": str(result.error) if result.error else "Max retries exceeded",
                        "step_id": step_config["id"],
                        "wrapped_step_id": wrapped_step["id"],
                        "attempts": attempt,
                        "logs": exec_logger.get_logs()
                    }
                    
        except Exception as e:
            if attempt < max_attempts:
                exec_logger.log_step_retry(wrapped_step["id"], wrapped_step["type"], attempt, max_attempts)
                time.sleep(delay_seconds)
            else:
                exec_logger.log_step_failed(wrapped_step["id"], wrapped_step["type"], e)
                return {
                    "success": False,
                    "error": str(e),
                    "step_id": step_config["id"],
                    "wrapped_step_id": wrapped_step["id"],
                    "attempts": attempt,
                    "logs": exec_logger.get_logs()
                }
    
    if last_result and not last_result.success:
        exec_logger.log_step_failed(wrapped_step["id"], wrapped_step["type"], 
                                    last_result.error or Exception("Stopped retries due to safety concerns"))
        return {
            "success": False,
            "error": str(last_result.error) if last_result.error else "Stopped retries due to safety concerns",
            "step_id": step_config["id"],
            "wrapped_step_id": wrapped_step["id"],
            "attempts": attempt,
            "logs": exec_logger.get_logs()
        }


def _is_safe_to_retry(result, retry_on_status_codes: list, retry_on_exceptions: list) -> bool:
    data = result.data if result.data else {}
    
    if isinstance(data, dict):
        if "safe_to_retry" in data:
            return data["safe_to_retry"]
        
        if "status_code" in data:
            return data["status_code"] in retry_on_status_codes
        
        if "error_type" in data:
            return data["error_type"] in retry_on_exceptions
    
    return True
