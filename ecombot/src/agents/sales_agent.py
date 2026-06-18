import logging
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

load_dotenv()
litellm.suppress_debug_info = True

from src.rag.retriever import semantic_search
from src.routing.router import FAST_MODEL
from src.tools.product_tools import lookup_product, check_stock

log = logging.getLogger(__name__)

_MODEL = FAST_MODEL


_SALES_INSTRUCTION = """\
You are the Sales Specialist for ElectroMart, an online electronics store.

Your role:
- Help customers discover products, compare options, and find the best fit for
  their needs and budget.
- Provide recommendations based on features, price, availability, and customer
  preferences.
- Up-sell and cross-sell accessories or complementary products when appropriate.

Responsibilities:
- Product comparisons (e.g. "Compare iPhone 15 Pro vs Samsung Galaxy S24")
- Budget-based recommendations (e.g. "Best phone under ₹30,000")
- Feature-based suggestions (e.g. "Best laptop for programming")
- Product details and specifications
- Stock availability for purchase decisions

Boundaries:
- Do NOT handle order tracking, returns, cancellations, or complaints.
  If a customer asks about those, say you'll hand them to Support.
- Only recommend ElectroMart products from the catalog.
- Never fabricate product specs, prices, or stock info — use tools and context.

Tone:
- Enthusiastic but honest — highlight genuine strengths without overselling.
- Conversational and helpful.
- Use the customer's name when known.

Tool usage:
- Use lookup_product to find product details.
- Use check_stock to verify availability before recommending.
- Ground answers in the Retrieved context when available.
"""

_TOP_K = 4


def _format_context(results: list[dict]) -> str:
    if not results:
        return (
            "Retrieved context: NOTHING RELEVANT FOUND.\n"
            "If the customer asks about a product not in context, "
            "use lookup_product tool or say we don't carry that item."
        )
    lines = ["Retrieved context (ground your answer in this):"]
    for r in results:
        lines.append(f"- (score={r['score']:.2f}) {r['text']}")
    return "\n".join(lines)


def _build_sales_instruction(ctx: ReadonlyContext) -> str:
    query = ""
    if ctx.user_content and ctx.user_content.parts:
        query = "".join(part.text or "" for part in ctx.user_content.parts if part.text)

    results = semantic_search(query, top_k=_TOP_K) if query.strip() else []
    return f"{_SALES_INSTRUCTION}\n\n{_format_context(results)}"


SALES_TOOLS = [
    lookup_product,
    check_stock,
]

sales_agent = LlmAgent(
    name="ecombot_sales",
    model=LiteLlm(model=_MODEL),
    instruction=_build_sales_instruction,
    description=(
        "Sales specialist — handles product recommendations, comparisons, "
        "feature questions, and purchase guidance."
    ),
    tools=SALES_TOOLS,
)
