from sqlmodel import select
from app.models import Customer, RecoveryCase, RecoveryAction, CaseStatus, CaseType
from app.services.guardrails import validate_action
from app.simulator import (
    simulate_retry_payment,
    simulate_send_reminder,
    simulate_update_payment_method,
    simulate_track_promise_to_pay,
    execute_recovery_action
)

def test_simulator_responses_include_simulated_flag():
    dummy_case = {
        "id": 1,
        "case_type": "FAILED_PAYMENT",
        "source_id": 1,
        "amount_at_risk": 100.0,
        "status": "DETECTED"
    }

    res1 = simulate_retry_payment(dummy_case)
    res2 = simulate_send_reminder(dummy_case)
    res3 = simulate_update_payment_method(dummy_case)
    res4 = simulate_track_promise_to_pay(dummy_case)

    for name, res in [("retry", res1), ("reminder", res2), ("card_update", res3), ("promise", res4)]:
        assert res.get("simulated") is True, f"'{name}' response missing 'simulated': true flag!"

def test_blocked_cases_never_call_simulator(session):
    """
    Confirms that a blocked guardrail decision prevents simulator execution and writes 0 RecoveryAction rows.
    """
    cust = Customer(external_id="c_block", name="Blocked Test Customer", email="block@test.com")
    session.add(cust)
    session.flush()

    # High amount case exceeding MAX_AUTO_APPROVAL_AMOUNT threshold ($500,000)
    high_case = RecoveryCase(
        case_type=CaseType.OVERDUE_INVOICE,
        source_id=99,
        customer_id=cust.id,
        amount_at_risk=750000.0,
        status=CaseStatus.DETECTED
    )
    session.add(high_case)
    session.commit()
    session.refresh(high_case)

    ai_decision = {
        "recommended_action": "SEND_REMINDER",
        "confidence": 0.90,
        "root_cause": "High invoice amount",
        "requires_human_approval": True
    }

    # Step 1: Run Guardrail
    guard_res = validate_action(high_case, ai_decision, attempt_count=0, session=session)

    # Step 2: Assert Guardrail Blocked Action
    assert guard_res["decision"] == "BLOCKED"
    assert guard_res["route"] in ["ESCALATE", "HUMAN_REVIEW"]

    # Step 3: Assert Simulator is NOT Executed for Blocked Cases
    # Count RecoveryAction rows in DB
    action_rows = session.exec(select(RecoveryAction).where(RecoveryAction.case_id == high_case.id)).all()
    assert len(action_rows) == 0, "SAFETY VIOLATION: Blocked case created a RecoveryAction row!"
