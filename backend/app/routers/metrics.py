import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import RecoveryCase, RecoveryAction, GuardrailEvent, CaseStatus, CaseType, GuardrailDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["metrics"])

@router.get("/metrics")
def get_live_metrics(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Calculates live un-cached recovery metrics directly from database state on every call.
    Returns: {total_at_risk, total_recovered, recovery_rate, by_category, human_escalations, guardrail_blocks}
    """
    cases = session.exec(select(RecoveryCase)).all()
    actions = session.exec(select(RecoveryAction)).all()
    guardrail_events = session.exec(select(GuardrailEvent)).all()

    # Pre-map recovered amounts from RecoveryAction JSON payloads
    action_recovered_map: Dict[int, float] = {}
    for act in actions:
        if act.payload:
            try:
                p_dict = json.loads(act.payload)
                rec_amt = float(p_dict.get("recovered_amount", 0.0))
                if rec_amt > 0:
                    action_recovered_map[act.case_id] = rec_amt
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    total_at_risk = 0.0
    total_recovered = 0.0

    category_stats: Dict[str, Dict[str, Any]] = {
        ct.value if hasattr(ct, "value") else str(ct): {
            "case_count": 0,
            "recovered_count": 0,
            "total_at_risk": 0.0,
            "total_recovered": 0.0,
            "recovery_rate": 0.0
        }
        for ct in CaseType
    }

    for case in cases:
        c_type = case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type)
        amt = float(case.amount_at_risk)

        total_at_risk += amt

        if c_type not in category_stats:
            category_stats[c_type] = {
                "case_count": 0,
                "recovered_count": 0,
                "total_at_risk": 0.0,
                "total_recovered": 0.0,
                "recovery_rate": 0.0
            }

        category_stats[c_type]["case_count"] += 1
        category_stats[c_type]["total_at_risk"] += amt

        # Calculate recovered revenue
        is_recovered = (case.status == CaseStatus.RECOVERED)
        if is_recovered:
            rec_amt = action_recovered_map.get(case.id, amt)
            total_recovered += rec_amt
            category_stats[c_type]["recovered_count"] += 1
            category_stats[c_type]["total_recovered"] += rec_amt

    # Compute percentage recovery rates
    total_at_risk = round(total_at_risk, 2)
    total_recovered = round(total_recovered, 2)
    overall_recovery_rate = round((total_recovered / total_at_risk) * 100.0, 1) if total_at_risk > 0 else 0.0

    for c_key, cat in category_stats.items():
        cat["total_at_risk"] = round(cat["total_at_risk"], 2)
        cat["total_recovered"] = round(cat["total_recovered"], 2)
        cat["recovery_rate"] = round((cat["total_recovered"] / cat["total_at_risk"]) * 100.0, 1) if cat["total_at_risk"] > 0 else 0.0

    # Count escalations & guardrail blocks
    human_escalations = sum(1 for c in cases if c.status == CaseStatus.ESCALATED)
    guardrail_blocks = sum(1 for ge in guardrail_events if ge.decision == GuardrailDecision.BLOCKED)

    return {
        "total_at_risk": total_at_risk,
        "total_recovered": total_recovered,
        "recovery_rate": overall_recovery_rate,
        "by_category": category_stats,
        "human_escalations": human_escalations,
        "guardrail_blocks": guardrail_blocks
    }

@router.get("/cases")
def get_all_cases(
    limit: int = 100,
    status: str = None,
    session: Session = Depends(get_session)
):
    """
    Returns list of recovery cases with customer metadata.
    """
    from app.models import Customer
    query = select(RecoveryCase, Customer).join(Customer, RecoveryCase.customer_id == Customer.id)
    if status:
        query = query.where(RecoveryCase.status == status)
    query = query.order_by(RecoveryCase.id.desc()).limit(limit)
    results = session.exec(query).all()

    cases_out = []
    for case, customer in results:
        cases_out.append({
            "id": case.id,
            "case_type": case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type),
            "status": case.status.value if hasattr(case.status, "value") else str(case.status),
            "amount_at_risk": case.amount_at_risk,
            "root_cause": case.root_cause,
            "recommended_action": case.recommended_action,
            "ai_confidence": case.ai_confidence,
            "customer_name": customer.name,
            "customer_email": customer.email,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None
        })
    return cases_out

@router.get("/events")
def get_guardrail_events(
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Returns list of GuardrailEvent audit records.
    """
    events = session.exec(
        select(GuardrailEvent)
        .order_by(GuardrailEvent.id.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": ge.id,
            "case_id": ge.case_id,
            "rule_triggered": ge.rule_triggered,
            "decision": ge.decision.value if hasattr(ge.decision, "value") else str(ge.decision),
            "reason": ge.reason,
            "created_at": ge.created_at.isoformat() if ge.created_at else None
        }
        for ge in events
    ]

@router.post("/reset")
def reset_demo_state(session: Session = Depends(get_session)):
    """
    Resets demo state by re-ingesting synthetic datasets and re-running detection.
    """
    from app.routers.ingestion import ingest_all_synthetic_data
    from app.services.detection import detect_revenue_at_risk

    ingest_res = ingest_all_synthetic_data()
    detect_res = detect_revenue_at_risk(session)

    return {
        "status": "success",
        "ingested": ingest_res,
        "detection": detect_res
    }

