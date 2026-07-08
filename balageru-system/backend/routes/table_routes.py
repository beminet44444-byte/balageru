import secrets
from flask import Blueprint, request, jsonify

import storage
from middleware.auth_middleware import roles_required

table_bp = Blueprint("tables", __name__, url_prefix="/api/tables")


@table_bp.get("")
@roles_required()
def list_tables():
    tables = sorted(storage.get_all("tables"), key=lambda t: t["table_number"])
    return jsonify(tables)


@table_bp.post("")
@roles_required("owner", "manager")
def add_table():
    data = request.get_json(silent=True) or {}
    number = data.get("table_number")
    if not number:
        return jsonify({"error": "table_number is required"}), 400
    if storage.find_one("tables", table_number=number):
        return jsonify({"error": "That table number already exists"}), 409

    table = {
        "id": storage.next_id("tables"),
        "table_number": number,
        "seats": data.get("seats", 4),
        "status": "available",
        "qr_token": secrets.token_urlsafe(12),
    }
    storage.insert("tables", table)
    return jsonify(table), 201


@table_bp.delete("/<int:table_id>")
@roles_required("owner", "manager")
def remove_table(table_id):
    if not storage.delete("tables", table_id):
        return jsonify({"error": "Table not found"}), 404
    return jsonify({"message": "Table removed"})


@table_bp.patch("/<int:table_id>/status")
@roles_required("owner", "manager", "waiter")
def set_table_status(table_id):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("available", "occupied", "reserved", "cleaning"):
        return jsonify({"error": "Invalid status"}), 400
    updated = storage.update("tables", table_id, {"status": status})
    if not updated:
        return jsonify({"error": "Table not found"}), 404
    return jsonify(updated)


# ---------- Public: resolve a scanned QR token to a table number ----------
@table_bp.get("/resolve/<qr_token>")
def resolve_qr(qr_token):
    table = storage.find_one("tables", qr_token=qr_token)
    if not table:
        return jsonify({"error": "Unknown or expired table code"}), 404
    return jsonify({"table_number": table["table_number"]})
