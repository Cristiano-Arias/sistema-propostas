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


class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Procurement(db.Model):
    __tablename__ = "procurements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(40), default="RASCUNHO")  # RASCUNHO|ABERTO|FECHADO
    org_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TR(db.Model):
    __tablename__ = "tr_terms"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=False)
    # TR sections (Escopo & Execução unificado + demais campos)
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

    status = db.Column(db.String(30), default="RASCUNHO")  # RASCUNHO|EM_APROVACAO|APROVADO|SUBMETIDO
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TRServiceItem(db.Model):
    __tablename__ = "tr_service_items"
    tr = relationship('TR', backref='service_items')
    id = db.Column(db.Integer, primary_key=True)
    tr_id = db.Column(db.Integer, db.ForeignKey("tr_terms.id"), nullable=False, index=True)
    item_ordem = db.Column(db.Integer, nullable=False)
    codigo = db.Column(db.String(80))
    descricao = db.Column(db.Text, nullable=False)
    unid = db.Column(db.String(20), nullable=False)
    qtde = db.Column(db.Numeric(18, 3), nullable=False)

    __table_args__ = (
        UniqueConstraint("tr_id", "item_ordem", name="uq_tr_item_ordem"),
    )


class Invite(db.Model):
    __tablename__ = "invites"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(64), nullable=False, unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Proposal(db.Model):
    __tablename__ = "proposals"
    id = db.Column(db.Integer, primary_key=True)
    procurement_id = db.Column(db.Integer, db.ForeignKey("procurements.id"), nullable=False, index=True)
    supplier_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(30), default="RASCUNHO")  # RASCUNHO|ENVIADA|AVALIACAO_TECNICA|COMERCIAL_ABERTA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("procurement_id", "supplier_user_id", name="uq_proposal_unique_supplier"),)


class ProposalService(db.Model):
    """Somente a quantidade pode mudar nos templates da proposta (regra de negócio)."""
    __tablename__ = "proposal_service"
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), primary_key=True)
    service_item_id = db.Column(db.Integer, db.ForeignKey("tr_service_items.id"), primary_key=True)
    qty = db.Column(db.Numeric(18, 3), nullable=False)


class ProposalPrice(db.Model):
    __tablename__ = "proposal_prices"
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), primary_key=True)
    service_item_id = db.Column(db.Integer, db.ForeignKey("tr_service_items.id"), primary_key=True)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="chk_price_nonneg"),
    )
