import os
import chromadb
from chromadb.utils import embedding_functions

# Initialize a persistent local ChromaDB instance
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Using default all-MiniLM-L6-v2 embeddings to keep it lightweight and blazing fast
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Create or load the knowledge collection
collection = chroma_client.get_or_create_collection(
    name="inventory_knowledge",
    embedding_function=embedding_function
)

def add_knowledge(doc_id: str, text: str, metadata: dict = None):
    """
    Ingests unstructured text into the RAG database for semantic search later.
    """
    if not metadata:
        metadata = {"source": "manual_ingest"}
        
    collection.add(
        documents=[text],
        metadatas=[metadata],
        ids=[doc_id]
    )

def search_knowledge_base(query: str, n_results: int = 2) -> dict:
    """
    Uses vector similarity to find unstructured information related to the user's query.
    Returns the raw chunks to the agent.
    """
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results["documents"][0]:
            return {"context": "No relevant documents found in the vault.", "sources": []}
            
        docs = results["documents"][0]
        sources = [m.get("source", "unknown") for m in results["metadatas"][0]]
        
        return {
            "retrieved_context": "\n---\n".join(docs),
            "sources": sources
        }
    except Exception as e:
        return {"error": f"Failed to traverse the knowledge base: {str(e)}"}
