import os
import csv
import sys
import time
import asyncio
import logging
from typing import List, Dict, Any

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai import classify_case_async
from app.simulator.recovery_simulator import find_synthetic_data_dir

# Silence verbose httpx / openrouter logs during benchmark
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("app.ai.openrouter_client").setLevel(logging.WARNING)
logging.getLogger("openrouter").setLevel(logging.WARNING)

def load_synthetic_cases(target_count: int = 1000) -> List[Dict[str, Any]]:
    data_dir = find_synthetic_data_dir()
    csv_path = os.path.join(data_dir, "recovery_ground_truth.csv")

    base_cases = []
    if os.path.isfile(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                base_cases.append({
                    "case_id": int(row.get("case_id", 0)),
                    "case_type": row.get("case_type", "FAILED_PAYMENT"),
                    "customer_id": int(row.get("customer_id", 0)),
                    "amount_at_risk": float(row.get("amount_at_risk", 100.0)),
                    "status": "DETECTED"
                })

    if not base_cases:
        # Fallback case generator if CSV missing
        base_cases = [
            {"case_id": i + 1, "case_type": "FAILED_PAYMENT", "customer_id": i + 1, "amount_at_risk": 150.0, "status": "DETECTED"}
            for i in range(100)
        ]

    # Replicate dataset up to target_count (1,000 cases)
    full_cases = []
    idx = 1
    while len(full_cases) < target_count:
        for c in base_cases:
            c_copy = dict(c)
            c_copy["case_id"] = idx
            full_cases.append(c_copy)
            idx += 1
            if len(full_cases) >= target_count:
                break

    return full_cases

async def worker_task(case: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    async with semaphore:
        start_t = time.perf_counter()
        try:
            res = await classify_case_async(case)
            latency = (time.perf_counter() - start_t) * 1000.0
            return {"success": True, "result": res, "latency_ms": latency, "error": None}
        except Exception as e:
            latency = (time.perf_counter() - start_t) * 1000.0
            return {"success": False, "result": None, "latency_ms": latency, "error": str(e)}

async def run_concurrency_benchmark(cases: List[Dict[str, Any]], concurrency_level: int) -> Dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency_level)
    print(f"--> Running Benchmark: Concurrency={concurrency_level}, Total Cases={len(cases)}...")

    start_wall_time = time.perf_counter()
    tasks = [worker_task(c, semaphore) for c in cases]
    results = await asyncio.gather(*tasks)
    total_wall_duration = time.perf_counter() - start_wall_time

    success_count = sum(1 for r in results if r["success"])
    error_count = len(results) - success_count
    latencies = [r["latency_ms"] for r in results]
    avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
    throughput_cps = len(cases) / total_wall_duration if total_wall_duration > 0 else 0.0

    return {
        "concurrency": concurrency_level,
        "total_cases": len(cases),
        "wall_time_sec": total_wall_duration,
        "avg_latency_ms": avg_latency_ms,
        "throughput_cases_per_sec": throughput_cps,
        "throughput_cases_per_min": throughput_cps * 60.0,
        "success_count": success_count,
        "error_count": error_count
    }

async def main():
    print("==========================================================================")
    print("  AI REVENUE RECOVERY AGENT - ASYNC CONCURRENCY LOAD BENCHMARK (1,000 CASES) ")
    print("==========================================================================")

    target_case_count = 1000
    cases = load_synthetic_cases(target_case_count)
    print(f"Loaded {len(cases)} synthetic recovery cases for load testing.\n")

    concurrency_levels = [5, 20, 50]
    benchmark_metrics = []

    for conc in concurrency_levels:
        metrics = await run_concurrency_benchmark(cases, conc)
        benchmark_metrics.append(metrics)
        print(f"    Completed: Duration={metrics['wall_time_sec']:.2f}s, Throughput={metrics['throughput_cases_per_sec']:.2f} cases/sec ({metrics['throughput_cases_per_min']:.1f} cases/min), Errors={metrics['error_count']}\n")

    # Print Comparison Table
    print("\n" + "=" * 90)
    print("                        CONCURRENCY LOAD TEST COMPARISON TABLE                    ")
    print("=" * 90)
    header = f"| {'Concurrency':<11} | {'Total Cases':<11} | {'Wall Time (s)':<13} | {'Avg Latency':<12} | {'Throughput (c/s)':<16} | {'Errors':<8} |"
    divider = "|-" + "-"*12 + "-|-" + "-"*12 + "-|-" + "-"*14 + "-|-" + "-"*13 + "-|-" + "-"*17 + "-|-" + "-"*9 + "-|"
    print(header)
    print(divider)

    for m in benchmark_metrics:
        row = f"| {m['concurrency']:<11} | {m['total_cases']:<11} | {m['wall_time_sec']:<13.2f} | {m['avg_latency_ms']:<9.1f} ms | {m['throughput_cases_per_sec']:<16.2f} | {m['error_count']:<8} |"
        print(row)

    print("=" * 90 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
