from . import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON, BYTEA
from argon2 import PasswordHasher

ph = PasswordHasher()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="FORNECEDOR")
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw):
        self.password_hash = ph.hash(raw)

    def verify_password(self, raw):
        try:
            return ph.verify(self.password_hash, raw)
        except Exception:
            return False

    def to_safe(self):
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role, "active": self.active}

class Invitation(db.Model):
    __tablename__ = "invitations"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), index=True, nullable=False)
    role = db.Column(db.String(32), nullable=False, default="FORNECEDOR")
    token_hash = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def used(self):
        return self.used_at is not None

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(128), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    data = db.Column(BYTEA, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    linked_type = db.Column(db.String(64))
    linked_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TR(db.Model):
    __tablename__ = "trs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    items = db.Column(JSON, nullable=False)
    status = db.Column(db.String(32), default="DRAFT", nullable=False)  # DRAFT/SUBMITTED/APPROVED
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    responsibility_matrix = db.Column(JSON, nullable=True)

class Process(db.Model):
    __tablename__ = "processes"
    id = db.Column(db.Integer, primary_key=True)
    tr_id = db.Column(db.Integer, db.ForeignKey("trs.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(32), default="OPEN", nullable=False)  # OPEN/INVITING/RECEIVING/CLOSED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SupplierInvite(db.Model):
    __tablename__ = "supplier_invites"
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    token_hash = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Proposal(db.Model):
    __tablename__ = "proposals"
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    tech = db.Column(JSON, nullable=False)
    commercial = db.Column(JSON, nullable=False)
    total_price = db.Column(db.Numeric(14,2), nullable=False, default=0)
    currency = db.Column(db.String(8), default="BRL")
    status = db.Column(db.String(32), default="SUBMITTED")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(64), nullable=False)
    entity = db.Column(db.String(64))
    entity_id = db.Column(db.Integer)
    meta = db.Column(JSON)
    at = db.Column(db.DateTime, default=datetime.utcnow)
