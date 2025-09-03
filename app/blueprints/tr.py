# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from .. import db, socketio
from ..models import TR, TRServiceItem, Procurement, TRStatus, ProcurementStatus, Proposal, ProposalStatus, User, Role
from ..utils.auth import get_current_user

bp = Blueprint("tr", __name__)


@bp.post("/tr/create-independent")
@jwt_required()
def create_independent_tr():
    """Requisitante cria TR independente"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem criar TR"}, 403
    
    data = request.get_json() or {}
    
    # Validações básicas
    if not data.get('objetivo') or not data.get('descricao_servicos'):
        return {"error": "Objetivo e descrição dos serviços são obrigatórios"}, 400
    
    # Criar TR independente
    tr = TR(
        created_by=user.id,
        objetivo=data.get('objetivo'),
        situacao_atual=data.get('situacao_atual'),
        descricao_servicos=data.get('descricao_servicos'),
        local_horario_trabalhos=data.get('local_horario_trabalhos'),
        prazo_execucao=data.get('prazo_execucao'),
        local_canteiro=data.get('local_canteiro'),
        atividades_preliminares=data.get('atividades_preliminares'),
        garantia=data.get('garantia'),
        matriz_responsabilidades=data.get('matriz_responsabilidades'),
        descricoes_gerais=data.get('descricoes_gerais'),
        normas_observar=data.get('normas_observar'),
        regras_responsabilidades=data.get('regras_responsabilidades'),
        relacoes_contratada_fiscalizacao=data.get('relacoes_contratada_fiscalizacao'),
        sst=data.get('sst'),
        credenciamento_observacoes=data.get('credenciamento_observacoes'),
        anexos_info=data.get('anexos_info'),
        titulo=data.get('titulo'),  # Adicionar campo título
        orcamento_estimado=data.get('orcamento_estimado', 0),
        prazo_maximo_execucao=data.get('prazo_maximo_execucao'),
        procurement_id=None,  # SEM PROCESSO
        status=TRStatus.RASCUNHO
    )
    db.session.add(tr)
    db.session.flush()
    
    # Adicionar itens de serviço
    if "planilha_servico" in data and isinstance(data["planilha_servico"], list):
        for idx, item in enumerate(data["planilha_servico"], start=1):
            if item.get("descricao"):  # Só adiciona se tem descrição
                service_item = TRServiceItem(
                    tr_id=tr.id,
                    item_ordem=item.get("item_ordem", idx),
                    codigo=item.get("codigo", f"COD-{idx}"),
                    descricao=item.get("descricao"),
                    unid=item.get("unid", "UN"),
                    qtde=float(item.get("qtde", 1))
                )
                db.session.add(service_item)
    
    db.session.commit()
    
    return {
        "tr_id": tr.id,
        "status": tr.status.value,
        "message": "TR criado com sucesso"
    }


@bp.put("/tr/<int:tr_id>")
@jwt_required()
def update_tr(tr_id: int):
    """Requisitante atualiza TR"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem editar TR"}, 403
    
    tr = TR.query.get_or_404(tr_id)
    
    # Verificar se é o criador do TR
    if tr.created_by != user.id:
        return {"error": "Você não é o criador deste TR"}, 403
    
    # Só pode editar se estiver em rascunho ou rejeitado
    if tr.status not in [TRStatus.RASCUNHO, TRStatus.REJEITADO]:
        return {"error": "TR não pode ser editado neste status"}, 400
    
    data = request.get_json() or {}
    
    # Atualizar campos
    fields = [
        "titulo", "objetivo", "situacao_atual", "descricao_servicos",
        "local_horario_trabalhos", "prazo_execucao", "local_canteiro",
        "atividades_preliminares", "garantia", "matriz_responsabilidades",
        "descricoes_gerais", "normas_observar", "regras_responsabilidades",
        "relacoes_contratada_fiscalizacao", "sst", "credenciamento_observacoes",
        "anexos_info", "orcamento_estimado", "prazo_maximo_execucao"
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
            if item.get("descricao"):  # Só adiciona se tem descrição
                service_item = TRServiceItem(
                    tr_id=tr.id,
                    item_ordem=item.get("item_ordem", idx),
                    codigo=item.get("codigo", f"COD-{idx}"),
                    descricao=item.get("descricao"),
                    unid=item.get("unid", "UN"),
                    qtde=float(item.get("qtde", 1))
                )
                db.session.add(service_item)
    
    db.session.commit()
    
    # Emitir evento real-time
    socketio.emit("tr.saved", {
        "tr_id": tr.id,
        "status": tr.status.value,
        "updated_by": user.id
    }, to=f"user:{user.id}")
    
    return {
        "tr_id": tr.id,
        "status": tr.status.value,
        "message": "TR atualizado com sucesso"
    }


@bp.post("/tr/<int:tr_id>/submit")
@jwt_required()
def submit_tr_for_approval(tr_id: int):
    """Requisitante submete TR para aprovação do comprador"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem submeter TR"}, 403
    
    tr = TR.query.get_or_404(tr_id)
    
    # Verificar se é o criador do TR
    if tr.created_by != user.id:
        return {"error": "Você não é o criador deste TR"}, 403
    
    if tr.status not in [TRStatus.RASCUNHO, TRStatus.REJEITADO]:
        return {"error": "TR não pode ser submetido neste status"}, 400
    
    # Validações obrigatórias
    if not tr.titulo or not tr.objetivo or not tr.descricao_servicos:
        return {"error": "Título, objetivo e descrição dos serviços são obrigatórios"}, 400
    
    if not tr.service_items:
        return {"error": "TR deve ter pelo menos um item de serviço"}, 400
    
    tr.status = TRStatus.SUBMETIDO
    tr.submitted_at = datetime.utcnow()
    
    db.session.commit()
    
    # Notificar compradores em real-time
    socketio.emit("tr.submitted", {
        "tr_id": tr.id,
        "titulo": tr.titulo,
        "submitted_by": user.full_name,
        "creator_name": user.full_name,
        "orcamento_estimado": float(tr.orcamento_estimado or 0),
        "prazo_maximo_execucao": tr.prazo_maximo_execucao
    }, to="role:COMPRADOR")
    
    return {
        "message": "TR submetido para aprovação",
        "tr_id": tr.id,
        "status": tr.status.value
    }


@bp.get("/tr/my-trs")
@jwt_required()
def get_my_trs():
    """Lista TRs criados pelo requisitante"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem ver seus TRs"}, 403
    
    trs = TR.query.filter_by(created_by=user.id).order_by(TR.created_at.desc()).all()
    
    result = []
    for tr in trs:
        result.append({
            "id": tr.id,
            "titulo": tr.titulo,
            "status": tr.status.value,
            "orcamento_estimado": float(tr.orcamento_estimado or 0),
            "prazo_maximo_execucao": tr.prazo_maximo_execucao,
            "created_at": tr.created_at.isoformat(),
            "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None,
            "approved_at": tr.approved_at.isoformat() if tr.approved_at else None,
            "procurement_id": tr.procurement_id,
            "approval_comments": tr.approval_comments,
            "revision_requested": tr.revision_requested
        })
    
    return result


@bp.get("/tr/pending-approval")
@jwt_required()
def get_pending_trs():
    """Lista TRs pendentes de aprovação - apenas COMPRADOR"""
    user = get_current_user()
    
    if user.role != Role.COMPRADOR:
        return {"error": "Apenas compradores podem ver TRs pendentes"}, 403
    
    trs = TR.query.filter_by(status=TRStatus.SUBMETIDO).order_by(TR.submitted_at.desc()).all()
    
    result = []
    for tr in trs:
        creator = User.query.get(tr.created_by)
        result.append({
            "id": tr.id,
            "titulo": tr.titulo,
            "status": tr.status.value,
            "orcamento_estimado": float(tr.orcamento_estimado or 0),
            "prazo_maximo_execucao": tr.prazo_maximo_execucao,
            "submitted_at": tr.submitted_at.isoformat(),
            "creator_name": creator.full_name if creator else "Desconhecido"
        })
    
    return result


@bp.get("/tr/approved-without-process")
@jwt_required()
def get_approved_without_process():
    """Lista TRs aprovados sem processo criado - apenas COMPRADOR"""
    user = get_current_user()
    
    if user.role != Role.COMPRADOR:
        return {"error": "Apenas compradores podem ver TRs aprovados"}, 403
    
    trs = TR.query.filter_by(
        status=TRStatus.APROVADO,
        procurement_id=None
    ).order_by(TR.approved_at.desc()).all()
    
    result = []
    for tr in trs:
        creator = User.query.get(tr.created_by)
        result.append({
            "id": tr.id,
            "titulo": tr.titulo,
            "status": tr.status.value,
            "orcamento_estimado": float(tr.orcamento_estimado or 0),
            "prazo_maximo_execucao": tr.prazo_maximo_execucao,
            "approved_at": tr.approved_at.isoformat(),
            "creator_name": creator.full_name if creator else "Desconhecido"
        })
    
    return result


@bp.get("/tr/<int:tr_id>")
@jwt_required()
def get_tr_details(tr_id: int):
    """Obtém detalhes completos do TR"""
    user = get_current_user()
    
    tr = TR.query.get_or_404(tr_id)
    
    # Verificar permissões
    if user.role == Role.REQUISITANTE and tr.created_by != user.id:
        return {"error": "Não autorizado"}, 403
    
    # Fornecedores só podem ver TR aprovados através do processo
    if user.role == Role.FORNECEDOR:
        if not tr.procurement_id or tr.status != TRStatus.APROVADO:
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
        "titulo": tr.titulo,
        "status": tr.status.value,
        "objetivo": tr.objetivo,
        "situacao_atual": tr.situacao_atual,
        "descricao_servicos": tr.descricao_servicos,
        "orcamento_estimado": float(tr.orcamento_estimado or 0),
        "prazo_maximo_execucao": tr.prazo_maximo_execucao,
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
        "created_at": tr.created_at.isoformat(),
        "submitted_at": tr.submitted_at.isoformat() if tr.submitted_at else None,
        "approved_at": tr.approved_at.isoformat() if tr.approved_at else None,
        "approval_comments": tr.approval_comments,
        "revision_requested": tr.revision_requested,
        "procurement_id": tr.procurement_id
    }


@bp.post("/tr/<int:tr_id>/approve")
@jwt_required()
def approve_or_reject_tr(tr_id: int):
    """Comprador aprova ou rejeita TR"""
    data = request.get_json() or {}
    user = get_current_user()
    
    if user.role != Role.COMPRADOR:
        return {"error": "Apenas compradores podem aprovar TR"}, 403
    
    tr = TR.query.get_or_404(tr_id)
    
    if tr.status != TRStatus.SUBMETIDO:
        return {"error": "TR não está aguardando aprovação"}, 400
    
    approved = data.get("approved", False)
    comments = data.get("comments", "")
    
    if approved:
        tr.status = TRStatus.APROVADO
        tr.approved_at = datetime.utcnow()
        tr.approved_by = user.id
        tr.approval_comments = comments
        message = "TR aprovado com sucesso"
        
    else:
        if not comments:
            return {"error": "Comentários são obrigatórios para rejeição"}, 400
        
        tr.status = TRStatus.REJEITADO
        tr.revision_requested = comments
        tr.rejection_reason = comments
        message = "TR rejeitado - revisão solicitada"
    
    db.session.commit()
    
    # Notificar requisitante
    socketio.emit("tr.approval_result", {
        "tr_id": tr.id,
        "approved": approved,
        "comments": comments,
        "message": message
    }, to=f"user:{tr.created_by}")
    
    return {
        "message": message,
        "tr_id": tr.id,
        "status": tr.status.value
    }


@bp.get("/tr/proposals-for-review")
@jwt_required()
def get_proposals_for_technical_review():
    """Lista propostas aguardando análise técnica do requisitante"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem ver propostas para análise"}, 403
    
    # Buscar propostas enviadas para processos com TR criado por este requisitante
    proposals = db.session.query(Proposal).join(
        Procurement, Proposal.procurement_id == Procurement.id
    ).join(
        TR, Procurement.id == TR.procurement_id
    ).filter(
        TR.created_by == user.id,
        Proposal.status == ProposalStatus.ENVIADA
    ).all()
    
    result = []
    for prop in proposals:
        proc = Procurement.query.get(prop.procurement_id)
        result.append({
            "id": prop.id,
            "procurement_id": prop.procurement_id,
            "procurement_title": proc.title if proc else "Processo não encontrado",
            "supplier": {
                "id": prop.supplier.id,
                "name": prop.supplier.full_name,
                "organization": prop.supplier.organization.name if prop.supplier.organization else None
            },
            "status": prop.status.value,
            "technical_score": prop.technical_score,
            "technical_review": prop.technical_review,
            "submitted_at": prop.technical_submitted_at.isoformat() if prop.technical_submitted_at else None,
            "technical_reviewed_at": prop.technical_reviewed_at.isoformat() if prop.technical_reviewed_at else None
        })
    
    return result


@bp.post("/tr/technical-review")
@jwt_required()
def submit_technical_review():
    """Requisitante faz análise técnica da proposta"""
    user = get_current_user()
    
    if user.role != Role.REQUISITANTE:
        return {"error": "Apenas requisitantes podem fazer análise técnica"}, 403
    
    data = request.get_json() or {}
    proposal_id = data.get("proposal_id")
    review = data.get("technical_review")
    score = data.get("technical_score", 0)
    approved = data.get("approved", False)
    
    if not proposal_id or not review or not score:
        return {"error": "proposal_id, technical_review e technical_score são obrigatórios"}, 400
    
    proposal = Proposal.query.get_or_404(proposal_id)
    
    # Verificar se o requisitante é o criador do TR do processo
    proc = Procurement.query.get(proposal.procurement_id)
    if not proc or not proc.tr or proc.tr.created_by != user.id:
        return {"error": "Você não tem permissão para revisar esta proposta"}, 403
    
    proposal.technical_review = review
    proposal.technical_score = score
    proposal.technical_reviewed_by = user.id
    proposal.technical_reviewed_at = datetime.utcnow()
    
    if approved:
        proposal.status = ProposalStatus.APROVADA_TECNICAMENTE
    else:
        proposal.status = ProposalStatus.REJEITADA_TECNICAMENTE
    
    db.session.commit()
    
    # Notificar comprador
    socketio.emit("proposal.technical_reviewed", {
        "proposal_id": proposal.id,
        "procurement_id": proposal.procurement_id,
        "approved": approved,
        "score": score,
        "reviewer": user.full_name
    }, to="role:COMPRADOR")
    
    return {
        "message": "Parecer técnico registrado com sucesso",
        "proposal_id": proposal.id,
        "approved": approved,
        "score": score
    }
