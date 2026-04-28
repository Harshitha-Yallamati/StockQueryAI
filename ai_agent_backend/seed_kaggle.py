from __future__ import annotations

import io
import os
import random
import sqlite3

import pandas as pd
import requests

import database


CSV_URL = "https://raw.githubusercontent.com/zulfaan/intro-to-data-engineer-project_pacmann/main/source-marketing_data/ElectronicsProductsPricingData.csv"
DB_PATH = os.path.join(os.path.dirname(__file__), "agent_inventory.db")


def download_and_seed() -> None:
    print(f"Downloading dataset from {CSV_URL}...")
    response = requests.get(CSV_URL, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))
    print(f"Loaded {len(df)} rows from CSV.")

    required_columns = ["name", "prices.amountMax", "categories", "prices.availability"]
    for column in required_columns:
        if column not in df.columns:
            print(f"Warning: Column {column} missing from CSV. Using fallback values.")
            df[column] = "N/A" if column != "prices.amountMax" else 0.0

    df["clean_category"] = df["categories"].apply(
        lambda value: str(value).split(",")[0].strip() if pd.notnull(value) else "Electronics"
    )

    def derive_quantity(availability: str) -> int:
        normalized = str(availability).lower()
        if "yes" in normalized or "in stock" in normalized or "true" in normalized:
            return random.randint(15, 300)
        return 0

    df["derived_quantity"] = df["prices.availability"].apply(derive_quantity)
    seed_data = df.drop_duplicates(subset=["name"]).head(150)

    database.init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM products")

        rows = []
        for _, row in seed_data.iterrows():
            name = str(row["name"]).strip()
            brand = name.split(" ")[0] if name else "Unknown"
            rows.append(
                (
                    name,
                    int(row["derived_quantity"]),
                    float(row["prices.amountMax"] or 0.0),
                    str(row["clean_category"]).strip() or "Electronics",
                    brand,
                    "Kaggle Import",
                    "Main Warehouse",
                    "Imported from Kaggle pricing dataset.",
                )
            )

        conn.executemany(
            """
            INSERT INTO products (
                name, quantity, price, category, brand, supplier, warehouse_location, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Successfully seeded {len(rows)} real products into the inventory.")


if __name__ == "__main__":
    download_and_seed()
