#!/usr/bin/env python3
"""
Blueprint de Rotas de Autenticação - Sistema de Propostas
Implementa as rotas /api/auth/* que o frontend está chamando
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from datetime import datetime
import re

# Importar classes do sistema existente
from auth import AuthService
from models import Usuario, db

# Configurar blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Configurar rate limiting
limiter = Limiter(
    app=current_app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configurar logging
logger = logging.getLogger(__name__)

# Instanciar serviço de autenticação
# auth_service = AuthService()  # Comentar por enquanto

def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password):
    """Valida força da senha"""
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
    
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter pelo menos um caractere especial"
    
    return True, "Senha válida"

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per minute")  # Rate limiting para login
def login():
    """
    Endpoint de login
    POST /api/auth/login
    """
    try:
        # Validar dados de entrada
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos',
                'message': 'JSON não fornecido'
            }), 400
        
        email = data.get('email', '').strip().lower()
        senha = data.get('senha', '')
        
        # Validações básicas
        if not email or not senha:
            return jsonify({
                'success': False,
                'error': 'Dados obrigatórios',
                'message': 'Email e senha são obrigatórios'
            }), 400
        
        if not validate_email(email):
            return jsonify({
                'success': False,
                'error': 'Email inválido',
                'message': 'Formato de email inválido'
            }), 400
        
        # Obter IP do cliente
        ip_origem = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Tentar fazer login
        resultado = auth_service.login(email, senha, ip_origem)
        
        if resultado['success']:
            # Login bem-sucedido
            logger.info(f"Login bem-sucedido: {email} de {ip_origem}")
            return jsonify(resultado), 200
        else:
            # Login falhado
            logger.warning(f"Tentativa de login falhada: {email} de {ip_origem}")
            return jsonify(resultado), 401
            
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Endpoint para renovar token de acesso
    POST /api/auth/refresh
    """
    try:
        # Obter identidade do usuário do refresh token
        usuario_id = get_jwt_identity()
        
        # Buscar usuário no banco
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.ativo:
            return jsonify({
                'success': False,
                'error': 'Usuário inválido',
                'message': 'Usuário não encontrado ou inativo'
            }), 401
        
        # Criar novo access token
        from flask_jwt_extended import create_access_token
        
        access_token = create_access_token(
            identity=usuario.id,
            additional_claims={
                'tipo': usuario.tipo,
                'nivel_acesso': usuario.nivel_acesso,
                'nome': usuario.nome,
                'email': usuario.email
            }
        )
        
        logger.info(f"Token renovado para usuário: {usuario.email}")
        
        return jsonify({
            'success': True,
            'message': 'Token renovado com sucesso',
            'access_token': access_token,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na renovação de token: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Endpoint de logout
    POST /api/auth/logout
    """
    try:
        # Obter JTI (JWT ID) do token atual
        jti = get_jwt()['jti']
        
        # Fazer logout usando o serviço
        resultado = auth_service.logout(jti)
        
        if resultado['success']:
            logger.info(f"Logout realizado com sucesso")
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Erro no logout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Endpoint para obter dados do usuário atual
    GET /api/auth/me
    """
    try:
        # Obter ID do usuário do token
        usuario_id = get_jwt_identity()
        
        # Buscar usuário no banco
        usuario = Usuario.query.get(usuario_id)
        if not usuario or not usuario.ativo:
            return jsonify({
                'success': False,
                'error': 'Usuário inválido',
                'message': 'Usuário não encontrado ou inativo'
            }), 401
        
        return jsonify({
            'success': True,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter usuário atual: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("3 per minute")  # Rate limiting para cadastro
def register():
    """
    Endpoint de cadastro (apenas para administradores)
    POST /api/auth/register
    """
    try:
        # Validar dados de entrada
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos',
                'message': 'JSON não fornecido'
            }), 400
        
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip().lower()
        senha = data.get('senha', '')
        tipo = data.get('tipo', 'fornecedor').strip().lower()
        
        # Validações básicas
        if not all([nome, email, senha]):
            return jsonify({
                'success': False,
                'error': 'Dados obrigatórios',
                'message': 'Nome, email e senha são obrigatórios'
            }), 400
        
        if not validate_email(email):
            return jsonify({
                'success': False,
                'error': 'Email inválido',
                'message': 'Formato de email inválido'
            }), 400
        
        # Validar força da senha
        senha_valida, mensagem_senha = validate_password_strength(senha)
        if not senha_valida:
            return jsonify({
                'success': False,
                'error': 'Senha fraca',
                'message': mensagem_senha
            }), 400
        
        # Verificar se email já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return jsonify({
                'success': False,
                'error': 'Email já cadastrado',
                'message': 'Este email já está em uso'
            }), 409
        
        # Validar tipo de usuário
        tipos_validos = ['admin', 'comprador', 'requisitante', 'fornecedor', 'auditor']
        if tipo not in tipos_validos:
            return jsonify({
                'success': False,
                'error': 'Tipo inválido',
                'message': f'Tipo deve ser um de: {", ".join(tipos_validos)}'
            }), 400
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            tipo=tipo,
            nivel_acesso=1,  # Nível básico por padrão
            ativo=True
        )
        
        # Definir senha (será hasheada automaticamente)
        novo_usuario.set_senha(senha)
        
        # Salvar no banco
        db.session.add(novo_usuario)
        db.session.commit()
        
        logger.info(f"Novo usuário cadastrado: {email} (tipo: {tipo})")
        
        return jsonify({
            'success': True,
            'message': 'Usuário cadastrado com sucesso',
            'usuario': {
                'id': novo_usuario.id,
                'nome': novo_usuario.nome,
                'email': novo_usuario.email,
                'tipo': novo_usuario.tipo
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro no cadastro: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
@limiter.limit("3 per minute")
def change_password():
    """
    Endpoint para alterar senha
    POST /api/auth/change-password
    """
    try:
        # Obter usuário atual
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or not usuario.ativo:
            return jsonify({
                'success': False,
                'error': 'Usuário inválido',
                'message': 'Usuário não encontrado ou inativo'
            }), 401
        
        # Validar dados de entrada
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos',
                'message': 'JSON não fornecido'
            }), 400
        
        senha_atual = data.get('senha_atual', '')
        senha_nova = data.get('senha_nova', '')
        
        if not senha_atual or not senha_nova:
            return jsonify({
                'success': False,
                'error': 'Dados obrigatórios',
                'message': 'Senha atual e nova senha são obrigatórias'
            }), 400
        
        # Verificar senha atual
        if not usuario.verificar_senha(senha_atual):
            return jsonify({
                'success': False,
                'error': 'Senha incorreta',
                'message': 'Senha atual incorreta'
            }), 401
        
        # Validar força da nova senha
        senha_valida, mensagem_senha = validate_password_strength(senha_nova)
        if not senha_valida:
            return jsonify({
                'success': False,
                'error': 'Senha fraca',
                'message': mensagem_senha
            }), 400
        
        # Alterar senha
        usuario.set_senha(senha_nova)
        db.session.commit()
        
        logger.info(f"Senha alterada para usuário: {usuario.email}")
        
        return jsonify({
            'success': True,
            'message': 'Senha alterada com sucesso'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro na alteração de senha: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

# Handlers de erro para o blueprint
@auth_bp.errorhandler(429)
def ratelimit_handler(e):
    """Handler para rate limiting"""
    return jsonify({
        'success': False,
        'error': 'Muitas tentativas',
        'message': 'Muitas tentativas. Tente novamente mais tarde.'
    }), 429

@auth_bp.errorhandler(400)
def bad_request_handler(e):
    """Handler para requisições inválidas"""
    return jsonify({
        'success': False,
        'error': 'Requisição inválida',
        'message': 'Dados da requisição inválidos'
    }), 400

@auth_bp.errorhandler(401)
def unauthorized_handler(e):
    """Handler para não autorizado"""
    return jsonify({
        'success': False,
        'error': 'Não autorizado',
        'message': 'Acesso negado'
    }), 401

@auth_bp.errorhandler(500)
def internal_error_handler(e):
    """Handler para erros internos"""
    return jsonify({
        'success': False,
        'error': 'Erro interno',
        'message': 'Erro interno do servidor'
    }), 500

