from database import get_db_connection

def query_inventory_db(product_name: str) -> dict:
    """Returns the stock quantity for a specific product."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT quantity FROM products WHERE name LIKE ?", (f"%{product_name}%",))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"product_name": product_name, "quantity": row["quantity"]}
    return {"error": f"Product '{product_name}' not found in inventory."}

def get_product_details(product_name: str) -> dict:
    """Returns full product info including price, category, and quantity."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{product_name}%",))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {"error": f"Product '{product_name}' not found."}

def get_low_stock_products(threshold: int) -> list:
    """Returns a list of products that have stock quantity below the threshold."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, quantity FROM products WHERE quantity <= ?", (threshold,))
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_total_inventory_value() -> dict:
    """Returns the total monetary value of all items in the inventory."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(price * quantity) as total_value FROM products")
    row = c.fetchone()
    conn.close()
    
    total = row["total_value"] if row["total_value"] else 0.0
    return {"total_inventory_value": round(total, 2)}
