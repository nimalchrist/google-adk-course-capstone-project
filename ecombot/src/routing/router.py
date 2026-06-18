import os

import litellm
from litellm import Router

FAST_MODEL = "openrouter/google/gemini-2.5-flash"
DEEP_MODEL = "openrouter/google/gemini-2.5-pro"
BACKUP_MODEL = "openrouter/openai/gpt-4o-mini"

routing_log: list[dict] = []


def _on_success(kwargs, completion_response, start_time, end_time) -> None:
    model = (
        kwargs.get("litellm_params", {}).get("model")
        or kwargs.get("model", "unknown")
    )
    ms = round((end_time - start_time).total_seconds() * 1000)
    routing_log.append({"status": "success", "model": model, "latency_ms": ms})


def _on_failure(kwargs, completion_response, start_time, end_time) -> None:
    model = (
        kwargs.get("litellm_params", {}).get("model")
        or kwargs.get("model", "unknown")
    )
    exc = kwargs.get("exception")
    routing_log.append({
        "status": "failure",
        "model": model,
        "error": type(exc).__name__ if exc else "unknown",
    })


def enable_routing_callbacks() -> None:
    if _on_success not in litellm.success_callback:
        litellm.success_callback.append(_on_success)
    if _on_failure not in litellm.failure_callback:
        litellm.failure_callback.append(_on_failure)


def _params(model: str, timeout: float = 30.0) -> dict:
    return {
        "model": model,
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "api_base": "https://openrouter.ai/api/v1",
        "timeout": timeout,
    }


def _make_router(
    primary: str,
    backup: str,
    *,
    primary_timeout: float = 30.0,
    num_retries: int = 0,
) -> Router:
    return Router(
        model_list=[
            {"model_name": "primary", "litellm_params": _params(primary, primary_timeout)},
            {"model_name": "backup", "litellm_params": _params(backup)},
        ],
        fallbacks=[{"primary": ["backup"]}],
        num_retries=num_retries,
        retry_after=1,
        allowed_fails=1,
        cooldown_time=5,
    )


faq_router = _make_router(FAST_MODEL, BACKUP_MODEL)
support_router = _make_router(DEEP_MODEL, BACKUP_MODEL)

fallback_demo_router = _make_router(
    primary="openrouter/google/bad-model-xyz",
    backup=BACKUP_MODEL,
    num_retries=1,
)

timeout_demo_router = _make_router(
    primary=DEEP_MODEL,
    backup=BACKUP_MODEL,
    primary_timeout=0.001,
    num_retries=0,
)


_DEEP_SIGNALS = {
    "compare", "comparison", "recommend", "recommendation", "which is better",
    "pros and cons", "detailed", "explain in detail", "complex",
    "multiple products", "budget", "help me choose", "troubleshoot",
    "not working", "problem", "issue", "complaint", "escalate",
}


def classify_query(prompt: str) -> str:
    lower = prompt.lower()
    if any(sig in lower for sig in _DEEP_SIGNALS):
        return "deep-support"
    return "fast-faq"
