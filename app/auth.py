from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from .models import User, AuditLog
from . import db, limiter
from datetime import timedelta

bp = Blueprint("auth", __name__)

@bp.post("/login")
@limiter.limit("10/minute")
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    u = User.query.filter_by(email=email, active=True).first()
    if not u or not u.verify_password(password):
        return jsonify({"error": "invalid_credentials"}), 401
    claims = {"role": u.role}
    access = create_access_token(identity=u.id, additional_claims=claims, expires_delta=timedelta(minutes=30))
    refresh = create_refresh_token(identity=u.id, additional_claims=claims)
    resp = jsonify({"ok": True, "user": u.to_safe()})
    set_access_cookies(resp, access)
    set_refresh_cookies(resp, refresh)
    db.session.add(AuditLog(user_id=u.id, action="login"))
    db.session.commit()
    return resp, 200

@bp.post("/logout")
def logout():
    resp = jsonify({"ok": True})
    unset_jwt_cookies(resp)
    return resp, 200

@bp.get("/session")
@jwt_required(optional=True)
def session():
    uid = get_jwt_identity()
    if not uid:
        return jsonify({"authenticated": False}), 200
    u = User.query.get(uid)
    return jsonify({"authenticated": True, "user": u.to_safe()}), 200
