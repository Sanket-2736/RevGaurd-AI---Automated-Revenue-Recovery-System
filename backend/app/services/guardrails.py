import os
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from sqlmodel import Session
from app.models import RecoveryCase, GuardrailEvent, GuardrailDecision, CaseStatus

logger = logging.getLogger(__name__)

def get_max_auto_approval_amount() -> float:
    try:
        return float(os.getenv("MAX_AUTO_APPROVAL_AMOUNT", "500000.0"))
    except ValueError:
        return 500000.0

def get_max_retries() -> int:
    try:
        return int(os.getenv("MAX_RETRIES", "3"))
    except ValueError:
        return 3

def get_min_confidence() -> float:
    try:
        return float(os.getenv("MIN_CONFIDENCE", "0.6"))
    except ValueError:
        return 0.6

def validate_action(
    case: Union[RecoveryCase, dict],
    ai_decision: dict,
    attempt_count: int = 0,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Validates an AI-recommended recovery action against 5 sequential safety guardrails:
    1. Case already resolved/paid -> BLOCKED (route=CLOSED)
    2. amount_at_risk > MAX_AUTO_APPROVAL_AMOUNT -> BLOCKED (route=HUMAN_REVIEW)
    3. action == RETRY_PAYMENT and attempt_count >= MAX_RETRIES -> BLOCKED (route=ESCALATE)
    4. confidence < MIN_CONFIDENCE -> BLOCKED (route=HUMAN_REVIEW)
    5. Otherwise -> APPROVED (route=AUTO_EXECUTE)

    Writes a GuardrailEvent database record for every evaluation regardless of outcome.
    Thresholds are dynamically read from environment variables.
    """
    max_amount = get_max_auto_approval_amount()
    max_retries = get_max_retries()
    min_confidence = get_min_confidence()

    # Extract case attributes
    if isinstance(case, dict):
        case_id = case.get("id") or case.get("case_id")
        case_status = case.get("status")
        amount_at_risk = float(case.get("amount_at_risk", 0.0))
        resolved_at = case.get("resolved_at")
    else:
        case_id = case.id
        case_status = case.status
        amount_at_risk = float(case.amount_at_risk)
        resolved_at = case.resolved_at

    # Extract decision attributes
    action = str(ai_decision.get("recommended_action", "")).upper()
    try:
        confidence = float(ai_decision.get("confidence", 0.0))
    except (ValueError, TypeError):
        confidence = 0.0

    # Rule evaluation variables
    decision: GuardrailDecision = GuardrailDecision.BLOCKED
    route: str = "HUMAN_REVIEW"
    rule_triggered: str = ""
    reason: str = ""

    # Rule 1: Case already closed / resolved
    is_closed_status = case_status in [CaseStatus.RECOVERED, CaseStatus.UNRECOVERABLE, "RECOVERED", "UNRECOVERABLE"]
    if is_closed_status or resolved_at is not None:
        decision = GuardrailDecision.BLOCKED
        route = "CLOSED"
        rule_triggered = "RULE_1_CASE_ALREADY_CLOSED"
        reason = f"Case is already resolved or closed (status={case_status})."

    # Rule 2: Exceeds maximum auto-approval threshold
    elif amount_at_risk > max_amount:
        decision = GuardrailDecision.BLOCKED
        route = "HUMAN_REVIEW"
        rule_triggered = "RULE_2_EXCEEDS_MAX_AUTO_APPROVAL_AMOUNT"
        reason = f"Amount at risk (${amount_at_risk:,.2f}) exceeds max auto-approval threshold (${max_amount:,.2f})."

    # Rule 3: Retry attempts limit reached
    elif action in ["RETRY_PAYMENT", "EXECUTE_SMART_RETRY"] and attempt_count >= max_retries:
        decision = GuardrailDecision.BLOCKED


        route = "ESCALATE"
        rule_triggered = "RULE_3_MAX_RETRIES_EXCEEDED"
        reason = f"Payment retry attempts ({attempt_count}) reached or exceeded limit ({max_retries})."

    # Rule 4: Low AI confidence score
    elif confidence < min_confidence:
        decision = GuardrailDecision.BLOCKED
        route = "HUMAN_REVIEW"
        rule_triggered = "RULE_4_LOW_CONFIDENCE"
        reason = f"AI confidence ({confidence:.2f}) is below minimum threshold ({min_confidence:.2f})."

    # Rule 5: Auto-execute approval
    else:
        decision = GuardrailDecision.APPROVED
        route = "AUTO_EXECUTE"
        rule_triggered = "RULE_5_AUTO_EXECUTE_PASSED"
        reason = "All guardrail safety checks passed successfully."

    # Persist GuardrailEvent row to database if session is available
    guardrail_event_id = None
    if session is not None and case_id is not None:
        try:
            event = GuardrailEvent(
                case_id=case_id,
                rule_triggered=rule_triggered,
                decision=decision,
                reason=reason,
                created_at=datetime.now(timezone.utc)
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            guardrail_event_id = event.id
        except Exception as e:
            logger.error(f"Failed to record GuardrailEvent for case {case_id}: {e}")

    logger.info(f"Guardrail check case #{case_id}: decision={decision.value}, route={route}, rule={rule_triggered}")

    return {
        "decision": decision.value if hasattr(decision, "value") else str(decision),
        "route": route,
        "rule_triggered": rule_triggered,
        "reason": reason,
        "guardrail_event_id": guardrail_event_id
    }
