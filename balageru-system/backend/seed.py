"""
Seeds the JSON data files with the existing Balageru menu (27 items across
7 categories) and 8 default tables with QR tokens.

Run once before starting the app for the first time:
    python seed.py
"""
import secrets
import storage

MENU = [
    # (category, code, name, description, price, emoji, popular, spice)
    ("Starters", "01", "Sambusa (Meat)", "Crisp pastry filled with spiced minced beef and onion.", 4.5, "🥟", True, 1),
    ("Starters", "02", "Sambusa (Lentil)", "Crisp pastry filled with spiced lentils, fasting-friendly.", 4.0, "🥟", False, 1),
    ("Starters", "03", "Dabo Kolo", "Roasted barley bites tossed in berbere spice.", 3.5, "🌰", False, 1),

    ("Wats & Stews", "04", "Doro Wat", "Slow-simmered chicken in berbere sauce with a hard-boiled egg.", 14.5, "🍗", True, 2),
    ("Wats & Stews", "05", "Key Wat", "Beef simmered in a rich, spicy berbere sauce.", 13.5, "🍲", False, 3),
    ("Wats & Stews", "06", "Yebeg Wat", "Tender lamb stewed in berbere and niter kibbeh.", 15.0, "🍲", False, 2),
    ("Wats & Stews", "07", "Alicha Wat", "Mild chicken stew with turmeric, ginger and garlic.", 13.5, "🍛", False, 0),
    ("Wats & Stews", "08", "Shiro Wat", "Spiced chickpea-flour stew, slow-cooked and smooth.", 10.5, "🍲", True, 1),
    ("Wats & Stews", "09", "Misir Wat", "Split red lentils simmered in berbere sauce.", 10.0, "🍲", True, 2),
    ("Wats & Stews", "10", "Kik Alicha", "Mild yellow split peas with turmeric and garlic.", 10.0, "🍛", False, 0),

    ("Tibs & Grills", "11", "Beef Tibs", "Sautéed beef cubes with onion, jalapeño and rosemary.", 15.0, "🥘", True, 2),
    ("Tibs & Grills", "12", "Zilzil Tibs", "Thin-sliced beef strips, pan-seared and lightly spiced.", 15.5, "🥘", False, 2),
    ("Tibs & Grills", "13", "Yebeg Tibs", "Sautéed lamb with garlic, rosemary and green chili.", 16.0, "🥘", False, 2),
    ("Tibs & Grills", "14", "Kitfo", "Minced beef warmed in mitmita and niter kibbeh, served leb-leb.", 16.5, "🍽️", True, 3),
    ("Tibs & Grills", "15", "Gored Gored", "Cubed beef tossed in spiced butter and mitmita.", 16.0, "🍽️", False, 2),

    ("Vegetarian & Fasting", "16", "Gomen", "Collard greens sautéed with garlic and ginger.", 9.5, "🥬", False, 0),
    ("Vegetarian & Fasting", "17", "Atkilt Wat", "Cabbage, carrot and potato in a mild turmeric sauce.", 9.5, "🥕", False, 0),
    ("Vegetarian & Fasting", "18", "Fasolia", "Green beans and carrots sautéed with garlic.", 9.0, "🫛", False, 0),
    ("Vegetarian & Fasting", "19", "Beyainatu", "Fasting combo platter — shiro, misir, gomen, atkilt and kik on injera.", 14.0, "🍱", True, 1),
    ("Vegetarian & Fasting", "20", "Ful Medames", "Warm mashed fava beans with onion, tomato and chili.", 9.0, "🫘", False, 1),

    ("Breads & Sides", "21", "Injera (extra)", "Traditional sourdough flatbread, made from teff.", 2.5, "🫓", False, 0),
    ("Breads & Sides", "22", "Chechebsa", "Torn flatbread warmed in spiced butter and berbere.", 6.5, "🫓", False, 1),
    ("Breads & Sides", "23", "Himbasha", "Slightly sweet, cardamom-spiced Ethiopian bread.", 4.5, "🍞", False, 0),

    ("Drinks", "24", "Buna (Ethiopian Coffee)", "Traditionally brewed, served strong and aromatic.", 3.0, "☕", True, 0),
    ("Drinks", "25", "Tej", "Ethiopian honey wine, lightly fermented.", 6.0, "🍯", False, 0),
    ("Drinks", "26", "Shai", "Spiced black tea with cinnamon and clove.", 2.5, "🍵", False, 0),

    ("Desserts", "27", "Fresh Fruit Plate", "Seasonal fruit, a traditional way to close the meal.", 5.0, "🍉", False, 0),
]

CATEGORY_ORDER = [
    "Starters", "Wats & Stews", "Tibs & Grills", "Vegetarian & Fasting",
    "Breads & Sides", "Drinks", "Desserts"
]


def run():
    storage.init_storage()

    if storage.get_all("menu_items"):
        print("Menu already seeded — skipping. Delete backend/data/*.json first to reseed.")
    else:
        for i, name in enumerate(CATEGORY_ORDER):
            storage.insert("categories", {"id": storage.next_id("categories"), "name": name, "sort_order": i})

        for cat_name, code, name, desc, price, emoji, popular, spice in MENU:
            storage.insert("menu_items", {
                "id": storage.next_id("menu_items"),
                "item_code": code,
                "name": name,
                "category": cat_name,
                "description": desc,
                "price": price,
                "emoji": emoji,
                "is_available": True,
                "is_popular": popular,
                "spice_level": spice,
            })
        print(f"Seeded {len(MENU)} menu items across {len(CATEGORY_ORDER)} categories.")

    if storage.get_all("tables"):
        print("Tables already seeded — skipping.")
    else:
        for n in range(1, 9):
            storage.insert("tables", {
                "id": storage.next_id("tables"),
                "table_number": n,
                "seats": 4,
                "status": "available",
                "qr_token": secrets.token_urlsafe(12),
            })
        print("Seeded 8 tables with QR tokens.")


if __name__ == "__main__":
    run()
