import asyncio
import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ecombot-inventory", log_level="WARNING")

_INVENTORY: dict[str, dict] = {
    "PRD-101": {
        "product_id": "PRD-101",
        "name": "iPhone 15 Pro",
        "stock": 25,
        "status": "in_stock",
        "variants": [
            {"color": "Natural Titanium", "storage": "256GB", "stock": 10},
            {"color": "Blue Titanium", "storage": "256GB", "stock": 8},
            {"color": "Black Titanium", "storage": "512GB", "stock": 5},
            {"color": "White Titanium", "storage": "1TB", "stock": 2},
        ],
    },
    "PRD-102": {
        "product_id": "PRD-102",
        "name": "Samsung Galaxy S24",
        "stock": 40,
        "status": "in_stock",
        "variants": [
            {"color": "Onyx Black", "storage": "128GB", "stock": 15},
            {"color": "Marble Gray", "storage": "128GB", "stock": 12},
            {"color": "Cobalt Violet", "storage": "256GB", "stock": 8},
            {"color": "Amber Yellow", "storage": "256GB", "stock": 5},
        ],
    },
    "PRD-103": {
        "product_id": "PRD-103",
        "name": "Sony WH-1000XM5",
        "stock": 60,
        "status": "in_stock",
        "variants": [
            {"color": "Black", "stock": 30},
            {"color": "Silver", "stock": 20},
            {"color": "Midnight Blue", "stock": 10},
        ],
    },
    "PRD-104": {
        "product_id": "PRD-104",
        "name": "MacBook Air M3",
        "stock": 15,
        "status": "in_stock",
        "variants": [
            {"color": "Midnight", "storage": "256GB", "stock": 5},
            {"color": "Starlight", "storage": "256GB", "stock": 4},
            {"color": "Space Gray", "storage": "512GB", "stock": 3},
            {"color": "Silver", "storage": "512GB", "stock": 3},
        ],
    },
    "PRD-105": {
        "product_id": "PRD-105",
        "name": "iPad Air",
        "stock": 0,
        "status": "out_of_stock",
        "variants": [
            {"color": "Space Gray", "storage": "64GB", "stock": 0},
            {"color": "Blue", "storage": "256GB", "stock": 0},
        ],
    },
    "PRD-106": {
        "product_id": "PRD-106",
        "name": "Pixel 9 Pro",
        "stock": 30,
        "status": "in_stock",
        "variants": [
            {"color": "Obsidian", "storage": "128GB", "stock": 12},
            {"color": "Porcelain", "storage": "128GB", "stock": 10},
            {"color": "Hazel", "storage": "256GB", "stock": 8},
        ],
    },
    "PRD-107": {
        "product_id": "PRD-107",
        "name": "AirPods Pro 2",
        "stock": 100,
        "status": "in_stock",
        "variants": [
            {"type": "USB-C", "stock": 60},
            {"type": "Lightning (legacy)", "stock": 40},
        ],
    },
}


@mcp.tool()
async def check_stock(product_id: str) -> dict:
    """Check stock availability for a specific product by ID.

    Args:
        product_id: Product reference, e.g. "PRD-101".

    Returns:
        A dict with product_id, name, total stock, availability status,
        and variant-level stock. Returns error if product not found.
    """
    delay = float(os.getenv("INVENTORY_SEARCH_DELAY_SECONDS", "0"))
    if delay > 0:
        await asyncio.sleep(delay)

    product = _INVENTORY.get(product_id.strip().upper())
    if product is None:
        return {
            "found": False,
            "product_id": product_id,
            "message": f"No product found with ID '{product_id}'.",
        }

    return {
        "found": True,
        "product_id": product["product_id"],
        "name": product["name"],
        "total_stock": product["stock"],
        "status": product["status"],
        "available": product["stock"] > 0,
        "variants": product["variants"],
    }


@mcp.tool()
async def list_variants(product_family: str) -> dict:
    """List available variants for a product family (search by name).

    Args:
        product_family: Product name or partial name, e.g. "iPhone" or
            "Galaxy S24".

    Returns:
        A dict with matching products and their variants (colors, storage
        options, stock levels). Empty list if nothing matches.
    """
    delay = float(os.getenv("INVENTORY_SEARCH_DELAY_SECONDS", "0"))
    if delay > 0:
        await asyncio.sleep(delay)

    family_lower = product_family.strip().lower()
    matches = [
        {
            "product_id": p["product_id"],
            "name": p["name"],
            "total_stock": p["stock"],
            "status": p["status"],
            "variants": p["variants"],
        }
        for p in _INVENTORY.values()
        if family_lower in p["name"].lower()
    ]

    if not matches:
        return {
            "query": product_family,
            "products": [],
            "message": f"No products found matching '{product_family}'.",
        }

    return {
        "query": product_family,
        "products": matches,
    }


if __name__ == "__main__":
    mcp.run()
