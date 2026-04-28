from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any

from core_config import get_settings


PRODUCT_COLUMNS = [
    "id",
    "name",
    "quantity",
    "price",
    "category",
    "brand",
    "supplier",
    "warehouse_location",
    "description",
    "last_updated",
]

ORDER_COLUMNS = [
    "id",
    "product_id",
    "name",
    "quantity",
    "total_cost",
    "status",
    "order_date",
]


class InventoryDataError(Exception):
    code = "INVENTORY_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ProductNotFoundError(InventoryDataError):
    code = "PRODUCT_NOT_FOUND"


class OrderNotFoundError(InventoryDataError):
    code = "ORDER_NOT_FOUND"


class EmptyDatabaseError(InventoryDataError):
    code = "EMPTY_DATABASE"


class ValidationError(InventoryDataError):
    code = "INVALID_INPUT"


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_settings().database_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(get_db_connection()) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        _migrate_products_table(conn)
        _migrate_orders_table(conn)
        _create_indexes(conn)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()


def get_all_products(category: str | None = None, out_of_stock: bool | None = None) -> list[dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        query = "SELECT * FROM products WHERE 1 = 1"
        params: list[Any] = []
        if category:
            query += " AND lower(category) = lower(?)"
            params.append(category.strip())
        if out_of_stock is True:
            query += " AND quantity = 0"
        elif out_of_stock is False:
            query += " AND quantity > 0"
        query += " ORDER BY lower(name)"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]


def get_product_by_id(product_id: int) -> dict[str, Any]:
    with closing(get_db_connection()) as conn:
        product = _get_product_by_id(conn, product_id)
        return _row_to_dict(product)


def find_product_by_name(product_name: str) -> dict[str, Any]:
    cleaned_name = (product_name or "").strip()
    if not cleaned_name:
        raise ValidationError("A product name is required.")

    with closing(get_db_connection()) as conn:
        _ensure_inventory_has_products(conn)
        exact_match = conn.execute(
            "SELECT * FROM products WHERE lower(name) = lower(?) LIMIT 1",
            (cleaned_name,),
        ).fetchone()
        if exact_match:
            return _row_to_dict(exact_match)

        wildcard = f"%{cleaned_name}%"
        partial_match = conn.execute(
            """
            SELECT *
            FROM products
            WHERE lower(name) LIKE lower(?)
            ORDER BY
                CASE
                    WHEN lower(name) LIKE lower(?) THEN 0
                    ELSE 1
                END,
                length(name)
            LIMIT 1
            """,
            (wildcard, f"{cleaned_name}%"),
        ).fetchone()
        if partial_match:
            return _row_to_dict(partial_match)

    raise ProductNotFoundError(f"Product '{cleaned_name}' was not found in inventory.")


def add_product(data: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_product_payload(data)
    with closing(get_db_connection()) as conn:
        timestamp = _utc_timestamp()
        cursor = conn.execute(
            """
            INSERT INTO products (
                name, quantity, price, category, brand, supplier, warehouse_location, description, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["quantity"],
                payload["price"],
                payload["category"],
                payload["brand"],
                payload["supplier"],
                payload["warehouse_location"],
                payload["description"],
                timestamp,
            ),
        )
        conn.commit()
        product = _get_product_by_id(conn, int(cursor.lastrowid))
        return _row_to_dict(product)


def update_product(product_id: int, data: dict[str, Any]) -> dict[str, Any]:
    with closing(get_db_connection()) as conn:
        existing = _row_to_dict(_get_product_by_id(conn, product_id))
        updates = _normalize_product_payload(data, partial=True)
        merged = {**existing, **updates, "last_updated": _utc_timestamp()}
        conn.execute(
            """
            UPDATE products
            SET name = ?, quantity = ?, price = ?, category = ?, brand = ?, supplier = ?,
                warehouse_location = ?, description = ?, last_updated = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged["quantity"],
                merged["price"],
                merged["category"],
                merged["brand"],
                merged["supplier"],
                merged["warehouse_location"],
                merged["description"],
                merged["last_updated"],
                product_id,
            ),
        )
        conn.commit()
        return _row_to_dict(_get_product_by_id(conn, product_id))


def delete_product(product_id: int) -> None:
    with closing(get_db_connection()) as conn:
        _get_product_by_id(conn, product_id)
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def get_all_orders() -> list[dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY datetime(order_date) DESC, id DESC"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def place_order(data: dict[str, Any]) -> dict[str, Any]:
    product_id = int(data.get("product_id") or 0)
    quantity = int(data.get("quantity") or 0)
    if product_id <= 0:
        raise ValidationError("A valid product_id is required.")
    if quantity <= 0:
        raise ValidationError("Order quantity must be greater than zero.")

    with closing(get_db_connection()) as conn:
        product = _row_to_dict(_get_product_by_id(conn, product_id))
        total_cost = round(product["price"] * quantity, 2)
        cursor = conn.execute(
            """
            INSERT INTO orders (product_id, name, quantity, total_cost, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, product["name"], quantity, total_cost, "Pending"),
        )
        conn.commit()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
        return _row_to_dict(order)


def update_order_status(order_id: int, status: str) -> dict[str, Any]:
    normalized_status = (status or "").strip().title()
    if normalized_status not in {"Pending", "Arrived", "Cancelled"}:
        raise ValidationError("Status must be Pending, Arrived, or Cancelled.")

    with closing(get_db_connection()) as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None:
            raise OrderNotFoundError(f"Order '{order_id}' was not found.")

        existing_order = _row_to_dict(order)
        if existing_order["status"] != "Arrived" and normalized_status == "Arrived":
            _get_product_by_id(conn, existing_order["product_id"])
            conn.execute(
                "UPDATE products SET quantity = quantity + ?, last_updated = ? WHERE id = ?",
                (existing_order["quantity"], _utc_timestamp(), existing_order["product_id"]),
            )

        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (normalized_status, order_id),
        )
        conn.commit()
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _row_to_dict(updated_order)


def get_inventory_stats() -> dict[str, Any]:
    with closing(get_db_connection()) as conn:
        low_stock_threshold = get_settings().low_stock_threshold
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_products,
                COALESCE(SUM(price * quantity), 0) AS total_value,
                SUM(CASE WHEN quantity <= ? THEN 1 ELSE 0 END) AS low_stock
            FROM products
            """,
            (low_stock_threshold,),
        ).fetchone()
        return {
            "totalProducts": int(totals["total_products"] or 0),
            "totalValue": round(float(totals["total_value"] or 0.0), 2),
            "lowStock": int(totals["low_stock"] or 0),
        }


def get_low_stock_products(threshold: int) -> list[dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        _ensure_inventory_has_products(conn)
        rows = conn.execute(
            "SELECT * FROM products WHERE quantity <= ? ORDER BY quantity ASC, lower(name)",
            (threshold,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def get_out_of_stock_products() -> list[dict[str, Any]]:
    with closing(get_db_connection()) as conn:
        _ensure_inventory_has_products(conn)
        rows = conn.execute(
            "SELECT * FROM products WHERE quantity = 0 ORDER BY lower(name)"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def get_cheapest_product() -> dict[str, Any]:
    with closing(get_db_connection()) as conn:
        _ensure_inventory_has_products(conn)
        row = conn.execute(
            "SELECT * FROM products ORDER BY price ASC, lower(name) ASC LIMIT 1"
        ).fetchone()
        if row is None:
            raise EmptyDatabaseError("The inventory database is empty.")
        return _row_to_dict(row)


def get_total_inventory_value() -> dict[str, Any]:
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS product_count, COALESCE(SUM(price * quantity), 0) AS total_value FROM products"
        ).fetchone()
        return {
            "product_count": int(row["product_count"] or 0),
            "total_inventory_value": round(float(row["total_value"] or 0.0), 2),
        }


def get_product_categories() -> list[str]:
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products WHERE trim(category) <> '' ORDER BY lower(category)"
        ).fetchall()
        return [str(row["category"]) for row in rows]


def _migrate_products_table(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "products")
    if columns == PRODUCT_COLUMNS:
        _create_products_table(conn)
        return

    existing_rows = []
    if columns:
        rows = conn.execute("SELECT * FROM products").fetchall()
        existing_rows = [_normalize_product_row(dict(row)) for row in rows]
        conn.execute("DROP TABLE products")

    _create_products_table(conn)
    if existing_rows:
        conn.executemany(
            """
            INSERT INTO products (
                id, name, quantity, price, category, brand, supplier, warehouse_location, description, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    row["name"],
                    row["quantity"],
                    row["price"],
                    row["category"],
                    row["brand"],
                    row["supplier"],
                    row["warehouse_location"],
                    row["description"],
                    row["last_updated"],
                )
                for row in existing_rows
            ],
        )


def _migrate_orders_table(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "orders")
    if columns == ORDER_COLUMNS:
        _create_orders_table(conn)
        return

    existing_rows = []
    if columns:
        rows = conn.execute("SELECT * FROM orders").fetchall()
        existing_rows = [_normalize_order_row(dict(row)) for row in rows]
        conn.execute("DROP TABLE orders")

    _create_orders_table(conn)
    if existing_rows:
        conn.executemany(
            """
            INSERT INTO orders (
                id, product_id, name, quantity, total_cost, status, order_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    row["product_id"],
                    row["name"],
                    row["quantity"],
                    row["total_cost"],
                    row["status"],
                    row["order_date"],
                )
                for row in existing_rows
            ],
        )


def _create_products_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 0,
            category TEXT NOT NULL DEFAULT 'Uncategorized',
            brand TEXT NOT NULL DEFAULT 'Unknown',
            supplier TEXT NOT NULL DEFAULT 'Unknown Supplier',
            warehouse_location TEXT NOT NULL DEFAULT 'Main Warehouse',
            description TEXT NOT NULL DEFAULT '',
            last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _create_orders_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_cost REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row["name"]) for row in rows]


def _get_product_by_id(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product '{product_id}' was not found in inventory.")
    return row


def _normalize_product_payload(data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    aliases = {
        "name": data.get("name", data.get("product_name")),
        "quantity": data.get("quantity", data.get("stock_quantity")),
        "price": data.get("price"),
        "category": data.get("category"),
        "brand": data.get("brand"),
        "supplier": data.get("supplier"),
        "warehouse_location": data.get("warehouse_location"),
        "description": data.get("description"),
    }

    normalized: dict[str, Any] = {}
    for key, value in aliases.items():
        if value is None:
            if not partial and key in {"name", "quantity", "price", "category"}:
                raise ValidationError(f"Field '{key}' is required.")
            continue

        if key in {"name", "category", "brand", "supplier", "warehouse_location", "description"}:
            value = str(value).strip()
        if key == "quantity":
            value = int(value)
            if value < 0:
                raise ValidationError("Quantity cannot be negative.")
        if key == "price":
            value = float(value)
            if value < 0:
                raise ValidationError("Price cannot be negative.")
        normalized[key] = value

    defaults = {
        "brand": "Unknown",
        "supplier": "Unknown Supplier",
        "warehouse_location": "Main Warehouse",
        "description": "",
    }
    for key, value in defaults.items():
        if not partial:
            normalized.setdefault(key, value)

    if not partial and not normalized.get("name"):
        raise ValidationError("Field 'name' is required.")
    if not partial and not normalized.get("category"):
        raise ValidationError("Field 'category' is required.")

    return normalized


def _normalize_product_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row.get("id") or 0) or None,
        "name": str(row.get("name") or row.get("product_name") or "Unnamed product").strip(),
        "quantity": int(row.get("quantity") or row.get("stock_quantity") or 0),
        "price": float(row.get("price") or 0.0),
        "category": str(row.get("category") or "Uncategorized").strip() or "Uncategorized",
        "brand": str(row.get("brand") or "Unknown").strip() or "Unknown",
        "supplier": str(row.get("supplier") or "Unknown Supplier").strip() or "Unknown Supplier",
        "warehouse_location": str(row.get("warehouse_location") or "Main Warehouse").strip() or "Main Warehouse",
        "description": str(row.get("description") or "").strip(),
        "last_updated": str(row.get("last_updated") or _utc_timestamp()),
    }


def _normalize_order_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row.get("id") or 0) or None,
        "product_id": int(row.get("product_id") or 0),
        "name": str(row.get("name") or row.get("product_name") or "Unknown product").strip(),
        "quantity": int(row.get("quantity") or 0),
        "total_cost": round(float(row.get("total_cost") or 0.0), 2),
        "status": str(row.get("status") or "Pending").strip().title() or "Pending",
        "order_date": str(row.get("order_date") or _utc_timestamp()),
    }


def _ensure_inventory_has_products(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()
    if int(row["total"] or 0) == 0:
        raise EmptyDatabaseError("The inventory database is empty.")


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {}
    payload = dict(row)
    if "price" in payload:
        payload["price"] = float(payload["price"])
    if "total_cost" in payload:
        payload["total_cost"] = float(payload["total_cost"])
    if "quantity" in payload:
        payload["quantity"] = int(payload["quantity"])
    if "id" in payload and payload["id"] is not None:
        payload["id"] = int(payload["id"])
    if "product_id" in payload and payload["product_id"] is not None:
        payload["product_id"] = int(payload["product_id"])
    return payload


def _utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    init_db()
    print("Database initialized and verified.")
