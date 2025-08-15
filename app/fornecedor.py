from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import SupplierInvite, Proposal, Process, AuditLog, User
from .utils import sha256, now
from . import db

bp = Blueprint("fornecedor", __name__)

@bp.post("/accept-process")
def accept_process():
    data = request.get_json(force=True)
    token = data.get("token") or ""
    inv = SupplierInvite.query.filter_by(token_hash=sha256(token)).first()
    if not inv or (inv.expires_at < now()) or inv.used_at:
        return {"error": "invalid_or_expired"}, 400
    inv.used_at = now()
    db.session.commit()
    return {"ok": True, "process_id": inv.process_id, "email": inv.email}

@bp.post("/proposal")
@jwt_required()
def submit_proposal():
    data = request.get_json(force=True)
    p = Proposal(process_id=data["process_id"], supplier_id=get_jwt_identity(),
                 tech=data.get("tech") or {}, commercial=data.get("commercial") or {},
                 total_price=data.get("total_price") or 0, currency=data.get("currency") or "BRL")
    db.session.add(p); db.session.add(AuditLog(user_id=get_jwt_identity(), action="proposal_submit", entity="Proposal", entity_id=None))
    db.session.commit()
    return {"ok": True, "proposal_id": p.id}, 201
