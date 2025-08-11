#!/usr/bin/env python3
"""
Configurações do Sistema de Propostas
Configuração para SQLite (desenvolvimento) e PostgreSQL (produção)
"""

import os
from datetime import timedelta

class Config:
    """Configuração base"""
    
    # Chave secreta para JWT e sessões
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configuração JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)  # Token expira em 8 horas
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # Refresh token expira em 30 dias
    
    # Configuração CORS
    CORS_ORIGINS = ['*']  # Em produção, especificar domínios exatos
    
    # Configuração de banco de dados
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Configuração de upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Configuração de logs
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    
    DEBUG = True
    
    # SQLite para desenvolvimento
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sistema_propostas.db')
    
    # Logs mais verbosos em desenvolvimento
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Configuração para produção"""
    
    DEBUG = False
    
    # PostgreSQL para produção (Render.com)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sistema_propostas.db')
    
    # Configurações de segurança para produção
    CORS_ORIGINS = [
        'https://sistema-propostas.onrender.com',
        'https://seu-dominio.com'  # Adicionar domínios específicos
    ]
    
    # Chaves mais seguras em produção
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-must-be-changed'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY

class TestingConfig(Config):
    """Configuração para testes"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Banco em memória para testes
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)  # Tokens de curta duração para testes

# Configuração baseada no ambiente
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retorna a configuração baseada na variável de ambiente"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

