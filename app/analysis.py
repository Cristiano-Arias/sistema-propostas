from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from .roles import require_roles
from .models import Proposal
from statistics import mean

bp = Blueprint("analysis", __name__)

@bp.get("/compare")
@jwt_required()
@require_roles("COMPRADOR", "ADMIN")
def compare():
    process_id = int(request.args.get("process_id", 0))
    props = Proposal.query.filter_by(process_id=process_id).all()
    if not props:
        return {"items": [], "summary": {"count": 0}}, 200
    totals = [float(p.total_price) for p in props]
    summary = {
        "count": len(props),
        "min_price": min(totals),
        "max_price": max(totals),
        "avg_price": round(mean(totals), 2),
    }
    items = [{"proposal_id": p.id, "supplier_id": p.supplier_id, "total_price": float(p.total_price), "currency": p.currency} for p in props]
    return {"items": items, "summary": summary}, 200
