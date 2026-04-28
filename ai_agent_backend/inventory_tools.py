from __future__ import annotations

from typing import Any

import database as db
from core_config import get_settings
from mcp import MCPTool


def query_inventory_db(product_name: str) -> dict[str, Any]:
    try:
        product = db.find_product_by_name(product_name)
        summary = f"{product['name']} has {product['quantity']} units in stock."
        return _success(
            data={"product": product},
            summary=summary,
            rendered_response=_format_product_availability(product),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def get_product_details(product_name: str) -> dict[str, Any]:
    try:
        product = db.find_product_by_name(product_name)
        summary = f"Retrieved full details for {product['name']}."
        return _success(
            data={"product": product},
            summary=summary,
            rendered_response=_format_product_details(product),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def get_low_stock_products(threshold: int | None = None) -> dict[str, Any]:
    threshold = threshold if threshold is not None else get_settings().low_stock_threshold
    if threshold < 0:
        return _error("INVALID_ARGUMENTS", "Threshold must be zero or greater.")
    try:
        products = db.get_low_stock_products(threshold)
        if not products:
            message = f"No products are at or below the low-stock threshold of {threshold}."
            return _success(
                data={"products": [], "count": 0, "threshold": threshold},
                summary=message,
                rendered_response=message,
            )
        summary = f"Found {len(products)} product(s) at or below {threshold} units."
        return _success(
            data={"products": products, "count": len(products), "threshold": threshold},
            summary=summary,
            rendered_response=_format_product_list(
                products,
                heading=f"Products at or below {threshold} units",
            ),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def get_total_inventory_value() -> dict[str, Any]:
    payload = db.get_total_inventory_value()
    total_value = payload["total_inventory_value"]
    if payload["product_count"] == 0:
        message = "The inventory database is empty. Total inventory value is $0.00."
        return _success(
            data=payload,
            summary=message,
            rendered_response=message,
        )
    message = f"Total inventory value is ${total_value:,.2f} across {payload['product_count']} products."
    return _success(data=payload, summary=message, rendered_response=message)


def list_products() -> dict[str, Any]:
    try:
        products = db.get_all_products()
        summary = f"Retrieved {len(products)} product(s) from inventory."
        return _success(
            data={"products": products, "count": len(products)},
            summary=summary,
            rendered_response=_format_product_list(products, heading="Inventory products"),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def list_out_of_stock_products() -> dict[str, Any]:
    try:
        products = db.get_out_of_stock_products()
        if not products:
            message = "No products are currently out of stock."
            return _success(
                data={"products": [], "count": 0},
                summary=message,
                rendered_response=message,
            )
        summary = f"Found {len(products)} out-of-stock product(s)."
        return _success(
            data={"products": products, "count": len(products)},
            summary=summary,
            rendered_response=_format_product_list(products, heading="Out-of-stock products"),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def list_products_by_category(category: str) -> dict[str, Any]:
    try:
        products = db.get_all_products(category=category)
        if not products:
            message = f"No products found in category '{category}'."
            return _success(
                data={"products": [], "count": 0, "category": category},
                summary=message,
                rendered_response=message,
            )
        summary = f"Found {len(products)} product(s) in category '{products[0]['category']}'."
        return _success(
            data={"products": products, "count": len(products), "category": products[0]["category"]},
            summary=summary,
            rendered_response=_format_product_list(
                products,
                heading=f"Products in category '{products[0]['category']}'",
            ),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def get_cheapest_product() -> dict[str, Any]:
    try:
        product = db.get_cheapest_product()
        summary = f"The cheapest product is {product['name']} at ${product['price']:.2f}."
        return _success(
            data={"product": product},
            summary=summary,
            rendered_response=_format_product_details(product, prefix="Cheapest product"),
        )
    except db.InventoryDataError as exc:
        return _error(exc.code, str(exc))


def build_inventory_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="query_inventory_db",
            description="Get the exact stock quantity for a specific product by name. Use for questions about stock, quantity, availability, or units for one product.",
            input_schema={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The product name or identifying phrase to search for.",
                    }
                },
                "required": ["product_name"],
            },
            handler=query_inventory_db,
        ),
        MCPTool(
            name="get_product_details",
            description="Get the full verified product record for one product, including name, quantity, price, category, brand, supplier, warehouse location, and description.",
            input_schema={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The product name or identifying phrase to search for.",
                    }
                },
                "required": ["product_name"],
            },
            handler=get_product_details,
        ),
        MCPTool(
            name="get_low_stock_products",
            description="List products with quantity at or below a threshold. Use for low-stock, reorder, or running-low questions.",
            input_schema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "The maximum quantity to include.",
                        "default": get_settings().low_stock_threshold,
                    }
                },
                "required": [],
            },
            handler=get_low_stock_products,
        ),
        MCPTool(
            name="get_total_inventory_value",
            description="Calculate the total dollar value of all inventory currently in the database.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=get_total_inventory_value,
        ),
        MCPTool(
            name="list_products",
            description="List all products in inventory. Use for requests like show all products, show inventory, or what products do we have.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=list_products,
        ),
        MCPTool(
            name="list_out_of_stock_products",
            description="List only products whose quantity is zero. Use for out-of-stock, unavailable, or zero stock questions.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=list_out_of_stock_products,
        ),
        MCPTool(
            name="list_products_by_category",
            description="List products filtered by category. Use when the user asks for products in a specific category.",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The exact or approximate category name to filter by.",
                    }
                },
                "required": ["category"],
            },
            handler=list_products_by_category,
        ),
        MCPTool(
            name="get_cheapest_product",
            description="Return the lowest-priced product in inventory. Use for cheapest, lowest price, or least expensive questions.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=get_cheapest_product,
        ),
    ]


def _success(data: dict[str, Any], summary: str, rendered_response: str) -> dict[str, Any]:
    return {
        "ok": True,
        "source": "inventory_db",
        "summary": summary,
        "rendered_response": rendered_response,
        "data": data,
    }


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "source": "inventory_db",
        "summary": message,
        "rendered_response": message,
        "error": {"code": code, "message": message},
    }


def _format_product_availability(product: dict[str, Any]) -> str:
    return (
        f"{product['name']} currently has {product['quantity']} units in stock at "
        f"${product['price']:.2f} each."
    )


def _format_product_details(product: dict[str, Any], prefix: str | None = None) -> str:
    title = prefix or product["name"]
    description = product.get("description") or "No description available."
    return (
        f"{title}\n"
        f"- Name: {product['name']}\n"
        f"- Category: {product['category']}\n"
        f"- Price: ${product['price']:.2f}\n"
        f"- Quantity: {product['quantity']}\n"
        f"- Brand: {product['brand']}\n"
        f"- Supplier: {product['supplier']}\n"
        f"- Warehouse: {product['warehouse_location']}\n"
        f"- Description: {description}"
    )


def _format_product_list(products: list[dict[str, Any]], heading: str) -> str:
    if not products:
        return f"{heading}\n- No matching products found."

    preview_limit = 12
    lines = [heading]
    for product in products[:preview_limit]:
        lines.append(
            f"- {product['name']} | {product['category']} | qty {product['quantity']} | ${product['price']:.2f}"
        )
    if len(products) > preview_limit:
        lines.append(f"- ...and {len(products) - preview_limit} more product(s).")
    return "\n".join(lines)
