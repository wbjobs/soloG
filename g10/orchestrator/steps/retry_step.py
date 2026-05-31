from typing import Dict, Any
from .base import BaseStep, StepResult


class RetryStep(BaseStep):
    def execute(self, context: Dict[str, Any], logger) -> StepResult:
        try:
            max_attempts = self.config.get("max_attempts", 3)
            delay_seconds = self.config.get("delay_seconds", 1)
            wrapped_step = self.config.get("step")

            return StepResult(
                success=True,
                data={
                    "max_attempts": max_attempts,
                    "delay_seconds": delay_seconds,
                    "wrapped_step": wrapped_step
                }
            )

        except Exception as e:
            return StepResult(success=False, error=e)
