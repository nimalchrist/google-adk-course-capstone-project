"""
product_tools.py — Product lookup and stock tools for eComBot
--------------------------------------------------------------
Day 04: PostgreSQL-backed product queries.
Day 05-06: Also supports RAG-grounded answers for product questions.

Tools:
  lookup_product(product_name)  → search product by name
  check_stock(product_id)       → check stock availability
"""

import logging
from typing import Any

from google.adk.tools import ToolContext

log = logging.getLogger(__name__)

# ── Mock data (fallback when PostgreSQL is unavailable) ────────────────────
MOCK_PRODUCTS = {
    "PRD-101": {"product_id": "PRD-101", "name": "iPhone 15 Pro", "category": "Smartphones", "price": 134900.00, "stock": 25, "status": "active"},
    "PRD-102": {"product_id": "PRD-102", "name": "Samsung Galaxy S24", "category": "Smartphones", "price": 79999.00, "stock": 40, "status": "active"},
    "PRD-103": {"product_id": "PRD-103", "name": "Sony WH-1000XM5", "category": "Audio", "price": 29990.00, "stock": 60, "status": "active"},
    "PRD-104": {"product_id": "PRD-104", "name": "MacBook Air M3", "category": "Laptops", "price": 114900.00, "stock": 15, "status": "active"},
    "PRD-105": {"product_id": "PRD-105", "name": "iPad Air", "category": "Tablets", "price": 59900.00, "stock": 0, "status": "out_of_stock"},
    "PRD-106": {"product_id": "PRD-106", "name": "Pixel 9 Pro", "category": "Smartphones", "price": 109999.00, "stock": 30, "status": "active"},
    "PRD-107": {"product_id": "PRD-107", "name": "AirPods Pro 2", "category": "Audio", "price": 24990.00, "stock": 100, "status": "active"},
}


def _try_db_query_all(query: str, params=None):
    """Attempt a PostgreSQL query_all; return None if DB is unavailable."""
    try:
        from src.services.db import query_all
        return query_all(query, params)
    except Exception as exc:
        log.debug("DB unavailable, using mock data: %s", exc)
        return None


def _try_db_query_one(query: str, params=None):
    """Attempt a PostgreSQL query_one; return None if DB is unavailable."""
    try:
        from src.services.db import query_one
        return query_one(query, params)
    except Exception as exc:
        log.debug("DB unavailable, using mock data: %s", exc)
        return None


# ── Product Tools ──────────────────────────────────────────────────────────

def lookup_product(
    product_name: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Search for a product by name (partial match supported).
    Saves the product context to session state for follow-up questions.

    Args:
        product_name: The product name or partial name to search for,
                      e.g. "iPhone" or "Galaxy S24".

    Returns:
        A dict with matching products, or an error if none found.
    """
    if not product_name or not product_name.strip():
        return {"found": False, "error": "Product name cannot be empty. Please tell me what you're looking for."}

    name = product_name.strip()

    # Try PostgreSQL (Day 04)
    rows = _try_db_query_all(
        """
        SELECT product_id, name, category, price, stock, description, specs, status
        FROM products
        WHERE LOWER(name) LIKE LOWER(%s) AND status != 'inactive'
        ORDER BY name ASC
        """,
        (f"%{name}%",),
    )

    if rows is not None:
        if not rows:
            return {
                "found": False,
                "query": name,
                "error": f"No products found matching '{name}'. Try a different search term.",
            }

        # Store the first match in session
        tool_context.state["current_product_id"] = rows[0]["product_id"]
        tool_context.state["last_lookup_key"] = name
        tool_context.state["last_intent"] = "product_lookup"

        return {
            "found": True,
            "query": name,
            "results": [
                {
                    "product_id": r["product_id"],
                    "name": r["name"],
                    "category": r["category"],
                    "price": float(r["price"]),
                    "in_stock": r["stock"] > 0,
                    "stock_count": r["stock"],
                    "description": r.get("description", ""),
                    "status": r["status"],
                }
                for r in rows
            ],
        }

    # Fallback to mock data
    matches = [
        p for p in MOCK_PRODUCTS.values()
        if name.lower() in p["name"].lower() and p["status"] != "inactive"
    ]

    if not matches:
        return {
            "found": False,
            "query": name,
            "error": f"No products found matching '{name}'.",
        }

    tool_context.state["current_product_id"] = matches[0]["product_id"]
    tool_context.state["last_lookup_key"] = name
    tool_context.state["last_intent"] = "product_lookup"

    return {
        "found": True,
        "query": name,
        "results": [
            {
                "product_id": p["product_id"],
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "in_stock": p["stock"] > 0,
                "stock_count": p["stock"],
                "status": p["status"],
            }
            for p in matches
        ],
    }


def check_stock(
    product_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Check stock availability for a specific product by ID.
    If product_id is "current" or empty, uses the last looked-up product.

    Args:
        product_id: The product reference (e.g. "PRD-101") or "current".

    Returns:
        A dict with stock information, or an error if product not found.
    """
    if not product_id or product_id.strip().lower() in ("", "current"):
        product_id = tool_context.state.get("current_product_id", "")

    if not product_id:
        return {
            "available": False,
            "error": "No product ID provided. Please specify a product ID like PRD-101.",
        }

    pid = product_id.strip().upper()

    # Try PostgreSQL
    row = _try_db_query_one(
        "SELECT product_id, name, stock, status FROM products WHERE product_id = %s",
        (pid,),
    )

    if row is not None:
        tool_context.state["current_product_id"] = pid
        tool_context.state["last_intent"] = "stock_check"
        in_stock = row["stock"] > 0 and row["status"] == "active"
        return {
            "product_id": pid,
            "name": row["name"],
            "stock_count": row["stock"],
            "available": in_stock,
            "status": row["status"],
            "message": (
                f"{row['name']} is {'in stock' if in_stock else 'currently out of stock'}."
                + (f" ({row['stock']} units available)" if in_stock else "")
            ),
        }

    # Fallback to mock data
    if pid in MOCK_PRODUCTS:
        product = MOCK_PRODUCTS[pid]
        tool_context.state["current_product_id"] = pid
        tool_context.state["last_intent"] = "stock_check"
        in_stock = product["stock"] > 0 and product["status"] == "active"
        return {
            "product_id": pid,
            "name": product["name"],
            "stock_count": product["stock"],
            "available": in_stock,
            "status": product["status"],
            "message": (
                f"{product['name']} is {'in stock' if in_stock else 'currently out of stock'}."
                + (f" ({product['stock']} units available)" if in_stock else "")
            ),
        }

    return {
        "available": False,
        "product_id": pid,
        "error": f"Product '{pid}' not found.",
    }
