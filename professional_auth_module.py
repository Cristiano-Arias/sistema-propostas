#!/usr/bin/env python3
"""
Módulo de Autenticação - Sistema de Propostas
Implementa autenticação JWT de forma profissional
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from extensions import db, bcrypt, limiter
from models.usuario import Usuario
from utils.validators import validate_email, validate_password
from utils.audit import log_user_action
import logging

logger = logging.getLogger(__name__)

# Criar blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    Endpoint de login
    
    Aceita:
    - email/login: string
    - senha: string
    
    Retorna:
    - access_token: JWT token
    - refresh_token: Refresh token
    - usuario: dados do usuário
    """
    try:
        data = request.get_json()
        
        # Validar entrada
        email = data.get('email') or data.get('login')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({
                'success': False,
                'message': 'Email e senha são obrigatórios'
            }), 400
        
        # Normalizar email
        email = email.strip().lower()
        
        # Validar formato do email
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Formato de email inválido'
            }), 400
        
        # Buscar usuário
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            logger.warning(f"Tentativa de login com email não cadastrado: {email}")
            return jsonify({
                'success': False,
                'message': 'Email ou senha incorretos'
            }), 401
        
        # Verificar se usuário está ativo
        if not usuario.ativo:
            logger.warning(f"Tentativa de login com usuário inativo: {email}")
            return jsonify({
                'success': False,
                'message': 'Usuário inativo. Entre em contato com o administrador.'
            }), 401
        
        # Verificar senha
        if not usuario.verificar_senha(senha):
            logger.warning(f"Senha incorreta para: {email}")
            log_user_action(
                usuario_id=usuario.id,
                acao='LOGIN_FALHOU',
                detalhes={'motivo': 'senha_incorreta'}
            )
            return jsonify({
                'success': False,
                'message': 'Email ou senha incorretos'
            }), 401
        
        # Atualizar último login
        usuario.atualizar_ultimo_login()
        
        # Criar tokens
        access_token = create_access_token(
            identity=str(usuario.id),
            additional_claims={
                'tipo': usuario.tipo,
                'perfil': usuario.tipo,  # Compatibilidade
                'nome': usuario.nome,
                'email': usuario.email
            }
        )
        
        refresh_token = create_refresh_token(identity=str(usuario.id))
        
        # Log de sucesso
        log_user_action(
            usuario_id=usuario.id,
            acao='LOGIN_SUCESSO',
            detalhes={'tipo': usuario.tipo}
        )
        
        logger.info(f"Login bem-sucedido: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renova o access token usando refresh token"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or not usuario.ativo:
            return jsonify({
                'success': False,
                'message': 'Usuário inválido'
            }), 401
        
        # Criar novo access token
        access_token = create_access_token(
            identity=str(usuario.id),
            additional_claims={
                'tipo': usuario.tipo,
                'perfil': usuario.tipo,
                'nome': usuario.nome,
                'email': usuario.email
            }
        )
        
        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao renovar token: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao renovar token'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Realiza logout do usuário"""
    try:
        usuario_id = get_jwt_identity()
        jti = get_jwt()['jti']
        
        # TODO: Adicionar token à blacklist (Redis em produção)
        
        log_user_action(
            usuario_id=usuario_id,
            acao='LOGOUT',
            detalhes={'jti': jti}
        )
        
        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no logout: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao realizar logout'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Retorna dados do usuário atual"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuário não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter usuário: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao obter dados do usuário'
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
@limiter.limit("3 per hour")
def change_password():
    """Altera a senha do usuário"""
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        senha_atual = data.get('senha_atual')
        senha_nova = data.get('senha_nova')
        
        if not senha_atual or not senha_nova:
            return jsonify({
                'success': False,
                'message': 'Senha atual e nova são obrigatórias'
            }), 400
        
        # Validar força da senha nova
        is_valid, message = validate_password(senha_nova)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Buscar usuário
        usuario = Usuario.query.get(usuario_id)
        
        # Verificar senha atual
        if not usuario.verificar_senha(senha_atual):
            return jsonify({
                'success': False,
                'message': 'Senha atual incorreta'
            }), 401
        
        # Alterar senha
        usuario.definir_senha(senha_nova)
        db.session.commit()
        
        log_user_action(
            usuario_id=usuario_id,
            acao='SENHA_ALTERADA'
        )
        
        return jsonify({
            'success': True,
            'message': 'Senha alterada com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao alterar senha'
        }), 500