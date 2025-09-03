# -*- coding: utf-8 -*-
from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, CheckConstraint
from . import db

class Role(str, Enum):
    REQUISITANTE = "REQUISITANTE"
    COMPRADOR = "COMPRADOR"
    FORNECEDOR = "FORNECEDOR"


class ProcurementStatus(str, Enum):
    TR_PENDENTE = "TR_PENDENTE"        # Aguardando criação do TR pelo requisitante
    TR_CRIADO = "TR_CRIADO"            # TR foi criado mas não submetido
    TR_SUBMETIDO = "TR_SUBMETIDO"      # TR aguardando aprovação do comprador
    TR_APROVADO = "TR_APROVADO"        # TR aprovado, processo pode ser aberto
    TR_REJEITADO = "TR_REJEITADO"      # TR rejeitado, precisa correções
    ABERTO = "ABERTO"                  # Recebendo propostas
    ANALISE_TECNICA = "ANALISE_TECNICA"
    ANALISE_COMERCIAL = "ANALISE_COMERCIAL"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"
    

class TRStatus(str, Enum):
    RASCUNHO = "RASCUNHO"
    SUBMETIDO = "SUBMETIDO"
    EM_REVISAO = "EM_REVISAO"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"


class ProposalStatus(str, Enum):
    RASCUNHO = "RASCUNHO"
    ENVIADA = "ENVIADA"
    EM_ANALISE_TECNICA = "EM_ANALISE_TECNICA"
    APROVADA_TECNICAMENTE = "APROVADA_TECNICAMENTE"
    REJEITADA_TECNICAMENTE = "REJEITADA_TECNICAMENTE"
    COMERCIAL_ABERTA = "COMERCIAL_ABERTA"
    FINALIZADA = "FINALIZADA"


class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    cnpj = db.Column(db.String(20), unique=True)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)


class Procurement(db.Model):
    __tablename__ = "procurements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(ProcurementStatus), default=ProcurementStatus.TR_PENDENTE)
    org_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    orcamento_disponivel = db.Column(db.Numeric(18, 2))
    prazo_maximo_contratacao = db.Column(db.String(100))
    tr_origem_id = db.Column(db.Integer)
    
    # MUDANÇA IMPORTANTE: Adicionar campo requisitante_id
    requisitante_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    deadline_proposals = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    requisitante = relationship("User", foreign_keys=[requisitante_id], backref="procurements_as_requisitante")
    creator = relationship("User", foreign_keys=[created_by], backref="procurements_created")
    approver = relationship("User", foreign_keys=[approved_by], backref="procurements_approved")
    
    tr = relationship("TR", backref="procurement", uselist=False)
    proposals = relationship("Proposal", backref="procurement")
    invites = relationship("Invite", backref="procurement")


class TR(db.Model):
    __tablename__ = "tr_terms"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=True, unique=True)
    
    # Campos do TR
    objetivo = db.Column(db.Text)
    situacao_atual = db.Column(db.Text)
    descricao_servicos = db.Column(db.Text)
    local_horario_trabalhos = db.Column(db.Text)
    prazo_execucao = db.Column(db.Text)
    local_canteiro = db.Column(db.Text)
    atividades_preliminares = db.Column(db.Text)
    garantia = db.Column(db.Text)
    matriz_responsabilidades = db.Column(db.Text)
    descricoes_gerais = db.Column(db.Text)
    normas_observar = db.Column(db.Text)
    regras_responsabilidades = db.Column(db.Text)
    relacoes_contratada_fiscalizacao = db.Column(db.Text)
    sst = db.Column(db.Text)
    credenciamento_observacoes = db.Column(db.Text)
    anexos_info = db.Column(db.Text)
    
    # Campos para aprovação
    status = db.Column(db.Enum(TRStatus), default=TRStatus.RASCUNHO)
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approval_comments = db.Column(db.Text)
    revision_requested = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)  # ADICIONAR: Motivo da rejeição
    
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TRServiceItem(db.Model):
    __tablename__ = "tr_service_items"
    id = db.Column(db.Integer, primary_key=True)
    tr_id = db.Column(db.Integer, db.ForeignKey("tr_terms.id"), nullable=False, index=True)
    item_ordem = db.Column(db.Integer, nullable=False)
    codigo = db.Column(db.String(80))
    descricao = db.Column(db.Text, nullable=False)
    unid = db.Column(db.String(20), nullable=False)
    qtde = db.Column(db.Numeric(18, 3), nullable=False)
    
    tr = relationship('TR', backref='service_items')
    
    __table_args__ = (
        UniqueConstraint("tr_id", "item_ordem", name="uq_tr_item_ordem"),
    )


class Invite(db.Model):
    __tablename__ = "invites"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(64), nullable=False, unique=True)
    accepted = db.Column(db.Boolean, default=False)
    accepted_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Proposal(db.Model):
    __tablename__ = "proposals"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=False, index=True)
    supplier_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(ProposalStatus), default=ProposalStatus.RASCUNHO)
    
    # Proposta técnica
    technical_description = db.Column(db.Text)
    technical_submitted_at = db.Column(db.DateTime)
    
    # Parecer técnico do requisitante
    technical_review = db.Column(db.Text)
    technical_score = db.Column(db.Integer)  # 0-100
    technical_reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    technical_reviewed_at = db.Column(db.DateTime)
    
    # Proposta comercial
    commercial_submitted_at = db.Column(db.DateTime)
    payment_conditions = db.Column(db.Text)
    delivery_time = db.Column(db.String(100))
    warranty_terms = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    service_items = relationship("ProposalService", backref="proposal", cascade="all, delete-orphan")
    prices = relationship("ProposalPrice", backref="proposal", cascade="all, delete-orphan")
    supplier = relationship("User", foreign_keys=[supplier_user_id])
    
    __table_args__ = (
        UniqueConstraint("procurement_id", "supplier_user_id", name="uq_proposal_unique_supplier"),
    )


class ProposalService(db.Model):
    """Quantidades propostas pelo fornecedor"""
    __tablename__ = "proposal_service"
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), primary_key=True)
    service_item_id = db.Column(db.Integer, db.ForeignKey("tr_service_items.id"), primary_key=True)
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    technical_notes = db.Column(db.Text)  # Observações técnicas específicas do item


class ProposalPrice(db.Model):
    __tablename__ = "proposal_prices"
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), primary_key=True)
    service_item_id = db.Column(db.Integer, db.ForeignKey("tr_service_items.id"), primary_key=True)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False)
    
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="chk_price_nonneg"),
    )

class AuditLog(db.Model):
    """Log de auditoria para todas as ações importantes"""
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
