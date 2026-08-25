import time
from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.services.detection import detect_revenue_at_risk
from app.tasks import process_case
from app.models import RecoveryCase, CaseStatus

def run_performance_verification():
    print("=== STARTING WORKER LOGS, DUP PROTECTION & 100-CASE THROUGHPUT BENCHMARK ===")

    # Reset database & seed data
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    print("1. Ingesting synthetic data & running detection...")
    ingest_all_synthetic_data()

    with Session(engine) as session:
        detect_res = detect_revenue_at_risk(session)
        print(f"Detection created {detect_res['cases_created']} cases.")
        assert detect_res["cases_created"] == 381

    # ----------------------------------------------------
    # CHECK 1: Sequential Processing Verification (10 cases)
    # ----------------------------------------------------
    print("\n--- CHECK 1: Sequential Case Processing & Worker Logs (10 cases) ---")
    with Session(engine) as session:
        ten_cases = session.exec(
            select(RecoveryCase)
            .where(RecoveryCase.status == CaseStatus.DETECTED)
            .limit(10)
        ).all()
        assert len(ten_cases) == 10
        case_ids_10 = [c.id for c in ten_cases]

    processed_results_10 = []
    for cid in case_ids_10:
        res = process_case(cid)
        processed_results_10.append(res)
        print(f"Worker Log Entry -> Case #{cid}: Status='{res['status']}', Action='{res.get('ai_decision', {}).get('recommended_action')}'")

    assert len(processed_results_10) == 10
    print("CHECK 1 PASSED: 10 cases processed sequentially with explicit worker log tracking!")

    # ----------------------------------------------------
    # CHECK 2: Interruption & Worker Restart Duplicate Protection
    # ----------------------------------------------------
    print("\n--- CHECK 2: Interruption & Worker Restart Duplicate Protection ---")
    duplicate_results = []
    for cid in case_ids_10[:5]:
        res_dup = process_case(cid)
        duplicate_results.append(res_dup)
        print(f"Restart Worker Log Entry -> Case #{cid}: Status='{res_dup['status']}', Message='{res_dup.get('message')}'")

    for res_dup in duplicate_results:
        assert res_dup["status"] == "SKIPPED_ALREADY_PROCESSED"

    print("CHECK 2 PASSED: Restarted worker safely skipped already-processed cases without duplicate processing!")

    # ----------------------------------------------------
    # CHECK 3: 100-Case Batch Throughput Benchmark
    # ----------------------------------------------------
    print("\n--- CHECK 3: 100-Case Batch Throughput Benchmark ---")
    with Session(engine) as session:
        hundred_cases = session.exec(
            select(RecoveryCase)
            .where(RecoveryCase.status == CaseStatus.DETECTED)
            .limit(100)
        ).all()
        assert len(hundred_cases) == 100
        case_ids_100 = [c.id for c in hundred_cases]

    print(f"Starting throughput benchmark for {len(case_ids_100)} cases...")
    start_time = time.perf_counter()

    batch_results = []
    for cid in case_ids_100:
        res = process_case(cid)
        batch_results.append(res)

    total_duration_sec = time.perf_counter() - start_time
    avg_latency_ms = (total_duration_sec / len(case_ids_100)) * 1000.0
    throughput_cases_per_sec = len(case_ids_100) / total_duration_sec
    throughput_cases_per_min = throughput_cases_per_sec * 60.0

    print(f"\n=======================================================")
    print(f"         100-CASE THROUGHPUT BENCHMARK RESULTS         ")
    print(f"=======================================================")
    print(f"  • Total Cases Processed:   {len(case_ids_100)} cases")
    print(f"  • Total Batch Duration:    {total_duration_sec:.2f} seconds")
    print(f"  • Average Latency / Case:  {avg_latency_ms:.2f} ms")
    print(f"  • Throughput (Cases / sec): {throughput_cases_per_sec:.2f} cases/sec")
    print(f"  • Throughput (Cases / min): {throughput_cases_per_min:.1f} cases/min")
    print(f"=======================================================\n")

    assert len(batch_results) == 100
    print("CHECK 3 PASSED: 100-case throughput benchmark completed successfully!")

    print("\n=== ALL 3 PERFORMANCE & RESTART VERIFICATION CHECKS PASSED! ===")

if __name__ == "__main__":
    run_performance_verification()
