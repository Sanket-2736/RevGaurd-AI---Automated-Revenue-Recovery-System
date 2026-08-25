from sqlmodel import SQLModel, Session, text
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk

def test_detection_idempotency(engine):
    """
    Verifies that running revenue-at-risk detection twice does not duplicate cases,
    and performs hand SQL verification to confirm exact case_type distribution.
    """
    # Reset DB tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Step 1: Ingest synthetic CSVs into database
    ingest_all_synthetic_data()

    # Step 2: First detection run
    with Session(engine) as session:
        res1 = detect_revenue_at_risk(session)
        assert res1["cases_created"] == 381
        assert res1["total_at_risk"] == 376590.0

        # Hand verification SQL Query 1: Total Count
        total_count = session.exec(text("SELECT COUNT(*) FROM recoverycase")).one()[0]
        assert total_count == 381, f"Expected 381 cases, got {total_count}"

        # Hand verification SQL Query 2: Group By case_type
        distribution_rows = session.exec(text("SELECT case_type, COUNT(*) FROM recoverycase GROUP BY case_type")).all()
        distribution = {row[0]: row[1] for row in distribution_rows}

        print("\n" + "=" * 55)
        print(" HAND SQL VERIFICATION: CASE_TYPE DISTRIBUTION")
        print("=" * 55)
        for c_type, count in sorted(distribution.items()):
            print(f"  {c_type:<25}: {count:>4} cases")
        print("-" * 55)
        print(f"  TOTAL COUNT               : {total_count:>4} cases")
        print("=" * 55 + "\n")

        # Verified SQL distribution from synthetic source tables
        EXPECTED_DISTRIBUTION = {
            "FAILED_PAYMENT": 129,
            "ABANDONED_CHECKOUT": 100,
            "FAILED_SUBSCRIPTION": 73,
            "OVERDUE_INVOICE": 79,
        }

        # Check total count matches sum of categories
        assert sum(distribution.values()) == 381, "Sum of category counts does not equal 381!"

        for c_type, expected_cnt in EXPECTED_DISTRIBUTION.items():
            actual_cnt = distribution.get(c_type, 0)
            assert actual_cnt == expected_cnt, (
                f"Mismatch for case_type '{c_type}': expected {expected_cnt}, got {actual_cnt}"
            )

        # Step 3: Second detection run (Idempotency Check)
        res2 = detect_revenue_at_risk(session)
        assert res2["cases_created"] == 0

        # Verify post-idempotency total count and distribution remain 100% identical
        post_total_count = session.exec(text("SELECT COUNT(*) FROM recoverycase")).one()[0]
        assert post_total_count == 381, f"Expected 381 cases after rerun, got {post_total_count}"

        post_distribution_rows = session.exec(text("SELECT case_type, COUNT(*) FROM recoverycase GROUP BY case_type")).all()
        post_distribution = {row[0]: row[1] for row in post_distribution_rows}

        assert post_distribution == EXPECTED_DISTRIBUTION, "Distribution changed after second detection run!"
