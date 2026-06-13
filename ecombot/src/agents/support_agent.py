"""
support_agent.py — eComBot Support Agent (Day 01 → Day 08 evolution)
=====================================================================
The main eComBot support agent. Evolved through all 8 days:
  Day 01-02: Basic LLM agent with refined instructions.
  Day 03:    Tool calling + in-memory session state.
  Day 04:    PostgreSQL-backed tools + Redis session persistence.
  Day 05-06: RAG grounding with ChromaDB knowledge base.
  Day 07:    LiteLLM routing (fast-faq vs deep-support).
  Day 08:    FastMCP external tool servers.

ADK Web:
    adk web .   ← discovers root_agent via agent.py
"""

import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

# ── Silence noisy loggers ──────────────────────────────────────────────────
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

litellm.suppress_debug_info = True
load_dotenv()

from src.tools.order_tools import get_order_status, cancel_order, save_customer_name, get_session_summary
from src.tools.product_tools import lookup_product, check_stock
from src.rag.retriever import semantic_search
from src.routing.router import FAST_MODEL, DEEP_MODEL, classify_query

# ── Model ──────────────────────────────────────────────────────────────────
_MODEL = FAST_MODEL

# ── Load instruction from file ─────────────────────────────────────────────
_INSTRUCTIONS_DIR = Path(__file__).parent
_BASE_INSTRUCTION = (_INSTRUCTIONS_DIR / "support_instructions_v2.txt").read_text()

# ── RAG Grounding Rules ────────────────────────────────────────────────────
_GROUNDING_RULES = """
Grounding rules (for product/FAQ questions):
- When answering product or policy questions, ONLY use information from the
  "Retrieved context" section below — never fall back on general knowledge.
- If the retrieved context says nothing relevant, say so plainly — for example
  "I don't have that information in our knowledge base" — instead of guessing.
- For order-related queries, use the appropriate tool instead of the knowledge base.
"""

_TOOL_RULES = """
Tool usage rules:
- When a customer asks about their order status, use get_order_status.
  Ask for the order ID if not provided.
- When a customer wants to cancel an order, use cancel_order.
  Confirm the order ID before proceeding.
- When a customer asks about a product, use lookup_product.
- When a customer asks about stock/availability, use check_stock.
- When a customer introduces themselves, use save_customer_name immediately.
- Use get_session_summary when asked for a conversation summary.
- Do NOT guess order details or product info — always use tools.
- Use the tool output directly in your response.
- If a tool returns an error, relay it clearly without exposing technical details.
"""

_TOP_K = 3


def _format_context(results: list[dict]) -> str:
    """Render retrieved chunks (or their absence) as an instruction section."""
    if not results:
        return (
            "Retrieved context: NOTHING RELEVANT FOUND.\n"
            "Follow the fallback rule above — say plainly that you don't have "
            "grounded information on this topic."
        )
    lines = ["Retrieved context (ground your answer in this only):"]
    for r in results:
        lines.append(f"- (similarity={r['score']:.2f}) {r['text']}")
    return "\n".join(lines)


def _build_instruction(ctx: ReadonlyContext) -> str:
    """
    InstructionProvider: runs once per turn, before the model is called.
    Retrieves relevant knowledge-base chunks and appends them to the instruction.
    """
    query = ""
    if ctx.user_content and ctx.user_content.parts:
        query = "".join(part.text or "" for part in ctx.user_content.parts if part.text)

    results = semantic_search(query, top_k=_TOP_K) if query.strip() else []
    return (
        f"{_BASE_INSTRUCTION}\n\n"
        f"{_TOOL_RULES}\n\n"
        f"{_GROUNDING_RULES}\n\n"
        f"{_format_context(results)}"
    )


# ── Tools list ─────────────────────────────────────────────────────────────
TOOLS = [
    get_order_status,
    cancel_order,
    lookup_product,
    check_stock,
    save_customer_name,
    get_session_summary,
]

# ── Support Agent (Day 01-06: tools + RAG) ─────────────────────────────────
support_agent = LlmAgent(
    name="ecombot_support",
    model=LiteLlm(model=_MODEL),
    instruction=_build_instruction,
    description=(
        "eComBot support agent — handles order tracking, product queries, "
        "cancellations, and knowledge-grounded FAQ answers."
    ),
    tools=TOOLS,
)

# ── FAQ Agent (Day 07: fast-faq route) ─────────────────────────────────────
faq_agent = LlmAgent(
    name="ecombot_faq",
    model=LiteLlm(model=FAST_MODEL),
    instruction=_build_instruction,
    description="eComBot FAQ agent — fast route for simple product/policy questions.",
    tools=TOOLS,
)

# ── Deep Support Agent (Day 07: deep-support route) ────────────────────────
deep_support_agent = LlmAgent(
    name="ecombot_deep_support",
    model=LiteLlm(model=DEEP_MODEL),
    instruction=_build_instruction,
    description="eComBot deep support agent — stronger model for complex queries.",
    tools=TOOLS,
)
