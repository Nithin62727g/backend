import functools
from flask import request, jsonify, g
from core.security import verify_token
from core.database import get_db


def require_auth(f):
    """
    Decorator to protect Flask routes with JWT Bearer token auth.
    On success, sets g.current_user to the full user row from the DB.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        payload = verify_token(token)
        if payload is None:
            return jsonify({"error": "Could not validate credentials"}), 401

        email = payload.get("sub")
        if not email:
            return jsonify({"error": "Could not validate credentials"}), 401

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "User not found"}), 401

        g.current_user = user
        return f(*args, **kwargs)
    return decorated
