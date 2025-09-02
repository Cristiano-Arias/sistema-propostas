# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select
from .. import db, socketio
from ..models import Proposal, ProposalService, ProposalPrice, TRServiceItem, Role
from .procurements import require_role

bp = Blueprint("proposals", __name__)


def _get_or_create_proposal(procurement_id: int, supplier_user_id: int) -> Proposal:
    p = Proposal.query.filter_by(procurement_id=procurement_id, supplier_user_id=supplier_user_id).first()
    if not p:
        p = Proposal(procurement_id=procurement_id, supplier_user_id=supplier_user_id, status="RASCUNHO")
        db.session.add(p)
        db.session.commit()
    return p


@bp.put("/proposals/<int:proc_id>/service-qty")
@require_role(["FORNECEDOR"])
def upsert_quantities(proc_id: int):
    ident = get_jwt_identity()
    prop = _get_or_create_proposal(proc_id, ident["user_id"])
    payload = request.get_json() or []
    if not isinstance(payload, list):
        return {"error": "payload deve ser lista de itens"}, 400

    # Verifica se service_item pertence ao TR do mesmo processo (segurança leve no app)
    valid_item_ids = {r.id for r in TRServiceItem.query.join(TRServiceItem.tr).filter_by(procurement_id=proc_id).all()}

    for row in payload:
        sid = row.get("service_item_id")
        qty = row.get("qty")
        if sid not in valid_item_ids:
            return {"error": f"service_item_id {sid} invalido para este processo"}, 400
        ps = ProposalService.query.filter_by(proposal_id=prop.id, service_item_id=sid).first()
        if not ps:
            ps = ProposalService(proposal_id=prop.id, service_item_id=sid, qty=qty)
            db.session.add(ps)
        else:
            ps.qty = qty

    db.session.commit()
    socketio.emit("proposal.tech.received", {"procurement_id": proc_id, "proposal_id": prop.id}, to=f"proc:{proc_id}")
    return {"proposal_id": prop.id, "items": len(payload)}


@bp.put("/proposals/<int:proc_id>/prices")
@require_role(["FORNECEDOR"])
def upsert_prices(proc_id: int):
    ident = get_jwt_identity()
    prop = _get_or_create_proposal(proc_id, ident["user_id"])
    payload = request.get_json() or []
    if not isinstance(payload, list):
        return {"error": "payload deve ser lista de itens"}, 400

    # Apenas preços; quantidade vem de ProposalService
    valid_item_ids = {r.id for r in TRServiceItem.query.join(TRServiceItem.tr).filter_by(procurement_id=proc_id).all()}

    for row in payload:
        sid = row.get("service_item_id")
        price = row.get("unit_price")
        if sid not in valid_item_ids:
            return {"error": f"service_item_id {sid} invalido para este processo"}, 400
        pp = ProposalPrice.query.filter_by(proposal_id=prop.id, service_item_id=sid).first()
        if not pp:
            pp = ProposalPrice(proposal_id=prop.id, service_item_id=sid, unit_price=price)
            db.session.add(pp)
        else:
            pp.unit_price = price

    db.session.commit()
    socketio.emit("proposal.comm.received", {"procurement_id": proc_id, "proposal_id": prop.id}, to=f"proc:{proc_id}")
    return {"proposal_id": prop.id, "items": len(payload)}


@bp.get("/proposals/<int:proc_id>/commercial-items")
@require_role(["COMPRADOR", "REQUISITANTE", "FORNECEDOR"])
def list_commercial_items(proc_id: int):
    """Consolidado por item (JOIN TR baseline + quantidade + preco unitario + total)."""
    ident = get_jwt_identity()
    props = Proposal.query.filter_by(procurement_id=proc_id).all()

    out = []
    for p in props:
        # Se fornecedor, só enxerga sua própria proposta
        if ident["role"] == "FORNECEDOR" and p.supplier_user_id != ident["user_id"]:
            continue

        items = db.session.query(
            TRServiceItem.item_ordem,
            TRServiceItem.codigo,
            TRServiceItem.descricao,
            TRServiceItem.unid,
            ProposalService.qty,
            ProposalPrice.unit_price,
        ).outerjoin(ProposalService, (ProposalService.service_item_id == TRServiceItem.id) & (ProposalService.proposal_id == p.id))\
         .outerjoin(ProposalPrice, (ProposalPrice.service_item_id == TRServiceItem.id) & (ProposalPrice.proposal_id == p.id))\
         .filter(TRServiceItem.tr.has(procurement_id=proc_id)).order_by(TRServiceItem.item_ordem).all()

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
