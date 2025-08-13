#!/usr/bin/env python3
"""
Backend unificado com autenticação JWT e SQLAlchemy.

Este módulo cria uma API REST para autenticação de usuários e gestão de
cadastros em um sistema de propostas. Ele utiliza o modelo de dados
definido em ``models.py`` para persistir usuários, processos,
propostas e notificações. A autenticação é feita através de tokens
JWT, usando o pacote ``flask_jwt_extended``. Diferentemente do
``backend_render_fix.py`` original, este backend evita duplicação de
lógica de autenticação e usa um único mecanismo de login para todas
as páginas do sistema.

Recursos principais fornecidos:
* Criação e listagem de usuários (somente para administradores).
* Login utilizando e‑mail e senha, com geração de access token e
  refresh token.
* Renovação de tokens via refresh token.
* Logout que revoga o token do usuário.
* Recuperação do usuário atual a partir do token.

Para integrar com as páginas HTML do sistema, configure seus
JavaScripts para enviar requisições para os endpoints ``/api/auth/login``
e ``/api/auth/refresh``. Proteja chamadas posteriores com o
``Authorization: Bearer <access_token>`` no cabeçalho.

"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import (
    jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt
)
from models import db, Usuario
import os
import uuid
import logging
from datetime import timedelta

import auth  # importa o módulo de autenticação existente

# Configuração básica do Flask
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Carrega configurações do ambiente ou usa valores padrão
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# Usar SQLite para simplicidade; em produção opte por PostgreSQL ou outro SGDB
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI',
    'sqlite:///' + os.path.join(base_dir, 'database.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configura expiração de tokens: 8 horas para access token, 7 dias para refresh
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

# Inicializa extensões
db.init_app(app)
migrate = Migrate(app, db)
jwt = auth.init_jwt(app)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.before_first_request
def setup_database():
    """Cria as tabelas e um usuário administrador padrão se necessário."""
    db.create_all()
    # Verificar se já existe algum usuário
    if Usuario.query.count() == 0:
        # Criar usuários padrão: admin, comprador, requisitante e fornecedor
        usuarios_iniciais = [
            {
                'nome': 'Administrador',
                'email': 'admin@sistema.com',
                'senha': 'Admin@2025!',
                'tipo': 'admin',
                'nivel_acesso': 'total'
            },
            {
                'nome': 'Comprador Padrão',
                'email': 'comprador@sistema.com',
                'senha': 'Comprador@123',
                'tipo': 'comprador',
                'nivel_acesso': 'padrao'
            },
            {
                'nome': 'Requisitante Padrão',
                'email': 'requisitante@sistema.com',
                'senha': 'Requisitante@123',
                'tipo': 'requisitante',
                'nivel_acesso': 'padrao'
            },
            {
                'nome': 'Fornecedor Padrão',
                'email': 'fornecedor@sistema.com',
                'senha': 'Fornecedor@123',
                'tipo': 'fornecedor',
                'nivel_acesso': 'padrao'
            },
        ]
        for usuario_data in usuarios_iniciais:
            usuario = Usuario(
                id=str(uuid.uuid4()),
                nome=usuario_data['nome'],
                email=usuario_data['email'],
                tipo=usuario_data['tipo'],
                nivel_acesso=usuario_data['nivel_acesso'],
            )
            usuario.set_senha(usuario_data['senha'])
            db.session.add(usuario)
        db.session.commit()
        logger.info("Usuários padrão criados com sucesso")


# Rotas de autenticação

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Realiza login com email e senha.

    Exemplo de corpo JSON:
        {
            "email": "admin@sistema.com",
            "senha": "Admin@2025!"
        }
    """
    data = request.get_json() or {}
    email = data.get('email')
    senha = data.get('senha')
    if not email or not senha:
        return jsonify({'success': False, 'error': 'Dados ausentes', 'message': 'Email e senha são obrigatórios'}), 400

    resultado = auth.AuthService.login(email, senha, request.remote_addr)
    status_code = 200 if resultado.get('success') else 401
    return jsonify(resultado), status_code


@app.route('/api/auth/refresh', methods=['POST'])
@auth.require_auth
def refresh():
    """Renova o access token usando o refresh token fornecido no cabeçalho."""
    resultado = auth.AuthService.refresh_token()
    status_code = 200 if resultado.get('success') else 401
    return jsonify(resultado), status_code


@app.route('/api/auth/logout', methods=['POST'])
@auth.require_auth
def logout():
    """Revoga o token corrente e registra logout."""
    # O JTI (JWT ID) é obtido do token atual
    jti = get_jwt().get('jti')
    resultado = auth.AuthService.logout(jti)
    status_code = 200 if resultado.get('success') else 400
    return jsonify(resultado), status_code


@app.route('/api/auth/me', methods=['GET'])
@auth.require_auth
def me():
    """Retorna informações sobre o usuário autenticado."""
    usuario = auth.AuthService.get_current_user()
    if usuario:
        return jsonify({'success': True, 'usuario': usuario.to_dict()}), 200
    return jsonify({'success': False, 'error': 'Não autenticado'}), 401


# Rotas para gestão de usuários (somente admin)

@app.route('/api/usuarios', methods=['GET'])
@auth.require_role('admin')
def listar_usuarios():
    """Retorna a lista de todos os usuários."""
    usuarios = Usuario.query.all()
    return jsonify([u.to_dict() for u in usuarios]), 200


@app.route('/api/usuarios', methods=['POST'])
@auth.require_role('admin')
def criar_usuario():
    """Cria um novo usuário.

    Exemplo de corpo JSON:
        {
            "nome": "Novo Usuário",
            "email": "novo@empresa.com",
            "senha": "SenhaForte!",
            "tipo": "comprador",
            "nivel_acesso": "padrao"
        }
    """
    data = request.get_json() or {}
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    tipo = data.get('tipo')
    nivel_acesso = data.get('nivel_acesso')

    if not all([nome, email, senha, tipo]):
        return jsonify({'success': False, 'error': 'Dados incompletos', 'message': 'Todos os campos são obrigatórios'}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email duplicado', 'message': 'Já existe usuário com esse email'}), 400

    novo_usuario = Usuario(
        id=str(uuid.uuid4()),
        nome=nome,
        email=email,
        tipo=tipo,
        nivel_acesso=nivel_acesso or 'padrao'
    )
    novo_usuario.set_senha(senha)
    db.session.add(novo_usuario)
    db.session.commit()
    return jsonify({'success': True, 'usuario': novo_usuario.to_dict()}), 201


@app.route('/api/usuarios/<string:usuario_id>', methods=['GET'])
@auth.require_role('admin')
def obter_usuario(usuario_id):
    """Obtém informações de um usuário específico."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
    return jsonify({'success': True, 'usuario': usuario.to_dict()}), 200


@app.route('/api/usuarios/<string:usuario_id>', methods=['PUT'])
@auth.require_role('admin')
def atualizar_usuario(usuario_id):
    """Atualiza informações de um usuário existente."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404

    data = request.get_json() or {}
    # Atualizar campos se fornecidos
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    tipo = data.get('tipo')
    nivel_acesso = data.get('nivel_acesso')
    ativo = data.get('ativo')

    if email and email != usuario.email:
        # Verifica duplicidade de email
        if Usuario.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email duplicado', 'message': 'Já existe usuário com esse email'}), 400
        usuario.email = email
    if nome:
        usuario.nome = nome
    if senha:
        usuario.set_senha(senha)
    if tipo:
        usuario.tipo = tipo
    if nivel_acesso:
        usuario.nivel_acesso = nivel_acesso
    if ativo is not None:
        usuario.ativo = bool(ativo)

    db.session.commit()
    return jsonify({'success': True, 'usuario': usuario.to_dict()}), 200


@app.route('/api/usuarios/<string:usuario_id>', methods=['DELETE'])
@auth.require_role('admin')
def desativar_usuario(usuario_id):
    """Desativa (soft delete) um usuário ao invés de apagar.

    Utiliza o campo ``ativo`` para desativar o acesso do usuário. O
    recurso não é removido do banco de dados para fins de auditoria.
    """
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
    usuario.ativo = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'Usuário desativado'}), 200


if __name__ == '__main__':
    # Apenas roda o servidor se executado diretamente
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))    
