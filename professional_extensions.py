#!/usr/bin/env python3
"""
Extensões Flask - Sistema de Propostas
Centraliza a criação de todas as extensões
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_caching import Cache

# Criar instâncias das extensões
db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()

# Configurações padrão do limiter
limiter._default_limits = ["200 per day", "50 per hour"]