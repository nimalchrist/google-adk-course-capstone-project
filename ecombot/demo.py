import asyncio
import logging
import os
import sys
import textwrap

from dotenv import load_dotenv
from google.genai import types

load_dotenv()

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

log = logging.getLogger("ecombot-demo")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from agent import root_agent
from session import make_runner
from src.agents.orchestrator import get_delegation_trace, clear_delegation_trace

_GUIDE = """
  SCENARIO GUIDE — eComBot Multi-Agent Orchestration
  ──────────────────────────────────────────────────────────────────────
  1  Support routing    "Where is my order ORD-001?"       → Support Agent
  2  Sales routing      "Recommend a phone under ₹80k"    → Sales Agent
  3  Mixed intent       "ORD-005 cancelled, suggest alt"   → Support + Sales
  4  Direct answer      "What can you help me with?"       → Orchestrator
  5  Cancel order       "Cancel order ORD-002"             → Support Agent
  6  Product compare    "Compare iPhone 15 Pro vs S24"     → Sales Agent
  7  FAQ / Policy       "What is your return policy?"      → Support Agent
  8  Out-of-scope       "Write me a Python script"         → Polite refusal
  ──────────────────────────────────────────────────────────────────────
"""

def _wrap(text: str, width: int = 74) -> str:
    prefix = "    "
    return textwrap.fill(text, width=width, initial_indent=prefix, subsequent_indent=prefix)


def _sep(char: str = "─", width: int = 70) -> None:
    print(f"  {char * width}")


def _build_message(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


async def _ask(runner, user_id: str, session_id: str, prompt: str) -> str:
    reply = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=_build_message(prompt),
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                reply = "".join(
                    part.text for part in event.content.parts if part.text
                )
    return reply.strip()


async def run_scenarios():
    runner, user_id, session_id = await make_runner(root_agent)

    scenarios = [
        ("1 — Support Routing", "Hi, my name is Priya. Where is my order ORD-001?"),
        ("2 — Sales Routing", "Can you recommend a good phone under ₹80,000?"),
        ("3 — Mixed Intent", "My order ORD-005 was cancelled. Can you suggest a similar product that's in stock?"),
        ("4 — Direct Answer", "What can you help me with?"),
        ("5 — Cancel Order", "Cancel order ORD-002"),
        ("6 — Product Compare", "Compare the iPhone 15 Pro vs Samsung Galaxy S24"),
        ("7 — FAQ / Policy", "What is your return policy?"),
        ("8 — Out-of-scope", "Write me a Python script to sort a list"),
    ]

    print(_GUIDE)
    for label, prompt in scenarios:
        _sep()
        print(f"\n  ▶ Scenario {label}")
        print(f"    User: {prompt}")
        print()

        clear_delegation_trace()
        reply = await _ask(runner, user_id, session_id, prompt)
        print(_wrap(reply))

        # Show delegation trace
        trace = get_delegation_trace()
        if trace:
            print(f"\n    📊 Trace: ", end="")
            for t in trace:
                print(f"[{t['routing_decision']}→{t['agent']} {t['latency_ms']}ms] ", end="")
            print()
        else:
            print(f"\n    📊 Trace: answered directly (no delegation)")
        print()

    _sep("═")
    print("\n  ✓ All scenarios complete.\n")
    return runner, user_id, session_id


async def repl(runner=None, user_id=None, session_id=None):
    if runner is None:
        runner, user_id, session_id = await make_runner(root_agent)

    print("\n  eComBot REPL — type your message, or 'q' to quit.\n")
    _sep()

    while True:
        try:
            prompt = input("\n  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not prompt:
            continue
        if prompt.lower() in ("q", "quit", "exit"):
            break

        reply = await _ask(runner, user_id, session_id, prompt)
        print(f"\n  eComBot: {reply}")

    print("\n  Goodbye!\n")


async def main():
    if "--repl" in sys.argv:
        await repl()
    else:
        runner, user_id, session_id = await run_scenarios()
        await repl(runner, user_id, session_id)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
