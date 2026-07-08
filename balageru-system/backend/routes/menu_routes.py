from flask import Blueprint, request, jsonify

import storage
from middleware.auth_middleware import roles_required

menu_bp = Blueprint("menu", __name__, url_prefix="/api/menu")


def _ensure_category(name):
    """Adds the category to the ordered category list if it's new."""
    cats = storage.get_all("categories")
    if not any(c["name"] == name for c in cats):
        storage.insert("categories", {
            "id": storage.next_id("categories"),
            "name": name,
            "sort_order": len(cats),
        })


# ---------- Public: browse menu ----------

@menu_bp.get("")
def get_menu():
    category = request.args.get("category")
    items = storage.get_all("menu_items")
    if category:
        items = [i for i in items if i.get("category") == category]
    items.sort(key=lambda i: i.get("item_code", ""))
    return jsonify(items)


@menu_bp.get("/categories")
def get_categories():
    cats = sorted(storage.get_all("categories"), key=lambda c: c.get("sort_order", 0))
    return jsonify(cats)


# ---------- Staff: manage menu ----------

@menu_bp.post("/items")
@roles_required("owner", "manager")
def create_item():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    price = data.get("price")

    if not name or not category or price is None:
        return jsonify({"error": "name, category and price are required"}), 400

    _ensure_category(category)
    next_code = str(len(storage.get_all("menu_items")) + 1).zfill(2)

    item = {
        "id": storage.next_id("menu_items"),
        "item_code": data.get("item_code") or next_code,
        "name": name,
        "category": category,
        "description": data.get("description", ""),
        "price": float(price),
        "emoji": data.get("emoji", "🍽️"),
        "is_available": bool(data.get("is_available", True)),
        "is_popular": bool(data.get("is_popular", False)),
        "spice_level": int(data.get("spice_level", 0)),
    }
    storage.insert("menu_items", item)
    return jsonify(item), 201


@menu_bp.put("/items/<int:item_id>")
@roles_required("owner", "manager")
def update_item(item_id):
    item = storage.get_by_id("menu_items", item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(silent=True) or {}
    fields = {}
    if "category" in data and data["category"]:
        _ensure_category(data["category"])
        fields["category"] = data["category"]
    for f in ("name", "description", "emoji", "item_code"):
        if f in data:
            fields[f] = data[f]
    if "price" in data:
        fields["price"] = float(data["price"])
    if "is_available" in data:
        fields["is_available"] = bool(data["is_available"])
    if "is_popular" in data:
        fields["is_popular"] = bool(data["is_popular"])
    if "spice_level" in data:
        fields["spice_level"] = int(data["spice_level"])

    updated = storage.update("menu_items", item_id, fields)
    return jsonify(updated)


@menu_bp.patch("/items/<int:item_id>/availability")
@roles_required("owner", "manager", "chef")
def toggle_availability(item_id):
    item = storage.get_by_id("menu_items", item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    updated = storage.update("menu_items", item_id, {"is_available": not item.get("is_available", True)})
    return jsonify(updated)


@menu_bp.delete("/items/<int:item_id>")
@roles_required("owner", "manager")
def delete_item(item_id):
    if not storage.delete("menu_items", item_id):
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"message": "Item deleted"})
