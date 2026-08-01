from __future__ import annotations

import os
import random
import sqlite3

import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter

import database


DB_PATH = os.path.join(os.path.dirname(__file__), "agent_inventory.db")


def download_and_seed() -> None:
    print("Loading retail store inventory forecasting dataset from Kaggle...")
    
    # Download the dataset first to see available files
    dataset_path = kagglehub.dataset_download("anirudhchauhan/retail-store-inventory-forecasting-dataset")
    print(f"Dataset downloaded to: {dataset_path}")
    
    # List files in the dataset directory
    import os
    files = os.listdir(dataset_path)
    print(f"Available files: {files}")
    
    # Find the first CSV file
    csv_file = None
    for file in files:
        if file.endswith('.csv'):
            csv_file = file
            break
    
    if not csv_file:
        raise ValueError(f"No CSV file found in dataset. Available files: {files}")
    
    print(f"Using file: {csv_file}")
    
    # Load the CSV file
    file_path = os.path.join(dataset_path, csv_file)
    df = pd.read_csv(file_path)

    print(f"Loaded {len(df)} rows from Kaggle dataset.")
    print("First 5 records:", df.head())
    print("Columns:", df.columns.tolist())

    # Check available columns and map to our schema
    # Common columns in retail inventory datasets
    possible_name_cols = ["Product ID", "product_name", "product", "name", "item_name", "item", "Product_ID"]
    possible_price_cols = ["Price", "price", "unit_price", "selling_price", "mrp", "Unit_Price"]
    possible_category_cols = ["Category", "category", "product_category", "item_category", "Product_Category"]
    possible_quantity_cols = ["Inventory Level", "inventory", "quantity", "stock", "units", "Inventory_Level", "Units Sold"]

    # Find matching columns
    name_col = next((col for col in possible_name_cols if col in df.columns), None)
    price_col = next((col for col in possible_price_cols if col in df.columns), None)
    category_col = next((col for col in possible_category_cols if col in df.columns), None)
    quantity_col = next((col for col in possible_quantity_cols if col in df.columns), None)

    print(f"Detected columns - Name: {name_col}, Price: {price_col}, Category: {category_col}, Quantity: {quantity_col}")

    # Create standardized dataframe
    seed_data = df.copy()
    
    # Map columns or use defaults
    if name_col:
        seed_data["name"] = seed_data[name_col]
    else:
        seed_data["name"] = "Product " + seed_data.index.astype(str)
    
    if price_col:
        seed_data["price"] = seed_data[price_col]
    else:
        seed_data["price"] = random.uniform(10.0, 500.0)
    
    if category_col:
        seed_data["category"] = seed_data[category_col]
    else:
        seed_data["category"] = "General"
    
    if quantity_col:
        seed_data["quantity"] = seed_data[quantity_col]
    else:
        seed_data["quantity"] = random.randint(10, 200)

    # Clean and prepare data
    seed_data["name"] = seed_data["name"].apply(lambda x: str(x).strip() if pd.notnull(x) else "Unknown Product")
    seed_data["category"] = seed_data["category"].apply(lambda x: str(x).strip() if pd.notnull(x) else "General")
    seed_data["brand"] = seed_data["name"].apply(lambda x: str(x).split()[0] if x else "Unknown")
    seed_data["price"] = seed_data["price"].apply(lambda x: float(x) if pd.notnull(x) and x != "" else random.uniform(10.0, 500.0))
    seed_data["quantity"] = seed_data["quantity"].apply(lambda x: int(x) if pd.notnull(x) and str(x).isdigit() else random.randint(10, 200))

    # Remove duplicates and limit to reasonable number
    seed_data = seed_data.drop_duplicates(subset=["name"]).head(200)

    database.init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM products")

        rows = []
        for _, row in seed_data.iterrows():
            rows.append(
                (
                    row["name"],
                    int(row["quantity"]),
                    float(row["price"]),
                    str(row["category"]),
                    str(row["brand"]),
                    "Kaggle Retail Dataset",
                    "Main Warehouse",
                    "Imported from Kaggle retail store inventory forecasting dataset.",
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

    print(f"Successfully seeded {len(rows)} retail products into the inventory.")


if __name__ == "__main__":
    download_and_seed()
