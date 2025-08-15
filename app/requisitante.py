from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .roles import require_roles
from .models import TR, AuditLog
from .resp_defaults import default_responsibility_matrix
from . import db

bp = Blueprint("requisitante", __name__)

@bp.post("/tr")
@jwt_required()
@require_roles("REQUISITANTE", "ADMIN")
def create_tr():
    data = request.get_json(force=True)
    items = data.get("items") or []
    status = data.get("status") or "SUBMITTED"
    if status == "SUBMITTED":
        required_when_submit = ["epi_epc", "exames_admissionais", "instalacoes_sanitarias", "sinalizacao_seg", "energia_eletrica"]
        matrix = data.get("responsibility_matrix") or default_responsibility_matrix()
        index = {r["key"]: r for r in matrix}
        faltando = [k for k in required_when_submit
                    if not index.get(k)
                    or index[k].get("aplicavel") is None
                    or (index[k].get("aplicavel") and not index[k].get("responsavel"))]
        if faltando:
            return jsonify({"erro": "responsabilidade_incompleta", "campos": faltando}), 400
    tr = TR(
        title=data.get("title"),
        description=data.get("description"),
        items=items,
        created_by=get_jwt_identity(),
        status=status,
        responsibility_matrix=data.get("responsibility_matrix") or default_responsibility_matrix()
    )
    db.session.add(tr); db.session.add(AuditLog(user_id=get_jwt_identity(), action="tr_create", entity="TR", entity_id=None))
    db.session.commit()
    return jsonify({"ok": True, "tr_id": tr.id}), 201

@bp.get("/tr")
@jwt_required()
@require_roles("REQUISITANTE", "ADMIN")
def list_tr_mine():
    uid = get_jwt_identity()
    rows = TR.query.filter_by(created_by=uid).order_by(TR.id.desc()).all()
    return jsonify([{"id": r.id, "title": r.title, "status": r.status} for r in rows])
