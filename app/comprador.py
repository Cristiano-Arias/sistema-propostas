from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .roles import require_roles
from .models import TR, Process, SupplierInvite, AuditLog
from .utils import token_hex, sha256, in_minutes
from . import db

bp = Blueprint("comprador", __name__)

@bp.post("/tr/<int:tr_id>/approve")
@jwt_required()
@require_roles("COMPRADOR", "ADMIN")
def approve_tr(tr_id):
    tr = TR.query.get_or_404(tr_id)
    tr.status = "APPROVED"
    tr.approved_by = get_jwt_identity()
    db.session.add(AuditLog(user_id=get_jwt_identity(), action="tr_approve", entity="TR", entity_id=tr_id))
    db.session.commit()
    return {"ok": True}

@bp.post("/process")
@jwt_required()
@require_roles("COMPRADOR", "ADMIN")
def create_process():
    data = request.get_json(force=True)
    tr_id = data.get("tr_id")
    p = Process(tr_id=tr_id, buyer_id=get_jwt_identity(), status="INVITING")
    db.session.add(p); db.session.add(AuditLog(user_id=get_jwt_identity(), action="process_create", entity="Process", entity_id=None))
    db.session.commit()
    return {"ok": True, "process_id": p.id}, 201

@bp.post("/process/<int:pid>/invite-supplier")
@jwt_required()
@require_roles("COMPRADOR", "ADMIN")
def invite_supplier(pid):
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    token = token_hex(24)
    inv = SupplierInvite(process_id=pid, email=email, token_hash=sha256(token), expires_at=in_minutes(120))
    db.session.add(inv); db.session.add(AuditLog(user_id=get_jwt_identity(), action="supplier_invite", entity="Process", entity_id=pid))
    db.session.commit()
    return {"ok": True, "supplier_token": token, "email": email}, 201
