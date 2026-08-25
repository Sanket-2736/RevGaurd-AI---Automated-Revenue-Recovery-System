from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk
from app.models import Payment, Checkout, Subscription, Invoice, RecoveryCase, CaseStatus

def run_detection_checklist():
    print("=== STARTING DETECTION CHECKLIST VERIFICATION ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Ingest data
    print("1. Ingesting synthetic data...")
    ingest_all_synthetic_data()

    # Count source at-risk rows directly from source tables
    with Session(engine) as session:
        failed_pay_cnt = len(session.exec(select(Payment).where(Payment.status == "FAILED")).all())
        abandoned_chk_cnt = len(session.exec(select(Checkout).where(Checkout.status == "ABANDONED")).all())
        failed_sub_cnt = len(session.exec(select(Subscription).where(Subscription.status == "FAILED")).all())
        overdue_inv_cnt = len(session.exec(select(Invoice).where(Invoice.status == "OVERDUE")).all())

        total_source_at_risk_count = failed_pay_cnt + abandoned_chk_cnt + failed_sub_cnt + overdue_inv_cnt
        print(f"Source Table At-Risk Counts:")
        print(f"  - Failed Payments: {failed_pay_cnt}")
        print(f"  - Abandoned Checkouts: {abandoned_chk_cnt}")
        print(f"  - Failed Subscriptions: {failed_sub_cnt}")
        print(f"  - Overdue Invoices: {overdue_inv_cnt}")
        print(f"  - TOTAL SOURCE AT-RISK ROWS: {total_source_at_risk_count}")

    # Check 1: First Run
    print("\n2. Executing First Detection Run...")
    with Session(engine) as session:
        res1 = detect_revenue_at_risk(session)
        print("Run 1 Result:", res1)

        # Assertion 1: cases_created matches count of at-risk rows across 4 source tables
        assert res1["cases_created"] == total_source_at_risk_count
        print(f"CHECK 1 PASSED: cases_created ({res1['cases_created']}) matches source at-risk count ({total_source_at_risk_count})!")

        # Assertion 3: total_at_risk matches baseline $376,590.00
        assert res1["total_at_risk"] == 376590.0
        print(f"CHECK 3 PASSED: total_at_risk (${res1['total_at_risk']:,.2f}) matches Phase 2 baseline ($376,590.00)!")

        # Assertion 4: Every RecoveryCase has non-null customer_id, amount_at_risk, case_type
        all_cases = session.exec(select(RecoveryCase)).all()
        assert len(all_cases) == total_source_at_risk_count

        for c in all_cases:
            assert c.customer_id is not None, f"Case {c.id} missing customer_id"
            assert c.amount_at_risk is not None and c.amount_at_risk > 0, f"Case {c.id} invalid amount_at_risk"
            assert c.case_type is not None, f"Case {c.id} missing case_type"
            assert c.status == CaseStatus.DETECTED, f"Case {c.id} unexpected status {c.status}"

        print("CHECK 4 PASSED: Every RecoveryCase has non-null customer_id, amount_at_risk, case_type, and status=DETECTED!")

    # Check 2: Second Run immediately (Idempotency)
    print("\n3. Executing Immediate Second Detection Run (Idempotency)...")
    with Session(engine) as session:
        res2 = detect_revenue_at_risk(session)
        print("Run 2 Result:", res2)

        # Assertion 2: cases_created should be 0
        assert res2["cases_created"] == 0
        assert res2["total_at_risk"] == 376590.0

        cases_after = session.exec(select(RecoveryCase)).all()
        assert len(cases_after) == total_source_at_risk_count

        print("CHECK 2 PASSED: cases_created on second run is 0 (Idempotency verified)!")

    print("\n=== ALL 4 CHECKLIST ITEMS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_detection_checklist()
