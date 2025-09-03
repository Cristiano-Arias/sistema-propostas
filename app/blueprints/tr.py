# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
from .. import db, socketio
from ..models import TR, TRServiceItem, Procurement, TRStatus, ProcurementStatus, AuditLog, Proposal, ProposalStatus

bp = Blueprint("tr", __name__)


@bp.post("/procurements/<int:proc_id>/tr")
def create_or_update_tr(proc_id: int):
    """Cria ou atualiza o TR com auto-save"""
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    proc = Procurement.query.get_or_404(proc_id)
    
    tr = TR.query.filter_by(procurement_id=proc_id).first()
    if not tr:
        tr = TR(procurement_id=proc_id, created_by=ident["user_id"])
        db.session.add(tr)
        action = "TR_CREATED"
    else:
        action = "TR_UPDATED"
    
    # Atualizar campos
    fields = [
        "objetivo", "situacao_atual", "descricao_servicos",
        "local_horario_trabalhos", "prazo_execucao", "local_canteiro",
        "atividades_preliminares", "garantia", "matriz_responsabilidades",
        "descricoes_gerais", "normas_observar", "regras_responsabilidades",
        "relacoes_contratada_fiscalizacao", "sst", "credenciamento_observacoes",
        "anexos_info"
    ]
    
    for field in fields:
        if field in data:
            setattr(tr, field, data[field])
    
    # Atualizar planilha de serviços se fornecida
    if "planilha_servico" in data and isinstance(data["planilha_servico"], list):
        # Remove itens antigos
        TRServiceItem.query.filter_by(tr_id=tr.id).delete()
        
        # Adiciona novos itens
        for idx, item in enumerate(data["planilha_servico"], start=1):
            service_item = TRServiceItem(
                tr_id=tr.id,
                item_ordem=item.get("item_ordem", idx),
                codigo=item.get("codigo", ""),
                descricao=item.get("descricao", ""),
                unid=item.get("unid", "UN"),
                qtde=item.get("qtde", 1)
            )
            db.session.add(service_item)
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action=action,
        entity_type="TR",
        entity_id=tr.id,
        details={"procurement_id": proc_id}
    )
    db.session.add(audit)
    
    db.session.commit()
    
    # Emitir evento real-time
    socketio.emit("tr.saved", {
        "procurement_id": proc_id,
        "tr_id": tr.id,
        "status": tr.status.value,
        "updated_by": ident["user_id"]
    }, to=f"proc:{proc_id}")
    
    return {
        "tr_id": tr.id,
        "status": tr.status.value,
        "message": "TR salvo com sucesso"
    }


@bp.post("/tr/<int:tr_id>/submit")
def submit_tr_for_approval(tr_id: int):
    """Submete TR para aprovação do comprador"""
    ident = get_jwt_identity()
    tr = TR.query.get_or_404(tr_id)
    
    if tr.status not in [TRStatus.RASCUNHO, TRStatus.REJEITADO]:
        return {"error": "TR não pode ser submetido neste status"}, 400
    
    # Validações básicas
    if not tr.objetivo or not tr.descricao_servicos:
        return {"error": "TR incompleto - objetivo e descrição são obrigatórios"}, 400
    
    if not tr.service_items:
        return {"error": "TR deve ter pelo menos um item de serviço"}, 400
    
    tr.status = TRStatus.SUBMETIDO
    tr.submitted_at = datetime.utcnow()
    
    # Atualizar status do processo
    proc = Procurement.query.get(tr.procurement_id)
    proc.status = ProcurementStatus.TR_PENDENTE
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="TR_SUBMITTED",
        entity_type="TR",
        entity_id=tr.id
    )
    db.session.add(audit)
    
    db.session.commit()
    
    # Notificar compradores em real-time
    socketio.emit("tr.submitted", {
        "procurement_id": tr.procurement_id,
        "tr_id": tr.id,
        "submitted_by": ident["user_id"],
        "title": proc.title
    }, to="role:COMPRADOR")
    
    return {
        "message": "TR submetido para aprovação",
        "tr_id": tr.id,
        "status": tr.status.value
    }


@bp.get("/tr/<int:proc_id>")
@require_role(["REQUISITANTE", "COMPRADOR", "FORNECEDOR"])
def get_tr_details(proc_id: int):
    """Obtém detalhes completos do TR baseado no procurement_id"""
    # Busca TR pelo procurement_id (não pelo tr.id)
    tr = TR.query.filter_by(procurement_id=proc_id).first()
    
    if not tr:
        return {"error": "TR não encontrado para este processo"}, 404
    
    ident = get_jwt_identity()
    
    # Fornecedores só podem ver TR aprovados
    if ident["role"] == "FORNECEDOR" and tr.status != TRStatus.APROVADO:
        return {"error": "TR não disponível"}, 403
    
    items = [{
        "id": item.id,
        "item_ordem": item.item_ordem,
        "codigo": item.codigo,
        "descricao": item.descricao,
        "unid": item.unid,
        "qtde": float(item.qtde)
    } for item in tr.service_items]
    
    return {
        "id": tr.id,
        "procurement_id": tr.procurement_id,
        "status": tr.status.value,
        "objetivo": tr.objetivo,
        "situacao_atual": tr.situacao_atual,
        "descricao_servicos": tr.descricao_servicos,
        "local_horario_trabalhos": tr.local_horario_trabalhos,
        "prazo_execucao": tr.prazo_execucao,
        "local_canteiro": tr.local_canteiro,
        "atividades_preliminares": tr.atividades_preliminares,
        "garantia": tr.garantia,
        "matriz_responsabilidades": tr.matriz_responsabilidades,
        "descricoes_gerais": tr.descricoes_gerais,
        "normas_observar": tr.normas_observar,
        "regras_responsabilidades": tr.regras_responsabilidades,
        "relacoes_contratada_fiscalizacao": tr.relacoes_contratada_fiscalizacao,
        "sst": tr.sst,
        "credenciamento_observacoes": tr.credenciamento_observacoes,
        "anexos_info": tr.anexos_info,
        "service_items": items,
        "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None,
        "approved_at": tr.approved_at.isoformat() if tr.approved_at else None,
        "approval_comments": tr.approval_comments
    }


@bp.post("/tr/<int:tr_id>/approve")
@require_role(["COMPRADOR"])
def approve_tr(tr_id: int):
    """Comprador aprova ou rejeita TR"""
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    tr = TR.query.get_or_404(tr_id)
    
    if tr.status != TRStatus.SUBMETIDO:
        return {"error": "TR não está aguardando aprovação"}, 400
    
    action = data.get("action")  # "approve" ou "reject"
    comments = data.get("comments", "")
    
    if action == "approve":
        tr.status = TRStatus.APROVADO
        tr.approved_at = datetime.utcnow()
        tr.approved_by = ident["user_id"]
        tr.approval_comments = comments
        
        # Atualizar processo
        proc = Procurement.query.get(tr.procurement_id)
        proc.status = ProcurementStatus.TR_APROVADO
        
        audit_action = "TR_APPROVED"
        message = "TR aprovado com sucesso"
        
    elif action == "reject":
        tr.status = TRStatus.REJEITADO
        tr.revision_requested = comments
        
        # Voltar processo para rascunho
        proc = Procurement.query.get(tr.procurement_id)
        proc.status = ProcurementStatus.RASCUNHO
        
        audit_action = "TR_REJECTED"
        message = "TR rejeitado - revisão solicitada"
        
    else:
        return {"error": "Ação inválida"}, 400
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action=audit_action,
        entity_type="TR",
        entity_id=tr.id,
        details={"comments": comments}
    )
    db.session.add(audit)
    
    db.session.commit()
    
    # Notificar requisitante
    socketio.emit("tr.approval_result", {
        "tr_id": tr.id,
        "procurement_id": tr.procurement_id,
        "approved": action == "approve",
        "comments": comments
    }, to=f"user:{tr.created_by}")
    
    return {
        "message": message,
        "tr_id": tr.id,
        "status": tr.status.value
    }


@bp.post("/tr/<int:tr_id>/technical-review")
def review_technical_proposal(tr_id: int):
    """Requisitante analisa proposta técnica"""
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    proposal_id = data.get("proposal_id")
    review = data.get("technical_review")
    score = data.get("technical_score", 0)
    approved = data.get("approved", False)
    
    proposal = Proposal.query.get_or_404(proposal_id)
    
    # Verificar se é o requisitante correto
    tr = TR.query.get_or_404(tr_id)
    if tr.created_by != ident["user_id"]:
        return {"error": "Apenas o requisitante original pode revisar"}, 403
    
    proposal.technical_review = review
    proposal.technical_score = score
    proposal.technical_reviewed_by = ident["user_id"]
    proposal.technical_reviewed_at = datetime.utcnow()
    
    if approved:
        proposal.status = ProposalStatus.APROVADA_TECNICAMENTE
    else:
        proposal.status = ProposalStatus.REJEITADA_TECNICAMENTE
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="TECHNICAL_REVIEW",
        entity_type="Proposal",
        entity_id=proposal.id,
        details={
            "score": score,
            "approved": approved
        }
    )
    db.session.add(audit)
    
    db.session.commit()
    
    # Notificar comprador e fornecedor
    socketio.emit("proposal.technical_reviewed", {
        "proposal_id": proposal.id,
        "procurement_id": proposal.procurement_id,
        "approved": approved,
        "score": score
    }, to=f"proc:{proposal.procurement_id}")
    
    return {
        "message": "Parecer técnico registrado",
        "proposal_id": proposal.id,
        "approved": approved
    }
