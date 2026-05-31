from typing import Dict, Any
from .base import BaseStep, StepResult


class NoopStep(BaseStep):
    def execute(self, context: Dict[str, Any], logger) -> StepResult:
        logger.logger.info(f"Executing Noop step: {self.id}")
        return StepResult(success=True, data={"message": "Noop step completed"})
