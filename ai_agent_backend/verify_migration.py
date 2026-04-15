import sqlite3
import os
import chromadb
from chromadb.utils import embedding_functions

DB_FILENAME = "agent_inventory.db"
DB_PATH = os.path.normpath("c:/Projects/StockQueryAI/ai_agent_backend/agent_inventory.db")
CHROMA_DATA_PATH = os.path.normpath("c:/Projects/StockQueryAI/ai_agent_backend/chroma_db")

def verify():
    print("--- Database Verification ---")
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
    else:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products")
        count = c.fetchone()[0]
        print(f"Total products in DB: {count}")
        
        c.execute("SELECT name, category FROM products LIMIT 3")
        rows = c.fetchall()
        print("Sample products:")
        for r in rows:
            print(f" - {r[0]} ({r[1]})")
        conn.close()

    print("\n--- ChromaDB Verification ---")
    if not os.path.exists(CHROMA_DATA_PATH):
        print(f"Error: {CHROMA_DATA_PATH} not found.")
    else:
        client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        collection = client.get_collection(name="inventory_knowledge")
        count = collection.count()
        print(f"Total items in knowledge base: {count}")
        
        # Simple query
        results = collection.query(query_texts=["home theater"], n_results=1)
        if results["documents"][0]:
            print(f"Sample retrieved context: {results['documents'][0][0][:100]}...")
        else:
            print("No items retrieved for 'home theater'")

if __name__ == "__main__":
    verify()
