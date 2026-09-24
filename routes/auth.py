from flask import Blueprint, jsonify, request

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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

    existing = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": "Username already exists"}), 409

    user = User(username=username, password_hash=password)
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

    if user is None or user.password_hash != password:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"token": "not-a-real-token"})
