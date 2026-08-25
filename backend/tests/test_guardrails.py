from datetime import datetime, timezone
from sqlmodel import select
from app.models import Customer, RecoveryCase, GuardrailEvent, CaseType, CaseStatus, GuardrailDecision
from app.services.guardrails import validate_action

def test_rule_1_already_closed(session):
    cust = Customer(external_id="c1", name="Test Customer 1", email="c1@test.com")
    session.add(cust)
    session.flush()

    case = RecoveryCase(
        case_type=CaseType.FAILED_PAYMENT,
        source_id=1,
        customer_id=cust.id,
        amount_at_risk=100.0,
        status=CaseStatus.RECOVERED,
        resolved_at=datetime.now(timezone.utc)
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    result = validate_action(case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.95}, attempt_count=0, session=session)

    assert result["decision"] == GuardrailDecision.BLOCKED.value
    assert result["route"] == "CLOSED"
    assert result["rule_triggered"] == "RULE_1_CASE_ALREADY_CLOSED"

    # Assert GuardrailEvent row created
    event = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == case.id)).first()
    assert event is not None
    assert event.decision == GuardrailDecision.BLOCKED

def test_rule_2_amount_threshold(session):
    cust = Customer(external_id="c2", name="Test Customer 2", email="c2@test.com")
    session.add(cust)
    session.flush()

    case = RecoveryCase(
        case_type=CaseType.OVERDUE_INVOICE,
        source_id=2,
        customer_id=cust.id,
        amount_at_risk=600000.0,
        status=CaseStatus.DETECTED
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    result = validate_action(case, {"recommended_action": "SEND_REMINDER", "confidence": 0.90}, attempt_count=0, session=session)

    assert result["decision"] == GuardrailDecision.BLOCKED.value
    assert result["route"] == "HUMAN_REVIEW"
    assert result["rule_triggered"] == "RULE_2_EXCEEDS_MAX_AUTO_APPROVAL_AMOUNT"

    event = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == case.id)).first()
    assert event is not None
    assert event.decision == GuardrailDecision.BLOCKED

def test_rule_3_retry_limit(session):
    cust = Customer(external_id="c3", name="Test Customer 3", email="c3@test.com")
    session.add(cust)
    session.flush()

    case = RecoveryCase(
        case_type=CaseType.FAILED_PAYMENT,
        source_id=3,
        customer_id=cust.id,
        amount_at_risk=150.0,
        status=CaseStatus.DETECTED
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    result = validate_action(case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.90}, attempt_count=3, session=session)

    assert result["decision"] == GuardrailDecision.BLOCKED.value
    assert result["route"] == "ESCALATE"
    assert result["rule_triggered"] == "RULE_3_MAX_RETRIES_EXCEEDED"

    event = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == case.id)).first()
    assert event is not None
    assert event.decision == GuardrailDecision.BLOCKED

def test_rule_4_low_confidence(session):
    cust = Customer(external_id="c4", name="Test Customer 4", email="c4@test.com")
    session.add(cust)
    session.flush()

    case = RecoveryCase(
        case_type=CaseType.FAILED_PAYMENT,
        source_id=4,
        customer_id=cust.id,
        amount_at_risk=200.0,
        status=CaseStatus.DETECTED
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    result = validate_action(case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.45}, attempt_count=1, session=session)

    assert result["decision"] == GuardrailDecision.BLOCKED.value
    assert result["route"] == "HUMAN_REVIEW"
    assert result["rule_triggered"] == "RULE_4_LOW_CONFIDENCE"

    event = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == case.id)).first()
    assert event is not None
    assert event.decision == GuardrailDecision.BLOCKED

def test_rule_5_happy_path(session):
    cust = Customer(external_id="c5", name="Test Customer 5", email="c5@test.com")
    session.add(cust)
    session.flush()

    case = RecoveryCase(
        case_type=CaseType.FAILED_PAYMENT,
        source_id=5,
        customer_id=cust.id,
        amount_at_risk=250.0,
        status=CaseStatus.DETECTED
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    result = validate_action(case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.85}, attempt_count=1, session=session)

    assert result["decision"] == GuardrailDecision.APPROVED.value
    assert result["route"] == "AUTO_EXECUTE"
    assert result["rule_triggered"] == "RULE_5_AUTO_EXECUTE_PASSED"

    event = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == case.id)).first()
    assert event is not None
    assert event.decision == GuardrailDecision.APPROVED
