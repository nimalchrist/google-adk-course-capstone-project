# eComBot — Capstone Project

## Overview
eComBot is a full-featured e-commerce support agent built with Google ADK.

## Features

| Feature | Implementation |
|---------|----------------|
| Base agent + prompt refinement | `src/agents/support_agent.py`, instruction files |
| Tool calling + in-memory state | `src/tools/order_tools.py`, session state |
| Redis + PostgreSQL persistence | `src/services/`, `docker-compose.yml` |
| RAG with ChromaDB | `src/rag/`, `data/` knowledge base |
| LiteLLM routing + fallback | `src/routing/router.py` |
| FastMCP external tool servers | `mcp_servers/` |

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### 3. Start infrastructure (optional, for persistence features)
```bash
docker compose up -d
```

### 4. Run with ADK Web
```bash
adk web .
```

### 5. Run demo script
```bash
python demo.py         # Run all scenarios then REPL
python demo.py --repl  # Skip scenarios, go straight to REPL
```

## Project Structure

```
ecombot/
├── agent.py                    # ADK Web entry point (root_agent)
├── demo.py                     # Interactive demo runner
├── session.py                  # Session service factory
├── __init__.py
├── src/
│   ├── agents/
│   │   ├── support_agent.py           # Main support agent (all days)
│   │   ├── support_instructions_v1.txt # Professional tone
│   │   ├── support_instructions_v2.txt # Warm & empathetic tone
│   │   └── support_instructions_v3.txt # Precise & efficient tone
│   ├── tools/
│   │   ├── order_tools.py            # Order status, cancel, session helpers
│   │   └── product_tools.py          # Product lookup, stock check
│   ├── services/
│   │   ├── db.py                     # PostgreSQL connection pool
│   │   ├── redis_client.py           # Redis cache helpers
│   │   ├── session_service.py        # ADK session backend factory
│   │   └── history_service.py        # Durable conversation history
│   ├── rag/
│   │   ├── embed_catalog.py          # Knowledge base embedding script
│   │   └── retriever.py              # Semantic search interface
│   ├── config/
│   │   └── settings.py               # Centralized settings
│   └── routing/
│       └── router.py                 # LiteLLM routing + fallback
├── mcp_servers/
│   ├── orders_server.py              # FastMCP order tools (HTTP)
│   └── inventory_server.py           # FastMCP inventory tools (stdio)
├── data/
│   ├── products.json                 # Product knowledge base
│   └── faq.json                      # FAQ knowledge base
├── scripts/
│   └── init_db.sql                   # PostgreSQL schema + seed data
├── tests/
│   ├── test_support_agent_manual.md  # Manual test notes
│   └── test_rag_manual.md            # RAG test notes
├── docker-compose.yml                # Redis + PostgreSQL
├── .env.example                      # Environment template
└── requirements.txt                  # Python dependencies
```

## Architecture

### Agent Layer
- LlmAgent with refined instructions
- Three instruction variants for different tones
- Dynamic instruction via InstructionProvider

### Tool Layer
- `get_order_status` — order tracking with validation
- `cancel_order` — order cancellation with state awareness
- `lookup_product` — product search (partial match)
- `check_stock` — stock availability check
- `save_customer_name` — session state management

### Persistence Layer
- **Redis**: Session state cache for fast recovery
- **PostgreSQL**: Durable order/product data + conversation history
- **InMemory**: Default fallback (no infrastructure needed)

### RAG Layer
- ChromaDB ephemeral collection for vector search
- OpenAI embedding model via OpenRouter
- Hallucination guards + graceful fallback
- Product specs + FAQ + policy documents

### Routing Layer
- `fast-faq` route: Gemini 2.5 Flash (lightweight queries)
- `deep-support` route: Gemini 2.5 Pro (complex queries)
- Keyword-based query classifier
- Cross-provider fallback (GPT-4o-mini backup)

### MCP Layer
- **Orders server**: Streamable HTTP transport (background process)
- **Inventory server**: stdio transport (spawned per-toolset)
- Tools: get_order_status, get_order_details, cancel_order, check_stock, list_variants
- Error handling: not-found, timeout, graceful fallback

## Session Backends

Set `SESSION_BACKEND` in `.env`:
- `memory` — InMemorySessionService (default, no persistence)
- `database` — DatabaseSessionService (PostgreSQL, requires Docker)

## Testing

### Manual Testing via ADK Web
```bash
adk web .
```
Then test the scenarios in `tests/test_support_agent_manual.md`.

### Demo Scenarios
```bash
python demo.py
```

### Rebuild Knowledge Base
```bash
python -m src.rag.embed_catalog
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key | (required) |
| `SESSION_BACKEND` | Session persistence backend | `memory` |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_DB` | PostgreSQL database name | `ecombot` |
| `PG_USER` | PostgreSQL username | `ecombot` |
| `PG_PASSWORD` | PostgreSQL password | (empty) |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | (empty) |
| `ORDERS_SERVER_HOST` | MCP orders server host | `127.0.0.1` |
| `ORDERS_SERVER_PORT` | MCP orders server port | `8766` |
