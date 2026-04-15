import sqlite3
import os

DB_FILENAME = "agent_inventory.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_cost REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_all_products() -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_product(data: dict) -> int:
    conn = get_db_connection()
    c = conn.cursor()
    # Handle possible frontend schema mismatches
    name = data.get("product_name") or data.get("name")
    quantity = data.get("stock_quantity") or data.get("quantity", 0)
    
    c.execute(
        "INSERT INTO products (name, quantity, price, category) VALUES (?, ?, ?, ?)",
        (name, int(quantity), float(data.get("price", 0.0)), data.get("category", "Uncategorized"))
    )
    product_id = c.lastrowid
    conn.commit()
    conn.close()
    return product_id

def update_product(product_id: int, data: dict):
    conn = get_db_connection()
    c = conn.cursor()
    name = data.get("product_name") or data.get("name")
    quantity = data.get("stock_quantity") or data.get("quantity")
    
    c.execute(
        "UPDATE products SET name=?, quantity=?, price=?, category=? WHERE id=?",
        (name, int(quantity), float(data.get("price")), data.get("category"), product_id)
    )
    conn.commit()
    conn.close()

def delete_product(product_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def get_all_orders() -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY order_date DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def place_order(data: dict) -> int:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (product_id, product_name, quantity, total_cost) VALUES (?, ?, ?, ?)",
        (data["product_id"], data["product_name"], int(data["quantity"]), float(data["total_cost"]))
    )
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id: int, status: str):
    conn = get_db_connection()
    c = conn.cursor()
    
    if status == "Arrived":
        # First, get the order details to update stock
        c.execute("SELECT product_id, quantity FROM orders WHERE id=?", (order_id,))
        order = c.fetchone()
        if order:
            c.execute(
                "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                (order["quantity"], order["product_id"])
            )
            
    c.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

def get_inventory_stats() -> dict:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as count FROM products')
    total_products = c.fetchone()['count']
    
    c.execute('SELECT SUM(price * quantity) as total FROM products')
    total_val_row = c.fetchone()['total']
    total_value = total_val_row if total_val_row else 0.0
    
    c.execute('SELECT COUNT(*) as count FROM products WHERE quantity < 10')
    low_stock = c.fetchone()['count']
    
    conn.close()
    return {
        "totalProducts": total_products, 
        "totalValue": round(total_value, 2), 
        "lowStock": low_stock
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized and verified.")
