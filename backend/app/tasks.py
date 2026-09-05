import json
import logging
from typing import Dict, Any, Optional
from sqlmodel import Session
from app.db import engine
from app.models import RecoveryCase, CaseStatus, Payment, Checkout, Subscription, Invoice, Customer
from app.ai import classify_case
from app.services.guardrails import validate_action
from app.simulator import execute_recovery_action

logger = logging.getLogger(__name__)

def build_full_case_payload(case: RecoveryCase, session: Session) -> Dict[str, Any]:
    c_type = case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type)
    payload = {
        "case_id": case.id,
        "case_type": c_type,
        "customer_id": case.customer_id,
        "amount_at_risk": float(case.amount_at_risk),
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
    }

    # Fetch Customer customer_type
    customer = session.get(Customer, case.customer_id)
    if customer:
        payload["customer_type"] = getattr(customer, "customer_type", "INDIVIDUAL")

    # Fetch source record metadata based on case_type & source_id
    if c_type == "FAILED_PAYMENT" and case.source_id:
        payment = session.get(Payment, case.source_id)
        if payment:
            payload["failure_reason"] = payment.failure_reason or ""
            payload["payment_method"] = payment.payment_method or ""
    elif c_type == "ABANDONED_CHECKOUT" and case.source_id:
        checkout = session.get(Checkout, case.source_id)
        if checkout:
            payload["abandoned_step"] = checkout.abandoned_step or "PAYMENT_METHOD"
    elif c_type == "FAILED_SUBSCRIPTION" and case.source_id:
        sub = session.get(Subscription, case.source_id)
        if sub:
            payload["plan_name"] = sub.plan_name or "PRO"
    elif c_type == "OVERDUE_INVOICE" and case.source_id:
        inv = session.get(Invoice, case.source_id)
        if inv and inv.due_date:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            due = inv.due_date if inv.due_date.tzinfo else inv.due_date.replace(tzinfo=timezone.utc)
            days = (now - due).days
            payload["days_overdue"] = max(1, days)
        else:
            payload["days_overdue"] = 30

    return payload

def process_case(case_id: int, batch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    RQ Worker task: Processes an at-risk RecoveryCase by case_id through the pipeline:
    classify_case -> validate_action -> execute_recovery_action (if APPROVED).
    Publishes SSE JSON event payload to Redis Pub/Sub.
    """
    import time
    start_time = time.time()
    logger.info(f"[WORKER START] Processing Case #{case_id} for batch_id='{batch_id}'")

    with Session(engine) as session:
        case = session.get(RecoveryCase, case_id)
        if not case:
            logger.error(f"Worker task failed: Case #{case_id} not found in database.")
            return {
                "case_id": case_id,
                "status": "NOT_FOUND",
                "error": f"Case #{case_id} not found"
            }

        if case.status in [CaseStatus.RECOVERED, CaseStatus.ESCALATED, CaseStatus.UNRECOVERABLE]:
            logger.info(f"Case #{case_id} already resolved (status={case.status.value if hasattr(case.status, 'value') else case.status}). Skipping duplicate processing.")
            return {
                "case_id": case_id,
                "status": "SKIPPED_ALREADY_PROCESSED",
                "case_status": case.status.value if hasattr(case.status, "value") else str(case.status),
                "message": "Case already resolved or processed."
            }

        # Update case status to PROCESSING
        case.status = CaseStatus.PROCESSING
        session.add(case)
        session.commit()
        session.refresh(case)

        # Build full rich case payload with source metadata
        case_payload = build_full_case_payload(case, session)

        # Step 1: AI Classification
        ai_decision = classify_case(case_payload)
        case.root_cause = ai_decision.get("root_cause")
        case.recommended_action = ai_decision.get("recommended_action")
        case.ai_confidence = ai_decision.get("confidence")
        dec_src = ai_decision.get("decision_source", "AI_PRIMARY")
        case.decision_source = dec_src.value if hasattr(dec_src, "value") else str(dec_src)
        session.add(case)
        session.commit()
        session.refresh(case)

        # Step 2: Guardrail Validation
        guardrail_result = validate_action(case, ai_decision, attempt_count=0, session=session)
        is_approved = (guardrail_result.get("decision") == "APPROVED")

        # Step 3: Execution / Action Simulator (Only if APPROVED by Guardrails)
        sim_result = None
        if is_approved:
            sim_result = execute_recovery_action(
                case,
                ai_decision["recommended_action"],
                session=session,
                guardrail_decision=guardrail_result["decision"]
            )
            logger.info(f"Case #{case_id} processed successfully: APPROVED & EXECUTED ({sim_result.get('outcome')})")
            res_payload = {
                "case_id": case_id,
                "status": "APPROVED_AND_EXECUTED",
                "ai_decision": ai_decision,
                "guardrail_result": guardrail_result,
                "execution_result": sim_result,
                "simulated": True
            }
        else:
            # Handle blocked case status
            if guardrail_result["route"] == "CLOSED":
                case.status = CaseStatus.UNRECOVERABLE
            elif guardrail_result["route"] in ["ESCALATE", "HUMAN_REVIEW"]:
                case.status = CaseStatus.ESCALATED
            else:
                case.status = CaseStatus.PROCESSING

            session.add(case)
            session.commit()

            logger.info(f"Case #{case_id} processed: BLOCKED by guardrail ({guardrail_result.get('rule_triggered')})")
            res_payload = {
                "case_id": case_id,
                "status": "BLOCKED",
                "ai_decision": ai_decision,
                "guardrail_result": guardrail_result,
                "execution_result": None,
                "simulated": False
            }

        # Publish SSE event payload for live streaming
        amount_recovered = float(sim_result.get("recovered_amount", 0.0)) if (is_approved and sim_result) else 0.0

        sse_event = {
            "batch_id": batch_id,
            "case_id": case.id,
            "case_type": case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type),
            "action": ai_decision.get("recommended_action", "UNKNOWN"),
            "approved": is_approved,
            "amount_recovered": amount_recovered,
            "route": guardrail_result.get("route", "HUMAN_REVIEW"),
            "decision_source": case.decision_source.value if hasattr(case.decision_source, "value") else str(case.decision_source)
        }

        if batch_id:
            try:
                from app.queue import get_redis_connection
                r = get_redis_connection()
                r.publish(f"batch_events:{batch_id}", json.dumps(sse_event))
                r.publish("batch_events_global", json.dumps(sse_event))
            except Exception as e:
                logger.exception(f"[SSE PUBLISH ERROR] Failed to publish batch event for batch '{batch_id}', case #{case.id}: {e}")

        res_payload["sse_event"] = sse_event
        elapsed = time.time() - start_time
        logger.info(f"[WORKER FINISH] Completed Case #{case_id} for batch_id='{batch_id}' in {elapsed:.2f}s (result={res_payload.get('status')})")
        return res_payload
