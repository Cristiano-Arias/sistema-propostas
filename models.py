from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.LargeBinary, nullable=False)
    perfil = db.Column(db.String(20), nullable=False)  # ADMIN/REQUISITANTE/COMPRADOR/FORNECEDOR
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    force_password_change = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Esboços simples para continuidade do seu fluxo
class TR(db.Model):
    __tablename__ = "trs"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Processo(db.Model):
    __tablename__ = "processos"
    id = db.Column(db.Integer, primary_key=True)
    tr_id = db.Column(db.Integer, db.ForeignKey("trs.id"), nullable=False)
    status = db.Column(db.String(50), default="ABERTO", nullable=False)

class Proposta(db.Model):
    __tablename__ = "propostas"
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey("processos.id"), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    valor_total = db.Column(db.Numeric(12,2))
    criada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
