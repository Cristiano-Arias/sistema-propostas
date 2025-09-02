# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from .. import db, socketio
from ..models import TR, TRServiceItem, Procurement
from .procurements import require_role

bp = Blueprint("tr", __name__)


@bp.post("/procurements/<int:proc_id>/tr")
@require_role(["REQUISITANTE"])
def create_tr(proc_id: int):
    """Cria/edita o TR e a planilha de serviços baseline."""
    data = request.get_json() or {}
    ident = get_jwt_identity()

    tr = TR.query.filter_by(procurement_id=proc_id).first()
    if not tr:
        tr = TR(procurement_id=proc_id, created_by=ident["user_id"])
        db.session.add(tr)
        db.session.commit()

    # Mapear campos principais (Escopo & Execução, etc.)
    fields = [
        "objetivo", "situacao_atual", "descricao_servicos",
        "local_horario_trabalhos", "prazo_execucao", "local_canteiro",
        "atividades_preliminares", "garantia", "matriz_responsabilidades",
        "descricoes_gerais", "normas_observar", "regras_responsabilidades",
        "relacoes_contratada_fiscalizacao", "sst", "credenciamento_observacoes",
        "anexos_info"
    ]
    for f in fields:
        if f in data:
            setattr(tr, f, data.get(f))

    # Baseline da tabela de serviços
    if "planilha_servico" in data and isinstance(data["planilha_servico"], list):
        # zera e recria baseline (MVP)
        TRServiceItem.query.filter_by(tr_id=tr.id).delete()
        for idx, it in enumerate(data["planilha_servico"], start=1):
            item = TRServiceItem(
                tr_id=tr.id,
                item_ordem=it.get("item_ordem", idx),
                codigo=it.get("codigo"),
                descricao=it.get("descricao", ""),
                unid=it.get("unid", ""),
                qtde=it.get("qtde", 0),
            )
            db.session.add(item)

    db.session.commit()
    socketio.emit("tr.saved", {"procurement_id": proc_id, "tr_id": tr.id}, to=f"proc:{proc_id}")
    return {"tr_id": tr.id}


@bp.post("/tr/<int:tr_id>/submit")
@require_role(["REQUISITANTE"])
def submit_tr(tr_id: int):
    tr = TR.query.get_or_404(tr_id)
    tr.status = "SUBMETIDO"
    db.session.commit()
    socketio.emit("tr.submitted", {"procurement_id": tr.procurement_id, "tr_id": tr.id}, to=f"proc:{tr.procurement_id}")
    return {"message": "TR submetido para aprovacao"}
