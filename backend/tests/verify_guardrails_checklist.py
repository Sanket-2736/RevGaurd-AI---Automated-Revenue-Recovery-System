from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.models import Customer, RecoveryCase, GuardrailEvent, CaseType, CaseStatus, GuardrailDecision
from app.services.guardrails import validate_action

def run_guardrails_checklist():
    print("=== STARTING GUARDRAILS AUDIT & CHECKLIST VERIFICATION ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        cust = Customer(external_id="cust_ledger", name="Ledger Test Customer", email="ledger@example.com")
        session.add(cust)
        session.flush()

        active_case = RecoveryCase(
            case_type=CaseType.FAILED_PAYMENT,
            source_id=10,
            customer_id=cust.id,
            amount_at_risk=200.0,
            status=CaseStatus.DETECTED
        )

        closed_case = RecoveryCase(
            case_type=CaseType.FAILED_PAYMENT,
            source_id=11,
            customer_id=cust.id,
            amount_at_risk=200.0,
            status=CaseStatus.RECOVERED
        )

        high_case = RecoveryCase(
            case_type=CaseType.OVERDUE_INVOICE,
            source_id=12,
            customer_id=cust.id,
            amount_at_risk=750000.0,
            status=CaseStatus.DETECTED
        )

        session.add_all([active_case, closed_case, high_case])
        session.commit()
        session.refresh(active_case)
        session.refresh(closed_case)
        session.refresh(high_case)

        # Count initial GuardrailEvent rows
        initial_event_count = len(session.exec(select(GuardrailEvent)).all())
        assert initial_event_count == 0
        print("Initial GuardrailEvent DB Count: 0")

        print("\n--- 1. Testing Rule 1 (Closed Case) ---")
        res1 = validate_action(closed_case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.9}, attempt_count=0, session=session)
        assert res1["decision"] == "BLOCKED"
        assert res1["route"] == "CLOSED"
        assert res1["rule_triggered"] == "RULE_1_CASE_ALREADY_CLOSED"
        assert "closed" in res1["reason"].lower() or "resolved" in res1["reason"].lower()
        print("Rule 1 verified: Blocked for exact reason ->", res1["reason"])

        print("\n--- 2. Testing Rule 2 (Exceeds Max Amount) ---")
        res2 = validate_action(high_case, {"recommended_action": "SEND_REMINDER", "confidence": 0.9}, attempt_count=0, session=session)
        assert res2["decision"] == "BLOCKED"
        assert res2["route"] == "HUMAN_REVIEW"
        assert res2["rule_triggered"] == "RULE_2_EXCEEDS_MAX_AUTO_APPROVAL_AMOUNT"
        assert "exceeds" in res2["reason"].lower()
        print("Rule 2 verified: Blocked for exact reason ->", res2["reason"])

        print("\n--- 3. Testing Rule 3 (Max Retries Exceeded) ---")
        res3 = validate_action(active_case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.9}, attempt_count=3, session=session)
        assert res3["decision"] == "BLOCKED"
        assert res3["route"] == "ESCALATE"
        assert res3["rule_triggered"] == "RULE_3_MAX_RETRIES_EXCEEDED"
        assert "retry" in res3["reason"].lower() or "limit" in res3["reason"].lower()
        print("Rule 3 verified: Blocked for exact reason ->", res3["reason"])

        print("\n--- 4. Testing Rule 4 (Low AI Confidence) ---")
        res4 = validate_action(active_case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.45}, attempt_count=1, session=session)
        assert res4["decision"] == "BLOCKED"
        assert res4["route"] == "HUMAN_REVIEW"
        assert res4["rule_triggered"] == "RULE_4_LOW_CONFIDENCE"
        assert "confidence" in res4["reason"].lower()
        print("Rule 4 verified: Blocked for exact reason ->", res4["reason"])

        print("\n--- 5. Testing Rule 5 (Healthy Approved Case) ---")
        res5 = validate_action(active_case, {"recommended_action": "RETRY_PAYMENT", "confidence": 0.85}, attempt_count=1, session=session)
        assert res5["decision"] == "APPROVED"
        assert res5["route"] == "AUTO_EXECUTE"
        assert res5["rule_triggered"] == "RULE_5_AUTO_EXECUTE_PASSED"
        print("Rule 5 verified: Approved cleanly ->", res5["reason"])

        # ----------------------------------------------------
        # Verify Complete Ledger Audit Trail
        # ----------------------------------------------------
        print("\n--- 6. Verifying Complete GuardrailEvent Ledger Audit Trail ---")
        events = session.exec(select(GuardrailEvent)).all()
        print(f"Total GuardrailEvent rows in database: {len(events)}")
        assert len(events) == 5, f"Expected exactly 5 event rows, got {len(events)}"

        # Check approved case event does NOT read as a block
        approved_event = session.exec(select(GuardrailEvent).where(GuardrailEvent.rule_triggered == "RULE_5_AUTO_EXECUTE_PASSED")).first()
        assert approved_event is not None
        assert approved_event.decision == GuardrailDecision.APPROVED
        assert "passed" in approved_event.reason.lower()
        print("Verified: Approved case writes decision=APPROVED into the ledger and does NOT read as a block!")

        blocked_events = [e for e in events if e.decision == GuardrailDecision.BLOCKED]
        approved_events = [e for e in events if e.decision == GuardrailDecision.APPROVED]
        assert len(blocked_events) == 4
        assert len(approved_events) == 1

        print(f"Ledger Summary: {len(events)} total evaluations logged ({len(approved_events)} APPROVED, {len(blocked_events)} BLOCKED).")
        print("\n=== ALL GUARDRAILS CHECKLIST VERIFICATION ITEMS PASSED! ===")

if __name__ == "__main__":
    run_guardrails_checklist()
