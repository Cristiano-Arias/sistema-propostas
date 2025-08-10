#!/usr/bin/env python3
"""
Sistema de Gestão de Propostas - Backend Principal
Versão Profissional 1.0
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

# Importar configurações
from config import Config, get_config

# Importar extensões
from extensions import db, jwt, bcrypt, limiter

# Importar blueprints
from modules.auth import auth_bp
from modules.termos_referencia import tr_bp
from modules.processos import processos_bp
from modules.propostas import propostas_bp
from modules.fornecedores import fornecedores_bp
from modules.notificacoes import notificacoes_bp
from modules.admin import admin_bp

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Factory pattern para criar a aplicação Flask"""
    
    # Criar aplicação
    app = Flask(__name__, static_folder='static')
    
    # Carregar configurações
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(get_config(config_name))
    
    # Inicializar extensões
    initialize_extensions(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar error handlers
    register_error_handlers(app)
    
    # Configurar CORS
    configure_cors(app)
    
    # Inicializar banco de dados
    with app.app_context():
        initialize_database(app)
    
    logger.info(f"Aplicação criada no modo: {config_name}")
    
    return app

def initialize_extensions(app):
    """Inicializa todas as extensões Flask"""
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    
    # Configurar callbacks do JWT
    from modules.auth.jwt_callbacks import configure_jwt_callbacks
    configure_jwt_callbacks(jwt)
    
    logger.info("Extensões inicializadas")

def register_blueprints(app):
    """Registra todos os blueprints da aplicação"""
    
    # API v1
    api_prefix = '/api/v1'
    
    app.register_blueprint(auth_bp, url_prefix=f'{api_prefix}/auth')
    app.register_blueprint(tr_bp, url_prefix=f'{api_prefix}/termos-referencia')
    app.register_blueprint(processos_bp, url_prefix=f'{api_prefix}/processos')
    app.register_blueprint(propostas_bp, url_prefix=f'{api_prefix}/propostas')
    app.register_blueprint(fornecedores_bp, url_prefix=f'{api_prefix}/fornecedores')
    app.register_blueprint(notificacoes_bp, url_prefix=f'{api_prefix}/notificacoes')
    app.register_blueprint(admin_bp, url_prefix=f'{api_prefix}/admin')
    
    # Rotas estáticas (frontend)
    from modules.static_routes import static_bp
    app.register_blueprint(static_bp)
    
    logger.info("Blueprints registrados")

def register_error_handlers(app):
    """Registra handlers de erro globais"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Requisição inválida', 'message': str(error)}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Não autorizado', 'message': 'Autenticação necessária'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Proibido', 'message': 'Sem permissão para acessar este recurso'}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Não encontrado', 'message': 'Recurso não encontrado'}, 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return {'error': 'Muitas requisições', 'message': 'Limite de requisições excedido'}, 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Erro interno: {error}")
        return {'error': 'Erro interno', 'message': 'Erro interno do servidor'}, 500

def configure_cors(app):
    """Configura CORS de forma segura"""
    if app.config.get('ENV') == 'production':
        # Em produção, restringir origens
        CORS(app, 
             origins=app.config.get('CORS_ORIGINS', []),
             supports_credentials=True,
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization']
        )
    else:
        # Em desenvolvimento, permitir localhost
        CORS(app, 
             origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5000'],
             supports_credentials=True
        )

def initialize_database(app):
    """Inicializa o banco de dados"""
    from database.init_db import init_database, create_default_users
    
    # Criar tabelas
    db.create_all()
    
    # Criar usuários padrão se necessário
    if app.config.get('CREATE_DEFAULT_USERS', True):
        create_default_users()
    
    logger.info("Banco de dados inicializado")

# Criar aplicação
app = create_app()

# Configurar migrações
migrate = Migrate(app, db)

# Health check endpoint
@app.route('/health')
def health_check():
    """Endpoint para verificar saúde da aplicação"""
    return {
        'status': 'healthy',
        'service': 'Sistema de Propostas API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', False)
    
    logger.info(f"Iniciando servidor na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)