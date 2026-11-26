import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from backend.db import close_pool, get_pool
from backend.main import app
from backend.seed import seed_database


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    await seed_database()
    yield
    await close_pool()


@pytest.fixture
def session_id() -> str:
    return f"test-{uuid.uuid4().hex[:10]}"


async def _cleanup_session(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM orders WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM chat_messages WHERE session_id = $1", session_id)


async def test_health_and_seeded_products():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        all_products = await client.get("/api/products?limit=100")
        assert all_products.status_code == 200
        data = all_products.json()
        assert data["count"] == 85

        filtered = await client.get(
            "/api/products?q=snacks&is_organic=true&max_price=15"
        )
        assert filtered.status_code == 200
        items = filtered.json()["products"]
        assert len(items) > 0
        assert all(p["is_organic"] is True and p["price"] <= 15.0 for p in items)


async def test_session_required_for_cart():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/cart")
        assert res.status_code == 400


async def test_cart_and_checkout_lifecycle(session_id: str):
    transport = ASGITransport(app=app)
    headers = {"X-Session-Id": session_id}
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            products_res = await client.get("/api/products?limit=2")
            first_product = products_res.json()["products"][0]

            add_res = await client.post(
                "/api/cart/items",
                headers=headers,
                json={"product_id": first_product["id"], "qty": 2},
            )
            assert add_res.status_code == 200
            assert add_res.json()["total_items"] == 2

            dec_res = await client.delete(
                f"/api/cart/items/{first_product['id']}?qty=1",
                headers=headers,
            )
            assert dec_res.status_code == 200
            assert dec_res.json()["total_items"] == 1

            checkout_res = await client.post("/api/checkout", headers=headers)
            assert checkout_res.status_code == 200
            order = checkout_res.json()
            assert order["status"] == "confirmed"
            assert order["items"][0]["product_id"] == first_product["id"]

            orders_res = await client.get("/api/orders", headers=headers)
            assert orders_res.status_code == 200
            assert len(orders_res.json()["orders"]) == 1

            cart_after = await client.get("/api/cart", headers=headers)
            assert cart_after.json()["total_items"] == 0
    finally:
        await _cleanup_session(session_id)


async def test_chat_sse_stream_mocked(monkeypatch: pytest.MonkeyPatch, session_id: str):
    async def fake_stream(session_id: str, message: str, **_kwargs):
        yield f"event: token\ndata: {json.dumps({'text': 'Here are some snacks.'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'message': 'Here are some snacks.'})}\n\n"

    monkeypatch.setattr("backend.main.stream_chat_response", fake_stream)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/chat",
            headers={"X-Session-Id": session_id},
            json={"message": "Show me organic snacks under $15"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "event: token" in res.text
        assert "Here are some snacks." in res.text
        assert "event: done" in res.text
