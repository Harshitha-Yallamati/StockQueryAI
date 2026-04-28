from __future__ import annotations

from typing import Any

from core_config import get_settings
from mcp import MCPTool

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception as chroma_import_error:  # pragma: no cover - depends on optional runtime
    chromadb = None
    embedding_functions = None
    _CHROMA_IMPORT_ERROR = chroma_import_error
else:
    _CHROMA_IMPORT_ERROR = None


_collection = None


def add_knowledge(doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    collection = _get_collection()
    metadata = metadata or {"source": "manual_ingest"}
    collection.upsert(documents=[text], metadatas=[metadata], ids=[doc_id])
    return {"status": "success", "doc_id": doc_id}


def search_knowledge_base(query: str, n_results: int = 2) -> dict[str, Any]:
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=n_results)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            message = "No relevant knowledge-base documents were found for that query."
            return {
                "ok": True,
                "source": "knowledge_base",
                "summary": message,
                "rendered_response": message,
                "data": {"results": [], "count": 0},
            }

        formatted_results = [
            {
                "text": document,
                "source": metadata.get("source", "unknown"),
            }
            for document, metadata in zip(documents, metadatas)
        ]
        summary = f"Retrieved {len(formatted_results)} knowledge-base document(s)."
        rendered = ["Knowledge-base matches"]
        for item in formatted_results:
            excerpt = item["text"].strip().replace("\n", " ")
            rendered.append(f"- {item['source']}: {excerpt[:180]}")
        return {
            "ok": True,
            "source": "knowledge_base",
            "summary": summary,
            "rendered_response": "\n".join(rendered),
            "data": {"results": formatted_results, "count": len(formatted_results)},
        }
    except Exception as exc:
        message = f"Knowledge-base search failed safely: {exc}"
        return {
            "ok": False,
            "source": "knowledge_base",
            "summary": message,
            "rendered_response": message,
            "error": {"code": "KNOWLEDGE_SEARCH_FAILED", "message": message},
        }


def build_knowledge_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="search_knowledge_base",
            description="Search the knowledge base for manuals, policies, and unstructured reference content related to the user's question.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search in the knowledge base.",
                    }
                },
                "required": ["query"],
            },
            handler=search_knowledge_base,
        )
    ]


def _get_collection():
    global _collection

    if _CHROMA_IMPORT_ERROR is not None or chromadb is None or embedding_functions is None:
        raise RuntimeError(f"ChromaDB is unavailable: {_CHROMA_IMPORT_ERROR}")

    if _collection is None:
        settings = get_settings()
        client = chromadb.PersistentClient(path=settings.chroma_path)
        embedding_function = embedding_functions.DefaultEmbeddingFunction()
        _collection = client.get_or_create_collection(
            name="inventory_knowledge",
            embedding_function=embedding_function,
        )
    return _collection
