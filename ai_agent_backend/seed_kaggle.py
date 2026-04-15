import sqlite3
import requests
import pandas as pd
import io
import random
import os

CSV_URL = "https://raw.githubusercontent.com/zulfaan/intro-to-data-engineer-project_pacmann/main/source-marketing_data/ElectronicsProductsPricingData.csv"
DB_FILENAME = "agent_inventory.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)

def download_and_seed():
    print(f"Downloading dataset from {CSV_URL}...")
    try:
        response = requests.get(CSV_URL)
        response.raise_for_status()
        
        # Load into pandas
        df = pd.read_csv(io.StringIO(response.text))
        print(f"Loaded {len(df)} rows from CSV.")
        
        # Cleanup and Mapping
        # Keep only relevant columns if they exist
        required_cols = ['name', 'prices.amountMax', 'categories', 'prices.availability']
        for col in required_cols:
            if col not in df.columns:
                print(f"Warning: Column {col} missing from CSV. Using fallback.")
                df[col] = "N/A" if col != 'prices.amountMax' else 0.0

        # Create localized dataframe for DB
        # 1. Primary Category
        df['clean_category'] = df['categories'].apply(lambda x: str(x).split(',')[0].strip() if pd.notnull(x) else "Electronics")
        
        # 2. Quantity Logic
        def derive_quantity(availability):
            avail = str(availability).lower()
            if "yes" in avail or "in stock" in avail or "true" in avail:
                return random.randint(15, 300)
            return 0
        
        df['derived_quantity'] = df['prices.availability'].apply(derive_quantity)
        
        # 3. Final Selection
        # Limit to 150 unique high-quality products
        seed_data = df.drop_duplicates(subset=['name']).head(150)
        
        # Open DB connection
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Wipe existing data
        print("Clearing existing products table...")
        c.execute("DELETE FROM products")
        
        # Insert new data
        print("Seeding real Kaggle data...")
        count = 0
        for _, row in seed_data.iterrows():
            c.execute(
                "INSERT INTO products (name, quantity, price, category) VALUES (?, ?, ?, ?)",
                (row['name'], int(row['derived_quantity']), float(row['prices.amountMax']), row['clean_category'])
            )
            count += 1
            
        conn.commit()
        conn.close()
        print(f"Successfully seeded {count} real products into the inventory!")
        
    except Exception as e:
        print(f"Failed to seed Kaggle data: {e}")

if __name__ == "__main__":
    download_and_seed()
