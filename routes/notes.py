from flask import Blueprint, jsonify, request, g

from extensions import db
from models import Note
from security import token_required

notes_bp = Blueprint("notes", __name__, url_prefix="/api")


@notes_bp.get("/data")
@token_required
def list_notes():
    notes = db.session.execute(
        db.select(Note).order_by(Note.created_at.desc()).filter_by(user_id=g.user_id)
    ).scalars().all()
    return jsonify([note.to_dict() for note in notes])


@notes_bp.post("/notes")
@token_required
def create_note():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    title = (data.get("title") or "").strip()
    text = data.get("text") or ""
    if not title or not text:
        return jsonify({"error": "Title and text required"}), 400

    note = Note(title=title, text=text, user_id=g.user_id)
    db.session.add(note)
    db.session.commit()

    return jsonify(note.to_dict()), 201
