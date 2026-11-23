import asyncio
import json

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError
from pytest import raises

from app.agent import build_graph
from app.main import ChatRequest, Product, app


def request(method, path, payload=None):
    events = []
    body = json.dumps(payload).encode() if payload is not None else b""

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(event):
        events.append(event)

    async def call():
        scope = {
            "type": "http", "asgi": {"spec_version": "2.4"}, "method": method,
            "scheme": "http", "path": path, "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
        }
        await asyncio.wait_for(app(scope, receive, send), 10)

    asyncio.run(call())
    return events[0]["status"], events[1]["body"]


def test_health_contract():
    assert request("GET", "/health") == (200, b"ok")


def test_bad_chat_is_rejected_before_services():
    code, _ = request("POST", "/chat", {"user_id": "x", "thread_id": "y", "message": "  "})
    assert code == 422


def test_seller_dashboard_requires_token():
    code, _ = request("GET", "/seller/dashboard")
    assert code == 401


def test_catalog_rejects_negative_stock():
    with raises(ValidationError):
        Product(sku="one", name="Shirt", size="M", color="black", price=100, stock=-1)


def test_grader_contract_rejects_unknown_fields():
    with raises(ValidationError):
        ChatRequest(user_id="x", thread_id="y", message="hello", role="system")


def test_confirmation_requires_pending_checkout():
    graph = build_graph(InMemorySaver())
    state = graph.invoke(
        {"turn": "one"}, {"configurable": {"thread_id": "unit-test"}},
        context={"message": "confirm order"}, durability="exit",
    )
    assert "Ask to check out first" in state["reply"]
    assert state["tool_calls"] == []
    assert state["tokens"] == {"in": 0, "out": 0}
