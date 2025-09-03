# -*- coding: utf-8 -*-
import secrets
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import or_, and_, func
from .. import db, socketio
from ..models import (
    Procurement, Invite, User, Role, TR, TRStatus, 
    ProcurementStatus, Proposal, ProposalStatus, AuditLog,
    Organization, TRServiceItem, ProposalPrice, ProposalService
)

bp = Blueprint("procurements", __name__)


def require_role(roles):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            ident = get_jwt_identity()
            if ident is None or ident.get("role") not in roles:
                return {"error": "forbidden"}, 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return jwt_required()(wrapper)
    return decorator


@bp.get("/procurements")
@jwt_required()
def list_procurements():
    """Lista processos baseado no role do usuário"""
    ident = get_jwt_identity()
    user = User.query.get(ident["user_id"])
    
    if user.role == Role.REQUISITANTE:
        # MUDANÇA: Requisitante vê apenas processos atribuídos a ele
        procurements = Procurement.query.filter_by(requisitante_id=user.id).all()
    elif user.role == Role.COMPRADOR:
        # Comprador vê todos os processos
        procurements = Procurement.query.all()
    else:  # FORNECEDOR
        # Fornecedor vê apenas processos abertos ou que foi convidado
        invited_proc_ids = db.session.query(Invite.procurement_id).filter_by(
            email=user.email
        ).subquery()
        
        procurements = Procurement.query.filter(
            or_(
                Procurement.status.in_([ProcurementStatus.ABERTO, ProcurementStatus.ANALISE_TECNICA]),
                Procurement.id.in_(invited_proc_ids)
            )
        ).all()
    
    result = []
    for proc in procurements:
        proc_dict = {
            "id": proc.id,
            "title": proc.title,
            "description": proc.description,
            "status": proc.status.value,
            "created_at": proc.created_at.isoformat(),
            "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None,
            "has_tr": proc.tr is not None,
            "tr_status": proc.tr.status.value if proc.tr else None
        }
        
        # Adicionar informação do requisitante
        if proc.requisitante:
            proc_dict["requisitante"] = {
                "id": proc.requisitante.id,
                "name": proc.requisitante.full_name,
                "email": proc.requisitante.email
            }
        
        result.append(proc_dict)
    
    return jsonify(result)


@bp.get("/procurements/<int:proc_id>")
@jwt_required()
def get_procurement(proc_id: int):
    """Obtém detalhes completos do processo"""
    ident = get_jwt_identity()
    proc = Procurement.query.get_or_404(proc_id)
    
    # Verificar permissões
    user = User.query.get(ident["user_id"])
    if user.role == Role.FORNECEDOR:
        # Fornecedor só pode ver se foi convidado ou processo está aberto
        if proc.status not in [ProcurementStatus.ABERTO, ProcurementStatus.ANALISE_TECNICA]:
            invited = Invite.query.filter_by(
                procurement_id=proc_id,
                email=user.email
            ).first()
            if not invited:
                return {"error": "Não autorizado"}, 403
    elif user.role == Role.REQUISITANTE:
        # Requisitante só pode ver processos atribuídos a ele
        if proc.requisitante_id != user.id:
            return {"error": "Não autorizado"}, 403
    
    # Montar resposta completa
    response = {
        "id": proc.id,
        "title": proc.title,
        "description": proc.description,
        "status": proc.status.value,
        "created_at": proc.created_at.isoformat(),
        "updated_at": proc.updated_at.isoformat() if proc.updated_at else None,
        "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None,
        "organization": {
            "id": proc.org_id,
            "name": Organization.query.get(proc.org_id).name if proc.org_id else None
        }
    }
    
    # Adicionar informação do requisitante
    if proc.requisitante:
        response["requisitante"] = {
            "id": proc.requisitante.id,
            "name": proc.requisitante.full_name,
            "email": proc.requisitante.email
        }
    
    # Adicionar informações do TR se existir
    if proc.tr:
        response["tr"] = {
            "id": proc.tr.id,
            "status": proc.tr.status.value,
            "submitted_at": proc.tr.submitted_at.isoformat() if proc.tr.submitted_at else None,
            "approved_at": proc.tr.approved_at.isoformat() if proc.tr.approved_at else None
        }
    
    # Adicionar contagem de propostas para compradores
    if user.role == Role.COMPRADOR:
        response["proposals_count"] = Proposal.query.filter_by(procurement_id=proc_id).count()
        response["invites_count"] = Invite.query.filter_by(procurement_id=proc_id).count()
    
    return jsonify(response)


@bp.post("/procurements")
@require_role(["COMPRADOR"])
def create_procurement():
    """
    MUDANÇA PRINCIPAL: Comprador cria processo e atribui requisitante
    """
    data = request.get_json() or {}
    ident = get_jwt_identity()
    user = User.query.get(ident["user_id"])
    
    title = data.get("title", "").strip()
    description = data.get("description", "")
    requisitante_email = data.get("requisitante_email")  # NOVO: email do requisitante
    
    if not title:
        return {"error": "Título é obrigatório"}, 400
    
    # NOVO: Buscar requisitante se fornecido
    requisitante = None
    if requisitante_email:
        requisitante = User.query.filter_by(
            email=requisitante_email,
            role=Role.REQUISITANTE
        ).first()
        
        if not requisitante:
            # Se não encontrar, tentar buscar qualquer requisitante disponível
            requisitante = User.query.filter_by(role=Role.REQUISITANTE).first()
    else:
        # Se não forneceu email, pegar o primeiro requisitante disponível
        requisitante = User.query.filter_by(role=Role.REQUISITANTE).first()
    
    # Criar processo com status inicial correto
    proc = Procurement(
        title=title,
        description=description,
        status=ProcurementStatus.TR_PENDENTE,  # MUDANÇA: Status inicial correto
        created_by=user.id,
        requisitante_id=requisitante.id if requisitante else None,  # NOVO: Atribuir requisitante
        org_id=user.org_id
    )
    db.session.add(proc)
    db.session.commit()
    
    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="PROCUREMENT_CREATED",
        entity_type="Procurement",
        entity_id=proc.id,
        details={
            "title": title,
            "requisitante_id": requisitante.id if requisitante else None
        }
    )
    db.session.add(audit)
    db.session.commit()
    
    # NOVO: Notificar requisitante atribuído
    if requisitante:
        socketio.emit("procurement.assigned", {
            "procurement_id": proc.id,
            "title": proc.title,
            "message": f"Você foi designado para criar o TR do processo '{proc.title}'"
        }, to=f"user:{requisitante.id}")
    
    # Notificar organização
    socketio.emit("procurement.created", {
        "procurement_id": proc.id,
        "title": proc.title,
        "created_by": user.full_name,
        "requisitante": requisitante.full_name if requisitante else None
    }, to=f"org:{user.org_id}")
    
    return {
        "id": proc.id,
        "title": proc.title,
        "status": proc.status.value,
        "requisitante": requisitante.full_name if requisitante else None,
        "message": "Processo criado com sucesso"
    }, 201


@bp.put("/procurements/<int:proc_id>")
@require_role(["COMPRADOR"])
def update_procurement(proc_id: int):
    """Atualiza informações do processo"""
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # Atualizar campos permitidos
    if "title" in data:
        proc.title = data["title"]
    if "description" in data:
        proc.description = data["description"]
    if "deadline_proposals" in data:
        proc.deadline_proposals = datetime.fromisoformat(data["deadline_proposals"])
    
    # NOVO: Permitir reatribuir requisitante
    if "requisitante_email" in data:
        requisitante = User.query.filter_by(
            email=data["requisitante_email"],
            role=Role.REQUISITANTE
        ).first()
        if requisitante:
            old_requisitante_id = proc.requisitante_id
            proc.requisitante_id = requisitante.id
            
            # Notificar novo requisitante
            if old_requisitante_id != requisitante.id:
                socketio.emit("procurement.assigned", {
                    "procurement_id": proc.id,
                    "title": proc.title,
                    "message": f"Você foi designado para o processo '{proc.title}'"
                }, to=f"user:{requisitante.id}")
    
    proc.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="PROCUREMENT_UPDATED",
        entity_type="Procurement",
        entity_id=proc.id,
        details=data
    )
    db.session.add(audit)
    db.session.commit()
    
    return {"message": "Processo atualizado", "procurement_id": proc.id}


@bp.post("/procurements/<int:proc_id>/open")
@require_role(["COMPRADOR"])
def open_procurement(proc_id: int):
    """
    MUDANÇA: Só pode abrir processo se TR estiver aprovado
    """
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # MUDANÇA: Verificar se TR está aprovado
    if not proc.tr or proc.tr.status != TRStatus.APROVADO:
        return {"error": "TR deve estar aprovado antes de abrir o processo"}, 400
    
    # MUDANÇA: Verificar status do processo
    if proc.status != ProcurementStatus.TR_APROVADO:
        return {"error": "Processo deve ter TR aprovado para ser aberto"}, 400
    
    # Verificar se tem pelo menos um convite enviado (opcional)
    invites_count = Invite.query.filter_by(procurement_id=proc_id).count()
    if invites_count == 0 and not data.get("force"):
        return {"warning": "Nenhum convite enviado. Adicione 'force': true para continuar"}, 400
    
    deadline = data.get("deadline")
    if deadline:
        proc.deadline_proposals = datetime.fromisoformat(deadline)
    
    proc.status = ProcurementStatus.ABERTO
    proc.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="PROCUREMENT_OPENED",
        entity_type="Procurement",
        entity_id=proc.id,
        details={"deadline": deadline}
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notificar todos os fornecedores convidados
    invites = Invite.query.filter_by(procurement_id=proc_id).all()
    for inv in invites:
        supplier = User.query.filter_by(email=inv.email, role=Role.FORNECEDOR).first()
        if supplier:
            socketio.emit("procurement.opened", {
                "procurement_id": proc.id,
                "title": proc.title,
                "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None
            }, to=f"user:{supplier.id}")
    
    # Notificar sala do processo e fornecedores em geral
    socketio.emit("procurement.opened", {
        "procurement_id": proc.id,
        "title": proc.title,
        "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None
    }, to=f"proc:{proc.id}")
    
    socketio.emit("procurement.opened", {
        "procurement_id": proc.id,
        "title": proc.title,
        "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None
    }, to="role:FORNECEDOR")
    
    return {
        "message": "Processo aberto para propostas",
        "procurement_id": proc.id,
        "status": proc.status.value,
        "deadline": proc.deadline_proposals.isoformat() if proc.deadline_proposals else None
    }


# Manter todas as outras rotas iguais...
# (send_invite, list_invites, accept_invite, close_procurement, get_proposals_comparison, list_procurement_proposals)

@bp.post("/procurements/<int:proc_id>/invites")
@require_role(["COMPRADOR"])
def send_invite(proc_id: int):
    """Envia convite para fornecedor"""
    data = request.get_json() or {}
    ident = get_jwt_identity()
    
    email = (data.get("email") or "").strip().lower()
    message = data.get("message", "")
    
    if not email:
        return {"error": "Email é obrigatório"}, 400
    
    proc = Procurement.query.get_or_404(proc_id)
    
    # Verificar se já foi convidado
    existing = Invite.query.filter_by(
        procurement_id=proc_id,
        email=email
    ).first()
    
    if existing:
        return {"error": "Fornecedor já foi convidado"}, 400
    
    # Criar convite
    token = secrets.token_urlsafe(32)
    invite = Invite(
        procurement_id=proc_id,
        email=email,
        token=token,
        created_by=ident["user_id"]
    )
    db.session.add(invite)
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="INVITE_SENT",
        entity_type="Invite",
        entity_id=invite.id,
        details={"email": email, "procurement_id": proc_id}
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notificar via WebSocket
    socketio.emit("invite.sent", {
        "procurement_id": proc_id,
        "email": email,
        "title": proc.title
    }, to=f"proc:{proc_id}")
    
    # Se o fornecedor já está cadastrado, notificar diretamente
    supplier = User.query.filter_by(email=email, role=Role.FORNECEDOR).first()
    if supplier:
        socketio.emit("invite.received", {
            "procurement_id": proc_id,
            "title": proc.title,
            "token": token
        }, to=f"user:{supplier.id}")
    
    return {
        "message": "Convite enviado",
        "token": token,
        "invite_id": invite.id
    }


@bp.get("/procurements/<int:proc_id>/invites")
@require_role(["COMPRADOR"])
def list_invites(proc_id: int):
    """Lista convites enviados para o processo"""
    invites = Invite.query.filter_by(procurement_id=proc_id).all()
    
    result = []
    for inv in invites:
        supplier = User.query.filter_by(email=inv.email, role=Role.FORNECEDOR).first()
        result.append({
            "id": inv.id,
            "email": inv.email,
            "accepted": inv.accepted,
            "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
            "created_at": inv.created_at.isoformat(),
            "supplier_name": supplier.full_name if supplier else None,
            "supplier_org": supplier.organization.name if supplier and supplier.organization else None
        })
    
    return jsonify(result)


@bp.post("/invites/accept/<token>")
@require_role(["FORNECEDOR"])
def accept_invite(token: str):
    """Fornecedor aceita convite"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    invite = Invite.query.filter_by(token=token).first()
    if not invite:
        return {"error": "Convite inválido"}, 404
    
    if invite.email != user.email:
        return {"error": "Convite não pertence a este usuário"}, 403
    
    if invite.accepted:
        return {"error": "Convite já foi aceito"}, 400
    
    invite.accepted = True
    invite.accepted_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="INVITE_ACCEPTED",
        entity_type="Invite",
        entity_id=invite.id,
        details={"procurement_id": invite.procurement_id}
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notificar comprador
    socketio.emit("invite.accepted", {
        "procurement_id": invite.procurement_id,
        "supplier": user.full_name,
        "email": user.email
    }, to=f"proc:{invite.procurement_id}")
    
    return {
        "message": "Convite aceito com sucesso",
        "procurement_id": invite.procurement_id
    }


@bp.post("/procurements/<int:proc_id>/close")
@require_role(["COMPRADOR"])
def close_procurement(proc_id: int):
    """Fecha processo para análise"""
    ident = get_jwt_identity()
    proc = Procurement.query.get_or_404(proc_id)
    
    if proc.status != ProcurementStatus.ABERTO:
        return {"error": "Processo não está aberto"}, 400
    
    proc.status = ProcurementStatus.ANALISE_TECNICA
    proc.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=ident["user_id"],
        action="PROCUREMENT_CLOSED",
        entity_type="Procurement",
        entity_id=proc.id
    )
    db.session.add(audit)
    db.session.commit()
    
    socketio.emit("procurement.closed", {
        "procurement_id": proc.id,
        "title": proc.title
    }, to=f"proc:{proc.id}")
    
    return {
        "message": "Processo fechado para análise",
        "procurement_id": proc.id,
        "status": proc.status.value
    }


@bp.get("/procurements/<int:proc_id>/comparison")
@require_role(["COMPRADOR"])
def get_proposals_comparison(proc_id: int):
    """Análise comparativa de propostas com IA"""
    proc = Procurement.query.get_or_404(proc_id)
    
    # Buscar apenas propostas aprovadas tecnicamente
    proposals = Proposal.query.filter_by(
        procurement_id=proc_id,
        status=ProposalStatus.APROVADA_TECNICAMENTE
    ).all()
    
    if not proposals:
        return {"error": "Nenhuma proposta aprovada tecnicamente"}, 404
    
    comparison = []
    for prop in proposals:
        # Calcular total da proposta
        total_price = 0
        items_detail = []
        
        for service in prop.service_items:
            price = ProposalPrice.query.filter_by(
                proposal_id=prop.id,
                service_item_id=service.service_item_id
            ).first()
            
            if price:
                item_total = float(service.qty) * float(price.unit_price)
                total_price += item_total
                
                tr_item = TRServiceItem.query.get(service.service_item_id)
                items_detail.append({
                    "descricao": tr_item.descricao,
                    "qty": float(service.qty),
                    "unit_price": float(price.unit_price),
                    "total": item_total
                })
        
        comparison.append({
            "proposal_id": prop.id,
            "supplier": prop.supplier.full_name,
            "organization": prop.supplier.organization.name if prop.supplier.organization else None,
            "technical_score": prop.technical_score or 0,
            "total_price": round(total_price, 2),
            "delivery_time": prop.delivery_time,
            "payment_conditions": prop.payment_conditions,
            "warranty_terms": prop.warranty_terms,
            "technical_review": prop.technical_review,
            "items": items_detail,
            "cost_benefit_score": (prop.technical_score or 0) / total_price if total_price > 0 else 0
        })
    
    # Ordenar por melhor custo-benefício
    comparison.sort(key=lambda x: x["cost_benefit_score"], reverse=True)
    
    # Análise com IA (simulada - você pode integrar com OpenAI/Claude API)
    best_price = min(comparison, key=lambda x: x["total_price"])
    best_technical = max(comparison, key=lambda x: x["technical_score"])
    best_overall = comparison[0] if comparison else None
    
    # Calcular médias
    avg_price = sum(p["total_price"] for p in comparison) / len(comparison)
    avg_score = sum(p["technical_score"] for p in comparison) / len(comparison)
    
    ai_analysis = {
        "summary": {
            "total_proposals": len(comparison),
            "average_price": round(avg_price, 2),
            "average_technical_score": round(avg_score, 1),
            "price_range": {
                "min": best_price["total_price"],
                "max": max(comparison, key=lambda x: x["total_price"])["total_price"]
            }
        },
        "best_options": {
            "best_price": {
                "supplier": best_price["supplier"],
                "price": best_price["total_price"],
                "savings": round(avg_price - best_price["total_price"], 2)
            },
            "best_technical": {
                "supplier": best_technical["supplier"],
                "score": best_technical["technical_score"],
                "price": best_technical["total_price"]
            },
            "best_overall": {
                "supplier": best_overall["supplier"],
                "score": best_overall["technical_score"],
                "price": best_overall["total_price"],
                "reason": "Melhor equilíbrio entre qualidade técnica e preço"
            } if best_overall else None
        },
        "recommendations": [
            f"A proposta de {best_overall['supplier']} oferece o melhor custo-benefício" if best_overall else "",
            f"Economia potencial de R$ {round(avg_price - best_price['total_price'], 2)} escolhendo o menor preço",
            "Considere os prazos de entrega conforme urgência do projeto",
            "Verifique as condições de pagamento e garantia antes da decisão final",
            "Avalie se a diferença de qualidade técnica justifica diferenças de preço"
        ],
        "risk_analysis": {
            "lowest_price_risk": "Baixo" if best_price["technical_score"] >= 70 else "Médio",
            "delivery_risk": "Avaliar prazos individualmente",
            "quality_risk": "Baixo" if avg_score >= 75 else "Médio"
        }
    }
    
    return {
        "proposals": comparison,
        "ai_analysis": ai_analysis,
        "generated_at": datetime.utcnow().isoformat()
    }


@bp.get("/procurements/<int:proc_id>/proposals")
@require_role(["COMPRADOR", "REQUISITANTE"])
def list_procurement_proposals(proc_id: int):
    """Lista todas as propostas do processo"""
    ident = get_jwt_identity()
    user = User.query.get(ident["user_id"])
    
    proposals = Proposal.query.filter_by(procurement_id=proc_id).all()
    
    result = []
    for prop in proposals:
        # Requisitante não vê valores
        include_prices = user.role == Role.COMPRADOR
        
        prop_data = {
            "id": prop.id,
            "supplier": {
                "name": prop.supplier.full_name,
                "organization": prop.supplier.organization.name if prop.supplier.organization else None
            },
            "status": prop.status.value,
            "technical_score": prop.technical_score,
            "technical_review": prop.technical_review,
            "submitted_at": prop.technical_submitted_at.isoformat() if prop.technical_submitted_at else None
        }
        
        if include_prices:
            # Calcular total
            total = 0
            for service in prop.service_items:
                price = ProposalPrice.query.filter_by(
                    proposal_id=prop.id,
                    service_item_id=service.service_item_id
                ).first()
                if price:
                    total += float(service.qty) * float(price.unit_price)
            
            prop_data["total_value"] = round(total, 2)
            prop_data["payment_conditions"] = prop.payment_conditions
            prop_data["delivery_time"] = prop.delivery_time
        
        result.append(prop_data)
    
    return jsonify(result)
