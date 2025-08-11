#!/usr/bin/env python3
"""
Modelos SQLAlchemy Adaptados para o Sistema de Propostas Existente
Versão RBAC - Compatível com estrutura atual
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import re
from typing import List, Optional

db = SQLAlchemy()

# ==================== TABELAS DE ASSOCIAÇÃO ====================

# Tabela de associação usuário-roles (many-to-many)
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('assigned_by', db.Integer, db.ForeignKey('usuario.id')),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow),
    db.Column('active', db.Boolean, default=True)
)

# Tabela de associação role-permissions (many-to-many)
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True),
    db.Column('granted_by', db.Integer, db.ForeignKey('usuario.id')),
    db.Column('granted_at', db.DateTime, default=datetime.utcnow)
)

# ==================== MODELO USUARIO APRIMORADO ====================

class Usuario(db.Model):
    """Modelo de usuário com funcionalidades RBAC aprimoradas"""
    
    __tablename__ = 'usuario'
    
    # Campos existentes (mantidos para compatibilidade)
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50))  # Mantido para compatibilidade
    nivel_acesso = db.Column(db.Integer, default=1)  # Mantido para compatibilidade
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    ultimo_ip = db.Column(db.String(45))
    
    # Novos campos para segurança aprimorada
    bloqueado = db.Column(db.Boolean, default=False)
    tentativas_login = db.Column(db.Integer, default=0)
    bloqueado_ate = db.Column(db.DateTime)
    senha_criada_em = db.Column(db.DateTime, default=datetime.utcnow)
    senha_expira_em = db.Column(db.DateTime)
    historico_senhas = db.Column(db.Text)  # JSON com últimas 5 senhas
    token_2fa = db.Column(db.String(32))
    ativo_2fa = db.Column(db.Boolean, default=False)
    
    # Relacionamentos RBAC
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                           backref=db.backref('users', lazy=True))
    
    # Relacionamentos existentes (mantidos)
    processos_criados = db.relationship('Processo', backref='criador', lazy=True,
                                       foreign_keys='Processo.criado_por')
    propostas = db.relationship('Proposta', backref='fornecedor', lazy=True,
                               foreign_keys='Proposta.fornecedor_id')
    
    def __init__(self, **kwargs):
        super(Usuario, self).__init__(**kwargs)
        if not self.senha_expira_em:
            self.senha_expira_em = datetime.utcnow() + timedelta(days=90)
        if not self.historico_senhas:
            self.historico_senhas = '[]'
    
    def set_senha(self, senha: str) -> None:
        """Define nova senha com validações de segurança"""
        # Validar força da senha
        self._validar_forca_senha(senha)
        
        # Verificar se não é uma senha já utilizada
        if self._senha_ja_utilizada(senha):
            raise ValueError("Esta senha já foi utilizada recentemente. Escolha uma senha diferente.")
        
        # Gerar hash da nova senha
        novo_hash = generate_password_hash(senha)
        
        # Atualizar histórico de senhas
        historico = json.loads(self.historico_senhas or '[]')
        if self.senha_hash:  # Se já tem senha anterior
            historico.append(self.senha_hash)
        
        # Manter apenas as últimas 5 senhas
        if len(historico) > 5:
            historico = historico[-5:]
        
        # Atualizar campos
        self.senha_hash = novo_hash
        self.historico_senhas = json.dumps(historico)
        self.senha_criada_em = datetime.utcnow()
        self.senha_expira_em = datetime.utcnow() + timedelta(days=90)
        self.tentativas_login = 0  # Reset tentativas ao alterar senha
        self.bloqueado = False
        self.bloqueado_ate = None
    
    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha fornecida está correta"""
        return check_password_hash(self.senha_hash, senha)
    
    def _validar_forca_senha(self, senha: str) -> None:
        """Valida se a senha atende aos critérios de segurança"""
        erros = []
        
        if len(senha) < 8:
            erros.append("A senha deve ter pelo menos 8 caracteres")
        
        if not re.search(r'[A-Z]', senha):
            erros.append("A senha deve conter pelo menos uma letra maiúscula")
        
        if not re.search(r'[a-z]', senha):
            erros.append("A senha deve conter pelo menos uma letra minúscula")
        
        if not re.search(r'\d', senha):
            erros.append("A senha deve conter pelo menos um número")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
            erros.append("A senha deve conter pelo menos um símbolo especial")
        
        # Verificar se não contém informações pessoais
        if self.nome and self.nome.lower() in senha.lower():
            erros.append("A senha não pode conter seu nome")
        
        if self.email and self.email.split('@')[0].lower() in senha.lower():
            erros.append("A senha não pode conter seu email")
        
        if erros:
            raise ValueError(". ".join(erros))
    
    def _senha_ja_utilizada(self, senha: str) -> bool:
        """Verifica se a senha já foi utilizada recentemente"""
        if not self.historico_senhas:
            return False
        
        historico = json.loads(self.historico_senhas)
        for senha_antiga in historico:
            if check_password_hash(senha_antiga, senha):
                return True
        
        # Verificar também a senha atual
        if self.senha_hash and check_password_hash(self.senha_hash, senha):
            return True
        
        return False
    
    def senha_expirada(self) -> bool:
        """Verifica se a senha está expirada"""
        if not self.senha_expira_em:
            return False
        return datetime.utcnow() > self.senha_expira_em
    
    def esta_bloqueado(self) -> bool:
        """Verifica se o usuário está bloqueado"""
        if not self.bloqueado:
            return False
        
        if self.bloqueado_ate and datetime.utcnow() > self.bloqueado_ate:
            # Desbloqueio automático
            self.bloqueado = False
            self.bloqueado_ate = None
            self.tentativas_login = 0
            db.session.commit()
            return False
        
        return True
    
    def incrementar_tentativas_login(self) -> None:
        """Incrementa tentativas de login e bloqueia se necessário"""
        self.tentativas_login += 1
        
        # Bloqueio progressivo
        if self.tentativas_login >= 10:
            # 10+ tentativas: bloqueio por 24 horas
            self.bloqueado = True
            self.bloqueado_ate = datetime.utcnow() + timedelta(hours=24)
        elif self.tentativas_login >= 7:
            # 7-9 tentativas: bloqueio por 1 hora
            self.bloqueado = True
            self.bloqueado_ate = datetime.utcnow() + timedelta(hours=1)
        elif self.tentativas_login >= 5:
            # 5-6 tentativas: bloqueio por 15 minutos
            self.bloqueado = True
            self.bloqueado_ate = datetime.utcnow() + timedelta(minutes=15)
    
    def resetar_tentativas_login(self) -> None:
        """Reseta tentativas de login após sucesso"""
        self.tentativas_login = 0
        self.bloqueado = False
        self.bloqueado_ate = None
        self.ultimo_login = datetime.utcnow()
    
    # ==================== MÉTODOS RBAC ====================
    
    def add_role(self, role: 'Role') -> None:
        """Adiciona um role ao usuário"""
        if not self.has_role(role.name):
            self.roles.append(role)
    
    def remove_role(self, role: 'Role') -> None:
        """Remove um role do usuário"""
        if self.has_role(role.name):
            self.roles.remove(role)
    
    def has_role(self, role_name: str) -> bool:
        """Verifica se o usuário tem um role específico"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Verifica se o usuário tem uma permissão específica"""
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False
    
    def get_permissions(self) -> List[str]:
        """Retorna lista de todas as permissões do usuário"""
        permissions = set()
        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        return list(permissions)
    
    def get_primary_role(self) -> Optional['Role']:
        """Retorna o role principal do usuário (primeiro da lista)"""
        return self.roles[0] if self.roles else None
    
    def to_dict(self) -> dict:
        """Converte usuário para dicionário (compatível com sistema atual)"""
        primary_role = self.get_primary_role()
        
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,  # Mantido para compatibilidade
            'nivel_acesso': self.nivel_acesso,  # Mantido para compatibilidade
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
            'roles': [role.name for role in self.roles],
            'primary_role': primary_role.name if primary_role else None,
            'permissions': self.get_permissions(),
            'senha_expira_em': self.senha_expira_em.isoformat() if self.senha_expira_em else None,
            'bloqueado': self.esta_bloqueado()
        }
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

# ==================== MODELO ROLE ====================

class Role(db.Model):
    """Modelo de roles/papéis do sistema"""
    
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                 backref=db.backref('roles', lazy=True))
    
    def add_permission(self, permission: 'Permission') -> None:
        """Adiciona uma permissão ao role"""
        if not self.has_permission(permission.name):
            self.permissions.append(permission)
    
    def remove_permission(self, permission: 'Permission') -> None:
        """Remove uma permissão do role"""
        if self.has_permission(permission.name):
            self.permissions.remove(permission)
    
    def has_permission(self, permission_name: str) -> bool:
        """Verifica se o role tem uma permissão específica"""
        return any(perm.name == permission_name for perm in self.permissions)
    
    def to_dict(self) -> dict:
        """Converte role para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'active': self.active,
            'permissions': [perm.name for perm in self.permissions],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Role {self.name}>'

# ==================== MODELO PERMISSION ====================

class Permission(db.Model):
    """Modelo de permissões do sistema"""
    
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    module = db.Column(db.String(50), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Converte permissão para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'module': self.module,
            'action': self.action,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Permission {self.name}>'

# ==================== MODELO AUDIT LOG ====================

class AuditLog(db.Model):
    """Modelo para logs de auditoria"""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource = db.Column(db.String(50), index=True)
    resource_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    endpoint = db.Column(db.String(255))
    method = db.Column(db.String(10))
    success = db.Column(db.Boolean, default=True)
    details = db.Column(db.Text)  # JSON com detalhes adicionais
    
    # Relacionamento
    user = db.relationship('Usuario', backref='audit_logs')
    
    def to_dict(self) -> dict:
        """Converte log para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.nome if self.user else None,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'endpoint': self.endpoint,
            'method': self.method,
            'success': self.success,
            'details': json.loads(self.details) if self.details else None
        }
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'

# ==================== MODELO LOGIN ATTEMPT ====================

class LoginAttempt(db.Model):
    """Modelo para tentativas de login"""
    
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    email = db.Column(db.String(120), index=True)
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_agent = db.Column(db.Text)
    details = db.Column(db.Text)
    
    @classmethod
    def get_recent_attempts(cls, ip_address: str, minutes: int = 1) -> int:
        """Conta tentativas recentes por IP"""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.ip_address == ip_address,
            cls.timestamp >= since,
            cls.success == False
        ).count()
    
    @classmethod
    def get_recent_attempts_by_email(cls, email: str, minutes: int = 60) -> int:
        """Conta tentativas recentes por email"""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.email == email,
            cls.timestamp >= since,
            cls.success == False
        ).count()
    
    def to_dict(self) -> dict:
        """Converte tentativa para dicionário"""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'email': self.email,
            'success': self.success,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'details': self.details
        }
    
    def __repr__(self):
        return f'<LoginAttempt {self.ip_address} - {self.success}>'

# ==================== MODELOS EXISTENTES (MANTIDOS) ====================

class Processo(db.Model):
    """Modelo de processo licitatório (mantido para compatibilidade)"""
    
    __tablename__ = 'processo'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    objeto = db.Column(db.Text, nullable=False)
    modalidade = db.Column(db.String(50), default='pregao')
    status = db.Column(db.String(20), default='ativo')
    prazo = db.Column(db.DateTime)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    propostas = db.relationship('Proposta', backref='processo', lazy=True)
    
    def to_dict(self) -> dict:
        """Converte processo para dicionário"""
        return {
            'id': self.id,
            'numero': self.numero,
            'objeto': self.objeto,
            'modalidade': self.modalidade,
            'status': self.status,
            'prazo': self.prazo.isoformat() if self.prazo else None,
            'criado_por': self.criado_por,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'total_propostas': len(self.propostas)
        }
    
    def __repr__(self):
        return f'<Processo {self.numero}>'

class Proposta(db.Model):
    """Modelo de proposta (mantido para compatibilidade)"""
    
    __tablename__ = 'proposta'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processo.id'), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    prazo_entrega = db.Column(db.Integer)  # Em dias
    descricao_tecnica = db.Column(db.Text)
    status = db.Column(db.String(20), default='submetida')
    data_submissao = db.Column(db.DateTime, default=datetime.utcnow)
    avaliacao_tecnica = db.Column(db.Text)
    pontuacao = db.Column(db.Float)
    
    def to_dict(self) -> dict:
        """Converte proposta para dicionário"""
        return {
            'id': self.id,
            'processo_id': self.processo_id,
            'processo_numero': self.processo.numero if self.processo else None,
            'fornecedor_id': self.fornecedor_id,
            'fornecedor_nome': self.fornecedor.nome if self.fornecedor else None,
            'valor': float(self.valor) if self.valor else None,
            'prazo_entrega': self.prazo_entrega,
            'descricao_tecnica': self.descricao_tecnica,
            'status': self.status,
            'data_submissao': self.data_submissao.isoformat() if self.data_submissao else None,
            'pontuacao': self.pontuacao
        }
    
    def __repr__(self):
        return f'<Proposta {self.id} - Processo {self.processo_id}>'

# ==================== FUNÇÕES AUXILIARES ====================

def init_db():
    """Inicializa o banco de dados com as tabelas"""
    db.create_all()

def create_default_roles_and_permissions():
    """Cria roles e permissões padrão do sistema"""
    
    # Criar permissões padrão
    default_permissions = [
        # Permissões de Processos
        ('processos.create', 'processos', 'create', 'Criar novos processos licitatórios'),
        ('processos.read', 'processos', 'read', 'Visualizar processos licitatórios'),
        ('processos.update', 'processos', 'update', 'Atualizar processos licitatórios'),
        ('processos.delete', 'processos', 'delete', 'Excluir processos licitatórios'),
        ('processos.approve', 'processos', 'approve', 'Aprovar processos licitatórios'),
        
        # Permissões de Propostas
        ('propostas.create', 'propostas', 'create', 'Criar propostas'),
        ('propostas.read', 'propostas', 'read', 'Visualizar propostas'),
        ('propostas.update', 'propostas', 'update', 'Atualizar propostas próprias'),
        ('propostas.evaluate', 'propostas', 'evaluate', 'Avaliar propostas tecnicamente'),
        ('propostas.approve', 'propostas', 'approve', 'Aprovar propostas'),
        
        # Permissões de Dashboards
        ('dashboard_comprador.access', 'dashboard_comprador', 'access', 'Acessar dashboard do comprador'),
        ('dashboard_requisitante.access', 'dashboard_requisitante', 'access', 'Acessar dashboard do requisitante'),
        ('dashboard_fornecedor.access', 'dashboard_fornecedor', 'access', 'Acessar dashboard do fornecedor'),
        
        # Permissões Administrativas
        ('usuarios.manage', 'usuarios', 'manage', 'Gerenciar usuários'),
        ('auditoria.read', 'auditoria', 'read', 'Visualizar logs de auditoria'),
        ('sistema.config', 'sistema', 'config', 'Configurar sistema')
    ]
    
    for perm_name, module, action, description in default_permissions:
        if not Permission.query.filter_by(name=perm_name).first():
            permission = Permission(
                name=perm_name,
                module=module,
                action=action,
                description=description
            )
            db.session.add(permission)
    
    # Criar roles padrão
    default_roles = [
        ('SUPER_ADMIN', 'Administrador geral do sistema com acesso total'),
        ('ADMIN_COMPRADOR', 'Administrador do módulo comprador'),
        ('ADMIN_REQUISITANTE', 'Administrador do módulo requisitante'),
        ('COMPRADOR_SENIOR', 'Comprador sênior com permissões de aprovação'),
        ('COMPRADOR_JUNIOR', 'Comprador júnior com permissões limitadas'),
        ('REQUISITANTE_SENIOR', 'Requisitante sênior com permissões completas'),
        ('REQUISITANTE_JUNIOR', 'Requisitante júnior com permissões limitadas'),
        ('FORNECEDOR_PREMIUM', 'Fornecedor premium com acesso a processos especiais'),
        ('FORNECEDOR_BASICO', 'Fornecedor básico com acesso limitado')
    ]
    
    for role_name, description in default_roles:
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name, description=description)
            db.session.add(role)
    
    db.session.commit()
    print("Roles e permissões padrão criados com sucesso!")

if __name__ == '__main__':
    # Para testes
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        init_db()
        create_default_roles_and_permissions()
        print("Banco de dados inicializado com sucesso!")
