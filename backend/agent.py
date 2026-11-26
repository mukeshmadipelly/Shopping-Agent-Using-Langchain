import json
from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import get_settings
from backend.services import append_chat_message_db, get_chat_history_db
from backend.tools import build_session_tools

SYSTEM_PROMPT = (
    "You are a helpful, concise shopping assistant for an online grocery & pantry store. "
    "Follow these rules strictly:\n\n"
    "1. GUARDRAILS — If the user's request is unrelated to shopping, groceries, products, cart, "
    "or orders, politely decline and remind them you are a shopping assistant.\n"
    "2. PRODUCT SEARCH & AMBIGUITY — When the user asks for products, call `search_products` with "
    "relevant keywords and filters (`max_price`, `min_rating`, `is_organic`, `category`). "
    "Distinguish whole/fresh items from derived or processed products: for example, if the user "
    "asks for 'apples' (fresh fruit) and the catalog only returns 'Apple Cider Vinegar', clearly "
    "state that fresh apples are not in the catalog and offer Apple Cider Vinegar only as a related "
    "pantry alternative. Present matching items with their ID, name, price, rating, organic status, "
    "and stock_qty, always including `(ID:X)`.\n"
    "3. CART & BULK QUANTITY LIMITS — Use `add_to_cart`, `remove_from_cart`, `view_cart`, and "
    "`clear_cart` to manage the cart. Our store enforces a per-item limit of 20 units and checks "
    "available inventory (`stock_qty`). If a user requests a bulk quantity (e.g. 100 units), "
    "call `add_to_cart` or inspect `stock_qty` and clearly explain the 20-unit per-item limit and "
    "current stock level, offering to add up to the allowed limit.\n"
    "4. CHECKOUT AUTHORIZATION — Never call `checkout` without explicit final confirmation. "
    "When the user asks to checkout (or before placing an order), first call `view_cart`, "
    "explicitly summarize every item in the cart (name, quantity, unit price, subtotal) and the "
    "total amount, and ask for explicit confirmation (e.g. 'Shall I place this order?'). "
    "Only call `checkout` after the user confirms that summary.\n"
    "5. ORDER HISTORY — When the user asks about past orders, call `get_order_history`.\n"
    "6. IMAGE SEARCH — If the user attaches a product image, identify the product type, organic "
    "status if visible, and call `search_products` to find matching items in our catalog."
)


def _create_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    )


def _format_sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content) if content else ""


async def stream_chat_response(
    session_id: str,
    message: str,
    image_base64: str | None = None,
    image_mime: str | None = None,
) -> AsyncGenerator[str, None]:
    """Run the LangChain agent for a session and yield SSE events."""
    history = await get_chat_history_db(session_id, limit=16)
    await append_chat_message_db(session_id, "user", message)

    event_sink: dict[str, Any] = {}
    tools = build_session_tools(session_id, event_sink)

    try:
        llm = _create_llm()
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        lc_messages: list[Any] = []
        for msg in history:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))

        if image_base64:
            mime = image_mime or "image/jpeg"
            lc_messages.append(
                HumanMessage(
                    content=[
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_base64}"},
                        },
                        {"type": "text", "text": message or "Find products similar to this image."},
                    ]
                )
            )
        else:
            lc_messages.append(HumanMessage(content=message))

        full_text_parts: list[str] = []

        async for chunk, _metadata in agent.astream(
            {"messages": lc_messages},
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessage) and chunk.content and not getattr(chunk, "tool_calls", None):
                text_piece = _extract_text(chunk.content)
                if text_piece:
                    full_text_parts.append(text_piece)
                    yield _format_sse("token", {"text": text_piece})

        final_text = "".join(full_text_parts).strip()
        if final_text:
            await append_chat_message_db(session_id, "assistant", final_text)

        if "products" in event_sink:
            yield _format_sse("products", {"products": event_sink["products"]})
        if "cart" in event_sink:
            yield _format_sse("cart", {"cart": event_sink["cart"]})
        if "order" in event_sink:
            yield _format_sse("order", {"order": event_sink["order"]})

        yield _format_sse("done", {"message": final_text})

    except Exception as exc:
        err_str = str(exc)
        is_rate_limit = "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower()
        yield _format_sse(
            "error",
            {
                "status": 429 if is_rate_limit else 500,
                "detail": (
                    "Gemini API rate limit reached. Please wait a moment and try again."
                    if is_rate_limit
                    else f"Agent error: {err_str}"
                ),
            },
        )
