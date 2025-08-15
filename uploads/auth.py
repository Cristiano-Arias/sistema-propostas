#!/usr/bin/env python3
"""
Sistema de Autenticação JWT - Sistema de Propostas
Substitui o sistema de autenticação baseado apenas em frontend
"""

from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from datetime import datetime, timedelta
from models import Usuario, LogAuditoria, db
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Lista de tokens revogados (em produção, usar Redis ou banco)
revoked_tokens = set()

def init_jwt(app):
    """Inicializa o sistema JWT"""
    jwt = JWTManager(app)
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Verifica se o token foi revogado"""
        return jwt_payload['jti'] in revoked_tokens
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Callback para token expirado"""
        return jsonify({
            'success': False,
            'error': 'Token expirado',
            'message': 'Faça login novamente'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Callback para token inválido"""
        return jsonify({
            'success': False,
            'error': 'Token inválido',
            'message': 'Token de acesso inválido'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Callback para token ausente"""
        return jsonify({
            'success': False,
            'error': 'Token ausente',
            'message': 'Token de acesso necessário'
        }), 401
    
    return jwt

class AuthService:
    """Serviço de autenticação"""
    
    @staticmethod
    def login(email, senha, ip_origem=None):
        """
        Realiza login do usuário
        
        Args:
            email (str): Email do usuário
            senha (str): Senha do usuário
            ip_origem (str): IP de origem da requisição
            
        Returns:
            dict: Resultado do login com tokens ou erro
        """
        try:
            # Buscar usuário no banco
            usuario = Usuario.query.filter_by(email=email).first()
            
            if not usuario:
                logger.warning(f"Tentativa de login com email inexistente: {email}")
                return {
                    'success': False,
                    'error': 'Credenciais inválidas',
                    'message': 'Email ou senha incorretos'
                }
            
            if not usuario.ativo:
                logger.warning(f"Tentativa de login com usuário inativo: {email}")
                return {
                    'success': False,
                    'error': 'Usuário inativo',
                    'message': 'Conta desativada. Entre em contato com o administrador.'
                }
            
            # Verificar senha
            if not usuario.verificar_senha(senha):
                logger.warning(f"Tentativa de login com senha incorreta: {email}")
                
                # Log de auditoria para tentativa de login falhada
                log = LogAuditoria(
                    usuario_id=usuario.id,
                    acao='LOGIN_FAILED',
                    recurso='usuario',
                    recurso_id=usuario.id,
                    ip_origem=ip_origem
                )
                log.set_detalhes({'motivo': 'senha_incorreta', 'email': email})
                db.session.add(log)
                db.session.commit()
                
                return {
                    'success': False,
                    'error': 'Credenciais inválidas',
                    'message': 'Email ou senha incorretos'
                }
            
            # Atualizar último login
            usuario.ultimo_login = datetime.utcnow()
            
            # Criar tokens JWT
            access_token = create_access_token(
                identity=usuario.id,
                additional_claims={
                    'tipo': usuario.tipo,
                    'nivel_acesso': usuario.nivel_acesso,
                    'nome': usuario.nome,
                    'email': usuario.email
                }
            )
            
            refresh_token = create_refresh_token(identity=usuario.id)
            
            # Log de auditoria para login bem-sucedido
            log = LogAuditoria(
                usuario_id=usuario.id,
                acao='LOGIN_SUCCESS',
                recurso='usuario',
                recurso_id=usuario.id,
                ip_origem=ip_origem
            )
            log.set_detalhes({'email': email, 'tipo': usuario.tipo})
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Login bem-sucedido: {email} ({usuario.tipo})")
            
            return {
                'success': True,
                'message': 'Login realizado com sucesso',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'usuario': usuario.to_dict(),
                'expires_in': current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': 'Erro interno',
                'message': 'Erro interno do servidor'
            }
    
    @staticmethod
    def logout(jti):
        """
        Realiza logout revogando o token
        
        Args:
            jti (str): ID único do token JWT
        """
        try:
            # Adicionar token à lista de revogados
            revoked_tokens.add(jti)
            
            # Log de auditoria
            usuario_id = get_jwt_identity()
            if usuario_id:
                log = LogAuditoria(
                    usuario_id=usuario_id,
                    acao='LOGOUT',
                    recurso='usuario',
                    recurso_id=usuario_id
                )
                log.set_detalhes({'jti': jti})
                db.session.add(log)
                db.session.commit()
            
            logger.info(f"Logout realizado: {usuario_id}")
            
            return {
                'success': True,
                'message': 'Logout realizado com sucesso'
            }
            
        except Exception as e:
            logger.error(f"Erro no logout: {e}")
            return {
                'success': False,
                'error': 'Erro interno',
                'message': 'Erro ao realizar logout'
            }
    
    @staticmethod
    def refresh_token():
        """Renova o token de acesso usando refresh token"""
        try:
            usuario_id = get_jwt_identity()
            usuario = Usuario.query.get(usuario_id)
            
            if not usuario or not usuario.ativo:
                return {
                    'success': False,
                    'error': 'Usuário inválido',
                    'message': 'Usuário não encontrado ou inativo'
                }
            
            # Criar novo access token
            new_access_token = create_access_token(
                identity=usuario.id,
                additional_claims={
                    'tipo': usuario.tipo,
                    'nivel_acesso': usuario.nivel_acesso,
                    'nome': usuario.nome,
                    'email': usuario.email
                }
            )
            
            return {
                'success': True,
                'access_token': new_access_token,
                'expires_in': current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return {
                'success': False,
                'error': 'Erro interno',
                'message': 'Erro ao renovar token'
            }
    
    @staticmethod
    def get_current_user():
        """Retorna o usuário atual baseado no token JWT"""
        try:
            usuario_id = get_jwt_identity()
            if usuario_id:
                usuario = Usuario.query.get(usuario_id)
                if usuario and usuario.ativo:
                    return usuario
            return None
        except Exception as e:
            logger.error(f"Erro ao obter usuário atual: {e}")
            return None

def require_auth(f):
    """Decorator para rotas que requerem autenticação"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """
    Decorator para rotas que requerem roles específicos
    
    Args:
        *roles: Lista de roles permitidos (admin, comprador, etc.)
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                claims = get_jwt()
                user_role = claims.get('tipo')
                
                if user_role not in roles:
                    logger.warning(f"Acesso negado - Role {user_role} não autorizado para {roles}")
                    return jsonify({
                        'success': False,
                        'error': 'Acesso negado',
                        'message': f'Acesso restrito a: {", ".join(roles)}'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Erro na verificação de role: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Erro interno',
                    'message': 'Erro na verificação de permissões'
                }), 500
        
        return decorated_function
    return decorator

def require_permission(permission):
    """
    Decorator para verificar permissões específicas
    
    Args:
        permission (str): Permissão necessária
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                claims = get_jwt()
                user_role = claims.get('tipo')
                nivel_acesso = claims.get('nivel_acesso')
                
                # Lógica de permissões baseada no tipo e nível
                if not _check_permission(user_role, nivel_acesso, permission):
                    logger.warning(f"Permissão negada - {user_role}/{nivel_acesso} para {permission}")
                    return jsonify({
                        'success': False,
                        'error': 'Permissão negada',
                        'message': f'Permissão necessária: {permission}'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Erro na verificação de permissão: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Erro interno',
                    'message': 'Erro na verificação de permissões'
                }), 500
        
        return decorated_function
    return decorator

def _check_permission(user_role, nivel_acesso, permission):
    """
    Verifica se o usuário tem a permissão necessária
    
    Args:
        user_role (str): Role do usuário
        nivel_acesso (str): Nível de acesso
        permission (str): Permissão a verificar
        
    Returns:
        bool: True se tem permissão, False caso contrário
    """
    # Admin tem todas as permissões
    if user_role == 'admin':
        return True
    
    # Mapeamento de permissões por role
    permissions_map = {
        'comprador': [
            'view_processos', 'create_processo', 'edit_processo',
            'view_propostas', 'analyze_propostas', 'generate_reports'
        ],
        'requisitante': [
            'view_processos', 'create_tr', 'view_tr', 'emit_parecer'
        ],
        'fornecedor': [
            'view_processos_publicos', 'create_proposta', 'view_minhas_propostas'
        ],
        'auditor': [
            'view_all', 'view_logs', 'generate_audit_reports'
        ]
    }
    
    user_permissions = permissions_map.get(user_role, [])
    return permission in user_permissions

def log_user_action(acao, recurso, recurso_id=None, detalhes=None):
    """
    Registra ação do usuário nos logs de auditoria
    
    Args:
        acao (str): Ação realizada
        recurso (str): Recurso afetado
        recurso_id (str): ID do recurso
        detalhes (dict): Detalhes adicionais
    """
    try:
        usuario_id = get_jwt_identity()
        if usuario_id:
            log = LogAuditoria(
                usuario_id=usuario_id,
                acao=acao,
                recurso=recurso,
                recurso_id=recurso_id,
                ip_origem=request.remote_addr
            )
            if detalhes:
                log.set_detalhes(detalhes)
            
            db.session.add(log)
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Erro ao registrar log de auditoria: {e}")
        db.session.rollback()

