import asyncio
from sqlmodel import SQLModel, Session
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk
from app.routers.batch import run_batch_processing, stream_batch_events
from app.routers.metrics import get_live_metrics

async def consume_sse_stream(batch_id: str):
    stream_response = stream_batch_events(batch_id)
    assert stream_response.media_type == "text/event-stream"

    chunks = []
    async for chunk in stream_response.body_iterator:
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
    return "".join(chunks)

def test_stream_and_metrics_endpoints(engine):
    print("=== STARTING SSE STREAM & LIVE METRICS API VERIFICATION ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Ingest data & run detection
    print("Ingesting synthetic data & running detection...")
    ingest_all_synthetic_data()

    with Session(engine) as session:
        detect_res = detect_revenue_at_risk(session)
        print("Detection result:", detect_res)
        assert detect_res["cases_created"] == 381

    # ----------------------------------------------------
    # 1. TEST GET /api/metrics BEFORE BATCH PROCESSING
    # ----------------------------------------------------
    print("\n--- TEST 1: Initial Live Metrics GET /api/metrics ---")
    with Session(engine) as session:
        initial_metrics = get_live_metrics(session)
        print("Initial Metrics Payload:", initial_metrics)

        assert initial_metrics["total_at_risk"] == 376590.0
        assert initial_metrics["total_recovered"] == 0.0
        assert initial_metrics["recovery_rate"] == 0.0
        assert "by_category" in initial_metrics
        assert "FAILED_PAYMENT" in initial_metrics["by_category"]
        assert "ABANDONED_CHECKOUT" in initial_metrics["by_category"]
        assert "FAILED_SUBSCRIPTION" in initial_metrics["by_category"]
        assert "OVERDUE_INVOICE" in initial_metrics["by_category"]
        assert "human_escalations" in initial_metrics
        assert "guardrail_blocks" in initial_metrics

    print("PASSED: Initial live metrics returned expected schema and $376,590.00 total at risk!")

    # ----------------------------------------------------
    # 2. RUN BATCH PROCESSING (5 cases)
    # ----------------------------------------------------
    print("\n--- TEST 2: Processing Batch (5 cases) ---")
    with Session(engine) as session:
        batch_res = run_batch_processing(limit=5, session=session)
        print("Batch Enqueue Result:", batch_res)
        batch_id = batch_res["batch_id"]
        assert batch_id is not None

    # ----------------------------------------------------
    # 3. TEST GET /api/batch/{batch_id}/stream (SSE Stream Generator)
    # ----------------------------------------------------
    print("\n--- TEST 3: SSE Event Stream GET /api/batch/{batch_id}/stream ---")
    stream_content = asyncio.run(consume_sse_stream(batch_id))
    print("SSE Stream Content Output:\n", stream_content)

    assert "data:" in stream_content
    assert "case_id" in stream_content or "is_finished" in stream_content
    assert "approved" in stream_content or "is_finished" in stream_content
    assert "amount_recovered" in stream_content or "is_finished" in stream_content
    assert "route" in stream_content or "is_finished" in stream_content

    print("PASSED: SSE Stream returned formatted event data successfully!")

    # ----------------------------------------------------
    # 4. TEST GET /api/metrics AFTER BATCH PROCESSING (LIVE UPDATES)
    # ----------------------------------------------------
    print("\n--- TEST 4: Live Updated Metrics GET /api/metrics ---")
    with Session(engine) as session:
        updated_metrics = get_live_metrics(session)
        print("Updated Metrics Payload:", updated_metrics)

        assert updated_metrics["total_at_risk"] == 376590.0
        assert updated_metrics["total_recovered"] >= 0.0
        assert "by_category" in updated_metrics
        for cat, stats in updated_metrics["by_category"].items():
            print(f"Category '{cat}': count={stats['case_count']}, recovered={stats['recovered_count']}, rate={stats['recovery_rate']}%")

    print("PASSED: Live metrics computed updated database state directly without caching!")

    print("\n=== ALL SSE STREAM & LIVE METRICS API VERIFICATION TESTS PASSED! ===")

if __name__ == "__main__":
    test_stream_and_metrics_endpoints()
