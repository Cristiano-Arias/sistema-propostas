from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Document, AuditLog
from . import db
from io import BytesIO

bp = Blueprint("files", __name__)

@bp.post("")
@jwt_required()
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no_file"}), 400
    f = request.files["file"]
    data = f.read()
    doc = Document(filename=f.filename, content_type=f.mimetype or "application/octet-stream",
                   size=len(data), data=data, owner_id=get_jwt_identity(),
                   linked_type=request.form.get("linked_type"), linked_id=request.form.get("linked_id"))
    db.session.add(doc); db.session.add(AuditLog(user_id=get_jwt_identity(), action="upload", entity="Document", entity_id=None))
    db.session.commit()
    return jsonify({"ok": True, "id": doc.id, "filename": doc.filename}), 201

@bp.get("/<int:doc_id>")
@jwt_required()
def download(doc_id):
    d = Document.query.get_or_404(doc_id)
    return send_file(BytesIO(d.data), mimetype=d.content_type, as_attachment=True, download_name=d.filename)
