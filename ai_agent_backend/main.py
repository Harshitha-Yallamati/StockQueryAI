import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import database as db
from agent import run_agent
import rag

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Boot the database directly on startup to ensure we have tables/data
db.init_db()

app = FastAPI(title="StockQuery AI Agent Backend", version="1.0.0")

# Enable CORS allowing the Vite dev server to hit this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8081", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str
    
class AskResponse(BaseModel):
    answer: str

class IngestRequest(BaseModel):
    doc_id: str
    text: str
    metadata: dict = {}

# Simple in-memory storage for previous messages (Bonus Requirement)
# In production, this should be scoped per-user/session in a database.
session_history = []

@app.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """
    Accepts a natural language query about the inventory, uses Ollama 
    tool calling to fetch data, and returns the response.
    """
    logger.info(f"Received question: {req.question}")
    
    try:
        # Pass question and history to our agent engine
        answer = run_agent(req.question, message_history=session_history)
        
        # Save standard history locally (preventing infinite memory growth via simple slice)
        session_history.append({"role": "user", "content": req.question})
        session_history.append({"role": "assistant", "content": answer})
        
        # Keep only the last 10 interactions for memory constraints
        if len(session_history) > 20:
            session_history.pop(0)
            session_history.pop(0)
            
        return AskResponse(answer=answer)
    
    except Exception as e:
        logger.error(f"Error handling /ask request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal AI Engine Error")

@app.post("/ingest")
async def ingest_document(req: IngestRequest):
    """
    Manually injects textual data into the vector database (RAG).
    Useful for pushing product manuals, return policies, or detailed specs.
    """
    try:
        rag.add_knowledge(doc_id=req.doc_id, text=req.text, metadata=req.metadata)
        return {"status": "success", "message": f"Document {req.doc_id} directly embedded."}
    except Exception as e:
        logger.error(f"Error ingesting document {req.doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to ingest document into Vector Store.")

# --- Frontend GUI Integrations ---

@app.get("/api/dashboard/stats")
def get_stats():
    return db.get_inventory_stats()

@app.get("/api/inventory")
def get_inventory():
    # Map 'quantity' back to 'stock_quantity' for UI expectations, and 'id' to 'product_id'
    products = db.get_all_products()
    return [{
        "product_id": p["id"],
        "product_name": p["name"],
        "stock_quantity": p["quantity"],
        "price": p["price"],
        "category": p["category"],
        "brand": "N/A"
    } for p in products]

@app.post("/api/inventory")
def add_inventory(payload: Dict[Any, Any]):
    try:
        new_id = db.add_product(payload)
        return {"id": new_id, "product_name": payload.get("product_name")}
    except Exception as e:
        logger.error(f"Failed to add product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/inventory/{product_id}")
def update_inventory(product_id: int, payload: Dict[Any, Any]):
    try:
        db.update_product(product_id, payload)
        return {"message": "Product updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/inventory/{product_id}")
def remove_inventory(product_id: int):
    try:
        db.delete_product(product_id)
        return {"message": "Product deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
def get_alerts():
    products = db.get_all_products()
    # Filter and format for alerts UI
    alerts = [p for p in products if p["quantity"] < 10]
    return [{
        "product_id": p["id"],
        "product_name": p["name"],
        "stock_quantity": p["quantity"],
        "category": p["category"]
    } for p in alerts]

@app.get("/")
def health_check():
    return {"status": "ok", "message": "StockQuery AI Agent is running on FastAPI"}
