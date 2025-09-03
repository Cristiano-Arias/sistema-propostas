# -*- coding: utf-8 -*-
"""
Helper functions para autenticação JWT
Resolve o problema de compatibilidade entre diferentes formatos de JWT
"""

from flask_jwt_extended import get_jwt_identity
from ..models import User

def get_current_user():
    identity = get_jwt_identity()
    
    # Converter para int se for string
    if isinstance(identity, str):
        try:
            user_id = int(identity)
        except:
            return None
    elif isinstance(identity, int):
        user_id = identity
    elif isinstance(identity, dict):
        user_id = identity.get("user_id")
    else:
        return None
    
    return User.query.get(user_id) if user_id else None


def require_roles(*allowed_roles):
    """
    Decorator para verificar roles do usuário
    Uso: @require_roles('COMPRADOR', 'REQUISITANTE')
    """
    def decorator(f):
        from functools import wraps
        from flask_jwt_extended import jwt_required
        
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return {"error": "Usuário não encontrado"}, 404
            
            if user.role.value not in allowed_roles:
                return {"error": f"Acesso negado. Requer um dos papéis: {', '.join(allowed_roles)}"}, 403
            
            # Injeta o usuário como primeiro argumento da função
            return f(user, *args, **kwargs)
        
        return decorated_function
    return decorator
