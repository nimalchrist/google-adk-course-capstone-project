import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

import chainlit as cl
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.orchestrator import orchestrator_agent, get_delegation_trace, clear_delegation_trace

log = logging.getLogger("ecombot-ui")

_session_service = InMemorySessionService()
_runner = Runner(
    agent=orchestrator_agent,
    app_name="ecombot_chainlit",
    session_service=_session_service,
)


@cl.on_chat_start
async def on_chat_start():
    session = await _session_service.create_session(
        app_name="ecombot_chainlit",
        user_id="chainlit_user",
    )
    cl.user_session.set("session_id", session.id)
    cl.user_session.set("user_id", session.user_id)
    cl.user_session.set("context", {})

    await cl.Message(
        content=(
            "👋 **Welcome to ElectroMart!**\n\n"
            "I'm your shopping assistant. I can help you with:\n"
            "- 📦 **Order tracking** — check status, delivery ETA\n"
            "- 🛒 **Product recommendations** — find the perfect device\n"
            "- 🔄 **Returns & cancellations** — manage your orders\n"
            "- ❓ **FAQs** — return policy, warranty, shipping\n\n"
            "How can I help you today?"
        ),
    ).send()

    actions = [
        cl.Action(name="check_order", payload={"action": "check_order"}, label="📦 Check Order"),
        cl.Action(name="recommend", payload={"action": "recommend"}, label="🛒 Get Recommendations"),
        cl.Action(name="return_policy", payload={"action": "return_policy"}, label="🔄 Return Policy"),
    ]
    await cl.Message(content="**Quick actions:**", actions=actions).send()


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    user_id = cl.user_session.get("user_id")

    if not session_id:
        await cl.Message(content="Session expired. Please refresh the page.").send()
        return

    ctx = cl.user_session.get("context") or {}
    ctx["last_message"] = message.content
    cl.user_session.set("context", ctx)

    clear_delegation_trace()

    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message.content)],
    )

    start_time = time.time()
    final_text = ""
    tool_calls_seen = []

    async with cl.Step(name="🧠 Processing", type="run") as main_step:
        main_step.input = message.content

        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_name = part.function_call.name
                        tool_calls_seen.append(tool_name)

            if event.is_final_response():
                if event.content and event.content.parts:
                    texts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                    if texts:
                        final_text = "\n".join(texts)

        elapsed_ms = round((time.time() - start_time) * 1000)
        main_step.output = f"Completed in {elapsed_ms}ms"

    trace = get_delegation_trace()
    if trace:
        for t in trace:
            async with cl.Step(
                name=f"🔀 {t['agent']} ({t['routing_decision']})",
                type="tool",
            ) as trace_step:
                trace_step.input = t["user_message"][:100]
                tools_str = ", ".join(t["tools_used"]) if t["tools_used"] else "none"
                trace_step.output = f"Tools: {tools_str} | Latency: {t['latency_ms']}ms"

    response_content = final_text or "I'm sorry, I couldn't process that request."

    elements = []
    if any(kw in response_content.lower() for kw in ["ord-", "order id", "shipped", "delivered", "processing"]):
        card = _build_order_card(response_content)
        if card:
            elements.append(card)

    if any(kw in response_content.lower() for kw in ["₹", "price", "stock", "specs", "features"]):
        card = _build_product_card(response_content)
        if card:
            elements.append(card)

    msg = cl.Message(content=response_content, elements=elements)
    await msg.send()

    await _show_contextual_actions(response_content, ctx)


@cl.action_callback("check_order")
async def on_check_order(action: cl.Action):
    await cl.Message(
        content="Please enter your order ID (e.g., ORD-001):"
    ).send()


@cl.action_callback("recommend")
async def on_recommend(action: cl.Action):
    actions = [
        cl.Action(name="budget_low", payload={"budget": "under_30k"}, label="Under ₹30,000"),
        cl.Action(name="budget_mid", payload={"budget": "30k_80k"}, label="₹30,000 – ₹80,000"),
        cl.Action(name="budget_high", payload={"budget": "above_80k"}, label="Above ₹80,000"),
    ]
    await cl.Message(
        content="What's your budget range?",
        actions=actions,
    ).send()


@cl.action_callback("return_policy")
async def on_return_policy(action: cl.Action):
    msg = cl.Message(content="What is your return policy?")
    await msg.send()
    await on_message(msg)


@cl.action_callback("budget_low")
async def on_budget_low(action: cl.Action):
    cl.user_session.set("budget", "under ₹30,000")
    msg = cl.Message(content="Recommend a phone under ₹30,000")
    await msg.send()
    await on_message(msg)


@cl.action_callback("budget_mid")
async def on_budget_mid(action: cl.Action):
    cl.user_session.set("budget", "₹30,000 to ₹80,000")
    msg = cl.Message(content="Recommend a phone between ₹30,000 and ₹80,000")
    await msg.send()
    await on_message(msg)


@cl.action_callback("budget_high")
async def on_budget_high(action: cl.Action):
    cl.user_session.set("budget", "above ₹80,000")
    msg = cl.Message(content="Recommend a premium phone above ₹80,000")
    await msg.send()
    await on_message(msg)


@cl.action_callback("view_details")
async def on_view_details(action: cl.Action):
    product_name = action.payload.get("product", "")
    if product_name:
        msg = cl.Message(content=f"Show me full details for {product_name}")
        await msg.send()
        await on_message(msg)


@cl.action_callback("check_stock_action")
async def on_check_stock_action(action: cl.Action):
    product_name = action.payload.get("product", "")
    if product_name:
        msg = cl.Message(content=f"Is {product_name} in stock?")
        await msg.send()
        await on_message(msg)


def _build_order_card(response: str) -> cl.Text | None:
    import re

    order_match = re.search(r"(ORD-\d{3,})", response, re.IGNORECASE)
    if not order_match:
        return None

    order_id = order_match.group(1).upper()

    lines = [f"📦 **Order Card: {order_id}**", ""]

    status_keywords = ["shipped", "delivered", "processing", "cancelled", "pending"]
    for kw in status_keywords:
        if kw in response.lower():
            lines.append(f"**Status:** {kw.capitalize()}")
            break

    eta_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", response)
    if eta_match:
        lines.append(f"**ETA:** {eta_match.group(1)}")

    if len(lines) > 2:
        return cl.Text(name=f"order_{order_id}", content="\n".join(lines), display="inline")
    return None


def _build_product_card(response: str) -> cl.Text | None:
    import re

    price_match = re.search(r"₹[\d,]+", response)
    if not price_match:
        return None

    if len(response) < 50:
        return None

    return cl.Text(
        name="product_info",
        content="🛍️ **Product details available in the response above.**",
        display="inline",
    )


async def _show_contextual_actions(response: str, ctx: dict):
    import re

    actions = []

    if re.search(r"ORD-\d{3,}", response, re.IGNORECASE):
        actions.append(
            cl.Action(name="check_order", payload={"action": "another_order"}, label="📦 Check Another Order")
        )

    product_keywords = ["iphone", "samsung", "galaxy", "pixel", "macbook", "airpods", "sony"]
    mentioned_products = [kw for kw in product_keywords if kw in response.lower()]
    if mentioned_products:
        actions.append(
            cl.Action(
                name="check_stock_action",
                payload={"product": mentioned_products[0]},
                label=f"📊 Check Stock",
            )
        )

    if any(kw in response.lower() for kw in ["cancelled", "cancel", "out of stock"]):
        actions.append(
            cl.Action(name="recommend", payload={"action": "recommend"}, label="🛒 Get Alternatives")
        )

    if actions:
        await cl.Message(content="**What would you like to do next?**", actions=actions).send()
