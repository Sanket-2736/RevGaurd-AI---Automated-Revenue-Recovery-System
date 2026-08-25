from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk
from app.tasks import process_case
from app.routers.batch import run_batch_processing, get_batch_status
from app.models import RecoveryCase, CaseStatus

def test_batch_processing_and_rq(engine):
    print("=== STARTING ASYNC BATCH & RQ WORKER TASK VERIFICATION ===")

    # Reset DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Ingest data & run detection
    print("Ingesting data and running detection...")
    ingest_all_synthetic_data()

    with Session(engine) as session:
        detect_res = detect_revenue_at_risk(session)
        print("Detection result:", detect_res)
        assert detect_res["cases_created"] == 381

    # 1. Test process_case worker task directly
    print("\n--- TEST 1: Direct process_case Worker Task Execution ---")
    with Session(engine) as session:
        first_case = session.exec(select(RecoveryCase).where(RecoveryCase.status == CaseStatus.DETECTED)).first()
        assert first_case is not None

        task_result = process_case(first_case.id)
        print("process_case Worker Task Result:", task_result)

        assert task_result["case_id"] == first_case.id
        assert task_result["status"] in ["APPROVED_AND_EXECUTED", "BLOCKED"]
        assert "ai_decision" in task_result
        assert "guardrail_result" in task_result

    print("PASSED: process_case worker task executed classify -> validate -> execute pipeline!")

    # 2. Test Non-Blocking Batch Enqueue API (POST /api/batch/run?limit=10)
    print("\n--- TEST 2: Non-Blocking Batch Enqueue API ---")
    with Session(engine) as session:
        batch_enqueue_res = run_batch_processing(limit=10, session=session)
        print("POST /api/batch/run Result:", batch_enqueue_res)

        assert batch_enqueue_res["batch_id"] is not None
        assert batch_enqueue_res["total_enqueued"] == 10
        batch_id = batch_enqueue_res["batch_id"]

    print(f"PASSED: Non-blocking batch API enqueued 10 jobs immediately with batch_id='{batch_id}'!")

    # 3. Test Polling Status API (GET /api/batch/{batch_id}/status)
    print("\n--- TEST 3: Polling Progress Status API ---")
    status_res = get_batch_status(batch_id)
    print("GET /api/batch/{batch_id}/status Result:", status_res)

    assert status_res["batch_id"] == batch_id
    assert status_res["total"] == 10
    assert "completed" in status_res
    assert "progress_pct" in status_res
    assert "is_finished" in status_res

    print("PASSED: Polling status endpoint returned progress metrics successfully!")

    print("\n=== ALL BATCH & RQ WORKER VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_batch_processing_and_rq()
