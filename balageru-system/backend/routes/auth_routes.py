from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, get_jwt, jwt_required, verify_jwt_in_request

import storage
from utils.security import hash_password, verify_password
from middleware.auth_middleware import roles_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALLOWED_ROLES = {"owner", "manager", "cashier", "chef", "waiter", "driver", "accountant"}


def public_user(u):
    return {
        "id": u["id"],
        "full_name": u["full_name"],
        "username": u["username"],
        "email": u.get("email"),
        "phone": u.get("phone"),
        "role": u["role"],
        "is_active": u.get("is_active", True),
    }


@auth_bp.post("/register")
def register():
    """
    Create a staff account.
    - If no users exist yet, the first account is auto-promoted to 'owner'
      (bootstrap case — setting up the restaurant for the first time).
    - Otherwise, only an existing owner/manager can create new staff accounts.
    """
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    requested_role = data.get("role", "waiter")

    if not full_name or not username or not password:
        return jsonify({"error": "full_name, username and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if storage.find_one("users", username=username):
        return jsonify({"error": "That username is already taken"}), 409

    is_bootstrap = len(storage.get_all("users")) == 0

    if is_bootstrap:
        role = "owner"
    else:
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"error": "Authentication required to create staff accounts"}), 401
        claims = get_jwt()
        if claims.get("role") not in ("owner", "manager"):
            return jsonify({"error": "Only an owner or manager can create staff accounts"}), 403
        role = requested_role if requested_role in ALLOWED_ROLES else "waiter"

    user = {
        "id": storage.next_id("users"),
        "full_name": full_name,
        "username": username,
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
        "role": role,
        "is_active": True,
    }
    storage.insert("users", user)

    return jsonify({"message": "Account created", "user": public_user(user)}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    user = storage.find_one("users", username=username)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid username or password"}), 401
    if not user.get("is_active", True):
        return jsonify({"error": "This account has been deactivated"}), 403

    token = create_access_token(
        identity=str(user["id"]),
        additional_claims={"role": user["role"], "username": user["username"]},
    )
    return jsonify({"access_token": token, "user": public_user(user)})


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = storage.get_by_id("users", user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(public_user(user))


@auth_bp.get("/staff")
@roles_required("owner", "manager")
def list_staff():
    users = sorted(storage.get_all("users"), key=lambda u: u.get("created_at", ""), reverse=True)
    return jsonify([public_user(u) for u in users])
