from typing import Any
from backend.db import get_pool

MAX_CART_ITEM_QTY = 20


def _serialize_product(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": float(row["price"]),
        "description": row["description"],
        "is_organic": bool(row["is_organic"]),
        "stock_qty": int(row["stock_qty"]),
        "image_url": row["image_url"],
        "average_rating": round(float(row["average_rating"]), 2) if row["average_rating"] is not None else 0.0,
        "review_count": int(row["review_count"]),
    }


async def search_products_db(
    query: str = "",
    max_price: float | None = None,
    min_rating: float | None = None,
    is_organic: bool | None = None,
    category: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Search products using PostgreSQL tsvector GIN index + structured filters."""
    pool = await get_pool()
    conditions: list[str] = []
    params: list[Any] = []
    rank_expr = "0.0"

    clean_query = query.strip()
    if clean_query:
        params.append(clean_query)
        q_idx = len(params)
        params.append(f"%{clean_query}%")
        like_idx = len(params)
        conditions.append(
            f"(p.search_vector @@ websearch_to_tsquery('english', ${q_idx}) "
            f"OR p.name ILIKE ${like_idx} OR p.category ILIKE ${like_idx} OR p.description ILIKE ${like_idx})"
        )
        rank_expr = f"ts_rank(p.search_vector, websearch_to_tsquery('english', ${q_idx}))"

    if max_price is not None:
        params.append(max_price)
        conditions.append(f"p.price <= ${len(params)}")

    if is_organic is not None:
        params.append(is_organic)
        conditions.append(f"p.is_organic = ${len(params)}")

    if category:
        params.append(category.strip().lower())
        conditions.append(f"LOWER(p.category) = ${len(params)}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    having_clause = ""
    if min_rating is not None:
        params.append(min_rating)
        having_clause = f"HAVING COALESCE(AVG(r.rating), 0) >= ${len(params)}"

    params.append(limit)
    limit_idx = len(params)

    sql = f"""
        SELECT
            p.id,
            p.name,
            p.category,
            p.price,
            p.description,
            p.is_organic,
            p.stock_qty,
            p.image_url,
            COALESCE(AVG(r.rating), 0) AS average_rating,
            COUNT(r.id) AS review_count,
            {rank_expr} AS rank_score
        FROM products p
        LEFT JOIN reviews r ON r.product_id = p.id
        {where_clause}
        GROUP BY p.id
        {having_clause}
        ORDER BY rank_score DESC, average_rating DESC, p.price ASC
        LIMIT ${limit_idx}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [_serialize_product(r) for r in rows]


async def get_product_reviews_db(product_id: int) -> dict[str, Any] | None:
    """Return average rating, review count, and recent comments for a product."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM products WHERE id = $1", product_id)
        if not exists:
            return None
        stats = await conn.fetchrow(
            """
            SELECT COALESCE(AVG(rating), 0) AS avg_rating, COUNT(*) AS review_count
            FROM reviews
            WHERE product_id = $1
            """,
            product_id,
        )
        rows = await conn.fetch(
            """
            SELECT reviewer_name, rating, comment, created_at
            FROM reviews
            WHERE product_id = $1
            ORDER BY id DESC
            LIMIT 5
            """,
            product_id,
        )
    return {
        "product_id": product_id,
        "average_rating": round(float(stats["avg_rating"]), 2),
        "review_count": int(stats["review_count"]),
        "reviews": [
            {
                "reviewer_name": r["reviewer_name"],
                "rating": float(r["rating"]),
                "comment": r["comment"],
            }
            for r in rows
        ],
    }


async def get_cart_db(session_id: str) -> dict[str, Any]:
    """Return all items and totals for the session's cart."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.product_id,
                c.qty,
                p.name,
                p.category,
                p.price,
                p.is_organic,
                p.image_url
            FROM cart_items c
            JOIN products p ON p.id = c.product_id
            WHERE c.session_id = $1
            ORDER BY c.id ASC
            """,
            session_id,
        )

    items = []
    total_amount = 0.0
    total_items = 0
    for r in rows:
        unit_price = float(r["price"])
        qty = int(r["qty"])
        subtotal = round(unit_price * qty, 2)
        total_amount += subtotal
        total_items += qty
        items.append(
            {
                "product_id": r["product_id"],
                "name": r["name"],
                "category": r["category"],
                "price": unit_price,
                "qty": qty,
                "subtotal": subtotal,
                "is_organic": bool(r["is_organic"]),
                "image_url": r["image_url"],
            }
        )

    return {
        "session_id": session_id,
        "items": items,
        "total_items": total_items,
        "total_amount": round(total_amount, 2),
    }


async def add_to_cart_db(session_id: str, product_id: int, qty: int = 1) -> dict[str, Any]:
    """Add quantity of a product to the session cart, enforcing inventory and per-item limits."""
    if qty <= 0:
        raise ValueError("Quantity must be greater than 0.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        product = await conn.fetchrow(
            "SELECT id, name, stock_qty FROM products WHERE id = $1",
            product_id,
        )
        if not product:
            raise LookupError(f"Product with ID {product_id} not found.")

        existing_qty = await conn.fetchval(
            "SELECT qty FROM cart_items WHERE session_id = $1 AND product_id = $2",
            session_id,
            product_id,
        )
        new_total_qty = (existing_qty or 0) + qty
        stock_qty = int(product["stock_qty"])

        if new_total_qty > MAX_CART_ITEM_QTY:
            raise ValueError(
                f"Cannot add {qty} of {product['name']}: maximum allowed per item is {MAX_CART_ITEM_QTY} "
                f"(you currently have {existing_qty or 0} in your cart, and {stock_qty} are in stock)."
            )
        if new_total_qty > stock_qty:
            raise ValueError(
                f"Insufficient stock for {product['name']}: only {stock_qty} available "
                f"(you already have {existing_qty or 0} in your cart)."
            )

        await conn.execute(
            """
            INSERT INTO cart_items (session_id, product_id, qty, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (session_id, product_id)
            DO UPDATE SET qty = cart_items.qty + EXCLUDED.qty, updated_at = NOW()
            """,
            session_id,
            product_id,
            qty,
        )
    return await get_cart_db(session_id)


async def remove_from_cart_db(session_id: str, product_id: int, qty: int | None = None) -> dict[str, Any]:
    """Remove a product (or decrement its quantity) from the session cart."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if qty is None:
            await conn.execute(
                "DELETE FROM cart_items WHERE session_id = $1 AND product_id = $2",
                session_id,
                product_id,
            )
        else:
            existing = await conn.fetchval(
                "SELECT qty FROM cart_items WHERE session_id = $1 AND product_id = $2",
                session_id,
                product_id,
            )
            if existing is not None:
                new_qty = existing - qty
                if new_qty <= 0:
                    await conn.execute(
                        "DELETE FROM cart_items WHERE session_id = $1 AND product_id = $2",
                        session_id,
                        product_id,
                    )
                else:
                    await conn.execute(
                        "UPDATE cart_items SET qty = $1, updated_at = NOW() WHERE session_id = $2 AND product_id = $3",
                        new_qty,
                        session_id,
                        product_id,
                    )
    return await get_cart_db(session_id)


async def clear_cart_db(session_id: str) -> dict[str, Any]:
    """Clear all items in the session cart."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)
    return await get_cart_db(session_id)


async def checkout_cart_db(session_id: str) -> dict[str, Any]:
    """Convert all items in the session cart into a confirmed order."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                """
                SELECT c.product_id, c.qty, p.name, p.price
                FROM cart_items c
                JOIN products p ON p.id = c.product_id
                WHERE c.session_id = $1
                ORDER BY c.id ASC
                """,
                session_id,
            )
            if not rows:
                raise ValueError("Your cart is empty.")

            total_amount = round(sum(float(r["price"]) * int(r["qty"]) for r in rows), 2)
            order_row = await conn.fetchrow(
                """
                INSERT INTO orders (session_id, total_amount, status)
                VALUES ($1, $2, 'confirmed')
                RETURNING id, total_amount, status, created_at
                """,
                session_id,
                total_amount,
            )

            items_summary = []
            for r in rows:
                await conn.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, unit_price, qty)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    order_row["id"],
                    r["product_id"],
                    r["name"],
                    float(r["price"]),
                    int(r["qty"]),
                )
                items_summary.append(
                    {
                        "product_id": r["product_id"],
                        "product_name": r["name"],
                        "unit_price": float(r["price"]),
                        "qty": int(r["qty"]),
                    }
                )

            await conn.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)

    return {
        "order_id": order_row["id"],
        "session_id": session_id,
        "total_amount": float(order_row["total_amount"]),
        "status": order_row["status"],
        "created_at": order_row["created_at"].isoformat(),
        "items": items_summary,
    }


async def get_order_history_db(session_id: str) -> list[dict[str, Any]]:
    """Return past orders and their line items for a session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        orders = await conn.fetch(
            """
            SELECT id, total_amount, status, created_at
            FROM orders
            WHERE session_id = $1
            ORDER BY id DESC
            """,
            session_id,
        )
        if not orders:
            return []

        order_ids = [o["id"] for o in orders]
        items = await conn.fetch(
            """
            SELECT order_id, product_id, product_name, unit_price, qty
            FROM order_items
            WHERE order_id = ANY($1::int[])
            ORDER BY id ASC
            """,
            order_ids,
        )

    items_by_order: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        items_by_order.setdefault(item["order_id"], []).append(
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "unit_price": float(item["unit_price"]),
                "qty": int(item["qty"]),
            }
        )

    return [
        {
            "order_id": o["id"],
            "total_amount": float(o["total_amount"]),
            "status": o["status"],
            "created_at": o["created_at"].isoformat(),
            "items": items_by_order.get(o["id"], []),
        }
        for o in orders
    ]


async def get_chat_history_db(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    """Return recent conversation messages for a session in chronological order."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = $1
            ORDER BY id DESC
            LIMIT $2
            """,
            session_id,
            limit,
        )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def append_chat_message_db(session_id: str, role: str, content: str) -> None:
    """Persist a single chat message for a session."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES ($1, $2, $3)
            """,
            session_id,
            role,
            content,
        )
