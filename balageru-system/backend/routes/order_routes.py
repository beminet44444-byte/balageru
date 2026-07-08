import random
import string
from flask import Blueprint, request, jsonify

import storage
from middleware.auth_middleware import roles_required

order_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

TAX_RATE = 0.15  # 15% VAT — adjust to your local requirement
STATUS_FLOW = ["new", "preparing", "ready", "completed"]


def generate_order_number():
    """Generate a short, human-readable, unique order number."""
    existing = {o["order_number"] for o in storage.get_all("orders")}
    for _ in range(20):
        candidate = "BG-" + "".join(random.choices(string.digits, k=4))
        if candidate not in existing:
            return candidate
    # Extremely unlikely fallback if the 4-digit space is exhausted
    return "BG-" + "".join(random.choices(string.digits, k=6))


# ---------- Public: place an order (self-service, no login required) ----------
@order_bp.post("")
def create_order():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "dine_in")
    table_number = data.get("table_number")
    items_in = data.get("items") or []

    if mode not in ("dine_in", "pickup", "delivery"):
        return jsonify({"error": "Invalid order mode"}), 400
    if not items_in:
        return jsonify({"error": "Order must contain at least one item"}), 400

    table = None
    if mode == "dine_in":
        if not table_number:
            return jsonify({"error": "table_number is required for dine-in orders"}), 400
        table = storage.find_one("tables", table_number=table_number)
        if not table:
            return jsonify({"error": "Unknown table number"}), 404

    order_items = []
    subtotal = 0.0
    for line in items_in:
        menu_item = storage.get_by_id("menu_items", line.get("menu_item_id"))
        if not menu_item or not menu_item.get("is_available", True):
            return jsonify({"error": f"Item unavailable: {line.get('menu_item_id')}"}), 400
        qty = max(1, int(line.get("quantity", 1)))
        unit_price = float(menu_item["price"])
        line_total = round(unit_price * qty, 2)
        subtotal += line_total
        order_items.append({
            "menu_item_id": menu_item["id"],
            "item_name": menu_item["name"],
            "unit_price": unit_price,
            "quantity": qty,
            "line_total": line_total,
        })

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)

    order = {
        "id": storage.next_id("orders"),
        "order_number": generate_order_number(),
        "mode": mode,
        "table_number": table["table_number"] if table else None,
        "customer_name": (data.get("customer_name") or "Guest").strip()[:120],
        "customer_phone": (data.get("customer_phone") or "").strip()[:30],
        "note": (data.get("note") or "").strip(),
        "status": "new",
        "subtotal": subtotal,
        "tax": tax,
        "service_charge": 0.0,
        "total": total,
        "items": order_items,
    }
    storage.insert("orders", order)

    if table:
        storage.update("tables", table["id"], {"status": "occupied"})

    return jsonify(order), 201


# ---------- Staff: order board ----------
@order_bp.get("")
@roles_required()
def list_orders():
    status = request.args.get("status")
    orders = storage.get_all("orders")
    if status:
        orders = [o for o in orders if o["status"] == status]
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return jsonify(orders[:200])


@order_bp.get("/<int:order_id>")
@roles_required()
def get_order(order_id):
    order = storage.get_by_id("orders", order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)


@order_bp.patch("/<int:order_id>/status")
@roles_required("owner", "manager", "chef", "waiter", "cashier")
def update_status(order_id):
    order = storage.get_by_id("orders", order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    new_status = (request.get_json(silent=True) or {}).get("status")
    valid = STATUS_FLOW + ["cancelled"]
    if new_status not in valid:
        return jsonify({"error": f"status must be one of {valid}"}), 400

    updated = storage.update("orders", order_id, {"status": new_status})

    if new_status in ("completed", "cancelled") and order.get("table_number"):
        table = storage.find_one("tables", table_number=order["table_number"])
        if table:
            storage.update("tables", table["id"], {"status": "cleaning"})

    return jsonify(updated)


# ---------- Reports (lightweight — full analytics module comes in a later phase) ----------
@order_bp.get("/reports/summary")
@roles_required("owner", "manager", "accountant")
def summary():
    orders = [o for o in storage.get_all("orders") if o["status"] != "cancelled"]
    total_orders = len(orders)
    total_revenue = round(sum(o["total"] for o in orders), 2)
    avg_order = round(total_revenue / total_orders, 2) if total_orders else 0.0

    best_sellers = {}
    for o in orders:
        for i in o["items"]:
            entry = best_sellers.setdefault(i["item_name"], {"quantity": 0, "revenue": 0.0})
            entry["quantity"] += i["quantity"]
            entry["revenue"] += i["line_total"]

    top = sorted(best_sellers.items(), key=lambda kv: kv[1]["quantity"], reverse=True)[:10]

    return jsonify({
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": avg_order,
        "best_sellers": [
            {"name": name, "quantity": d["quantity"], "revenue": round(d["revenue"], 2)}
            for name, d in top
        ],
    })
