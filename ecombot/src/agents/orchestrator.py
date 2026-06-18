import asyncio
import logging
import time
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.sales_agent import sales_agent
from src.agents.support_agent import support_agent
from src.routing.router import FAST_MODEL

log = logging.getLogger(__name__)

_MODEL = FAST_MODEL

delegation_trace: list[dict] = []


def get_delegation_trace() -> list[dict]:
    return delegation_trace


def clear_delegation_trace() -> None:
    delegation_trace.clear()


async def _run_specialist(agent: LlmAgent, user_text: str) -> dict[str, Any]:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="ecombot_orchestrator",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="ecombot_orchestrator",
        user_id="orchestrator_internal",
    )

    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_text)],
    )

    tool_calls: list[str] = []
    final_text = ""

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        if event.actions and event.actions.tool_code_execution_result:
            tool_calls.append("code_execution")

        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls.append(part.function_call.name)
                if hasattr(part, "text") and part.text:
                    final_text = part.text

        if event.is_final_response():
            if event.content and event.content.parts:
                texts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                if texts:
                    final_text = "\n".join(texts)

    return {
        "reply": final_text,
        "tools_used": tool_calls,
        "agent_name": agent.name,
    }


def delegate_to_support_agent(
    user_message: str,
) -> dict[str, Any]:
    """
    Delegate a support-related query to the Support Agent.
    Use this when the user asks about order status, returns, cancellations,
    delivery issues, complaints, or refunds.

    Args:
        user_message: The user's message or the support-related portion of it.

    Returns:
        A dict with the Support Agent's reply and tools it used internally.
    """
    start = time.time()
    log.info("Delegating to Support Agent: %s", user_message[:80])

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, _run_specialist(support_agent, user_message)
                ).result(timeout=30)
        else:
            result = asyncio.run(_run_specialist(support_agent, user_message))
    except Exception as exc:
        log.error("Support Agent delegation failed: %s", exc)
        result = {
            "reply": f"I'm sorry, I encountered an issue contacting our support team. Error: {exc}",
            "tools_used": [],
            "agent_name": "ecombot_support",
        }

    elapsed_ms = round((time.time() - start) * 1000)

    delegation_trace.append({
        "timestamp": time.time(),
        "routing_decision": "support",
        "user_message": user_message[:200],
        "agent": result["agent_name"],
        "tools_used": result["tools_used"],
        "latency_ms": elapsed_ms,
        "success": "Error" not in result.get("reply", ""),
    })

    return {
        "agent": "Support Agent",
        "response": result["reply"],
        "tools_used": result["tools_used"],
    }


def delegate_to_sales_agent(
    user_message: str,
) -> dict[str, Any]:
    """
    Delegate a sales-related query to the Sales Agent.
    Use this when the user asks for product recommendations, comparisons,
    pricing, availability for purchase, or feature-based suggestions.

    Args:
        user_message: The user's message or the sales-related portion of it.

    Returns:
        A dict with the Sales Agent's reply and tools it used internally.
    """
    start = time.time()
    log.info("Delegating to Sales Agent: %s", user_message[:80])

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, _run_specialist(sales_agent, user_message)
                ).result(timeout=30)
        else:
            result = asyncio.run(_run_specialist(sales_agent, user_message))
    except Exception as exc:
        log.error("Sales Agent delegation failed: %s", exc)
        result = {
            "reply": f"I'm sorry, I encountered an issue contacting our sales team. Error: {exc}",
            "tools_used": [],
            "agent_name": "ecombot_sales",
        }

    elapsed_ms = round((time.time() - start) * 1000)

    delegation_trace.append({
        "timestamp": time.time(),
        "routing_decision": "sales",
        "user_message": user_message[:200],
        "agent": result["agent_name"],
        "tools_used": result["tools_used"],
        "latency_ms": elapsed_ms,
        "success": "Error" not in result.get("reply", ""),
    })

    return {
        "agent": "Sales Agent",
        "response": result["reply"],
        "tools_used": result["tools_used"],
    }


_ORCHESTRATOR_INSTRUCTION = """\
You are the eComBot Orchestrator for ElectroMart, an online electronics store.

Your role:
- Receive all user messages and decide who should handle them.
- Route to the correct specialist agent using delegation tools.
- Combine results when a query spans both support and sales.
- Answer trivial/meta questions yourself without delegating.

Routing rules:
1. **Support queries** → delegate_to_support_agent
   - Order status, tracking, delivery ETAs
   - Cancellations, returns, refunds
   - Complaints or issues with orders
   - Account or payment problems
   - Keywords: "order", "ORD-", "cancel", "return", "refund", "delivery",
     "shipped", "track", "complaint", "issue", "problem"

2. **Sales queries** → delegate_to_sales_agent
   - Product recommendations and comparisons
   - Budget-based suggestions
   - Feature queries and product specs
   - Stock availability for purchasing decisions
   - Keywords: "recommend", "compare", "suggest", "best", "buy",
     "price", "budget", "looking for", "which phone", "specs"

3. **Mixed queries** (both support + sales):
   - First delegate the support part to the Support Agent.
   - Then use the Support Agent's answer as context and delegate
     the sales part to the Sales Agent.
   - Combine both results into a coherent final answer.

4. **Meta/trivial queries** → answer directly (no delegation):
   - "What can you do?", "Hello", "Thanks", "Who are you?"
   - Simple greetings and goodbyes.

Response guidelines:
- When you delegate, present the specialist's reply naturally to the user.
  Do NOT say "The Support Agent said..." — just give the answer directly.
- For mixed queries, clearly separate the support answer from the sales
  recommendation with appropriate transitions.
- Always be helpful, warm, and professional.
- Use the customer's name when known.
"""


orchestrator_agent = LlmAgent(
    name="ecombot_orchestrator",
    model=LiteLlm(model=_MODEL),
    instruction=_ORCHESTRATOR_INSTRUCTION,
    description=(
        "eComBot Orchestrator — routes user queries to Support or Sales "
        "specialists, handles mixed intents via Planner-Executor pattern, "
        "and answers meta questions directly."
    ),
    tools=[
        delegate_to_support_agent,
        delegate_to_sales_agent,
    ],
)
