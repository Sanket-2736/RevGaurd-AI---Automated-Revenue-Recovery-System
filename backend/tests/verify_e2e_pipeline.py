import json
from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.models import Customer, RecoveryCase, GuardrailEvent, RecoveryAction, CaseStatus, CaseType, GuardrailDecision
from app.ai import classify_case
from app.services.guardrails import validate_action
from app.simulator import execute_recovery_action

def run_pipeline_for_case(case_id: int, session: Session) -> dict:
    """
    Executes the end-to-end pipeline for a RecoveryCase:
    1. Fetch case & customer details
    2. Classify case using AI (OpenRouter / fallback)
    3. Validate action through Guardrails engine
    4. IF APPROVED: Execute recovery action in Simulator
    5. IF BLOCKED: Assert simulator is NEVER called & return guardrail blockage payload
    """
    case = session.get(RecoveryCase, case_id)
    assert case is not None, f"RecoveryCase #{case_id} not found"

    # Step 1: Classify Case
    case_payload = {
        "case_id": case.id,
        "case_type": case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type),
        "customer_id": case.customer_id,
        "amount_at_risk": case.amount_at_risk,
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
    }

    ai_decision = classify_case(case_payload)

    # Update case with AI classification details
    case.root_cause = ai_decision.get("root_cause")
    case.recommended_action = ai_decision.get("recommended_action")
    case.ai_confidence = ai_decision.get("confidence")
    session.add(case)
    session.commit()
    session.refresh(case)

    # Step 2: Run Guardrail Safety Check
    guardrail_result = validate_action(case, ai_decision, attempt_count=0, session=session)

    # Step 3: Branch on Guardrail Decision
    if guardrail_result["decision"] == "APPROVED":
        # Execute simulator
        sim_result = execute_recovery_action(case, ai_decision["recommended_action"], session=session)
        assert sim_result.get("simulated") is True, "CRITICAL ERROR: 'simulated': true missing from simulator payload!"

        return {
            "case_id": case.id,
            "status": "APPROVED_AND_EXECUTED",
            "ai_decision": ai_decision,
            "guardrail_result": guardrail_result,
            "execution_result": sim_result,
            "simulated": True
        }
    else:
        # STRICT SAFETY ASSERTION: Blocked cases MUST NOT call the simulator!
        # Update case status to ESCALATED or PROCESSING for human review
        if guardrail_result["route"] == "CLOSED":
            case.status = CaseStatus.UNRECOVERABLE
        elif guardrail_result["route"] == "ESCALATE":
            case.status = CaseStatus.ESCALATED
        else:
            case.status = CaseStatus.PROCESSING

        session.add(case)
        session.commit()

        print(f"[SAFETY GUARDRAIL BLOCKED] Case #{case.id} blocked by {guardrail_result['rule_triggered']}. Simulator invocation SKIPPED.")

        return {
            "case_id": case.id,
            "status": "BLOCKED",
            "ai_decision": ai_decision,
            "guardrail_result": guardrail_result,
            "execution_result": None,
            "simulated": False
        }

def test_end_to_end_pipeline():
    print("=== STARTING END-TO-END PIPELINE (CLASSIFY -> GUARDRAIL -> SIMULATE) VERIFICATION ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        cust = Customer(external_id="cust_e2e", name="E2E Pipeline Customer", email="e2e@example.com")
        session.add(cust)
        session.flush()

        # 1. Normal Healthy Case ($120.00)
        approved_case = RecoveryCase(
            case_type=CaseType.FAILED_PAYMENT,
            source_id=1,
            customer_id=cust.id,
            amount_at_risk=120.00,
            status=CaseStatus.DETECTED
        )

        # 2. Risky High-Amount Case ($750,000.00)
        blocked_case = RecoveryCase(
            case_type=CaseType.OVERDUE_INVOICE,
            source_id=2,
            customer_id=cust.id,
            amount_at_risk=750000.00,
            status=CaseStatus.DETECTED
        )

        session.add_all([approved_case, blocked_case])
        session.commit()
        session.refresh(approved_case)
        session.refresh(blocked_case)

        # ----------------------------------------------------
        # RUN APPROVED CASE PIPELINE
        # ----------------------------------------------------
        print("\n--- TEST 1: End-to-End Approved Case Flow ---")
        app_res = run_pipeline_for_case(approved_case.id, session)
        print("Approved Pipeline Response JSON:", json.dumps(app_res, indent=2, default=str))

        # Check API Response contains "simulated": true
        assert app_res.get("simulated") is True, "API Response must contain 'simulated': true!"
        assert app_res["execution_result"]["simulated"] is True

        # Check matching rows across all 3 tables for Approved Case
        db_case1 = session.get(RecoveryCase, approved_case.id)
        db_gevent1 = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == approved_case.id)).first()
        db_action1 = session.exec(select(RecoveryAction).where(RecoveryAction.case_id == approved_case.id)).first()

        assert db_case1 is not None and db_case1.status != CaseStatus.DETECTED
        assert db_gevent1 is not None and db_gevent1.decision == GuardrailDecision.APPROVED
        assert db_action1 is not None and "simulated" in db_action1.payload

        print("PASSED: Approved case successfully created matching rows across RecoveryCase, GuardrailEvent, and RecoveryAction tables!")

        # ----------------------------------------------------
        # RUN BLOCKED CASE PIPELINE (BLOCKED CASE MUST NOT REACH SIMULATOR)
        # ----------------------------------------------------
        print("\n--- TEST 2: End-to-End Blocked Case Flow (Safety Check) ---")
        block_res = run_pipeline_for_case(blocked_case.id, session)
        print("Blocked Pipeline Response JSON:", json.dumps(block_res, indent=2, default=str))

        assert block_res["status"] == "BLOCKED"
        assert block_res["execution_result"] is None

        # Verify Database Tables for Blocked Case
        db_case2 = session.get(RecoveryCase, blocked_case.id)
        db_gevent2 = session.exec(select(GuardrailEvent).where(GuardrailEvent.case_id == blocked_case.id)).first()
        db_action2 = session.exec(select(RecoveryAction).where(RecoveryAction.case_id == blocked_case.id)).first()

        assert db_case2 is not None
        assert db_gevent2 is not None and db_gevent2.decision == GuardrailDecision.BLOCKED
        assert db_gevent2.rule_triggered == "RULE_2_EXCEEDS_MAX_AUTO_APPROVAL_AMOUNT"

        # STRICT ASSERTION: Blocked case must NEVER write a RecoveryAction row!
        assert db_action2 is None, "SAFETY VIOLATION: Blocked case created a RecoveryAction row!"

        print("PASSED: Blocked case correctly generated GuardrailEvent(BLOCKED) and NEVER reached the simulator!")

        print("\n=== ALL END-TO-END PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_end_to_end_pipeline()
