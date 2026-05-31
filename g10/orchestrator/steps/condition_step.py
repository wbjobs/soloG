from typing import Dict, Any, List
from .base import BaseStep, StepResult


class ConditionStep(BaseStep):
    def execute(self, context: Dict[str, Any], logger) -> StepResult:
        try:
            condition = self.config.get("condition", "")
            then_steps = self.config.get("then", [])
            else_steps = self.config.get("else", [])

            logger.logger.info(f"Evaluating condition: {condition}")
            condition_result = self._evaluate_condition(condition, context)
            
            logger.log_condition_branch(self.id, condition, condition_result, "then" if condition_result else "else")

            if condition_result:
                branch_steps = then_steps
                branch_name = "then"
            else:
                branch_steps = else_steps
                branch_name = "else"

            return StepResult(
                success=True,
                data={
                    "condition_result": condition_result,
                    "branch": branch_name,
                    "branch_steps": branch_steps
                }
            )

        except Exception as e:
            return StepResult(success=False, error=e)
