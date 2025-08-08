#!/usr/bin/env python3
"""
Middleware de Segurança - Sistema de Propostas
Implementa headers de segurança, rate limiting e outras proteções
"""

from flask import request, jsonify, g, current_app
from functools import wraps
import time
import logging
from datetime import datetime, timedelta
import hashlib
import hmac
from collections import defaultdict
import ipaddress

from secure_config import SECURITY_HEADERS, MONITORING

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Middleware de segurança para a aplicação"""
    
    def __init__(self, app=None):
        self.app = app
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = defaultdict(datetime)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o middleware com a aplicação Flask"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown)
    
    def before_request(self):
        """Executado antes de cada requisição"""
        # Registrar início da requisição
        g.start_time = time.time()
        g.request_id = self.generate_request_id()
        
        # Verificar IP bloqueado
        client_ip = self.get_client_ip()
        if self.is_ip_blocked(client_ip):
            logger.warning(f"Requisição bloqueada de IP: {client_ip}")
            return jsonify({
                'success': False,
                'error': 'IP bloqueado',
                'message': 'Seu IP foi temporariamente bloqueado devido a atividade suspeita'
            }), 429
        
        # Verificar rate limiting básico
        if self.check_rate_limit(client_ip):
            self.record_failed_attempt(client_ip)
            return jsonify({
                'success': False,
                'error': 'Rate limit excedido',
                'message': 'Muitas requisições. Tente novamente mais tarde.'
            }), 429
        
        # Validar headers de segurança
        if not self.validate_security_headers():
            logger.warning(f"Headers de segurança inválidos de {client_ip}")
            return jsonify({
                'success': False,
                'error': 'Headers inválidos',
                'message': 'Headers de requisição inválidos'
            }), 400
        
        # Log da requisição
        logger.info(f"[{g.request_id}] {request.method} {request.path} de {client_ip}")
    
    def after_request(self, response):
        """Executado após cada requisição"""
        # Adicionar headers de segurança
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Adicionar header de request ID
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        
        # Calcular tempo de resposta
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        
        # Log da resposta
        client_ip = self.get_client_ip()
        status_code = response.status_code
        
        if status_code >= 400:
            logger.warning(f"[{g.request_id}] Resposta {status_code} para {client_ip}")
        else:
            logger.info(f"[{g.request_id}] Resposta {status_code} para {client_ip}")
        
        # Detectar atividade suspeita
        if status_code == 401:  # Não autorizado
            self.record_failed_attempt(client_ip, 'auth_failed')
        elif status_code == 403:  # Proibido
            self.record_failed_attempt(client_ip, 'access_denied')
        elif status_code >= 500:  # Erro do servidor
            logger.error(f"[{g.request_id}] Erro interno: {status_code}")
        
        return response
    
    def teardown(self, exception):
        """Executado no final de cada requisição"""
        if exception:
            logger.error(f"[{getattr(g, 'request_id', 'unknown')}] Exceção: {exception}")
    
    def get_client_ip(self):
        """Obtém o IP real do cliente"""
        # Verificar headers de proxy
        if request.headers.get('X-Forwarded-For'):
            # Pegar o primeiro IP da lista (cliente original)
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr
    
    def generate_request_id(self):
        """Gera um ID único para a requisição"""
        timestamp = str(int(time.time() * 1000))
        client_ip = self.get_client_ip()
        data = f"{timestamp}-{client_ip}-{request.method}-{request.path}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def is_ip_blocked(self, ip):
        """Verifica se um IP está bloqueado"""
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            if datetime.now() < block_time:
                return True
            else:
                # Remover bloqueio expirado
                del self.blocked_ips[ip]
        return False
    
    def block_ip(self, ip, duration_minutes=15):
        """Bloqueia um IP por um período determinado"""
        block_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.blocked_ips[ip] = block_until
        logger.warning(f"IP {ip} bloqueado até {block_until}")
    
    def record_failed_attempt(self, ip, attempt_type='general'):
        """Registra uma tentativa falhada"""
        now = datetime.now()
        
        # Limpar tentativas antigas (últimos 15 minutos)
        cutoff = now - timedelta(minutes=15)
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip] 
            if attempt['time'] > cutoff
        ]
        
        # Adicionar nova tentativa
        self.failed_attempts[ip].append({
            'time': now,
            'type': attempt_type
        })
        
        # Verificar se deve bloquear
        if len(self.failed_attempts[ip]) >= MONITORING['max_failed_attempts']:
            self.block_ip(ip, MONITORING['lockout_duration'] // 60)
            logger.warning(f"IP {ip} bloqueado após {len(self.failed_attempts[ip])} tentativas falhadas")
    
    def check_rate_limit(self, ip):
        """Verifica rate limiting básico"""
        # Implementação simples - em produção usar Redis
        now = time.time()
        window = 60  # 1 minuto
        max_requests = 60  # 60 requisições por minuto
        
        # Esta é uma implementação básica - em produção usar Flask-Limiter com Redis
        return False  # Por enquanto, não bloquear
    
    def validate_security_headers(self):
        """Valida headers de segurança da requisição"""
        # Verificar User-Agent suspeito
        user_agent = request.headers.get('User-Agent', '')
        suspicious_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            'burp', 'w3af', 'acunetix', 'nessus'
        ]
        
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            logger.warning(f"User-Agent suspeito detectado: {user_agent}")
            return False
        
        # Verificar Content-Type para requisições POST/PUT
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('Content-Type', '')
            if not content_type.startswith(('application/json', 'multipart/form-data')):
                logger.warning(f"Content-Type inválido: {content_type}")
                return False
        
        return True
    
    def is_private_ip(self, ip):
        """Verifica se um IP é privado"""
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False

def require_https(f):
    """Decorator para exigir HTTPS em produção"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get('FLASK_ENV') == 'production':
            if not request.is_secure:
                return jsonify({
                    'success': False,
                    'error': 'HTTPS obrigatório',
                    'message': 'Esta operação requer conexão segura (HTTPS)'
                }), 400
        return f(*args, **kwargs)
    return decorated_function

def validate_json_input(required_fields=None):
    """Decorator para validar entrada JSON"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'JSON obrigatório',
                    'message': 'Content-Type deve ser application/json'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido',
                    'message': 'Corpo da requisição deve conter JSON válido'
                }), 400
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': 'Campos obrigatórios',
                        'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(data):
    """Sanitiza dados de entrada"""
    if isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        # Remover caracteres perigosos
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            data = data.replace(char, '')
        return data.strip()
    else:
        return data

def log_security_event(event_type, details, user_id=None, ip_address=None):
    """Registra eventos de segurança"""
    if not ip_address:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'details': details,
        'user_id': user_id,
        'ip_address': ip_address,
        'user_agent': request.headers.get('User-Agent', ''),
        'request_id': getattr(g, 'request_id', 'unknown')
    }
    
    # Em produção, enviar para sistema de monitoramento
    logger.warning(f"SECURITY_EVENT: {log_entry}")

class CSRFProtection:
    """Proteção CSRF customizada"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa proteção CSRF"""
        app.before_request(self.check_csrf)
    
    def check_csrf(self):
        """Verifica token CSRF para requisições que modificam dados"""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Pular verificação para APIs com autenticação JWT
            if request.path.startswith('/api/'):
                return
            
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not csrf_token or not self.validate_csrf_token(csrf_token):
                return jsonify({
                    'success': False,
                    'error': 'Token CSRF inválido',
                    'message': 'Token CSRF ausente ou inválido'
                }), 403
    
    def validate_csrf_token(self, token):
        """Valida token CSRF"""
        # Implementação básica - em produção usar Flask-WTF
        secret = current_app.config.get('WTF_CSRF_SECRET_KEY')
        if not secret:
            return True  # Se não configurado, pular validação
        
        # Validação simples - em produção usar implementação mais robusta
        expected = hmac.new(
            secret.encode(),
            request.session.get('csrf_token', '').encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(token, expected)

def init_security_middleware(app):
    """Inicializa todos os middlewares de segurança"""
    # Middleware principal
    SecurityMiddleware(app)
    
    # Proteção CSRF
    CSRFProtection(app)
    
    # Configurar logging de segurança
    security_logger = logging.getLogger('security')
    security_handler = logging.FileHandler('security.log')
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    logger.info("Middleware de segurança inicializado")

