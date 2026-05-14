from __future__ import annotations

import os
import random
import sqlite3

import database


DB_PATH = os.path.join(os.path.dirname(__file__), "agent_inventory.db")


def generate_fake_data() -> list[tuple[str, int, float, str, str, str, str, str]]:
    brands = ["Sony", "Samsung", "Apple", "Dell", "HP", "Lenovo", "Asus", "Logitech", "Corsair", "Razer", "LG", "Bose"]
    categories = {
        "Electronics": ["Laptop", "Smartphone", "Tablet", "Monitor", "TV"],
        "Accessories": ["Mouse", "Keyboard", "Headphones", "Webcam", "USB Hub", "Cable"],
        "Audio": ["Bluetooth Speaker", "Soundbar", "Earbuds", "Microphone"],
    }

    data = []
    for _ in range(200):
        category = random.choice(list(categories.keys()))
        product_type = random.choice(categories[category])
        brand = random.choice(brands)
        model_letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        model_numbers = random.randint(100, 9000)

        name = f"{brand} {product_type} {model_letters}-{model_numbers}"
        quantity = random.randint(0, 500)
        if category == "Electronics":
            price = round(random.uniform(199.99, 2999.99), 2)
        elif category == "Accessories":
            price = round(random.uniform(9.99, 149.99), 2)
        else:
            price = round(random.uniform(29.99, 399.99), 2)

        data.append(
            (
                name,
                quantity,
                price,
                category,
                brand,
                "Seeded Supplier",
                "Main Warehouse",
                f"Demo {product_type.lower()} generated for local testing.",
            )
        )

    return data


def seed_db() -> None:
    database.init_db()
    seed_data = generate_fake_data()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM products")
        conn.executemany(
            """
            INSERT INTO products (
                name, quantity, price, category, brand, supplier, warehouse_location, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seed_data,
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Successfully seeded {len(seed_data)} items into the database.")


if __name__ == "__main__":
    seed_db()
