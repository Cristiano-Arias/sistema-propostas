#!/usr/bin/env python3
"""
Backend Consolidado - Sistema de Gestão de Propostas
Versão 4.1 - Render Deploy Fix
Arquivo único com todas as dependências internas

CORREÇÕES IMPLEMENTADAS:
- Banco de dados SQLite real (substitui dados em memória)
- Sistema de autenticação JWT seguro
- APIs RESTful padronizadas
- Logs de auditoria
- Tratamento de erros robusto
- Consolidado em arquivo único para deploy
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from werkzeug.security import generate_password_hash, check_password_hash

# ========================================
# CONFIGURAÇÃO DO FLASK
# ========================================

app = Flask(__name__, static_folder='static')

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///sistema_propostas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar CORS
CORS(app, origins=['*'])

# Inicializar extensões
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lista de tokens revogados
revoked_tokens = set()

# ========================================
# MODELOS DE BANCO DE DADOS
# ========================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    nivel_acesso = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,
            'nivelAcesso': self.nivel_acesso,
            'ativo': self.ativo,
            'dataCriacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'ultimoLogin': self.ultimo_login.isoformat() if self.ultimo_login else None
        }

class Processo(db.Model):
    __tablename__ = 'processos'
    
    id = db.Column(db.String(50), primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    objeto = db.Column(db.Text, nullable=False)
    modalidade = db.Column(db.String(50), nullable=False)
    prazo = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='ativo')
    criado_por = db.Column(db.String(50), db.ForeignKey('usuarios.id'), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    fornecedores_convidados = db.Column(db.Text)
    
    def set_fornecedores_convidados(self, fornecedores_list):
        self.fornecedores_convidados = json.dumps(fornecedores_list)
    
    def get_fornecedores_convidados(self):
        if self.fornecedores_convidados:
            return json.loads(self.fornecedores_convidados)
        return []
    
    def calcular_status(self):
        if self.prazo < datetime.now():
            return 'encerrado'
        else:
            dias_restantes = (self.prazo - datetime.now()).days
            if dias_restantes <= 5:
                return 'urgente'
            else:
                return 'ativo'
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'objeto': self.objeto,
            'modalidade': self.modalidade,
            'prazo': self.prazo.isoformat() if self.prazo else None,
            'status': self.status,
            'criadoPor': self.criado_por,
            'dataCadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'status_calculado': self.calcular_status(),
            'fornecedoresConvidados': self.get_fornecedores_convidados()
        }

class Proposta(db.Model):
    __tablename__ = 'propostas'
    
    id = db.Column(db.String(50), primary_key=True)
    protocolo = db.Column(db.String(50), unique=True, nullable=False)
    processo_id = db.Column(db.String(50), db.ForeignKey('processos.id'), nullable=False)
    empresa = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    validade_proposta = db.Column(db.String(20))
    fornecedor_id = db.Column(db.String(50), db.ForeignKey('usuarios.id'))
    dados_tecnicos = db.Column(db.Text)
    dados_comerciais = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'protocolo': self.protocolo,
            'processo': self.processo_id,
            'empresa': self.empresa,
            'cnpj': self.cnpj,
            'data': self.data_envio.isoformat() if self.data_envio else None,
            'valorTotal': str(self.valor_total),
            'validadeProposta': self.validade_proposta
        }

class LogAuditoria(db.Model):
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.String(50), db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(100), nullable=False)
    recurso = db.Column(db.String(100), nullable=False)
    recurso_id = db.Column(db.String(50))
    detalhes = db.Column(db.Text)
    ip_origem = db.Column(db.String(45))
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)

# ========================================
# CONFIGURAÇÃO JWT
# ========================================

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload['jti'] in revoked_tokens

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'success': False,
        'error': 'Token expirado',
        'message': 'Faça login novamente'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'success': False,
        'error': 'Token inválido',
        'message': 'Token de acesso inválido'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'success': False,
        'error': 'Token ausente',
        'message': 'Token de acesso necessário'
    }), 401

# ========================================
# DECORATORS DE AUTENTICAÇÃO
# ========================================

def require_auth(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                claims = get_jwt()
                user_role = claims.get('tipo')
                
                if user_role not in roles:
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

# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def log_user_action(acao, recurso, recurso_id=None, detalhes=None):
    try:
        usuario_id = get_jwt_identity()
        if usuario_id:
            log = LogAuditoria(
                usuario_id=usuario_id,
                acao=acao,
                recurso=recurso,
                recurso_id=recurso_id,
                ip_origem=request.remote_addr,
                detalhes=json.dumps(detalhes) if detalhes else None
            )
            db.session.add(log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")
        db.session.rollback()

def popular_dados_iniciais():
    if Usuario.query.count() == 0:
        usuarios_iniciais = [
            {
                'id': 'admin_001',
                'nome': 'Administrador Sistema',
                'email': 'admin@sistema.com',
                'senha': 'admin123',
                'tipo': 'admin',
                'nivel_acesso': 'admin_senior'
            },
            {
                'id': 'comprador_001',
                'nome': 'João Silva',
                'email': 'joao.silva@empresa.com',
                'senha': 'comprador123',
                'tipo': 'comprador',
                'nivel_acesso': 'comprador_senior'
            },
            {
                'id': 'requisitante_001',
                'nome': 'Maria Santos',
                'email': 'carlos.oliveira@requisitante.com',
                'senha': 'requisitante123',
                'tipo': 'requisitante',
                'nivel_acesso': 'requisitante_pleno'
            },
            {
                'id': 'forn_001',
                'nome': 'Construtora Alpha LTDA',
                'email': 'contato@alpha.com',
                'senha': 'fornecedor123',
                'tipo': 'fornecedor',
                'nivel_acesso': 'fornecedor'
            },
            {
                'id': 'auditor_001',
                'nome': 'Ana Auditora',
                'email': 'ana.auditora@sistema.com',
                'senha': 'auditor123',
                'tipo': 'auditor',
                'nivel_acesso': 'auditor_senior'
            }
        ]
        
        for usuario_data in usuarios_iniciais:
            usuario = Usuario(
                id=usuario_data['id'],
                nome=usuario_data['nome'],
                email=usuario_data['email'],
                tipo=usuario_data['tipo'],
                nivel_acesso=usuario_data['nivel_acesso']
            )
            usuario.set_senha(usuario_data['senha'])
            db.session.add(usuario)
        
        # Processos iniciais
        processos_iniciais = [
            {
                'id': 'proc_001',
                'numero': 'LIC-2025-001',
                'objeto': 'Construção de Escola Municipal de Ensino Fundamental',
                'modalidade': 'Concorrência',
                'prazo': datetime(2025, 8, 15, 14, 0),
                'criado_por': 'requisitante_001'
            },
            {
                'id': 'proc_002',
                'numero': 'LIC-2025-002',
                'objeto': 'Reforma e Ampliação do Centro de Saúde',
                'modalidade': 'Tomada de Preços',
                'prazo': datetime(2025, 8, 20, 16, 0),
                'criado_por': 'requisitante_001'
            }
        ]
        
        for processo_data in processos_iniciais:
            processo = Processo(**processo_data)
            db.session.add(processo)
        
        try:
            db.session.commit()
            print("✅ Dados iniciais populados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao popular dados iniciais: {e}")

# ========================================
# ROTAS DE AUTENTICAÇÃO
# ========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('senha'):
            return jsonify({
                'success': False,
                'error': 'Dados incompletos',
                'message': 'Email e senha são obrigatórios'
            }), 400
        
        usuario = Usuario.query.filter_by(email=data['email']).first()
        
        if not usuario or not usuario.verificar_senha(data['senha']):
            return jsonify({
                'success': False,
                'error': 'Credenciais inválidas',
                'message': 'Email ou senha incorretos'
            }), 401
        
        if not usuario.ativo:
            return jsonify({
                'success': False,
                'error': 'Usuário inativo',
                'message': 'Conta desativada'
            }), 401
        
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
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'usuario': usuario.to_dict(),
            'expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
        })
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    try:
        jti = get_jwt()['jti']
        revoked_tokens.add(jti)
        
        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro ao realizar logout'
        }), 500

# ========================================
# ROTAS DE STATUS E INFORMAÇÕES
# ========================================

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def api_status():
    try:
        stats = {
            'processos_total': Processo.query.count(),
            'processos_ativos': Processo.query.filter(Processo.prazo >= datetime.now()).count(),
            'propostas_total': Proposta.query.count(),
            'usuarios_total': Usuario.query.count(),
            'usuarios_ativos': Usuario.query.filter_by(ativo=True).count()
        }
        
        return jsonify({
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "versao": "4.1",
            "ambiente": os.environ.get('FLASK_ENV', 'development'),
            "estatisticas": stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# ========================================
# ROTAS DE PROCESSOS
# ========================================

@app.route('/api/v1/processos', methods=['GET'])
@require_auth
def listar_processos():
    try:
        status_filtro = request.args.get('status', 'todos')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        query = Processo.query
        
        if status_filtro != 'todos':
            if status_filtro == 'ativo':
                query = query.filter(Processo.prazo >= datetime.now())
            elif status_filtro == 'encerrado':
                query = query.filter(Processo.prazo < datetime.now())
        
        processos_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        processos = []
        for processo in processos_paginated.items:
            processo_dict = processo.to_dict()
            processos.append(processo_dict)
        
        log_user_action('VIEW_PROCESSOS', 'processo', detalhes={
            'filtro': status_filtro,
            'total': len(processos)
        })
        
        return jsonify({
            "success": True,
            "processos": processos,
            "total": processos_paginated.total,
            "pages": processos_paginated.pages,
            "current_page": page,
            "filtro_aplicado": status_filtro
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return jsonify({
            "success": False,
            "error": "Erro ao carregar processos"
        }), 500

@app.route('/api/v1/processos/<processo_id>', methods=['GET'])
@require_auth
def obter_processo(processo_id):
    try:
        processo = Processo.query.get(processo_id)
        
        if not processo:
            return jsonify({
                'success': False,
                'error': 'Processo não encontrado'
            }), 404
        
        processo_dict = processo.to_dict()
        
        log_user_action('VIEW_PROCESSO', 'processo', processo_id)
        
        return jsonify({
            'success': True,
            'processo': processo_dict
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter processo {processo_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar processo'
        }), 500

# ========================================
# ROTAS DE PROPOSTAS
# ========================================

@app.route('/api/v1/propostas', methods=['GET'])
@require_auth
def listar_propostas():
    try:
        processo_id = request.args.get('processo_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        query = Proposta.query
        
        if processo_id:
            query = query.filter_by(processo_id=processo_id)
        
        propostas_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        propostas = [p.to_dict() for p in propostas_paginated.items]
        
        return jsonify({
            'success': True,
            'propostas': propostas,
            'total': propostas_paginated.total,
            'pages': propostas_paginated.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar propostas'
        }), 500

# ========================================
# ROTAS ESTÁTICAS
# ========================================

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# ========================================
# TRATAMENTO DE ERROS
# ========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Recurso não encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {error}")
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor'
    }), 500

# ========================================
# INICIALIZAÇÃO
# ========================================

def init_app():
    with app.app_context():
        db.create_all()
        popular_dados_iniciais()

if __name__ == '__main__':
    init_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando Sistema de Propostas v4.1")
    logger.info(f"📊 Ambiente: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"🔌 Porta: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # Para Gunicorn
    init_app()

