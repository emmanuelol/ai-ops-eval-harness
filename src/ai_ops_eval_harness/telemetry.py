"""High-resolution latency, token counting, and rate-limit backoff decorators for LLM APIs."""

import time
import functools
import logging
from typing import Callable, Optional, Any, Dict

logger = logging.getLogger(__name__)


def track_llm_telemetry(
    retries: int = 3,
    base_backoff: float = 2.0,
    on_alert: Optional[Callable[[Dict[str, Any]], None]] = None,
):
    """Decorator to measure execution latency, record token usage, and manage 429 rate limits.
    
    Wraps LLM calling functions returning objects with an optional `usage_metadata` attribute.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            last_exception = None

            for attempt in range(retries):
                try:
                    response = func(*args, **kwargs)
                    latency = time.perf_counter() - start_time

                    tokens = "UNKNOWN"
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        tokens = getattr(response.usage_metadata, "total_token_count", "UNKNOWN")
                    elif isinstance(response, dict) and "usage_metadata" in response:
                        tokens = response["usage_metadata"].get("total_token_count", "UNKNOWN")

                    model = kwargs.get("model", "UNKNOWN_MODEL")
                    logger.info(
                        f"LLM_TELEMETRY | Model: {model} | Latency: {latency:.2f}s | Tokens: {tokens} | Attempt: {attempt + 1}"
                    )
                    return response

                except Exception as e:
                    last_exception = e
                    is_rate_limit = "429" in str(e) or "resource exhausted" in str(e).lower()

                    if (is_rate_limit or attempt < retries - 1) and attempt < retries - 1:
                        sleep_time = base_backoff ** (attempt + 1)
                        logger.warning(
                            f"LLM_TELEMETRY_RETRY | API Error | Retrying in {sleep_time}s (Attempt {attempt + 1}/{retries})..."
                        )
                        time.sleep(sleep_time)
                        continue

                    # Exhaustion reached
                    latency = time.perf_counter() - start_time
                    model = kwargs.get("model", "UNKNOWN_MODEL")
                    error_payload = {
                        "event": "LLM_TELEMETRY_EXHAUSTION",
                        "model": model,
                        "latency_seconds": round(latency, 4),
                        "attempts": attempt + 1,
                        "error": str(e),
                    }
                    logger.error(f"LLM_TELEMETRY_ERROR | {error_payload}")

                    if on_alert:
                        try:
                            on_alert(error_payload)
                        except Exception as alert_err:
                            logger.error(f"Failed to trigger on_alert callback: {alert_err}")

                    raise last_exception

        return wrapper
    return decorator
