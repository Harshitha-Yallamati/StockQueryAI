import sqlite3
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import database
import main
from inventory_tools import get_cheapest_product

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    db_uri = f"file:stockquery-test-{uuid.uuid4().hex}?mode=memory&cache=shared"
    keeper_connection = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
    keeper_connection.row_factory = sqlite3.Row

    def mock_get_db_connection(*args, **kwargs):
        # Keep one connection open for the full test so shared in-memory state survives schema setup.
        conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def mock_llm_create(*args, **kwargs):
        raise RuntimeError("LLM disabled during tests")

    monkeypatch.setattr(database, "get_db_connection", mock_get_db_connection)
    monkeypatch.setattr(
        main.stock_query_agent,
        "client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=mock_llm_create),
            )
        ),
    )

    database.init_db()
    database.add_product({
        "name": "Test Laptop",
        "quantity": 5,
        "price": 999.99,
        "category": "Electronics",
        "brand": "Acer",
        "supplier": "Tech Distributors",
        "warehouse_location": "A-01",
        "description": "15-inch productivity laptop",
    })
    mouse = database.add_product({
        "name": "Cheap Mouse",
        "quantity": 50,
        "price": 19.99,
        "category": "Accessories",
        "brand": "Logitech",
        "supplier": "Ingram Micro",
        "warehouse_location": "B-02",
        "description": "Budget wireless mouse",
    })
    database.place_order({"product_id": mouse["id"], "quantity": 12})

    yield

    main.stock_query_agent.sessions._sessions.clear()
    keeper_connection.close()


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_inventory(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [p["name"] for p in data]
    assert "Test Laptop" in names
    assert "Cheap Mouse" in names

def test_cheapest_product_tool():
    result = get_cheapest_product()
    assert result["ok"] is True
    assert result["data"]["product"]["name"] == "Cheap Mouse"

def test_chat_fallback(client):
    response = client.post("/api/chat", json={
        "question": "What is the capital of France?",
        "session_id": "test_session"
    })
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "inventory and knowledge-base questions only" in data["answer"]

def test_chat_routing_to_tool(client):
    response = client.post("/api/chat", json={
        "question": "What is the cheapest product?",
        "session_id": "test_session_2"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Cheap Mouse" in data["answer"] or "get_cheapest_product" in data["tools_used"]


def test_chat_greeting_skips_tools(client):
    response = client.post("/api/chat", json={
        "question": "hlo",
        "session_id": "test_greeting_session"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Hello!" in data["answer"]
    assert "inventory, products, stock levels, and orders" in data["answer"]
    assert data["tools_used"] == []


def test_chat_routes_price_lookup_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "What is the price of Test Laptop?",
        "session_id": "test_session_3"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Price: $999.99" in data["answer"]
    assert "get_product_details" in data["tools_used"]


def test_chat_routes_catalog_search_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "Show Logitech products",
        "session_id": "test_session_4"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Cheap Mouse" in data["answer"]
    assert "search_inventory_catalog" in data["tools_used"]


def test_chat_routes_broad_availability_search_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "What Logitech products do we have?",
        "session_id": "test_session_4b"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Cheap Mouse" in data["answer"]
    assert "search_inventory_catalog" in data["tools_used"]


def test_chat_routes_inventory_overview_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "Give me an inventory overview",
        "session_id": "test_session_5"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Inventory overview" in data["answer"]
    assert "get_inventory_overview" in data["tools_used"]


def test_chat_routes_pending_orders_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "Show pending orders",
        "session_id": "test_session_6"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Pending orders" in data["answer"]
    assert "list_orders_by_status" in data["tools_used"]


def test_chat_routes_category_listing_without_llm(client):
    response = client.post("/api/chat", json={
        "question": "What categories do we have?",
        "session_id": "test_session_7"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Inventory categories" in data["answer"]
    assert "Accessories" in data["answer"]
    assert "list_product_categories" in data["tools_used"]


def test_chat_handles_typo_for_out_of_stock_query(client):
    response = client.post("/api/chat", json={
        "question": "what are out os stock",
        "session_id": "test_typo_out_stock"
    })
    assert response.status_code == 200
    data = response.json()
    assert "No products are currently out of stock." in data["answer"]
    assert "list_out_of_stock_products" in data["tools_used"]


def test_chat_handles_bare_product_name_without_exact_question(client):
    response = client.post("/api/chat", json={
        "question": "Test Laptop",
        "session_id": "test_bare_product"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Test Laptop" in data["answer"]
    assert "Price: $999.99" in data["answer"]
    assert "get_product_details" in data["tools_used"]


def test_chat_handles_typo_in_product_name(client):
    response = client.post("/api/chat", json={
        "question": "tell me about Tst Laptop",
        "session_id": "test_typo_product"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Test Laptop" in data["answer"]
    assert "get_product_details" in data["tools_used"]


def test_chat_reuses_previous_verified_order_result(client):
    first = client.post("/api/chat", json={
        "question": "how many orders are there?",
        "session_id": "test_repeat_orders"
    })
    assert first.status_code == 200
    first_data = first.json()
    assert "Found 1 order(s)." in first_data["answer"]
    assert "list_orders" in first_data["tools_used"]

    second = client.post("/api/chat", json={
        "question": "what are the orders remaining",
        "session_id": "test_repeat_orders"
    })
    assert second.status_code == 200
    second_data = second.json()
    assert "Based on the latest verified result:" in second_data["answer"]
    assert "Cheap Mouse" in second_data["answer"]
    assert second_data["tools_used"] == []
