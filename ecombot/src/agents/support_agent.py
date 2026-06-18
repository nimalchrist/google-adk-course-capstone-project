import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

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
from src.routing.router import FAST_MODEL, DEEP_MODEL

_MODEL = FAST_MODEL

_INSTRUCTIONS_DIR = Path(__file__).parent
_BASE_INSTRUCTION = (_INSTRUCTIONS_DIR / "support_instructions_v2.txt").read_text()

_SUPPORT_SCOPE = """
Your scope as the Support Agent:
- Order tracking, delivery status, and ETAs
- Order cancellations, returns, and refunds
- Customer complaints and issue resolution
- Account and payment problems
- Warranty and repair questions
- Shipping and logistics queries

You do NOT handle:
- Product recommendations or comparisons (that's the Sales Agent)
- Helping users choose what to buy
- Upselling or cross-selling

If a customer asks about something outside your scope, just answer what you
can and note that product recommendations are handled separately.
"""

_GROUNDING_RULES = """
Grounding rules (for FAQ/policy questions):
- When answering policy questions (returns policy, warranty, shipping times),
  ONLY use information from the "Retrieved context" section below.
- If the retrieved context says nothing relevant, say so plainly.
- For order-related queries, use the appropriate tool instead of the knowledge base.
"""

_TOOL_RULES = """
Tool usage rules:
- When a customer asks about their order status, use get_order_status.
  Ask for the order ID (format: ORD-XXX) if not provided.
- When a customer wants to cancel an order, use cancel_order.
  Confirm the order ID before proceeding.
- When a customer asks about a product's stock availability for an existing
  order issue, use check_stock.
- When a customer introduces themselves, use save_customer_name immediately.
- Use get_session_summary when asked for a conversation summary.
- Do NOT guess order details — always use tools.
- If a tool returns an error, relay it clearly without exposing technical details.
"""

_TOP_K = 3


def _format_context(results: list[dict]) -> str:
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
    query = ""
    if ctx.user_content and ctx.user_content.parts:
        query = "".join(part.text or "" for part in ctx.user_content.parts if part.text)

    results = semantic_search(query, top_k=_TOP_K) if query.strip() else []
    return (
        f"{_BASE_INSTRUCTION}\n\n"
        f"{_SUPPORT_SCOPE}\n\n"
        f"{_TOOL_RULES}\n\n"
        f"{_GROUNDING_RULES}\n\n"
        f"{_format_context(results)}"
    )


TOOLS = [
    get_order_status,
    cancel_order,
    check_stock,
    save_customer_name,
    get_session_summary,
]

support_agent = LlmAgent(
    name="ecombot_support",
    model=LiteLlm(model=_MODEL),
    instruction=_build_instruction,
    description=(
        "Support specialist — handles order tracking, cancellations, returns, "
        "refunds, complaints, and policy FAQ answers."
    ),
    tools=TOOLS,
)

faq_agent = LlmAgent(
    name="ecombot_faq",
    model=LiteLlm(model=FAST_MODEL),
    instruction=_build_instruction,
    description="eComBot FAQ agent — fast route for simple policy questions.",
    tools=TOOLS,
)

deep_support_agent = LlmAgent(
    name="ecombot_deep_support",
    model=LiteLlm(model=DEEP_MODEL),
    instruction=_build_instruction,
    description="eComBot deep support agent — stronger model for complex queries.",
    tools=TOOLS,
)
