"""
router.py — LiteLLM routing and fallback configuration for eComBot
===================================================================
Day 07: Route queries by complexity and protect against provider failures.

Two model groups:
  fast-faq       → lower-latency model for FAQ-style answers
  deep-support   → stronger model for complex multi-step queries

Fallback routers for resilience testing:
  fallback_demo_router  — primary is non-existent (error → fallback)
  timeout_demo_router   — primary has near-zero timeout (timeout → fallback)

Public API:
    FAST_MODEL, DEEP_MODEL, BACKUP_MODEL
    classify_query(prompt) → "fast-faq" | "deep-support"
    routing_log  — list of routing events for observability
    enable_routing_callbacks()
"""

import os

import litellm
from litellm import Router

# ── Model identifiers (single source of truth) ─────────────────────────────
FAST_MODEL = "openrouter/google/gemini-2.5-flash"       # fast, cost-effective
DEEP_MODEL = "openrouter/google/gemini-2.5-pro"         # stronger reasoning
BACKUP_MODEL = "openrouter/openai/gpt-4o-mini"          # cross-provider fallback

# ── Routing event capture ──────────────────────────────────────────────────
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
    """Attach routing event callbacks to litellm. Call once at startup."""
    if _on_success not in litellm.success_callback:
        litellm.success_callback.append(_on_success)
    if _on_failure not in litellm.failure_callback:
        litellm.failure_callback.append(_on_failure)


# ── Router factory ─────────────────────────────────────────────────────────

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


# ── Named routers ─────────────────────────────────────────────────────────
faq_router = _make_router(FAST_MODEL, BACKUP_MODEL)
support_router = _make_router(DEEP_MODEL, BACKUP_MODEL)

# Fallback demo: primary model doesn't exist → fallback fires
fallback_demo_router = _make_router(
    primary="openrouter/google/bad-model-xyz",
    backup=BACKUP_MODEL,
    num_retries=1,
)

# Timeout demo: near-zero timeout → timeout → fallback
timeout_demo_router = _make_router(
    primary=DEEP_MODEL,
    backup=BACKUP_MODEL,
    primary_timeout=0.001,
    num_retries=0,
)


# ── Query classifier ───────────────────────────────────────────────────────

_DEEP_SIGNALS = {
    "compare", "comparison", "recommend", "recommendation", "which is better",
    "pros and cons", "detailed", "explain in detail", "complex",
    "multiple products", "budget", "help me choose", "troubleshoot",
    "not working", "problem", "issue", "complaint", "escalate",
}


def classify_query(prompt: str) -> str:
    """
    Return 'fast-faq' or 'deep-support' based on prompt content.
    Simple keyword-based classification — in production this runs at
    the gateway as a pre-call hook.
    """
    lower = prompt.lower()
    if any(sig in lower for sig in _DEEP_SIGNALS):
        return "deep-support"
    return "fast-faq"
