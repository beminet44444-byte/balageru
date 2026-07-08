from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def roles_required(*allowed_roles):
    """
    Decorator for staff-only routes.
    Usage: @roles_required("owner", "manager")
    With no arguments, just requires a valid JWT (any staff role).
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if allowed_roles and role not in allowed_roles:
                return jsonify({"error": "Forbidden — insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
