import sqlite3
import os
import rag

DB_FILENAME = "agent_inventory.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_FILENAME)

def seed_knowledge_base():
    if not os.path.exists(DB_PATH):
        print("Database not found. Please run seed_kaggle.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT name, category, price FROM products LIMIT 50')
    products = c.fetchall()
    conn.close()

    print(f"Seeding {len(products)} products into ChromaDB for RAG...")
    
    for p in products:
        doc_id = f"prod_{p['name'].replace(' ', '_')[:40]}"
        text = f"Product: {p['name']}. Category: {p['category']}. Price: ${p['price']}. This is part of our standard electronics inventory."
        metadata = {"source": "kaggle_migration", "category": p['category']}
        
        try:
            rag.add_knowledge(doc_id=doc_id, text=text, metadata=metadata)
        except Exception as e:
            print(f"Failed to ingest {p['name']}: {e}")

    print("ChromaDB seeding complete!")

if __name__ == "__main__":
    seed_knowledge_base()
