"""
agent.py — eComBot: Main agent entry point for ADK Web
=======================================================
Day 08: Full-featured eComBot with MCP tool servers.

This file defines root_agent which ADK Web discovers automatically:
    adk web .

The root_agent combines:
  - Day 01-02: Refined instruction and persona
  - Day 03:    In-process tools (order_tools, product_tools)
  - Day 04:    PostgreSQL/Redis persistence (via tools layer)
  - Day 05-06: RAG grounding via ChromaDB knowledge base
  - Day 07:    LiteLLM model routing (fast-faq / deep-support)
  - Day 08:    FastMCP external tool servers (orders + inventory)

Architecture:
  - Orders MCP server runs as a background HTTP process (Streamable HTTP)
  - Inventory MCP server spawns per-toolset via stdio
  - Both are combined with in-process tools for a unified agent
"""

import atexit
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import (
    McpToolset,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

# ── Silence noisy loggers ──────────────────────────────────────────────────
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_LOG", "ERROR")
for _name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

litellm.suppress_debug_info = True
load_dotenv()

from src.routing.router import FAST_MODEL, DEEP_MODEL
from src.rag.retriever import semantic_search
from src.tools.order_tools import get_order_status, cancel_order, save_customer_name, get_session_summary
from src.tools.product_tools import lookup_product, check_stock

# ── Config ─────────────────────────────────────────────────────────────────
_MODEL = FAST_MODEL
_MCP_SERVERS_DIR = Path(__file__).parent / "mcp_servers"
_ORDERS_SERVER = str(_MCP_SERVERS_DIR / "orders_server.py")
_INVENTORY_SERVER = str(_MCP_SERVERS_DIR / "inventory_server.py")

_ORDERS_HOST = os.getenv("ORDERS_SERVER_HOST", "127.0.0.1")
_ORDERS_PORT = int(os.getenv("ORDERS_SERVER_PORT", "8766"))
_ORDERS_URL = f"http://{_ORDERS_HOST}:{_ORDERS_PORT}/mcp"

# ── Start Orders MCP server (background HTTP process) ──────────────────────

def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"orders_server.py did not start on {host}:{port} within {timeout}s")


def _start_orders_server() -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, _ORDERS_SERVER],
        env={
            **os.environ,
            "ORDERS_SERVER_HOST": _ORDERS_HOST,
            "ORDERS_SERVER_PORT": str(_ORDERS_PORT),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_port(_ORDERS_HOST, _ORDERS_PORT)
    return proc


_orders_server_process = _start_orders_server()


def shutdown_orders_server() -> None:
    """Stop the background orders MCP server."""
    if _orders_server_process.poll() is None:
        _orders_server_process.terminate()
        _orders_server_process.wait(timeout=5)


atexit.register(shutdown_orders_server)


# ── Instruction ────────────────────────────────────────────────────────────
_INSTRUCTIONS_DIR = Path(__file__).parent / "src" / "agents"
_BASE_INSTRUCTION = (_INSTRUCTIONS_DIR / "support_instructions_v2.txt").read_text()

_TOOL_RULES = """
Tool usage rules:
- When a customer asks about their order status, use get_order_status tool.
  Ask for the order ID (format: ORD-XXX) if not provided.
- When a customer wants to cancel an order, use cancel_order tool.
- When a customer asks about a product, use lookup_product tool.
- When a customer asks about stock/availability/variants, use check_stock tool.
- When a customer introduces themselves, use save_customer_name immediately.
- Use get_session_summary when asked for a conversation summary.

MCP tool rules (orders and inventory servers):
- You also have access to external MCP tools for orders and inventory.
- For detailed order info, you can use get_order_details from the MCP server.
- For variant/color/storage options, use check_stock or list_variants from inventory.
- If an MCP tool returns an error or is unavailable, explain plainly and suggest
  the user try again or provide alternative help.

General rules:
- Do NOT guess order details, stock levels, or product specs.
- Always use tools to get real data.
- If a tool returns an error, relay it clearly without exposing technical details.
- Use the customer's name in responses when known.
"""

_GROUNDING_RULES = """
Grounding rules (for product/FAQ questions):
- When answering product or policy questions, prefer information from the
  "Retrieved context" section below.
- If retrieved context says nothing relevant, say so plainly instead of guessing.
- For order-related queries, always use tools rather than the knowledge base.
"""

_TOP_K = 3


def _format_context(results: list[dict]) -> str:
    if not results:
        return (
            "Retrieved context: NOTHING RELEVANT FOUND.\n"
            "If this is a product/policy question, say you don't have "
            "that information in the knowledge base."
        )
    lines = ["Retrieved context (ground your answer in this only):"]
    for r in results:
        lines.append(f"- (score={r['score']:.2f}) {r['text']}")
    return "\n".join(lines)


def _build_instruction(ctx: ReadonlyContext) -> str:
    """InstructionProvider: retrieves KB chunks and builds full prompt."""
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


# ── MCP Toolsets ───────────────────────────────────────────────────────────
orders_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=_ORDERS_URL,
        timeout=10,
    ),
)

inventory_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_INVENTORY_SERVER],
            env={"INVENTORY_SEARCH_DELAY_SECONDS": "0"},
        ),
        timeout=10,
    ),
)

# ── In-process tools (only those NOT duplicated by MCP servers) ────────────
IN_PROCESS_TOOLS = [
    lookup_product,
    save_customer_name,
    get_session_summary,
]

# ── Root Agent (Day 08: Full eComBot with MCP + in-process tools + RAG) ────
root_agent = LlmAgent(
    name="ecombot",
    model=LiteLlm(model=_MODEL),
    instruction=_build_instruction,
    description=(
        "eComBot — full-featured e-commerce support agent with order tracking, "
        "product search, RAG-grounded FAQ answers, and external MCP tool servers."
    ),
    tools=[
        *IN_PROCESS_TOOLS,
        orders_toolset,
        inventory_toolset,
    ],
)
