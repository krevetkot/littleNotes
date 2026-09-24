from flask import Blueprint, jsonify, request

from extensions import db
from models import Note

notes_bp = Blueprint("notes", __name__, url_prefix="/api")


@notes_bp.get("/data")
def list_notes():
    notes = db.session.execute(
        db.select(Note).order_by(Note.created_at.desc())
    ).scalars().all()
    return jsonify([note.to_dict() for note in notes])


@notes_bp.post("/notes")
def create_note():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    title = (data.get("title") or "").strip()
    text = data.get("text") or ""
    if not title or not text:
        return jsonify({"error": "Title and text required"}), 400

    note = Note(title=title, text=text)
    db.session.add(note)
    db.session.commit()

    return jsonify(note.to_dict()), 201
