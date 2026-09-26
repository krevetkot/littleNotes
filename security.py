from functools import wraps

import jwt
from flask import request, jsonify, g, current_app


def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = header.split(" ", 1)[1]
        key = current_app.config["SECRET_KEY"]
        try:
            payload = jwt.decode(token, key, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        g.user_id = int(payload["sub"])
        return func(*args, **kwargs)

    return wrapper
