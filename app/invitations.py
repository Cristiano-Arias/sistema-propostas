from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from .roles import require_roles
from .models import Invitation, User, AuditLog
from .utils import token_hex, sha256, in_minutes, now
from . import db, limiter

bp = Blueprint("invitations", __name__)

@bp.post("")
@jwt_required()
@require_roles("ADMIN", "COMPRADOR")
@limiter.limit("20/hour")
def create_invite():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "FORNECEDOR").upper()
    t = token_hex(24)
    inv = Invitation(email=email, role=role, token_hash=sha256(t), expires_at=in_minutes(120))
    inv.created_by = get_jwt().get("sub")
    db.session.add(inv); db.session.commit()
    return jsonify({"ok": True, "token": t, "expires_at": inv.expires_at.isoformat(), "email": email, "role": role}), 201

@bp.post("/accept")
@limiter.limit("30/hour")
def accept_invite():
    data = request.get_json(force=True)
    token = data.get("token") or ""
    name = data.get("name") or ""
    password = data.get("password") or ""
    inv = Invitation.query.filter_by(token_hash=sha256(token)).first()
    if not inv or inv.used():
        return jsonify({"error": "invalid_or_used"}), 400
    if inv.expires_at < now():
        return jsonify({"error": "expired"}), 400
    if User.query.filter_by(email=inv.email).first():
        return jsonify({"error": "email_exists"}), 409
    u = User(email=inv.email, name=name, role=inv.role, active=True)
    u.set_password(password)
    db.session.add(u)
    inv.used_at = now()
    db.session.add(AuditLog(user_id=u.id, action="invite_accept"))
    db.session.commit()
    return jsonify({"ok": True, "user": u.to_safe()}), 201
