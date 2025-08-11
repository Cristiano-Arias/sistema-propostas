#!/usr/bin/env python3
"""
Sistema de Autenticação Aprimorado - Adaptado para Sistema de Propostas Existente
Mantém compatibilidade total com estrutura atual
"""

from flask import Flask, request, jsonify, session, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import secrets
import re
import json
from typing import Dict, Any, Optional, List

# Importar modelos (assumindo que models.py foi atualizado)
try:
    from models import db, Usuario, Role, Permission, AuditLog, LoginAttempt
except ImportError:
    # Fallback para desenvolvimento
    from models_para_sistema_atual import db, Usuario, Role, Permission, AuditLog, LoginAttempt

class AuthService:
    """
    Serviço de autenticação aprimorado - Compatível com sistema atual
    Mantém métodos existentes e adiciona funcionalidades RBAC
    """
    
    def __init__(self):
        self.max_attempts_per_ip = 5  # Por minuto
        self.max_attempts_per_user = 10  # Por hora
        self.lockout_duration = 15  # Minutos
    
    # ==================== MÉTODOS EXISTENTES (MANTIDOS) ====================
    
    def verificar_usuario(self, email: str, senha: str) -> Dict[str, Any]:
        """
        Método original mantido para compatibilidade
        Agora usa o sistema RBAC internamente
        """
        return self.login(email, senha, request.remote_addr, request.headers.get('User-Agent'))
    
    def criar_sessao(self, usuario: Usuario) -> Dict[str, Any]:
        """
        Método original mantido - agora cria tokens JWT
        """
        try:
            # Gerar tokens JWT
            access_token = create_access_token(
                identity=usuario.id,
                expires_delta=timedelta(minutes=15),
                additional_claims={
                    'roles': [role.name for role in usuario.roles],
                    'permissions': usuario.get_permissions(),
                    'primary_role': usuario.get_primary_role().name if usuario.get_primary_role() else None
                }
            )
            
            refresh_token = create_refresh_token(
                identity=usuario.id,
                expires_delta=timedelta(days=7)
            )
            
            # Manter compatibilidade com sessão Flask se necessário
            session['user_id'] = usuario.id
            session['user_email'] = usuario.email
            session['user_tipo'] = usuario.tipo  # Compatibilidade
            
            return {
                'success': True,
                'user': usuario.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': 900  # 15 minutos
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao criar sessão: {str(e)}'
            }
    
    def validar_sessao(self) -> Optional[Usuario]:
        """
        Método original mantido - agora verifica JWT ou sessão Flask
        """
        # Tentar JWT primeiro
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if user_id:
                return Usuario.query.get(user_id)
        except:
            pass
        
        # Fallback para sessão Flask (compatibilidade)
        user_id = session.get('user_id')
        if user_id:
            return Usuario.query.get(user_id)
        
        return None
    
    def logout(self) -> Dict[str, Any]:
        """
        Método original mantido - agora limpa JWT e sessão
        """
        try:
            # Limpar sessão Flask
            session.clear()
            
            # Log de auditoria
            user_id = session.get('user_id')
            if user_id:
                self._create_audit_log(
                    user_id, 'LOGOUT', 'usuario', user_id,
                    request.remote_addr, True, "Logout realizado"
                )
            
            return {
                'success': True,
                'message': 'Logout realizado com sucesso'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro no logout: {str(e)}'
            }
    
    # ==================== NOVOS MÉTODOS RBAC ====================
    
    def login(self, email: str, senha: str, ip_origem: str = None, user_agent: str = None) -> Dict[str, Any]:
        """
        Método de login aprimorado com segurança RBAC
        """
        try:
            # 1. Validações de rate limiting
            if not self._check_rate_limits(email, ip_origem):
                self._log_login_attempt(email, ip_origem, False, user_agent, "Rate limit exceeded")
                return {
                    'success': False,
                    'error': 'Muitas tentativas de login. Tente novamente mais tarde.',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }
            
            # 2. Buscar usuário
            usuario = Usuario.query.filter_by(email=email).first()
            
            if not usuario:
                self._log_login_attempt(email, ip_origem, False, user_agent, "User not found")
                return {
                    'success': False,
                    'error': 'Credenciais inválidas',
                    'code': 'INVALID_CREDENTIALS'
                }
            
            # 3. Verificar se usuário está ativo
            if not usuario.ativo:
                self._log_login_attempt(email, ip_origem, False, user_agent, "User inactive")
                self._create_audit_log(usuario.id, 'LOGIN_FAILED', 'usuario', usuario.id, 
                                     ip_origem, False, "Usuário inativo")
                return {
                    'success': False,
                    'error': 'Conta desativada. Entre em contato com o administrador.',
                    'code': 'ACCOUNT_INACTIVE'
                }
            
            # 4. Verificar se usuário está bloqueado
            if usuario.esta_bloqueado():
                self._log_login_attempt(email, ip_origem, False, user_agent, "User blocked")
                self._create_audit_log(usuario.id, 'LOGIN_FAILED', 'usuario', usuario.id, 
                                     ip_origem, False, "Usuário bloqueado")
                return {
                    'success': False,
                    'error': f'Conta bloqueada até {usuario.bloqueado_ate.strftime("%d/%m/%Y %H:%M")}',
                    'code': 'ACCOUNT_BLOCKED'
                }
            
            # 5. Verificar senha
            if not usuario.verificar_senha(senha):
                usuario.incrementar_tentativas_login()
                db.session.commit()
                
                self._log_login_attempt(email, ip_origem, False, user_agent, "Invalid password")
                self._create_audit_log(usuario.id, 'LOGIN_FAILED', 'usuario', usuario.id, 
                                     ip_origem, False, "Senha incorreta")
                
                return {
                    'success': False,
                    'error': 'Credenciais inválidas',
                    'code': 'INVALID_CREDENTIALS'
                }
            
            # 6. Verificar se senha está expirada
            if usuario.senha_expirada():
                self._create_audit_log(usuario.id, 'LOGIN_PASSWORD_EXPIRED', 'usuario', usuario.id, 
                                     ip_origem, True, "Senha expirada")
                return {
                    'success': False,
                    'error': 'Senha expirada. É necessário alterar a senha.',
                    'code': 'PASSWORD_EXPIRED',
                    'user_id': usuario.id
                }
            
            # 7. Login bem-sucedido
            usuario.resetar_tentativas_login()
            usuario.ultimo_ip = ip_origem
            db.session.commit()
            
            # 8. Criar sessão (compatibilidade + JWT)
            result = self.criar_sessao(usuario)
            
            if result['success']:
                # 9. Log de sucesso
                self._log_login_attempt(email, ip_origem, True, user_agent, "Login successful")
                self._create_audit_log(usuario.id, 'LOGIN_SUCCESS', 'usuario', usuario.id, 
                                     ip_origem, True, "Login realizado com sucesso")
            
            return result
            
        except Exception as e:
            self._log_login_attempt(email, ip_origem, False, user_agent, f"System error: {str(e)}")
            return {
                'success': False,
                'error': 'Erro interno do sistema. Tente novamente.',
                'code': 'SYSTEM_ERROR'
            }
    
    def refresh_token(self, user_id: int) -> Dict[str, Any]:
        """
        Renova token de acesso usando refresh token
        """
        try:
            usuario = Usuario.query.get(user_id)
            
            if not usuario or not usuario.ativo:
                return {
                    'success': False,
                    'error': 'Usuário inválido ou inativo',
                    'code': 'INVALID_USER'
                }
            
            # Gerar novo access token
            access_token = create_access_token(
                identity=usuario.id,
                expires_delta=timedelta(minutes=15),
                additional_claims={
                    'roles': [role.name for role in usuario.roles],
                    'permissions': usuario.get_permissions(),
                    'primary_role': usuario.get_primary_role().name if usuario.get_primary_role() else None
                }
            )
            
            self._create_audit_log(usuario.id, 'TOKEN_REFRESH', 'token', None, 
                                 request.remote_addr, True, "Token renovado")
            
            return {
                'success': True,
                'access_token': access_token,
                'expires_in': 900
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Erro ao renovar token',
                'code': 'REFRESH_ERROR'
            }
    
    def change_password(self, user_id: int, senha_atual: str, nova_senha: str) -> Dict[str, Any]:
        """
        Altera senha do usuário com validações de segurança
        """
        try:
            usuario = Usuario.query.get(user_id)
            
            if not usuario:
                return {
                    'success': False,
                    'error': 'Usuário não encontrado',
                    'code': 'USER_NOT_FOUND'
                }
            
            # Verificar senha atual
            if not usuario.verificar_senha(senha_atual):
                self._create_audit_log(user_id, 'PASSWORD_CHANGE_FAILED', 'usuario', user_id, 
                                     request.remote_addr, False, "Senha atual incorreta")
                return {
                    'success': False,
                    'error': 'Senha atual incorreta',
                    'code': 'INVALID_CURRENT_PASSWORD'
                }
            
            # Definir nova senha (com validações)
            try:
                usuario.set_senha(nova_senha)
                db.session.commit()
                
                self._create_audit_log(user_id, 'PASSWORD_CHANGED', 'usuario', user_id, 
                                     request.remote_addr, True, "Senha alterada com sucesso")
                
                return {
                    'success': True,
                    'message': 'Senha alterada com sucesso'
                }
                
            except ValueError as e:
                return {
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_PASSWORD'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Erro interno do sistema',
                'code': 'SYSTEM_ERROR'
            }
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    def _check_rate_limits(self, email: str, ip_origem: str) -> bool:
        """Verifica limites de tentativas de login"""
        if ip_origem:
            # Verificar tentativas por IP (5 por minuto)
            attempts_by_ip = LoginAttempt.get_recent_attempts(ip_origem, 1)
            if attempts_by_ip >= self.max_attempts_per_ip:
                return False
        
        if email:
            # Verificar tentativas por email (10 por hora)
            attempts_by_email = LoginAttempt.get_recent_attempts_by_email(email, 60)
            if attempts_by_email >= self.max_attempts_per_user:
                return False
        
        return True
    
    def _log_login_attempt(self, email: str, ip_origem: str, success: bool, user_agent: str, details: str):
        """Registra tentativa de login"""
        try:
            attempt = LoginAttempt(
                ip_address=ip_origem,
                email=email,
                success=success,
                user_agent=user_agent,
                details=details
            )
            db.session.add(attempt)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao registrar tentativa de login: {e}")
    
    def _create_audit_log(self, user_id: int, action: str, resource: str, resource_id: int, 
                         ip_address: str, success: bool, details: str):
        """Cria log de auditoria"""
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent') if request else None,
                endpoint=request.endpoint if request else None,
                method=request.method if request else None,
                success=success,
                details=json.dumps({'message': details}) if isinstance(details, str) else json.dumps(details)
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao criar log de auditoria: {e}")

# ==================== DECORADORES DE CONTROLE DE ACESSO ====================

def require_permission(permission_name: str):
    """Decorador que exige uma permissão específica"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se usuário está autenticado
            auth_service = AuthService()
            usuario = auth_service.validar_sessao()
            
            if not usuario or not usuario.ativo:
                return jsonify({'error': 'Usuário inválido ou inativo'}), 401
            
            if not usuario.has_permission(permission_name):
                # Log de acesso negado
                auth_service._create_audit_log(
                    usuario.id, 'ACCESS_DENIED', 'permission', None,
                    request.remote_addr, False, 
                    f"Permissão negada: {permission_name}"
                )
                
                return jsonify({
                    'error': 'Acesso negado',
                    'required_permission': permission_name
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(role_names):
    """Decorador que exige um ou mais roles específicos"""
    if isinstance(role_names, str):
        role_names = [role_names]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se usuário está autenticado
            auth_service = AuthService()
            usuario = auth_service.validar_sessao()
            
            if not usuario or not usuario.ativo:
                return jsonify({'error': 'Usuário inválido ou inativo'}), 401
            
            user_roles = [role.name for role in usuario.roles]
            if not any(role in user_roles for role in role_names):
                # Log de acesso negado
                auth_service._create_audit_log(
                    usuario.id, 'ACCESS_DENIED', 'role', None,
                    request.remote_addr, False, 
                    f"Role negado. Requerido: {role_names}, Usuário tem: {user_roles}"
                )
                
                return jsonify({
                    'error': 'Acesso negado',
                    'required_roles': role_names,
                    'user_roles': user_roles
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_login(f):
    """Decorador que exige login (compatibilidade com sistema atual)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        usuario = auth_service.validar_sessao()
        
        if not usuario:
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS DE AUTENTICAÇÃO ====================

def create_auth_routes(app: Flask):
    """
    Cria rotas de autenticação compatíveis com sistema atual
    """
    
    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        """Endpoint de login para API"""
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('senha'):
                return jsonify({
                    'success': False,
                    'error': 'Email e senha são obrigatórios',
                    'code': 'MISSING_CREDENTIALS'
                }), 400
            
            auth_service = AuthService()
            result = auth_service.login(
                email=data['email'],
                senha=data['senha'],
                ip_origem=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 401
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Erro interno do servidor',
                'code': 'INTERNAL_ERROR'
            }), 500
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Rota de login compatível com sistema atual"""
        if request.method == 'GET':
            # Renderizar página de login unificada
            return app.send_static_file('login.html')
        
        # POST - processar login
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if not email or not senha:
            return jsonify({
                'success': False,
                'error': 'Email e senha são obrigatórios'
            }), 400
        
        auth_service = AuthService()
        result = auth_service.login(email, senha, request.remote_addr, request.headers.get('User-Agent'))
        
        if result['success']:
            # Redirecionar baseado no role
            user = result['user']
            primary_role = user.get('primary_role')
            
            # Mapeamento de redirecionamento
            role_redirects = {
                'SUPER_ADMIN': '/admin/dashboard',
                'ADMIN_COMPRADOR': '/dashboard-comprador-funcional.html',
                'ADMIN_REQUISITANTE': '/dashboard-requisitante-integrado.html',
                'COMPRADOR_SENIOR': '/dashboard-comprador-funcional.html',
                'COMPRADOR_JUNIOR': '/dashboard-comprador-funcional.html',
                'REQUISITANTE_SENIOR': '/dashboard-requisitante-integrado.html',
                'REQUISITANTE_JUNIOR': '/dashboard-requisitante-funcional.html',
                'FORNECEDOR_PREMIUM': '/dashboard-fornecedor-funcional.html',
                'FORNECEDOR_BASICO': '/dashboard-fornecedor-funcional.html'
            }
            
            redirect_url = role_redirects.get(primary_role, '/index.html')
            return redirect(redirect_url)
        else:
            return jsonify(result), 401
    
    @app.route('/logout')
    def logout_route():
        """Rota de logout compatível"""
        auth_service = AuthService()
        auth_service.logout()
        return redirect('/login')
    
    @app.route('/api/auth/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """Endpoint para renovar token"""
        try:
            user_id = get_jwt_identity()
            auth_service = AuthService()
            result = auth_service.refresh_token(user_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 401
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Erro ao renovar token',
                'code': 'REFRESH_ERROR'
            }), 500

# ==================== INICIALIZAÇÃO ====================

def init_auth(app: Flask):
    """
    Inicializa sistema de autenticação na aplicação Flask
    """
    # Configurar JWT
    jwt = JWTManager(app)
    
    # Configurações JWT
    app.config.setdefault('JWT_SECRET_KEY', 'sua-chave-super-secreta-aqui')
    app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(minutes=15))
    app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=7))
    
    # Criar rotas de autenticação
    create_auth_routes(app)
    
    # Handlers de erro JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'error': 'Token expirado',
            'code': 'TOKEN_EXPIRED'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Token inválido',
            'code': 'INVALID_TOKEN'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Token de acesso requerido',
            'code': 'MISSING_TOKEN'
        }), 401
    
    return jwt

# ==================== FUNÇÕES AUXILIARES ====================

def get_current_user() -> Optional[Usuario]:
    """Retorna o usuário atual da sessão"""
    auth_service = AuthService()
    return auth_service.validar_sessao()

def current_user_has_permission(permission_name: str) -> bool:
    """Verifica se o usuário atual tem uma permissão"""
    usuario = get_current_user()
    return usuario and usuario.has_permission(permission_name)

def current_user_has_role(role_name: str) -> bool:
    """Verifica se o usuário atual tem um role"""
    usuario = get_current_user()
    return usuario and usuario.has_role(role_name)

# ==================== EXEMPLO DE USO ====================

if __name__ == '__main__':
    # Exemplo de como usar o sistema
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sua-chave-secreta'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema_propostas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar banco
    db.init_app(app)
    
    # Inicializar autenticação
    jwt = init_auth(app)
    
    # Exemplo de rota protegida
    @app.route('/dashboard-comprador')
    @require_permission('dashboard_comprador.access')
    def dashboard_comprador():
        return app.send_static_file('dashboard-comprador-funcional.html')
    
    # Criar tabelas
    with app.app_context():
        db.create_all()
    
    print("Sistema de autenticação inicializado!")
    print("Acesse /login para fazer login")
    print("Use /api/auth/login para API")
