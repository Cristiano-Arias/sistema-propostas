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
    """Fornecedor cria ou atualiza proposta completa - apenas FORNECEDOR"""
    data = request.get_json() or {}
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem criar propostas"}, 403
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # Verificar se processo está aberto
    if proc.status != ProcurementStatus.ABERTO:
        return {"error": "Processo não está aberto para propostas"}, 400
    
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
    
    # Atualizar itens de serviço (quantidades e observações técnicas)
    if "service_items" in data:
        for item_data in data["service_items"]:
            service_item_id = item_data.get("service_item_id")
            qty = item_data.get("qty", 0)
            technical_notes = item_data.get("technical_notes", "")
            
            # Verificar se item pertence ao TR
            item = TRServiceItem.query.filter_by(
                id=service_item_id,
                tr_id=proc.tr.id
            ).first()
            
            if not item:
                continue
            
            # Criar ou atualizar ProposalService
            prop_service = ProposalService.query.filter_by(
                proposal_id=proposal.id,
                service_item_id=service_item_id
            ).first()
            
            if not prop_service:
                prop_service = ProposalService(
                    proposal_id=proposal.id,
                    service_item_id=service_item_id,
                    qty=qty,
                    technical_notes=technical_notes
                )
                db.session.add(prop_service)
            else:
                prop_service.qty = qty
                prop_service.technical_notes = technical_notes
    
    # Atualizar preços
    if "prices" in data:
        for price_data in data["prices"]:
            service_item_id = price_data.get("service_item_id")
            unit_price = price_data.get("unit_price", 0)
            
            # Verificar se item pertence ao TR
            item = TRServiceItem.query.filter_by(
                id=service_item_id,
                tr_id=proc.tr.id
            ).first()
            
            if not item:
                continue
            
            # Criar ou atualizar ProposalPrice
            prop_price = ProposalPrice.query.filter_by(
                proposal_id=proposal.id,
                service_item_id=service_item_id
            ).first()
            
            if not prop_price:
                prop_price = ProposalPrice(
                    proposal_id=proposal.id,
                    service_item_id=service_item_id,
                    unit_price=unit_price
                )
                db.session.add(prop_price)
            else:
                prop_price.unit_price = unit_price
    
    db.session.commit()
    
    # Notificar compradores
    socketio.emit("proposal.updated", {
        "proposal_id": proposal.id,
        "procurement_id": proc_id,
        "supplier": user.id,
        "status": proposal.status.value
    }, to=f"proc:{proc_id}")
    
    return {
        "proposal_id": proposal.id,
        "status": proposal.status.value,
        "message": "Proposta salva com sucesso"
    }


@bp.post("/proposals/<int:proposal_id>/submit")
@jwt_required()
def submit_proposal(proposal_id: int):
    """Fornecedor envia proposta finalizada - apenas FORNECEDOR"""
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem submeter propostas"}, 403
    
    proposal = Proposal.query.get_or_404(proposal_id)
    
    # Verificar se é o fornecedor correto
    if proposal.supplier_user_id != user.id:
        return {"error": "Não autorizado"}, 403
    
    # Validar proposta
    if not proposal.technical_description:
        return {"error": "Descrição técnica é obrigatória"}, 400
    
    if not proposal.service_items:
        return {"error": "Proposta deve incluir itens de serviço"}, 400
    
    if not proposal.prices:
        return {"error": "Proposta deve incluir preços"}, 400
    
    proposal.status = ProposalStatus.ENVIADA
    proposal.technical_submitted_at = datetime.utcnow()
    proposal.commercial_submitted_at = datetime.utcnow()
    
    db.session.commit()
    
    # Notificar comprador e requisitante
    socketio.emit("proposal.submitted", {
        "proposal_id": proposal.id,
        "procurement_id": proposal.procurement_id,
        "supplier": proposal.supplier.full_name,
        "submitted_at": datetime.utcnow().isoformat()
    }, to=f"proc:{proposal.procurement_id}")
    
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
    
    # Montar resposta com todos os detalhes
    items = []
    for service in proposal.service_items:
        price = ProposalPrice.query.filter_by(
            proposal_id=proposal.id,
            service_item_id=service.service_item_id
        ).first()
        
        tr_item = TRServiceItem.query.get(service.service_item_id)
        
        items.append({
            "service_item_id": service.service_item_id,
            "item_ordem": tr_item.item_ordem,
            "codigo": tr_item.codigo,
            "descricao": tr_item.descricao,
            "unid": tr_item.unid,
            "qty_proposed": float(service.qty),
            "qty_baseline": float(tr_item.qtde),
            "unit_price": float(price.unit_price) if price else 0,
            "total": float(service.qty * price.unit_price) if price else 0,
            "technical_notes": service.technical_notes
        })
    
    return {
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
        "payment_conditions": proposal.payment_conditions,
        "delivery_time": proposal.delivery_time,
        "warranty_terms": proposal.warranty_terms,
        "items": items,
        "total_value": sum(item["total"] for item in items),
        "submitted_at": proposal.technical_submitted_at.isoformat() if proposal.technical_submitted_at else None
    }


@bp.put("/proposals/<int:proc_id>/service-qty")
@jwt_required()
def upsert_quantities(proc_id: int):
    """Atualiza quantidades da proposta técnica - apenas FORNECEDOR"""
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem atualizar quantidades"}, 403
    
    # Criar ou obter proposta
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
        db.session.commit()
    
    payload = request.get_json() or []
    if not isinstance(payload, list):
        return {"error": "payload deve ser lista de itens"}, 400
    
    # Verificar se service_item pertence ao TR do processo
    proc = Procurement.query.get_or_404(proc_id)
    valid_item_ids = {r.id for r in TRServiceItem.query.filter_by(tr_id=proc.tr.id).all()}
    
    for row in payload:
        sid = row.get("service_item_id")
        qty = row.get("qty")
        
        if sid not in valid_item_ids:
            return {"error": f"service_item_id {sid} inválido para este processo"}, 400
        
        ps = ProposalService.query.filter_by(
            proposal_id=proposal.id,
            service_item_id=sid
        ).first()
        
        if not ps:
            ps = ProposalService(
                proposal_id=proposal.id,
                service_item_id=sid,
                qty=qty
            )
            db.session.add(ps)
        else:
            ps.qty = qty
    
    db.session.commit()
    
    socketio.emit("proposal.tech.received", {
        "procurement_id": proc_id,
        "proposal_id": proposal.id
    }, to=f"proc:{proc_id}")
    
    return {"proposal_id": proposal.id, "items": len(payload)}


@bp.put("/proposals/<int:proc_id>/prices")
@jwt_required()
def upsert_prices(proc_id: int):
    """Atualiza preços da proposta comercial - apenas FORNECEDOR"""
    user = get_current_user()
    
    # Verificar se é fornecedor
    if user.role != Role.FORNECEDOR:
        return {"error": "Apenas fornecedores podem atualizar preços"}, 403
    
    # Criar ou obter proposta
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
        db.session.commit()
    
    payload = request.get_json() or []
    if not isinstance(payload, list):
        return {"error": "payload deve ser lista de itens"}, 400
    
    # Verificar se service_item pertence ao TR do processo
    proc = Procurement.query.get_or_404(proc_id)
    valid_item_ids = {r.id for r in TRServiceItem.query.filter_by(tr_id=proc.tr.id).all()}
    
    for row in payload:
        sid = row.get("service_item_id")
        price = row.get("unit_price")
        
        if sid not in valid_item_ids:
            return {"error": f"service_item_id {sid} inválido para este processo"}, 400
        
        pp = ProposalPrice.query.filter_by(
            proposal_id=proposal.id,
            service_item_id=sid
        ).first()
        
        if not pp:
            pp = ProposalPrice(
                proposal_id=proposal.id,
                service_item_id=sid,
                unit_price=price
            )
            db.session.add(pp)
        else:
            pp.unit_price = price
    
    db.session.commit()
    
    socketio.emit("proposal.comm.received", {
        "procurement_id": proc_id,
        "proposal_id": proposal.id
    }, to=f"proc:{proc_id}")
    
    return {"proposal_id": proposal.id, "items": len(payload)}


@bp.get("/proposals/<int:proc_id>/commercial-items")
@jwt_required()
def list_commercial_items(proc_id: int):
    """Consolidado por item (JOIN TR baseline + quantidade + preço unitário + total)."""
    user = get_current_user()
    
    props = Proposal.query.filter_by(procurement_id=proc_id).all()
    
    out = []
    for p in props:
        # Se fornecedor, só enxerga sua própria proposta
        if user.role == Role.FORNECEDOR and p.supplier_user_id != user.id:
            continue
        
        items = db.session.query(
            TRServiceItem.item_ordem,
            TRServiceItem.codigo,
            TRServiceItem.descricao,
            TRServiceItem.unid,
            ProposalService.qty,
            ProposalPrice.unit_price,
        ).outerjoin(
            ProposalService, 
            (ProposalService.service_item_id == TRServiceItem.id) & 
            (ProposalService.proposal_id == p.id)
        ).outerjoin(
            ProposalPrice, 
            (ProposalPrice.service_item_id == TRServiceItem.id) & 
            (ProposalPrice.proposal_id == p.id)
        ).filter(
            TRServiceItem.tr.has(procurement_id=proc_id)
        ).order_by(TRServiceItem.item_ordem).all()
        
        items_out = []
        total_geral = 0.0
        for item in items:
            qty = float(item.qty or 0)
            unit_price = float(item.unit_price or 0)
            total = qty * unit_price
            total_geral += total
            items_out.append({
                "item_ordem": item.item_ordem,
                "codigo": item.codigo,
                "descricao": item.descricao,
                "unid": item.unid,
                "qty": qty,
                "unit_price": unit_price,
                "total_item": total,
            })
        
        out.append({
            "proposal_id": p.id,
            "supplier_user_id": p.supplier_user_id,
            "total_geral": round(total_geral, 2),
            "itens": items_out,
        })
    
    return {"proposals": out}
