import re

from flask import Blueprint, jsonify, request, current_app

from extensions import db
from models import User
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
PASSWORD_RULES = (
    "Password must be at least 8 characters long and contain a lowercase letter, "
    "an uppercase letter, a digit and a special character"
)


def read_credentials():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return "", ""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    return username, password


@auth_bp.post("/register")
def register():
    username, password = read_credentials()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if not PASSWORD_RE.fullmatch(password):
        return jsonify({"error": PASSWORD_RULES}), 400

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    existing = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": "Username already exists"}), 409

    user = User(username=username, password_hash=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"id": user.id, "username": user.username}), 201


@auth_bp.post("/login")
def login():
    username, password = read_credentials()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()

    if user is None or not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"error": "Invalid credentials"}), 401

    key = current_app.config["SECRET_KEY"]
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(hours=12),
    }
    token = jwt.encode(payload, key, algorithm="HS256")

    return jsonify({"token": token})
