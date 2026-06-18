import logging
import re
from typing import Any

from google.adk.tools import ToolContext

log = logging.getLogger(__name__)

MOCK_ORDERS = {
    "ORD-001": {"order_id": "ORD-001", "customer_name": "Priya Sharma", "product_name": "iPhone 15 Pro", "status": "Shipped", "eta": "15 Jun 2026", "carrier": "BlueDart", "total_amount": 134900.00},
    "ORD-002": {"order_id": "ORD-002", "customer_name": "Ravi Kumar", "product_name": "Samsung Galaxy S24", "status": "Processing", "eta": "18 Jun 2026", "carrier": "DTDC", "total_amount": 79999.00},
    "ORD-003": {"order_id": "ORD-003", "customer_name": "Meera Nair", "product_name": "Sony WH-1000XM5", "status": "Delivered", "eta": "Already delivered", "carrier": "FedEx", "total_amount": 29990.00},
    "ORD-004": {"order_id": "ORD-004", "customer_name": "John Mathews", "product_name": "MacBook Air M3", "status": "Shipped", "eta": "16 Jun 2026", "carrier": "Delhivery", "total_amount": 114900.00},
    "ORD-005": {"order_id": "ORD-005", "customer_name": "Aisha Mehta", "product_name": "iPad Air", "status": "Cancelled", "eta": None, "carrier": None, "total_amount": 59900.00},
}

_ORDER_ID_PATTERN = re.compile(r"^ORD-\d{3,}$", re.IGNORECASE)


def _is_valid_order_id(order_id: str) -> bool:
    return bool(_ORDER_ID_PATTERN.match(order_id.strip()))


def _try_db_query(query: str, params=None):
    try:
        from src.services.db import query_one
        return query_one(query, params)
    except Exception as exc:
        log.debug("DB unavailable, using mock data: %s", exc)
        return None


def _try_db_execute(query: str, params=None):
    try:
        from src.services.db import execute
        return execute(query, params)
    except Exception as exc:
        log.debug("DB unavailable: %s", exc)
        return None



def get_order_status(
    order_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Look up an order by ID and return its current status and details.
    Saves current_order_id and customer_name to session state for follow-ups.

    Args:
        order_id: The order reference, e.g. "ORD-001".

    Returns:
        A dict with order details, or an error dict if not found or invalid.
    """
    if not order_id or not order_id.strip():
        return {"found": False, "error": "Order ID cannot be empty. Please provide an order ID like ORD-001."}

    oid = order_id.strip().upper()

    if not _is_valid_order_id(oid):
        return {"found": False, "error": f"Invalid order ID format: '{oid}'. Order IDs look like ORD-001, ORD-002, etc."}

    row = _try_db_query("SELECT * FROM orders WHERE order_id = %s", (oid,))

    if row is not None:
        tool_context.state["current_order_id"] = oid
        tool_context.state["current_customer_name"] = row.get("customer_name", "")
        tool_context.state["last_intent"] = "order_status"
        return {
            "found": True,
            "order_id": row["order_id"],
            "customer_name": row["customer_name"],
            "product_name": row["product_name"],
            "quantity": row.get("quantity", 1),
            "status": row["status"],
            "eta": row.get("eta", "Not available"),
            "carrier": row.get("carrier", "Not assigned"),
            "total_amount": float(row["total_amount"]) if row.get("total_amount") else None,
        }

    if oid in MOCK_ORDERS:
        order = MOCK_ORDERS[oid]
        tool_context.state["current_order_id"] = oid
        tool_context.state["current_customer_name"] = order["customer_name"]
        tool_context.state["last_intent"] = "order_status"
        return {"found": True, **order}

    return {
        "found": False,
        "order_id": oid,
        "error": f"Order '{oid}' not found. Please check the order ID and try again.",
    }


def cancel_order(
    order_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Cancel an order by ID. If order_id is "current" or empty, uses the last
    looked-up order from session state.

    Args:
        order_id: The order reference, or "current" to use the session value.

    Returns:
        A dict indicating success or the reason cancellation failed.
    """
    if not order_id or order_id.strip().lower() in ("", "current"):
        order_id = tool_context.state.get("current_order_id", "")

    if not order_id:
        return {
            "cancelled": False,
            "error": "No order ID provided or found in this session. Please specify an order ID.",
        }

    oid = order_id.strip().upper()

    if not _is_valid_order_id(oid):
        return {"cancelled": False, "error": f"Invalid order ID format: '{oid}'."}

    row = _try_db_query("SELECT status, customer_name FROM orders WHERE order_id = %s", (oid,))

    if row is not None:
        if row["status"].lower() == "cancelled":
            return {
                "cancelled": False,
                "order_id": oid,
                "error": f"Order '{oid}' is already cancelled. No changes were made.",
            }
        if row["status"].lower() == "delivered":
            return {
                "cancelled": False,
                "order_id": oid,
                "error": f"Order '{oid}' has already been delivered and cannot be cancelled.",
            }

        result = _try_db_execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = %s", (oid,))
        if result is not None:
            tool_context.state["current_order_id"] = oid
            tool_context.state["last_intent"] = "cancel_order"
            return {
                "cancelled": True,
                "order_id": oid,
                "customer_name": row["customer_name"],
                "message": f"Order {oid} for {row['customer_name']} has been successfully cancelled.",
            }
        return {"cancelled": False, "error": "Cancellation could not be saved. Please try again."}

    if oid in MOCK_ORDERS:
        order = MOCK_ORDERS[oid]
        if order["status"].lower() == "cancelled":
            return {
                "cancelled": False,
                "order_id": oid,
                "error": f"Order '{oid}' is already cancelled.",
            }
        if order["status"].lower() == "delivered":
            return {
                "cancelled": False,
                "order_id": oid,
                "error": f"Order '{oid}' has already been delivered and cannot be cancelled.",
            }
        order["status"] = "Cancelled"
        tool_context.state["current_order_id"] = oid
        tool_context.state["last_intent"] = "cancel_order"
        return {
            "cancelled": True,
            "order_id": oid,
            "customer_name": order["customer_name"],
            "message": f"Order {oid} for {order['customer_name']} has been successfully cancelled.",
        }

    return {"cancelled": False, "order_id": oid, "error": f"Order '{oid}' not found."}



def save_customer_name(
    name: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Save the customer's name to session state.
    Call this as soon as the user introduces themselves.

    Args:
        name: The customer's name.
    """
    if not name or not name.strip():
        return {"saved": False, "error": "Name cannot be empty."}
    clean = name.strip()
    tool_context.state["customer_name"] = clean
    return {"saved": True, "customer_name": clean}


def get_session_summary(tool_context: ToolContext) -> dict[str, Any]:
    """
    Return the customer's current session working memory.
    Reads all known state keys — order context, product, and name.
    """
    return {
        "customer_name": tool_context.state.get("customer_name", "unknown"),
        "current_order_id": tool_context.state.get("current_order_id", "none"),
        "current_customer_name": tool_context.state.get("current_customer_name", "unknown"),
        "current_product_id": tool_context.state.get("current_product_id", "none"),
        "last_intent": tool_context.state.get("last_intent", "not set"),
        "last_lookup_key": tool_context.state.get("last_lookup_key", "not set"),
    }
