# -*- coding: utf-8 -*-
import secrets
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db, socketio
from ..models import Procurement, Invite, User, Role

bp = Blueprint("procurements", __name__)


def require_role(roles):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            ident = get_jwt_identity()
            if ident is None or ident.get("role") not in roles:
                return {"error": "forbidden"}, 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return jwt_required()(wrapper)
    return decorator


@bp.post("/procurements")
@require_role(["COMPRADOR"])
def create_procurement():
    data = request.get_json() or {}
    title = data.get("title") or "Processo"
    ident = get_jwt_identity()
    p = Procurement(title=title, status="RASCUNHO", created_by=ident["user_id"])
    db.session.add(p)
    db.session.commit()
    socketio.emit("procurement.created", {"procurement_id": p.id, "title": p.title}, to=f"org:default")
    return {"id": p.id, "title": p.title, "status": p.status}


@bp.post("/procurements/<int:proc_id>/invites")
@require_role(["COMPRADOR"])
def invite_supplier(proc_id: int):
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return {"error": "email obrigatorio"}, 400
    ident = get_jwt_identity()
    token = secrets.token_urlsafe(32)
    inv = Invite(procurement_id=proc_id, email=email, token=token, created_by=ident["user_id"])
    db.session.add(inv)
    db.session.commit()
    socketio.emit("invite.sent", {"procurement_id": proc_id, "email": email}, to=f"proc:{proc_id}")
    return {"message": "convite criado", "token": token}


@bp.get("/procurements/<int:proc_id>/invites")
@require_role(["COMPRADOR"])
def list_invites(proc_id: int):
    invs = Invite.query.filter_by(procurement_id=proc_id).all()
    return {"invites": [{"id": i.id, "email": i.email, "token": i.token, "created_at": i.created_at.isoformat()} for i in invs]}
