# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from .. import db, socketio
from ..models import (
    Proposal, ProposalService, ProposalPrice, TRServiceItem, 
    ProposalStatus, Procurement, ProcurementStatus, User, Role
)
from ..utils.auth import get_current_user

bp = Blueprint("proposals", __name__)


@bp.post("/procurements/<int:proc_id>/proposals")
@jwt_required()
def create_or_update_proposal(proc_id: int):
    """Fornecedor cria ou atualiza proposta completa"""
    data = request.get_json() or {}
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem criar propostas"}, 403
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # Verificar se processo está aberto
    if proc.status != ProcurementStatus.ABERTO:
        return {"error": "Processo não está aberto para propostas"}, 400
    
    # Verificar se foi convidado ou se processo é público
    from ..models import Invite
    invite = Invite.query.filter_by(
        procurement_id=proc_id,
        email=user.email,
        accepted=True
    ).first()
    
    if not invite:
        return {"error": "Você não foi convidado para este processo"}, 403
    
    # Criar ou obter proposta existente
    proposal = Proposal.query.filter_by(
        procurement_id=proc_id,
        supplier_user_id=user.id
    ).first()
    
    if not proposal:
        proposal = Proposal(
            procurement_id=proc_id,
            supplier_user_id=user.id,
            status=ProposalStatus.RASCUNHO
        )
        db.session.add(proposal)
        db.session.flush()
    
    # Verificar se proposta ainda pode ser editada
    if proposal.status not in [ProposalStatus.RASCUNHO, ProposalStatus.EM_ELABORACAO]:
        return {"error": "Proposta já foi enviada e não pode ser alterada"}, 400
    
    # Atualizar dados técnicos
    if "technical_description" in data:
        proposal.technical_description = data["technical_description"]
    
    # Atualizar dados comerciais
    if "payment_conditions" in data:
        proposal.payment_conditions = data["payment_conditions"]
    if "delivery_time" in data:
        proposal.delivery_time = data["delivery_time"]
    if "warranty_terms" in data:
        proposal.warranty_terms = data["warranty_terms"]
    
    # Atualizar itens de serviço (quantidades)
    if "service_items" in data:
        # Remover itens existentes
        ProposalService.query.filter_by(proposal_id=proposal.id).delete()
        
        for item_data in data["service_items"]:
            service_item_id = item_data.get("service_item_id")
            qty = item_data.get("qty", 0)
            technical_notes = item_data.get("technical_notes", "")
            
            # Verificar se item pertence ao TR
            tr_item = TRServiceItem.query.filter_by(
                id=service_item_id,
                tr_id=proc.tr.id
            ).first()
            
            if not tr_item:
                continue
            
            # Criar ProposalService
            prop_service = ProposalService(
                proposal_id=proposal.id,
                service_item_id=service_item_id,
                qty=qty,
                technical_notes=technical_notes
            )
            db.session.add(prop_service)
    
    # Atualizar preços
    if "prices" in data:
        # Remover preços existentes
        ProposalPrice.query.filter_by(proposal_id=proposal.id).delete()
        
        for price_data in data["prices"]:
            service_item_id = price_data.get("service_item_id")
            unit_price = price_data.get("unit_price", 0)
            
            # Verificar se item pertence ao TR
            tr_item = TRServiceItem.query.filter_by(
                id=service_item_id,
                tr_id=proc.tr.id
            ).first()
            
            if not tr_item:
                continue
            
            # Criar ProposalPrice
            prop_price = ProposalPrice(
                proposal_id=proposal.id,
                service_item_id=service_item_id,
                unit_price=unit_price
            )
            db.session.add(prop_price)
    
    proposal.status = ProposalStatus.EM_ELABORACAO
    db.session.commit()
    
    # Notificar compradores
    socketio.emit("proposal.updated", {
        "proposal_id": proposal.id,
        "procurement_id": proc_id,
        "supplier": user.full_name,
        "status": proposal.status.value
    }, to="role:COMPRADOR")
    
    return {
        "proposal_id": proposal.id,
        "status": proposal.status.value,
        "message": "Proposta salva com sucesso"
    }


@bp.post("/proposals/<int:proposal_id>/submit")
@jwt_required()
def submit_proposal(proposal_id: int):
    """Fornecedor envia proposta finalizada"""
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem submeter propostas"}, 403
    
    proposal = Proposal.query.get_or_404(proposal_id)
    
    # Verificar se é o fornecedor correto
    if proposal.supplier_user_id != user.id:
        return {"error": "Não autorizado"}, 403
    
    # Verificar se pode ser enviada
    if proposal.status not in [ProposalStatus.RASCUNHO, ProposalStatus.EM_ELABORACAO]:
        return {"error": "Proposta não pode ser enviada neste status"}, 400
    
    # Validações obrigatórias
    if not proposal.technical_description:
        return {"error": "Descrição técnica é obrigatória"}, 400
    
    if not proposal.payment_conditions or not proposal.delivery_time or not proposal.warranty_terms:
        return {"error": "Todas as condições comerciais são obrigatórias"}, 400
    
    if not proposal.service_items:
        return {"error": "Proposta deve incluir itens de serviço"}, 400
    
    # Verificar se tem preços para todos os itens
    service_items_count = len(proposal.service_items)
    prices_count = ProposalPrice.query.filter_by(proposal_id=proposal.id).count()
    
    if prices_count == 0:
        return {"error": "Proposta deve incluir preços"}, 400
    
    # Marcar como enviada
    proposal.status = ProposalStatus.ENVIADA
    proposal.technical_submitted_at = datetime.utcnow()
    proposal.commercial_submitted_at = datetime.utcnow()
    
    db.session.commit()
    
    # Notificar comprador
    socketio.emit("proposal.submitted", {
        "proposal_id": proposal.id,
        "procurement_id": proposal.procurement_id,
        "supplier": proposal.supplier.full_name,
        "submitted_at": datetime.utcnow().isoformat()
    }, to="role:COMPRADOR")
    
    return {
        "message": "Proposta enviada com sucesso",
        "proposal_id": proposal.id,
        "status": proposal.status.value
    }


@bp.get("/proposals/<int:proposal_id>")
@jwt_required()
def get_proposal_details(proposal_id: int):
    """Obtém detalhes completos da proposta"""
    user = get_current_user()
    
    proposal = Proposal.query.get_or_404(proposal_id)
    
    # Verificar permissões
    if user.role == Role.FORNECEDOR and proposal.supplier_user_id != user.id:
        return {"error": "Não autorizado"}, 403
    
    # Verificar se requisitante pode ver (apenas propostas enviadas)
    if user.role == Role.REQUISITANTE:
        if proposal.status not in [ProposalStatus.ENVIADA, ProposalStatus.APROVADA_TECNICAMENTE, ProposalStatus.REJEITADA_TECNICAMENTE]:
            return {"error": "Proposta não disponível para análise"}, 403
    
    # Montar resposta com todos os detalhes
    items = []
    for service in proposal.service_items:
        price = ProposalPrice.query.filter_by(
            proposal_id=proposal.id,
            service_item_id=service.service_item_id
        ).first()
        
        tr_item = TRServiceItem.query.get(service.service_item_id)
        
        item_data = {
            "service_item_id": service.service_item_id,
            "item_ordem": tr_item.item_ordem if tr_item else 0,
            "codigo": tr_item.codigo if tr_item else "",
            "descricao": tr_item.descricao if tr_item else "",
            "unid": tr_item.unid if tr_item else "",
            "qty_proposed": float(service.qty),
            "qty_baseline": float(tr_item.qtde) if tr_item else 0,
            "technical_notes": service.technical_notes
        }
        
        # Requisitante não vê preços comerciais
        if user.role != Role.REQUISITANTE and price:
            item_data["unit_price"] = float(price.unit_price)
            item_data["total"] = float(service.qty * price.unit_price)
        
        items.append(item_data)
    
    response_data = {
        "id": proposal.id,
        "procurement_id": proposal.procurement_id,
        "supplier": {
            "id": proposal.supplier.id,
            "name": proposal.supplier.full_name,
            "organization": proposal.supplier.organization.name if proposal.supplier.organization else None
        },
        "status": proposal.status.value,
        "technical_description": proposal.technical_description,
        "technical_review": proposal.technical_review,
        "technical_score": proposal.technical_score,
        "items": items,
        "submitted_at": proposal.technical_submitted_at.isoformat() if proposal.technical_submitted_at else None,
        "technical_reviewed_at": proposal.technical_reviewed_at.isoformat() if proposal.technical_reviewed_at else None
    }
    
    # Adicionar dados comerciais apenas para comprador e fornecedor
    if user.role != Role.REQUISITANTE:
        response_data.update({
            "payment_conditions": proposal.payment_conditions,
            "delivery_time": proposal.delivery_time,
            "warranty_terms": proposal.warranty_terms,
            "total_value": sum(item.get("total", 0) for item in items if "total" in item)
        })
    
    return response_data


@bp.get("/proposals/my-proposals")
@jwt_required()
def get_my_proposals():
    """Lista propostas do fornecedor logado"""
    user = get_current_user()
    
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem ver suas propostas"}, 403
    
    proposals = Proposal.query.filter_by(supplier_user_id=user.id).all()
    
    result = []
    for prop in proposals:
        proc = Procurement.query.get(prop.procurement_id)
        
        # Calcular valor total
        total_value = 0
        for service in prop.service_items:
            price = ProposalPrice.query.filter_by(
                proposal_id=prop.id,
                service_item_id=service.service_item_id
            ).first()
            if price:
                total_value += float(service.qty * price.unit_price)
        
        result.append({
            "id": prop.id,
            "procurement_id": prop.procurement_id,
            "procurement_title": proc.title if proc else "Processo não encontrado",
            "status": prop.status.value,
            "total_value": round(total_value, 2),
            "technical_score": prop.technical_score,
            "submitted_at": prop.technical_submitted_at.isoformat() if prop.technical_submitted_at else None,
            "technical_reviewed_at": prop.technical_reviewed_at.isoformat() if prop.technical_reviewed_at else None
        })
    
    return result


# Rotas auxiliares para facilitar o desenvolvimento do frontend
@bp.get("/procurements/<int:proc_id>/tr-items")
@jwt_required()
def get_tr_items_for_proposal(proc_id: int):
    """Obtém itens do TR para elaboração de proposta - apenas FORNECEDOR"""
    user = get_current_user()
    
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem acessar"}, 403
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # Verificar se foi convidado
    from ..models import Invite
    invite = Invite.query.filter_by(
        procurement_id=proc_id,
        email=user.email,
        accepted=True
    ).first()
    
    if not invite:
        return {"error": "Você não foi convidado para este processo"}, 403
    
    if not proc.tr:
        return {"error": "TR não encontrado"}, 404
    
    items = []
    for item in proc.tr.service_items:
        items.append({
            "id": item.id,
            "item_ordem": item.item_ordem,
            "codigo": item.codigo,
            "descricao": item.descricao,
            "unid": item.unid,
            "qtde_baseline": float(item.qtde)
        })
    
    return {
        "tr_id": proc.tr.id,
        "tr_title": proc.tr.titulo,
        "items": items
    }
