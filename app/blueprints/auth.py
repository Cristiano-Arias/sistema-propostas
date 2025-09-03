# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from .. import db
from ..models import User, Organization, Role
from ..utils.passwords import hash_password, verify_password

bp = Blueprint("auth", __name__)

@bp.post("/register")
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    full_name = data.get("full_name") or ""
    password = data.get("password") or ""
    role = data.get("role") or "FORNECEDOR"
    org_name = data.get("organization")  # opcional
    
    if not email or not password or not full_name:
        return {"error": "email, full_name e password sao obrigatorios"}, 400
    
    if role not in [r.value for r in Role]:
        return {"error": "role invalido"}, 400
    
    if User.query.filter_by(email=email).first():
        return {"error": "email ja cadastrado"}, 409
    
    org = None
    if org_name:
        org = Organization.query.filter_by(name=org_name).first()
        if not org:
            org = Organization(name=org_name)
            db.session.add(org)
    
    user = User(
        email=email, 
        full_name=full_name, 
        password_hash=hash_password(password), 
        role=Role(role), 
        organization=org
    )
    db.session.add(user)
    db.session.commit()
    
    return {"message": "usuario registrado", "user_id": user.id}

@bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        return {"error": "credenciais invalidas"}, 401
    
    # IMPORTANTE: Use apenas o ID como string
    token = create_access_token(
        identity=str(user.id),  # Converter para string
        expires_delta=timedelta(days=7)
    )
    
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "full_name": user.full_name
        }
    }

@bp.get("/me")
@jwt_required()
def me():
    from ..utils.auth import get_current_user
    u = get_current_user()
    
    if not u:
        return {"error": "Usuario nao encontrado"}, 404
    
    return {
        "id": u.id, 
        "email": u.email, 
        "role": u.role.value, 
        "full_name": u.full_name,
        "organization": u.organization.name if u.organization else None
    }
