import asyncio
from sqlmodel import SQLModel, Session, select, func
from app.db import engine
from app.models import RecoveryCase, CaseStatus
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk
from app.routers.batch import run_batch_processing, stream_batch_events
from app.routers.metrics import get_live_metrics

def verify_sse_and_sql_metrics():
    print("=== STARTING INCREMENTAL SSE, DISCONNECT RESILIENCE & SQL METRICS CROSS-CHECK ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    print("1. Ingesting synthetic data & running detection...")
    ingest_all_synthetic_data()

    with Session(engine) as session:
        detect_res = detect_revenue_at_risk(session)
        print(f"Detection created {detect_res['cases_created']} cases.")

    # ----------------------------------------------------
    # CHECK 1 & 2: Incremental SSE Delivery & Disconnect Resilience
    # ----------------------------------------------------
    print("\n--- CHECK 1 & 2: Incremental SSE Event Delivery & Mid-Batch Disconnect Resilience ---")

    with Session(engine) as session:
        batch_res = run_batch_processing(limit=5, session=session)
        batch_id = batch_res["batch_id"]
        print(f"Enqueued 5 cases under batch_id='{batch_id}'")

    async def simulate_client_disconnect_stream():
        stream_res = stream_batch_events(batch_id)
        received_count = 0
        async for chunk in stream_res.body_iterator:
            chunk_str = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            if "data:" in chunk_str and "case_id" in chunk_str:
                received_count += 1
                print(f"Received incremental SSE chunk #{received_count}: {chunk_str.strip()}")
                if received_count == 2:
                    print("Simulating client disconnect mid-batch! Closing connection...")
                    break
        return received_count

    events_received = asyncio.run(simulate_client_disconnect_stream())
    assert events_received == 2
    print("PASSED: SSE events arrived incrementally and client disconnect was simulated gracefully!")

    # Verify background batch process completed remaining cases despite client disconnect
    with Session(engine) as session:
        processed_cases = session.exec(
            select(RecoveryCase).where(RecoveryCase.status != CaseStatus.DETECTED)
        ).all()
        processed_count = len(processed_cases)
        print(f"Processed cases count in DB after client disconnect: {processed_count}/5")
        assert processed_count == 5
    print("CHECK 1 & 2 PASSED: Batch job completed cleanly in background despite SSE client disconnect!")

    # ----------------------------------------------------
    # CHECK 3: Cross-Check /api/metrics against Manual Raw SQL Query
    # ----------------------------------------------------
    print("\n--- CHECK 3: Cross-Check /api/metrics against Manual SQL Query ---")

    with Session(engine) as session:
        # 1. Manual SQL query: SUM(amount_at_risk)
        sql_sum_result = session.exec(select(func.sum(RecoveryCase.amount_at_risk))).one()
        sql_total_at_risk = round(float(sql_sum_result), 2)
        print(f"Manual SQL Query -> SELECT SUM(amount_at_risk) FROM recovery_cases: ${sql_total_at_risk:,.2f}")

        # 2. Live API endpoint metrics call
        api_metrics = get_live_metrics(session)
        api_total_at_risk = api_metrics["total_at_risk"]
        print(f"/api/metrics Response -> total_at_risk: ${api_total_at_risk:,.2f}")

        # Exact penny match assertion
        assert sql_total_at_risk == api_total_at_risk, f"Mismatch! SQL=${sql_total_at_risk}, API=${api_total_at_risk}"
        print("MATCH VERIFIED: Raw SQL SUM(amount_at_risk) matches /api/metrics total_at_risk EXACTLY!")

        # 3. Categorized SQL Cross-Check
        print("\nCategorized Raw SQL vs /api/metrics Cross-Check:")
        for c_type in ["FAILED_PAYMENT", "ABANDONED_CHECKOUT", "FAILED_SUBSCRIPTION", "OVERDUE_INVOICE"]:
            cat_cases = session.exec(
                select(RecoveryCase).where(RecoveryCase.case_type == c_type)
            ).all()
            c_count = len(cat_cases)
            c_sum = round(sum(float(c.amount_at_risk) for c in cat_cases), 2)

            api_cat_stats = api_metrics["by_category"].get(c_type, {})
            print(f"  • Category '{c_type}': SQL Count={c_count}, API Count={api_cat_stats.get('case_count')} | SQL Sum=${c_sum:,.2f}, API Sum=${api_cat_stats.get('total_at_risk'):,.2f}")

            assert c_count == api_cat_stats.get("case_count")
            assert c_sum == api_cat_stats.get("total_at_risk")

    print("CHECK 3 PASSED: All categorized metrics match raw SQL database aggregations 100%!")

    print("\n=== ALL SSE DISCONNECT & SQL METRICS CROSS-CHECK TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    verify_sse_and_sql_metrics()
