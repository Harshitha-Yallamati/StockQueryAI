import sqlite3
import random
import os

DB_FILENAME = "agent_inventory.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)

def generate_fake_data():
    brands = ["Sony", "Samsung", "Apple", "Dell", "HP", "Lenovo", "Asus", "Logitech", "Corsair", "Razer", "LG", "Bose"]
    categories = {"Electronics": ["Laptop", "Smartphone", "Tablet", "Monitor", "TV"], 
                  "Accessories": ["Mouse", "Keyboard", "Headphones", "Webcam", "USB Hub", "Cable"],
                  "Audio": ["Bluetooth Speaker", "Soundbar", "Earbuds", "Microphone"]}
    
    data = []
    
    # Generate 150-200 fake items
    for i in range(1, 201):
        category = random.choice(list(categories.keys()))
        product_type = random.choice(categories[category])
        brand = random.choice(brands)
        
        # Add random variations
        model_letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        model_nums = random.randint(100, 9000)
        
        name = f"{brand} {product_type} {model_letters}-{model_nums}"
        quantity = random.randint(0, 500) # Some will be zero for low stock testing
        
        price = 0.0
        if category == "Electronics":
            price = round(random.uniform(199.99, 2999.99), 2)
        elif category == "Accessories":
            price = round(random.uniform(9.99, 149.99), 2)
        else:
            price = round(random.uniform(29.99, 399.99), 2)
            
        data.append((name, quantity, price, category))
        
    return data

def seed_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Ensure table exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    
    fake_data = generate_fake_data()
    c.executemany("INSERT INTO products (name, quantity, price, category) VALUES (?, ?, ?, ?)", fake_data)
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(fake_data)} items into the database!")

if __name__ == "__main__":
    seed_db()
