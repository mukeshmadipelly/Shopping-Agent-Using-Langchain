from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent import stream_chat_response
from backend.config import get_settings
from backend.db import close_pool
from backend.seed import seed_database
from backend.services import (
    add_to_cart_db,
    checkout_cart_db,
    clear_cart_db,
    get_cart_db,
    get_chat_history_db,
    get_order_history_db,
    get_product_reviews_db,
    remove_from_cart_db,
    search_products_db,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await seed_database()
    yield
    await close_pool()


app = FastAPI(
    title="Scalable Shopping Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    image_base64: str | None = None
    image_mime: str | None = None


class CartItemRequest(BaseModel):
    product_id: int
    qty: int = Field(default=1, ge=1)


def _require_session(x_session_id: str | None) -> str:
    if not x_session_id or not x_session_id.strip():
        raise HTTPException(status_code=400, detail="X-Session-Id header is required.")
    return x_session_id.strip()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/products")
async def list_products(
    q: str = Query(default=""),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=1, le=5),
    is_organic: bool | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    products = await search_products_db(
        query=q,
        max_price=max_price,
        min_rating=min_rating,
        is_organic=is_organic,
        category=category,
        limit=limit,
    )
    return {"products": products, "count": len(products)}


@app.get("/api/products/{product_id}/reviews")
async def product_reviews(product_id: int):
    reviews = await get_product_reviews_db(product_id)
    if reviews is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return reviews


@app.get("/api/cart")
async def get_cart(x_session_id: str | None = Header(default=None)):
    session_id = _require_session(x_session_id)
    return await get_cart_db(session_id)


@app.post("/api/cart/items")
async def add_cart_item(
    payload: CartItemRequest,
    x_session_id: str | None = Header(default=None),
):
    session_id = _require_session(x_session_id)
    try:
        return await add_to_cart_db(session_id, payload.product_id, payload.qty)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/cart/items/{product_id}")
async def remove_cart_item(
    product_id: int,
    qty: int | None = Query(default=None, ge=1),
    x_session_id: str | None = Header(default=None),
):
    session_id = _require_session(x_session_id)
    return await remove_from_cart_db(session_id, product_id, qty)


@app.delete("/api/cart")
async def clear_cart(x_session_id: str | None = Header(default=None)):
    session_id = _require_session(x_session_id)
    return await clear_cart_db(session_id)


@app.post("/api/checkout")
async def checkout(x_session_id: str | None = Header(default=None)):
    session_id = _require_session(x_session_id)
    try:
        return await checkout_cart_db(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/orders")
async def list_orders(x_session_id: str | None = Header(default=None)):
    session_id = _require_session(x_session_id)
    orders = await get_order_history_db(session_id)
    return {"orders": orders}


@app.get("/api/chat/history")
async def chat_history(x_session_id: str | None = Header(default=None)):
    session_id = _require_session(x_session_id)
    messages = await get_chat_history_db(session_id)
    return {"messages": messages}


@app.post("/api/chat")
async def chat(
    payload: ChatRequest,
    x_session_id: str | None = Header(default=None),
):
    session_id = _require_session(x_session_id)
    return StreamingResponse(
        stream_chat_response(
            session_id=session_id,
            message=payload.message,
            image_base64=payload.image_base64,
            image_mime=payload.image_mime,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
