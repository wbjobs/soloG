import requests
from typing import Dict, Any
from .base import BaseStep, StepResult


class HttpStep(BaseStep):
    SAFE_RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    
    def execute(self, context: Dict[str, Any], logger) -> StepResult:
        try:
            method = self._resolve_variables(self.config.get("method", "GET"), context)
            url = self._resolve_variables(self.config.get("url", ""), context)
            headers = self._resolve_variables(self.config.get("headers", {}), context)
            body = self._resolve_variables(self.config.get("body"), context)
            timeout = self.config.get("timeout", 30)
            query_params = self._resolve_variables(self.config.get("query_params", {}), context)
            idempotency_key = self._resolve_variables(self.config.get("idempotency_key"), context)
            
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
                logger.logger.info(f"Using idempotency key: {idempotency_key}")

            logger.logger.info(f"Executing HTTP {method} request to: {url}")

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if isinstance(body, (dict, list)) else None,
                data=body if isinstance(body, str) else None,
                params=query_params,
                timeout=timeout
            )

            result_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }

            try:
                response.raise_for_status()
                result_data["safe_to_retry"] = False
                return StepResult(success=True, data=result_data)
            except requests.exceptions.HTTPError as e:
                result_data["safe_to_retry"] = response.status_code in self.SAFE_RETRY_STATUS_CODES
                result_data["error"] = str(e)
                return StepResult(success=False, error=e, data=result_data)

        except requests.exceptions.ConnectionError as e:
            return StepResult(
                success=False, 
                error=e, 
                data={"error": str(e), "safe_to_retry": True, "error_type": "connection_error"}
            )
        except requests.exceptions.Timeout as e:
            return StepResult(
                success=False, 
                error=e, 
                data={"error": str(e), "safe_to_retry": True, "error_type": "timeout"}
            )
        except requests.exceptions.TooManyRedirects as e:
            return StepResult(
                success=False, 
                error=e, 
                data={"error": str(e), "safe_to_retry": False, "error_type": "too_many_redirects"}
            )
        except requests.exceptions.RequestException as e:
            return StepResult(
                success=False, 
                error=e, 
                data={"error": str(e), "safe_to_retry": True, "error_type": "request_exception"}
            )
        except Exception as e:
            return StepResult(
                success=False, 
                error=e,
                data={"error": str(e), "safe_to_retry": False, "error_type": "unknown"}
            )
