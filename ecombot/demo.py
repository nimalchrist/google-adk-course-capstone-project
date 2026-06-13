"""
demo.py — eComBot: Interactive demo and scenario runner
========================================================
Google ADK · LiteLLM · OpenRouter · ChromaDB · FastMCP

Runs scripted scenarios demonstrating all Day 01-08 features,
then drops into a free REPL for exploration.

Run:
    docker compose up -d          # start Postgres + Redis (Day 04)
    cp .env.example .env          # fill in OPENROUTER_API_KEY
    python demo.py                # run all scenarios
    python demo.py --repl         # skip scenarios, go straight to REPL
"""

import asyncio
import logging
import os
import sys
import textwrap

from dotenv import load_dotenv
from google.genai import types

load_dotenv()

# ── Silence LiteLLM noise ─────────────────────────────────────────────────
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

log = logging.getLogger("ecombot-demo")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from agent import root_agent, shutdown_orders_server
from session import make_runner

# ── Scenario guide ─────────────────────────────────────────────────────────
_GUIDE = """
  SCENARIO GUIDE — eComBot (Day 01-08 Features)
  ──────────────────────────────────────────────────────────────────────
  1  Order status       "Where is my order ORD-001?"
  2  Follow-up (state)  "What about ORD-002?"          ← session state
  3  Product lookup     "Show me the iPhone 15 Pro"
  4  Stock check        "Is the iPad Air in stock?"
  5  Cancel order       "Cancel order ORD-002"
  6  RAG / FAQ          "What is your return policy?"
  7  Out-of-scope       "Write me a Python script"     ← polite refusal
  8  MCP inventory      "What colors does the Pixel 9 Pro come in?"
  ──────────────────────────────────────────────────────────────────────
"""

# ── Console helpers ────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 74) -> str:
    prefix = "    "
    return textwrap.fill(text, width=width, initial_indent=prefix, subsequent_indent=prefix)


def _sep(char: str = "─", width: int = 70) -> None:
    print(f"  {char * width}")


def _build_message(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


# ── ADK ask helper ─────────────────────────────────────────────────────────

async def _ask(runner, user_id: str, session_id: str, prompt: str) -> str:
    """Send a prompt to the agent and return its reply."""
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


# ── Scenarios ──────────────────────────────────────────────────────────────

async def run_scenarios():
    """Run the scripted demo scenarios."""
    runner, user_id, session_id = await make_runner(root_agent)

    scenarios = [
        ("1 — Order Status", "Hi, my name is Priya. Where is my order ORD-001?"),
        ("2 — Follow-up (state)", "What about ORD-002?"),
        ("3 — Product Lookup", "Show me the iPhone 15 Pro"),
        ("4 — Stock Check", "Is the iPad Air in stock?"),
        ("5 — Cancel Order", "Cancel order ORD-002"),
        ("6 — RAG / FAQ", "What is your return policy?"),
        ("7 — Out-of-scope", "Write me a Python script to sort a list"),
        ("8 — MCP Inventory", "What colors does the Pixel 9 Pro come in?"),
    ]

    print(_GUIDE)
    for label, prompt in scenarios:
        _sep()
        print(f"\n  ▶ Scenario {label}")
        print(f"    User: {prompt}")
        print()

        reply = await _ask(runner, user_id, session_id, prompt)
        print(_wrap(reply))
        print()

    _sep("═")
    print("\n  ✓ All scenarios complete.\n")
    return runner, user_id, session_id


# ── REPL ───────────────────────────────────────────────────────────────────

async def repl(runner=None, user_id=None, session_id=None):
    """Interactive REPL for exploring eComBot."""
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


# ── Main ───────────────────────────────────────────────────────────────────

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
    finally:
        shutdown_orders_server()
