#!/usr/bin/env python3
"""
Modelos de Banco de Dados - Sistema de Propostas
Implementação SQLAlchemy para substituir dados em memória
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # admin, comprador, requisitante, fornecedor, auditor
    nivel_acesso = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    
    # Relacionamentos
    processos_criados = db.relationship('Processo', backref='criador', lazy=True, foreign_keys='Processo.criado_por')
    propostas = db.relationship('Proposta', backref='fornecedor', lazy=True)
    
    def set_senha(self, senha):
        """Define senha com hash seguro"""
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        """Verifica senha contra hash"""
        return check_password_hash(self.senha_hash, senha)
    
    def to_dict(self):
        """Converte para dicionário (compatibilidade com código atual)"""
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
    prazo_formatado = db.Column(db.String(20))
    status_calculado = db.Column(db.String(20))
    fornecedores_convidados = db.Column(db.Text)  # JSON array
    
    # Relacionamentos
    propostas = db.relationship('Proposta', backref='processo', lazy=True, cascade='all, delete-orphan')
    
    def set_fornecedores_convidados(self, fornecedores_list):
        """Define lista de fornecedores convidados"""
        self.fornecedores_convidados = json.dumps(fornecedores_list)
    
    def get_fornecedores_convidados(self):
        """Retorna lista de fornecedores convidados"""
        if self.fornecedores_convidados:
            return json.loads(self.fornecedores_convidados)
        return []
    
    def calcular_status(self):
        """Calcula status baseado no prazo"""
        if self.prazo < datetime.now():
            self.status_calculado = 'encerrado'
        else:
            dias_restantes = (self.prazo - datetime.now()).days
            if dias_restantes <= 5:
                self.status_calculado = 'urgente'
            else:
                self.status_calculado = 'ativo'
        return self.status_calculado
    
    def to_dict(self):
        """Converte para dicionário (compatibilidade com código atual)"""
        return {
            'id': self.id,
            'numero': self.numero,
            'objeto': self.objeto,
            'modalidade': self.modalidade,
            'prazo': self.prazo.isoformat() if self.prazo else None,
            'status': self.status,
            'criadoPor': self.criado_por,
            'dataCadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'prazo_formatado': self.prazo_formatado,
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
    
    # Dados técnicos (JSON)
    dados_tecnicos = db.Column(db.Text)  # JSON object
    dados_comerciais = db.Column(db.Text)  # JSON object
    
    def set_dados_tecnicos(self, dados_dict):
        """Define dados técnicos como JSON"""
        self.dados_tecnicos = json.dumps(dados_dict)
    
    def get_dados_tecnicos(self):
        """Retorna dados técnicos como dict"""
        if self.dados_tecnicos:
            return json.loads(self.dados_tecnicos)
        return {}
    
    def set_dados_comerciais(self, dados_dict):
        """Define dados comerciais como JSON"""
        self.dados_comerciais = json.dumps(dados_dict)
    
    def get_dados_comerciais(self):
        """Retorna dados comerciais como dict"""
        if self.dados_comerciais:
            return json.loads(self.dados_comerciais)
        return {}
    
    def to_dict(self):
        """Converte para dicionário (compatibilidade com código atual)"""
        return {
            'id': self.id,
            'protocolo': self.protocolo,
            'processo': self.processo_id,
            'empresa': self.empresa,
            'cnpj': self.cnpj,
            'data': self.data_envio.isoformat() if self.data_envio else None,
            'valorTotal': str(self.valor_total),
            'validadeProposta': self.validade_proposta,
            'dados': self.get_dados_tecnicos(),
            'tecnica': self.get_dados_tecnicos(),
            'comercial': self.get_dados_comerciais()
        }

class Notificacao(db.Model):
    __tablename__ = 'notificacoes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.String(50), db.ForeignKey('usuarios.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default='info')  # info, warning, error, success
    lida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    usuario = db.relationship('Usuario', backref='notificacoes')
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'tipo': self.tipo,
            'lida': self.lida,
            'dataCriacao': self.data_criacao.isoformat() if self.data_criacao else None
        }

class LogAuditoria(db.Model):
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.String(50), db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(100), nullable=False)
    recurso = db.Column(db.String(100), nullable=False)  # processo, proposta, usuario
    recurso_id = db.Column(db.String(50))
    detalhes = db.Column(db.Text)  # JSON com detalhes da ação
    ip_origem = db.Column(db.String(45))
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    usuario = db.relationship('Usuario', backref='logs_auditoria')
    
    def set_detalhes(self, detalhes_dict):
        """Define detalhes como JSON"""
        self.detalhes = json.dumps(detalhes_dict)
    
    def get_detalhes(self):
        """Retorna detalhes como dict"""
        if self.detalhes:
            return json.loads(self.detalhes)
        return {}
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'usuario': self.usuario.nome if self.usuario else 'Sistema',
            'acao': self.acao,
            'recurso': self.recurso,
            'recurso_id': self.recurso_id,
            'detalhes': self.get_detalhes(),
            'ip_origem': self.ip_origem,
            'data_acao': self.data_acao.isoformat() if self.data_acao else None
        }

def init_db(app):
    """Inicializa o banco de dados"""
    db.init_app(app)
    
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se já existem dados
        if Usuario.query.count() == 0:
            popular_dados_iniciais()

def popular_dados_iniciais():
    """Popula o banco com dados iniciais (migração dos dados hardcoded)"""
    
    # Usuários iniciais
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
            'criado_por': 'requisitante_001',
            'fornecedores_convidados': ['forn_001', 'forn_002']
        },
        {
            'id': 'proc_002',
            'numero': 'LIC-2025-002',
            'objeto': 'Reforma e Ampliação do Centro de Saúde',
            'modalidade': 'Tomada de Preços',
            'prazo': datetime(2025, 8, 20, 16, 0),
            'criado_por': 'requisitante_001',
            'fornecedores_convidados': ['forn_001']
        },
        {
            'id': 'proc_003',
            'numero': 'LIC-2025-003',
            'objeto': 'Pavimentação Asfáltica de Vias Urbanas',
            'modalidade': 'Concorrência',
            'prazo': datetime(2025, 8, 25, 10, 0),
            'criado_por': 'requisitante_001',
            'fornecedores_convidados': ['forn_002', 'forn_003']
        }
    ]
    
    for processo_data in processos_iniciais:
        processo = Processo(
            id=processo_data['id'],
            numero=processo_data['numero'],
            objeto=processo_data['objeto'],
            modalidade=processo_data['modalidade'],
            prazo=processo_data['prazo'],
            criado_por=processo_data['criado_por']
        )
        processo.set_fornecedores_convidados(processo_data['fornecedores_convidados'])
        db.session.add(processo)
    
    # Commit das alterações
    try:
        db.session.commit()
        print("✅ Dados iniciais populados com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao popular dados iniciais: {e}")

