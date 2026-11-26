import asyncio
from backend.db import close_pool, get_pool, run_migrations

# Curated category-level Unsplash photo URLs (primary) and Wikimedia Commons fallbacks
CATEGORY_IMAGES: dict[str, tuple[str, str]] = {
    "honey": (
        "https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Runny_hunny.jpg/640px-Runny_hunny.jpg",
    ),
    "oil": (
        "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Olive_oil_from_Oneglia.jpg/640px-Olive_oil_from_Oneglia.jpg",
    ),
    "nuts": (
        "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Almonds_in_bowl.jpg/640px-Almonds_in_bowl.jpg",
    ),
    "seeds": (
        "https://images.unsplash.com/photo-1515543904379-3d757afe72e4?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Chia_seeds.jpg/640px-Chia_seeds.jpg",
    ),
    "grains": (
        "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Rolled_oats.jpg/640px-Rolled_oats.jpg",
    ),
    "tea": (
        "https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Green_tea_leaves.jpg/640px-Green_tea_leaves.jpg",
    ),
    "coffee": (
        "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG",
    ),
    "snacks": (
        "https://images.unsplash.com/photo-1599490659213-e2b9527bd087?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Granola_in_bowl.jpg/640px-Granola_in_bowl.jpg",
    ),
    "dairy-alt": (
        "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Almond_milk_in_glass.jpg/640px-Almond_milk_in_glass.jpg",
    ),
    "spices": (
        "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Turmeric_powder.jpg/640px-Turmeric_powder.jpg",
    ),
    "condiments": (
        "https://images.unsplash.com/photo-1472476443507-c7a5948772fc?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Maple_syrup.jpg/640px-Maple_syrup.jpg",
    ),
    "baking": (
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Wheat_flour.jpg/640px-Wheat_flour.jpg",
    ),
    "superfoods": (
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Spirulina_powder.jpg/640px-Spirulina_powder.jpg",
    ),
    "beverages": (
        "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=600&q=80",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Kombucha_bottle.jpg/640px-Kombucha_bottle.jpg",
    ),
}

# 85 products: (name, category, price, description, is_organic)
PRODUCTS: list[tuple[str, str, float, str, bool]] = [
    # --- Honey (8) ---
    ("Organic Raw Honey", "honey", 14.99, "Pure organic raw honey, unfiltered and cold-pressed", True),
    ("Wildflower Honey", "honey", 12.99, "Natural wildflower honey from local beekeepers", False),
    ("Organic Manuka Honey", "honey", 29.99, "Premium organic Manuka honey from New Zealand", True),
    ("Clover Honey", "honey", 8.99, "Classic clover honey, smooth and sweet", False),
    ("Organic Buckwheat Honey", "honey", 18.99, "Dark and robust organic buckwheat honey, antioxidant-rich", True),
    ("Orange Blossom Honey", "honey", 15.99, "Light and floral orange blossom honey", False),
    ("Organic Acacia Honey", "honey", 17.99, "Light and mild organic acacia honey, low glycemic index", True),
    ("Creamed Honey", "honey", 11.99, "Smooth creamed honey with spreadable texture", False),
    # --- Oils (6) ---
    ("Organic Extra Virgin Olive Oil", "oil", 16.99, "Cold-pressed organic EVOO from Mediterranean olives", True),
    ("Coconut Oil", "oil", 12.49, "Refined coconut oil, great for high-heat cooking", False),
    ("Organic Flaxseed Oil", "oil", 14.99, "Cold-pressed organic flaxseed oil, rich in omega-3", True),
    ("Avocado Oil", "oil", 18.99, "Cold-pressed avocado oil, high smoke point", False),
    ("Organic Sesame Oil", "oil", 11.49, "Toasted organic sesame oil for stir-fries and dressings", True),
    ("Ghee Clarified Butter", "oil", 15.49, "Grass-fed clarified butter with rich nutty aroma", False),
    # --- Nuts & Seeds (10) ---
    ("Organic Almonds", "nuts", 11.99, "Raw organic almonds, unsalted, non-GMO certified", True),
    ("Roasted Cashews", "nuts", 9.99, "Lightly salted dry-roasted cashews", False),
    ("Organic Chia Seeds", "seeds", 8.49, "Organic black chia seeds, high in fiber and omega-3", True),
    ("Mixed Nuts", "nuts", 13.99, "Premium mix of walnuts, pecans, almonds and Brazil nuts", False),
    ("Organic Walnuts", "nuts", 12.99, "Raw organic walnut halves, rich in plant-based omega-3", True),
    ("Organic Pumpkin Seeds", "seeds", 9.49, "Raw organic pepitas, great source of magnesium and zinc", True),
    ("Roasted Pistachios", "nuts", 14.49, "California dry-roasted pistachios with sea salt", False),
    ("Organic Hemp Hearts", "seeds", 13.49, "Shelled organic hemp seeds, complete plant protein", True),
    ("Organic Flax Seeds", "seeds", 6.99, "Whole organic golden flax seeds for smoothies and baking", True),
    ("Pecan Halves", "nuts", 15.99, "Fresh unsalted pecan halves for snacking and pies", False),
    # --- Grains & Cereals (8) ---
    ("Organic Quinoa", "grains", 10.99, "Organic white quinoa, complete protein, gluten-free", True),
    ("Rolled Oats", "grains", 5.49, "Whole grain rolled oats, great for porridge and baking", False),
    ("Organic Brown Rice", "grains", 7.99, "Long-grain organic brown rice, naturally gluten-free", True),
    ("Steel-Cut Oats", "grains", 6.99, "Traditional steel-cut oats, low GI, hearty texture", False),
    ("Organic Red Lentils", "grains", 6.49, "Split organic red lentils, quick-cooking protein staple", True),
    ("Organic Chickpeas", "grains", 5.99, "Dried organic garbanzo beans for hummus and curries", True),
    ("Jasmine Rice", "grains", 8.49, "Fragrant Thai jasmine white rice, 2 lb bag", False),
    ("Organic Buckwheat Groats", "grains", 9.29, "Toasted organic kasha buckwheat groats, gluten-free", True),
    # --- Tea & Coffee (10) ---
    ("Organic Green Tea", "tea", 12.99, "Japanese organic sencha green tea, 50 bags", True),
    ("Chamomile Tea", "tea", 8.99, "Dried chamomile flowers, caffeine-free, soothing", False),
    ("Organic Ethiopian Coffee", "coffee", 16.99, "Single-origin organic Arabica, medium roast whole bean", True),
    ("Dark Roast Espresso Blend", "coffee", 14.49, "Bold dark roast espresso blend, ground", False),
    ("Organic Matcha Powder", "tea", 21.99, "Ceremonial grade organic Japanese matcha green tea", True),
    ("Peppermint Herbal Tea", "tea", 7.49, "Refreshing caffeine-free peppermint leaf tea bags", False),
    ("Organic Earl Grey Tea", "tea", 10.99, "Organic black tea infused with Italian bergamot oil", True),
    ("Colombian Supremo Coffee", "coffee", 13.99, "Smooth medium-roast Colombian whole bean coffee", False),
    ("Organic Decaf Coffee", "coffee", 15.49, "Swiss water process organic decaf medium roast", True),
    ("Chai Spice Black Tea", "tea", 9.49, "Aromatic black tea with cardamom, cinnamon, and ginger", False),
    # --- Snacks (12) ---
    ("Organic Granola", "snacks", 9.99, "Organic oat granola with honey, almonds and dried cranberries", True),
    ("Rice Cakes", "snacks", 4.49, "Lightly salted brown rice cakes, low calorie", False),
    ("Organic Dried Mango", "snacks", 7.99, "Unsweetened organic dried mango slices, no preservatives", True),
    ("Trail Mix", "snacks", 8.49, "Classic trail mix with raisins, peanuts and sunflower seeds", False),
    ("Organic Dark Chocolate Almonds", "snacks", 11.49, "70% organic dark chocolate coated roasted almonds", True),
    ("Sea Salt Popcorn", "snacks", 4.99, "Air-popped whole grain popcorn with flaky sea salt", False),
    ("Organic Kale Chips", "snacks", 6.49, "Crispy dehydrated organic kale chips with nutritional yeast", True),
    ("Organic Medjool Dates", "snacks", 10.99, "Soft caramel-like organic Medjool dates, pitted", True),
    ("Baked Plantain Chips", "snacks", 5.29, "Crisp lightly salted green plantain chips", False),
    ("Organic Protein Energy Bites", "snacks", 8.99, "Oat, peanut butter, and chia organic snack bites", True),
    ("Roasted Seaweed Snacks", "snacks", 5.49, "Crispy roasted seaweed sheets with sesame oil, 6-pack", False),
    ("Organic Freeze-Dried Strawberries", "snacks", 7.49, "Crunchy 100% organic strawberries, no added sugar", True),
    # --- Dairy Alternatives (6) ---
    ("Organic Almond Milk", "dairy-alt", 4.99, "Unsweetened organic almond milk, fortified with calcium", True),
    ("Oat Milk", "dairy-alt", 4.49, "Barista-style oat milk, great for coffee", False),
    ("Organic Coconut Milk", "dairy-alt", 3.99, "Full-fat organic coconut milk, great for curries", True),
    ("Soy Milk", "dairy-alt", 3.49, "Unsweetened soy milk, high protein", False),
    ("Organic Cashew Milk", "dairy-alt", 5.49, "Creamy unsweetened organic cashew milk", True),
    ("Hemp Milk", "dairy-alt", 4.79, "Original plant-based hemp milk with omega-3 and omega-6", False),
    # --- Spices & Herbs (7) ---
    ("Organic Turmeric Powder", "spices", 8.99, "High-curcumin organic ground turmeric root", True),
    ("Organic Ceylon Cinnamon", "spices", 9.99, "True organic Ceylon cinnamon, sweet and delicate", True),
    ("Smoked Paprika", "spices", 6.49, "Spanish oak-smoked sweet paprika", False),
    ("Organic Ground Ginger", "spices", 7.49, "Warm aromatic organic dried ginger powder", True),
    ("Black Peppercorns", "spices", 8.29, "Whole Tellicherry black peppercorns for grinding", False),
    ("Organic Garlic Powder", "spices", 6.99, "Pure dehydrated organic garlic, no anti-caking agents", True),
    ("Italian Herb Seasoning", "spices", 5.49, "Blend of oregano, basil, thyme, and rosemary", False),
    # --- Condiments & Sweeteners (6) ---
    ("Organic Maple Syrup", "condiments", 16.49, "Grade A dark robust organic Vermont maple syrup", True),
    ("Apple Cider Vinegar", "condiments", 6.99, "Raw unfiltered apple cider vinegar with the mother", True),
    ("Organic Almond Butter", "condiments", 13.99, "Creamy roasted organic almond butter, no palm oil", True),
    ("Tahini Sesame Paste", "condiments", 9.99, "Smooth stone-ground roasted sesame tahini", False),
    ("Organic Tamari Soy Sauce", "condiments", 8.49, "Gluten-free brewed organic tamari sauce", True),
    ("Dijon Mustard", "condiments", 4.99, "Traditional French-style tangy Dijon mustard", False),
    # --- Baking (6) ---
    ("Organic Almond Flour", "baking", 12.99, "Super-fine blanched organic almond flour, keto-friendly", True),
    ("Organic Cacao Powder", "baking", 11.49, "Raw unsweetened organic Peruvian cacao powder", True),
    ("Coconut Sugar", "baking", 6.99, "Unrefined coconut palm sugar, caramel flavor", False),
    ("Organic Vanilla Extract", "baking", 14.99, "Pure Madagascar Bourbon organic vanilla extract", True),
    ("Whole Wheat Pastry Flour", "baking", 5.99, "Stone-ground whole wheat flour for tender baked goods", False),
    ("Organic Baking Chocolate Chips", "baking", 7.99, "70% dark organic chocolate chips, dairy-free", True),
    # --- Superfoods & Beverages (6) ---
    ("Organic Spirulina Powder", "superfoods", 17.99, "Nutrient-dense organic blue-green spirulina algae", True),
    ("Organic Maca Root Powder", "superfoods", 13.49, "Gelatinized organic Peruvian maca root powder", True),
    ("Collagen Peptides", "superfoods", 24.99, "Unflavored grass-fed hydrolyzed collagen powder", False),
    ("Organic Ginger Kombucha", "beverages", 4.29, "Probiotic fermented organic ginger kombucha, 16 oz", True),
    ("Sparkling Mineral Water", "beverages", 2.99, "Natural spring sparkling mineral water, 750 ml", False),
    ("Organic Tart Cherry Juice", "beverages", 9.99, "100% pure organic Montmorency tart cherry juice", True),
]

REVIEWERS = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack"]


def _build_reviews(product_idx: int, name: str, is_organic: bool) -> list[tuple[float, str, str]]:
    """Generate deterministic, realistic reviews for each product."""
    # Vary ratings between ~3.5 and ~4.9 so rating filters (e.g. 4.5+) are meaningful
    if is_organic and product_idx % 4 != 0:
        ratings = [5.0, 4.5, 5.0, 4.5]
        comments = [
            f"Love this {name}! Super fresh and high quality.",
            "Great organic option, will definitely order again.",
            "Clean ingredients and rich flavor.",
            "Worth the price, arrived quickly and well packaged.",
        ]
    elif product_idx % 3 == 0:
        ratings = [4.5, 4.0, 4.5]
        comments = [
            f"Very solid {name}, meets expectations.",
            "Good everyday staple for the pantry.",
            "Nice flavor and reliable quality.",
        ]
    else:
        ratings = [4.0, 3.5, 4.0]
        comments = [
            f"Decent {name} for the price.",
            "Good overall, though nothing extraordinary.",
            "Works well for daily use.",
        ]

    return [
        (rating, REVIEWERS[(product_idx + i) % len(REVIEWERS)], comment)
        for i, (rating, comment) in enumerate(zip(ratings, comments))
    ]


async def seed_database() -> int:
    """Run migrations and idempotently seed 85 products and their reviews."""
    await run_migrations()
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM products")
        if existing_count and existing_count >= len(PRODUCTS):
            return existing_count

        async with conn.transaction():
            for idx, (name, category, price, description, is_organic) in enumerate(PRODUCTS, start=1):
                primary_img, _fallback = CATEGORY_IMAGES.get(
                    category,
                    CATEGORY_IMAGES["snacks"],
                )
                product_id = await conn.fetchval(
                    """
                    INSERT INTO products (name, category, price, description, is_organic, image_url)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (name) DO UPDATE SET
                        category = EXCLUDED.category,
                        price = EXCLUDED.price,
                        description = EXCLUDED.description,
                        is_organic = EXCLUDED.is_organic,
                        image_url = EXCLUDED.image_url
                    RETURNING id
                    """,
                    name,
                    category,
                    price,
                    description,
                    is_organic,
                    primary_img,
                )

                has_reviews = await conn.fetchval(
                    "SELECT COUNT(*) FROM reviews WHERE product_id = $1",
                    product_id,
                )
                if not has_reviews:
                    for rating, reviewer_name, comment in _build_reviews(idx, name, is_organic):
                        await conn.execute(
                            """
                            INSERT INTO reviews (product_id, rating, reviewer_name, comment)
                            VALUES ($1, $2, $3, $4)
                            """,
                            product_id,
                            rating,
                            reviewer_name,
                            comment,
                        )

        return await conn.fetchval("SELECT COUNT(*) FROM products")


async def _main() -> None:
    count = await seed_database()
    print(f"Database seeded successfully with {count} products.")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
