import json
import uuid
import pytest

from backend.db import close_pool, get_pool
from backend.seed import seed_database
from backend.tools import build_session_tools


@pytest.fixture(autouse=True)
async def setup_and_teardown():
    await seed_database()
    yield
    await close_pool()


async def test_session_bound_tools_flow():
    session_id = f"tool-test-{uuid.uuid4().hex[:10]}"
    sink: dict = {}
    tools = {t.name: t for t in build_session_tools(session_id, sink)}

    try:
        search_out = json.loads(
            await tools["search_products"].ainvoke(
                {"query": "honey", "is_organic": True, "max_price": 20.0}
            )
        )
        assert len(search_out) >= 1
        assert "products" in sink
        assert "stock_qty" in search_out[0]
        product_id = search_out[0]["id"]

        bulk_out = json.loads(
            await tools["add_to_cart"].ainvoke({"product_id": product_id, "qty": 100})
        )
        assert "error" in bulk_out
        assert "20" in bulk_out["error"]

        reviews_out = json.loads(
            await tools["get_product_reviews"].ainvoke({"product_id": product_id})
        )
        assert reviews_out["product_id"] == product_id
        assert reviews_out["review_count"] > 0

        cart_out = json.loads(
            await tools["add_to_cart"].ainvoke({"product_id": product_id, "qty": 2})
        )
        assert cart_out["total_items"] == 2
        assert sink["cart"]["total_items"] == 2

        order_out = json.loads(await tools["checkout"].ainvoke({}))
        assert order_out["status"] == "confirmed"
        assert sink["order"]["order_id"] == order_out["order_id"]

        history_out = json.loads(await tools["get_order_history"].ainvoke({}))
        assert len(history_out) == 1
        assert history_out[0]["order_id"] == order_out["order_id"]
    finally:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)
            await conn.execute("DELETE FROM orders WHERE session_id = $1", session_id)
