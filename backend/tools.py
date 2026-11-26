import json
from typing import Any

from langchain_core.tools import tool

from backend.services import (
    add_to_cart_db,
    checkout_cart_db,
    clear_cart_db,
    get_cart_db,
    get_order_history_db,
    get_product_reviews_db,
    remove_from_cart_db,
    search_products_db,
)


def build_session_tools(session_id: str, event_sink: dict[str, Any]) -> list:
    """Create session-bound async LangChain tools for a single user session."""

    @tool
    async def search_products(
        query: str = "",
        max_price: float | None = None,
        min_rating: float | None = None,
        is_organic: bool | None = None,
        category: str | None = None,
    ) -> str:
        """
        Search the product catalog by keyword and optional filters.
        Args:
            query: Search keyword(s) matched against name, category, and description.
            max_price: Maximum price in USD.
            min_rating: Minimum average customer rating (1.0 to 5.0).
            is_organic: Filter to organic-only (True) or non-organic (False).
            category: Exact category slug (e.g. 'honey', 'snacks', 'oil', 'nuts', 'tea', 'coffee').
        Returns a JSON array of matching products with id, name, category, price,
        description, is_organic, image_url, average_rating, and review_count.
        """
        products = await search_products_db(
            query=query,
            max_price=max_price,
            min_rating=min_rating,
            is_organic=is_organic,
            category=category,
            limit=10,
        )
        event_sink["products"] = products
        return json.dumps(products)

    @tool
    async def get_product_reviews(product_id: int) -> str:
        """
        Get average rating, review count, and recent customer comments for a product by ID.
        """
        result = await get_product_reviews_db(product_id)
        if result is None:
            return json.dumps({"error": f"Product with ID {product_id} not found."})
        return json.dumps(result)

    @tool
    async def view_cart() -> str:
        """
        View the current items, quantities, and total amount in the user's shopping cart.
        """
        cart = await get_cart_db(session_id)
        event_sink["cart"] = cart
        return json.dumps(cart)

    @tool
    async def add_to_cart(product_id: int, qty: int = 1) -> str:
        """
        Add a product (by product_id) to the user's shopping cart.
        """
        try:
            cart = await add_to_cart_db(session_id, product_id, qty)
            event_sink["cart"] = cart
            return json.dumps(cart)
        except (ValueError, LookupError) as exc:
            return json.dumps({"error": str(exc)})

    @tool
    async def remove_from_cart(product_id: int, qty: int | None = None) -> str:
        """
        Remove a product from the cart, or reduce its quantity by qty if provided.
        """
        cart = await remove_from_cart_db(session_id, product_id, qty)
        event_sink["cart"] = cart
        return json.dumps(cart)

    @tool
    async def clear_cart() -> str:
        """
        Remove all items from the user's shopping cart.
        """
        cart = await clear_cart_db(session_id)
        event_sink["cart"] = cart
        return json.dumps(cart)

    @tool
    async def checkout() -> str:
        """
        Place an order for all items currently in the user's shopping cart.
        Only call this after the user explicitly confirms they want to place the order.
        """
        try:
            order = await checkout_cart_db(session_id)
            event_sink["order"] = order
            event_sink["cart"] = await get_cart_db(session_id)
            return json.dumps(order)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    @tool
    async def get_order_history() -> str:
        """
        Retrieve the user's past orders and their items for the current session.
        """
        orders = await get_order_history_db(session_id)
        return json.dumps(orders)

    return [
        search_products,
        get_product_reviews,
        view_cart,
        add_to_cart,
        remove_from_cart,
        clear_cart,
        checkout,
        get_order_history,
    ]
