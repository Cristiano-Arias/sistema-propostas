#!/usr/bin/env python3
"""
Modelo de Usuário - Sistema de Propostas
Implementação profissional com SQLAlchemy
"""

from datetime import datetime
from extensions import db, bcrypt
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Usuario(db.Model):
    """Modelo de usuário do sistema"""
    
    __tablename__ = 'usuarios'
    
    # Campos principais
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # fornecedor, comprador, requisitante, admin
    
    # Campos de controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    email_verificado = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    
    # Campos específicos de fornecedor
    cnpj = db.Column(db.String(18), unique=True, sparse=True)
    razao_social = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    responsavel_tecnico = db.Column(db.String(100))
    crea = db.Column(db.String(50))
    
    # Relacionamentos
    processos_criados = db.relationship('Processo', back_populates='criador', lazy='dynamic')
    propostas = db.relationship('Proposta', back_populates='fornecedor', lazy='dynamic')
    notificacoes = db.relationship('Notificacao', back_populates='usuario', lazy='dynamic')
    logs_auditoria = db.relationship('LogAuditoria', back_populates='usuario', lazy='dynamic')
    termos_referencia = db.relationship('TermoReferencia', back_populates='usuario', lazy='dynamic')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    def definir_senha(self, senha):
        """Define a senha do usuário com hash bcrypt"""
        self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
    
    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        return bcrypt.check_password_hash(self.senha_hash, senha)
    
    def atualizar_ultimo_login(self):
        """Atualiza data/hora do último login"""
        self.ultimo_login = datetime.utcnow()
        db.session.commit()
    
    def ativar(self):
        """Ativa o usuário"""
        self.ativo = True
        db.session.commit()
    
    def desativar(self):
        """Desativa o usuário"""
        self.ativo = False
        db.session.commit()
    
    def verificar_email(self):
        """Marca email como verificado"""
        self.email_verificado = True
        db.session.commit()
    
    def tem_permissao(self, permissao):
        """Verifica se usuário tem determinada permissão"""
        permissoes = {
            'admin': ['*'],  # Admin tem todas as permissões
            'comprador': [
                'criar_processo',
                'editar_processo',
                'visualizar_propostas',
                'aprovar_tr',
                'convidar_fornecedores',
                'gerar_relatorios'
            ],
            'requisitante': [
                'criar_tr',
                'editar_tr',
                'visualizar_tr',
                'acompanhar_processo'
            ],
            'fornecedor': [
                'visualizar_processos_publicos',
                'enviar_proposta',
                'editar_proposta',
                'visualizar_propostas_proprias'
            ]
        }
        
        tipo_permissoes = permissoes.get(self.tipo, [])
        return '*' in tipo_permissoes or permissao in tipo_permissoes
    
    def to_dict(self, include_sensitive=False):
        """Converte o usuário para dicionário"""
        data = {
            'id': str(self.id),
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,
            'perfil': self.tipo,  # Compatibilidade
            'ativo': self.ativo,
            'email_verificado': self.email_verificado,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None
        }
        
        # Adicionar dados de fornecedor se aplicável
        if self.tipo == 'fornecedor':
            data.update({
                'cnpj': self.cnpj,
                'razao_social': self.razao_social,
                'telefone': self.telefone,
                'endereco': self.endereco,
                'cidade': self.cidade,
                'estado': self.estado,
                'cep': self.cep,
                'responsavel_tecnico': self.responsavel_tecnico,
                'crea': self.crea
            })
        
        return data
    
    @staticmethod
    def criar_usuario(dados):
        """Cria novo usuário com validações"""
        # Verificar se email já existe
        if Usuario.query.filter_by(email=dados['email'].lower()).first():
            raise ValueError('Email já cadastrado')
        
        # Verificar CNPJ para fornecedores
        if dados.get('tipo') == 'fornecedor' and dados.get('cnpj'):
            if Usuario.query.filter_by(cnpj=dados['cnpj']).first():
                raise ValueError('CNPJ já cadastrado')
        
        # Criar usuário
        usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'].lower(),
            tipo=dados['tipo']
        )
        
        # Definir senha
        usuario.definir_senha(dados['senha'])
        
        # Adicionar dados de fornecedor se aplicável
        if dados.get('tipo') == 'fornecedor':
            usuario.cnpj = dados.get('cnpj')
            usuario.razao_social = dados.get('razao_social')
            usuario.telefone = dados.get('telefone')
            usuario.endereco = dados.get('endereco')
            usuario.cidade = dados.get('cidade')
            usuario.estado = dados.get('estado')
            usuario.cep = dados.get('cep')
            usuario.responsavel_tecnico = dados.get('responsavel_tecnico')
            usuario.crea = dados.get('crea')
        
        db.session.add(usuario)
        db.session.commit()
        
        return usuario