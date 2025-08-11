#!/usr/bin/env python3
"""
Configurações atualizadas para o Sistema de Propostas
Inclui configurações RBAC e JWT
"""

import os
from datetime import timedelta

class Config:
    """Configuração base"""
    
    # Configurações existentes (mantidas)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua-chave-secreta-super-forte-aqui'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///sistema_propostas.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de upload (se existirem)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # ==================== NOVAS CONFIGURAÇÕES RBAC/JWT ====================
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 15)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 7)))
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Login Security Configuration
    MAX_LOGIN_ATTEMPTS_PER_IP = int(os.environ.get('MAX_LOGIN_ATTEMPTS_PER_IP', 5))  # Por minuto
    MAX_LOGIN_ATTEMPTS_PER_USER = int(os.environ.get('MAX_LOGIN_ATTEMPTS_PER_USER', 10))  # Por hora
    ACCOUNT_LOCKOUT_DURATION = int(os.environ.get('ACCOUNT_LOCKOUT_DURATION', 15))  # Minutos
    
    # Password Policy Configuration
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_NUMBERS = os.environ.get('PASSWORD_REQUIRE_NUMBERS', 'True').lower() == 'true'
    PASSWORD_REQUIRE_SYMBOLS = os.environ.get('PASSWORD_REQUIRE_SYMBOLS', 'True').lower() == 'true'
    PASSWORD_EXPIRY_DAYS = int(os.environ.get('PASSWORD_EXPIRY_DAYS', 90))
    PASSWORD_HISTORY_COUNT = int(os.environ.get('PASSWORD_HISTORY_COUNT', 5))
    
    # Session Configuration
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 30))  # Minutos
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Audit Log Configuration
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 365))
    AUDIT_LOG_LEVEL = os.environ.get('AUDIT_LOG_LEVEL', 'INFO')
    
    # Email Configuration (para notificações de segurança)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Azure AI Configuration (se existir)
    AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_KEY = os.environ.get('AZURE_OPENAI_KEY')
    AZURE_OPENAI_VERSION = os.environ.get('AZURE_OPENAI_VERSION', '2023-05-15')
    
    # Feature Flags
    ENABLE_2FA = os.environ.get('ENABLE_2FA', 'False').lower() == 'true'
    ENABLE_PASSWORD_RESET = os.environ.get('ENABLE_PASSWORD_RESET', 'True').lower() == 'true'
    ENABLE_AUDIT_LOGGING = os.environ.get('ENABLE_AUDIT_LOGGING', 'True').lower() == 'true'
    ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'True').lower() == 'true'

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///sistema_propostas_dev.db'
    
    # JWT mais permissivo em desenvolvimento
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # 1 hora em dev
    
    # Rate limiting mais permissivo
    MAX_LOGIN_ATTEMPTS_PER_IP = 20
    MAX_LOGIN_ATTEMPTS_PER_USER = 50
    
    # Logs mais verbosos
    AUDIT_LOG_LEVEL = 'DEBUG'

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # JWT para testes
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=10)
    
    # Desabilitar rate limiting em testes
    ENABLE_RATE_LIMITING = False
    
    # Senha mais simples para testes
    PASSWORD_MIN_LENGTH = 4
    PASSWORD_REQUIRE_UPPERCASE = False
    PASSWORD_REQUIRE_SYMBOLS = False

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    
    # Configurações de segurança mais rigorosas
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    
    # Rate limiting mais rigoroso
    MAX_LOGIN_ATTEMPTS_PER_IP = 3  # Por minuto
    MAX_LOGIN_ATTEMPTS_PER_USER = 5  # Por hora
    ACCOUNT_LOCKOUT_DURATION = 30  # 30 minutos
    
    # Logs de auditoria obrigatórios
    ENABLE_AUDIT_LOGGING = True
    AUDIT_LOG_RETENTION_DAYS = 2555  # 7 anos para compliance
    
    # Validação de senha mais rigorosa
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_EXPIRY_DAYS = 60  # 60 dias em produção

# Mapeamento de configurações por ambiente
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retorna a configuração baseada na variável de ambiente FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])

# ==================== CONFIGURAÇÕES ESPECÍFICAS DO SISTEMA ====================

# Mapeamento de tipos de usuário para roles (migração)
USER_TYPE_TO_ROLE_MAPPING = {
    'admin': 'SUPER_ADMIN',
    'comprador': 'COMPRADOR_SENIOR',
    'requisitante': 'REQUISITANTE_SENIOR',
    'fornecedor': 'FORNECEDOR_BASICO'
}

# Mapeamento de roles para dashboards
ROLE_DASHBOARD_MAPPING = {
    'SUPER_ADMIN': '/admin/dashboard',
    'ADMIN_COMPRADOR': '/dashboard-comprador-funcional.html',
    'ADMIN_REQUISITANTE': '/dashboard-requisitante-integrado.html',
    'ADMIN_FORNECEDOR': '/dashboard-fornecedor-funcional.html',
    'COMPRADOR_SENIOR': '/dashboard-comprador-funcional.html',
    'COMPRADOR_JUNIOR': '/dashboard-comprador-analise-tecnica.html',
    'REQUISITANTE_SENIOR': '/dashboard-requisitante-integrado.html',
    'REQUISITANTE_JUNIOR': '/dashboard-requisitante-funcional.html',
    'FORNECEDOR_PREMIUM': '/dashboard-fornecedor-funcional.html',
    'FORNECEDOR_BASICO': '/dashboard-fornecedor-funcional.html'
}

# Permissões por módulo
MODULE_PERMISSIONS = {
    'dashboard_comprador': [
        'dashboard_comprador.access',
        'processos.read',
        'propostas.read',
        'propostas.evaluate'
    ],
    'dashboard_requisitante': [
        'dashboard_requisitante.access',
        'processos.create',
        'processos.read',
        'processos.update',
        'tr.create',
        'tr.update'
    ],
    'dashboard_fornecedor': [
        'dashboard_fornecedor.access',
        'processos.read',
        'propostas.create',
        'propostas.read',
        'propostas.update'
    ],
    'admin': [
        'usuarios.manage',
        'auditoria.read',
        'sistema.config'
    ]
}

# Configurações de integração com IA (Azure)
AZURE_AI_CONFIG = {
    'enabled': bool(os.environ.get('AZURE_OPENAI_ENDPOINT')),
    'endpoint': os.environ.get('AZURE_OPENAI_ENDPOINT'),
    'key': os.environ.get('AZURE_OPENAI_KEY'),
    'version': os.environ.get('AZURE_OPENAI_VERSION', '2023-05-15'),
    'deployment_name': os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'gpt-35-turbo'),
    'max_tokens': int(os.environ.get('AZURE_AI_MAX_TOKENS', 1000)),
    'temperature': float(os.environ.get('AZURE_AI_TEMPERATURE', 0.7))
}

# Configurações de backup automático
BACKUP_CONFIG = {
    'enabled': os.environ.get('ENABLE_AUTO_BACKUP', 'True').lower() == 'true',
    'frequency': os.environ.get('BACKUP_FREQUENCY', 'daily'),  # daily, weekly, monthly
    'retention_days': int(os.environ.get('BACKUP_RETENTION_DAYS', 30)),
    'storage_path': os.environ.get('BACKUP_STORAGE_PATH', 'backups/'),
    'include_uploads': os.environ.get('BACKUP_INCLUDE_UPLOADS', 'True').lower() == 'true'
}

# Configurações de monitoramento
MONITORING_CONFIG = {
    'enabled': os.environ.get('ENABLE_MONITORING', 'True').lower() == 'true',
    'metrics_endpoint': os.environ.get('METRICS_ENDPOINT', '/metrics'),
    'health_endpoint': os.environ.get('HEALTH_ENDPOINT', '/health'),
    'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
    'log_format': os.environ.get('LOG_FORMAT', 'json')  # json or text
}

# ==================== VALIDAÇÃO DE CONFIGURAÇÃO ====================

def validate_config(config_obj):
    """Valida se todas as configurações necessárias estão presentes"""
    required_vars = [
        'SECRET_KEY',
        'JWT_SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(config_obj, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Configurações obrigatórias não encontradas: {', '.join(missing_vars)}")
    
    # Validar configurações de segurança
    if config_obj.PASSWORD_MIN_LENGTH < 8:
        raise ValueError("PASSWORD_MIN_LENGTH deve ser pelo menos 8")
    
    if config_obj.JWT_ACCESS_TOKEN_EXPIRES.total_seconds() > 3600:  # 1 hora
        print("AVISO: JWT_ACCESS_TOKEN_EXPIRES é muito longo para produção")
    
    return True

# ==================== EXEMPLO DE USO ====================

if __name__ == '__main__':
    # Exemplo de como usar as configurações
    config_class = get_config()
    print(f"Configuração carregada: {config_class.__name__}")
    
    # Validar configuração
    try:
        validate_config(config_class)
        print("✓ Configuração válida")
    except ValueError as e:
        print(f"✗ Erro na configuração: {e}")
    
    # Mostrar algumas configurações importantes
    print(f"JWT Access Token Expires: {config_class.JWT_ACCESS_TOKEN_EXPIRES}")
    print(f"Max Login Attempts per IP: {config_class.MAX_LOGIN_ATTEMPTS_PER_IP}")
    print(f"Password Min Length: {config_class.PASSWORD_MIN_LENGTH}")
    print(f"Audit Logging Enabled: {config_class.ENABLE_AUDIT_LOGGING}")
    print(f"2FA Enabled: {config_class.ENABLE_2FA}")
