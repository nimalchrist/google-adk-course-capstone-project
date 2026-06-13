"""
orders_server.py — Order Management MCP tool server for eComBot
================================================================
Day 08: FastMCP server exposing order tools over Streamable HTTP.

Tools:
  get_order_status(order_id)    → quick status lookup
  get_order_details(order_id)   → full order record
  cancel_order(order_id, confirm) → cancel ONE order with confirmation

Run directly:
    python orders_server.py
    # serves on http://127.0.0.1:8766/mcp by default
"""

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ecombot-orders",
    log_level="WARNING",
    host=os.getenv("ORDERS_SERVER_HOST", "127.0.0.1"),
    port=int(os.getenv("ORDERS_SERVER_PORT", "8766")),
)

# ── Mock order data ─────────────────────────────────────────────────────────
_ORDERS: dict[str, dict] = {
    "ORD-001": {
        "order_id": "ORD-001",
        "customer_name": "Priya Sharma",
        "email": "priya@example.com",
        "product_name": "iPhone 15 Pro",
        "quantity": 1,
        "status": "Shipped",
        "eta": "15 Jun 2026",
        "carrier": "BlueDart",
        "total_amount": 134900.00,
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "customer_name": "Ravi Kumar",
        "email": "ravi@example.com",
        "product_name": "Samsung Galaxy S24",
        "quantity": 1,
        "status": "Processing",
        "eta": "18 Jun 2026",
        "carrier": "DTDC",
        "total_amount": 79999.00,
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "customer_name": "Meera Nair",
        "email": "meera@example.com",
        "product_name": "Sony WH-1000XM5",
        "quantity": 1,
        "status": "Delivered",
        "eta": "Already delivered",
        "carrier": "FedEx",
        "total_amount": 29990.00,
    },
    "ORD-004": {
        "order_id": "ORD-004",
        "customer_name": "John Mathews",
        "email": "john@example.com",
        "product_name": "MacBook Air M3",
        "quantity": 1,
        "status": "Shipped",
        "eta": "16 Jun 2026",
        "carrier": "Delhivery",
        "total_amount": 114900.00,
    },
    "ORD-005": {
        "order_id": "ORD-005",
        "customer_name": "Aisha Mehta",
        "email": "aisha@example.com",
        "product_name": "iPad Air",
        "quantity": 1,
        "status": "Cancelled",
        "eta": None,
        "carrier": None,
        "total_amount": 59900.00,
    },
    "ORD-006": {
        "order_id": "ORD-006",
        "customer_name": "Kenji Tanaka",
        "email": "kenji@example.com",
        "product_name": "Pixel 9 Pro",
        "quantity": 1,
        "status": "Processing",
        "eta": "20 Jun 2026",
        "carrier": "BlueDart",
        "total_amount": 109999.00,
    },
    "ORD-007": {
        "order_id": "ORD-007",
        "customer_name": "Fatima Al-Ali",
        "email": "fatima@example.com",
        "product_name": "AirPods Pro 2",
        "quantity": 2,
        "status": "Shipped",
        "eta": "14 Jun 2026",
        "carrier": "FedEx",
        "total_amount": 49980.00,
    },
}


def _not_found(order_id: str) -> dict:
    return {
        "found": False,
        "order_id": order_id,
        "message": (
            f"No order found with ID '{order_id}'. Please check the "
            "order reference (format: ORD-XXX)."
        ),
    }


@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """Look up the status of an order by its reference ID.

    Args:
        order_id: Order reference, e.g. "ORD-001".

    Returns:
        A dict with order_id, product, status, eta, and carrier if found,
        or {"found": False, ...} with guidance if not.
    """
    order = _ORDERS.get(order_id.strip().upper())
    if order is None:
        return _not_found(order_id)

    return {
        "found": True,
        "order_id": order["order_id"],
        "product_name": order["product_name"],
        "status": order["status"],
        "eta": order.get("eta", "Not available"),
        "carrier": order.get("carrier", "Not assigned"),
    }


@mcp.tool()
def get_order_details(order_id: str) -> dict:
    """Fetch the full record for an order.

    Args:
        order_id: Order reference, e.g. "ORD-002".

    Returns:
        The full order record if found, or {"found": False, ...} if not.
    """
    order = _ORDERS.get(order_id.strip().upper())
    if order is None:
        return _not_found(order_id)

    return {"found": True, **order}


@mcp.tool()
def cancel_order(order_id: str, confirm: bool = False) -> dict:
    """Cancel a single order. Requires explicit confirmation.

    This tool only accepts ONE order_id — there is no way to cancel
    multiple orders in one call.

    Args:
        order_id: Order reference to cancel, e.g. "ORD-002".
        confirm: Must be True to actually cancel. Call first with
            confirm=False to preview, then with confirm=True after
            user agrees.

    Returns:
        Preview of cancellation (confirm=False), confirmation of
        cancellation (confirm=True), or error if not found/not eligible.
    """
    order = _ORDERS.get(order_id.strip().upper())
    if order is None:
        return _not_found(order_id)

    if order["status"] == "Cancelled":
        return {
            "found": True,
            "order_id": order["order_id"],
            "error": f"Order {order['order_id']} is already cancelled.",
        }

    if order["status"] == "Delivered":
        return {
            "found": True,
            "order_id": order["order_id"],
            "error": f"Order {order['order_id']} has been delivered and cannot be cancelled.",
        }

    if not confirm:
        return {
            "found": True,
            "order_id": order["order_id"],
            "status": "cancellation_pending",
            "message": (
                f"This will cancel order {order['order_id']} "
                f"({order['product_name']} for {order['customer_name']}). "
                "Call cancel_order again with confirm=True to proceed."
            ),
        }

    order["status"] = "Cancelled"
    return {
        "found": True,
        "order_id": order["order_id"],
        "status": "Cancelled",
        "message": f"Order {order['order_id']} ({order['product_name']}) has been cancelled.",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
