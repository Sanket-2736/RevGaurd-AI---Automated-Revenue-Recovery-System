import os
import shutil
import filecmp
import csv
from scripts.generate_synthetic_data import main as generate_main

def run_verification():
    dir1 = os.path.abspath("temp_seed42_1")
    dir2 = os.path.abspath("temp_seed42_2")
    dir3 = os.path.abspath("temp_seed99")

    # 1. Generate seed 42 twice
    os.makedirs(dir1, exist_ok=True)
    os.makedirs(dir2, exist_ok=True)
    os.makedirs(dir3, exist_ok=True)

    import sys
    orig_argv = sys.argv

    print("--- STEP 1: Testing Deterministic Seed Reproducibility ---")
    sys.argv = ["generate_synthetic_data.py", "--seed", "42", "--output-dir", dir1]
    generate_main()

    sys.argv = ["generate_synthetic_data.py", "--seed", "42", "--output-dir", dir2]
    generate_main()

    sys.argv = ["generate_synthetic_data.py", "--seed", "99", "--output-dir", dir3]
    generate_main()

    sys.argv = orig_argv

    filenames = ["customers.csv", "payments.csv", "checkouts.csv", "subscriptions.csv", "invoices.csv", "recovery_ground_truth.csv"]

    print("\n--- STEP 2: Diffing Files (Seed 42 #1 vs Seed 42 #2) ---")
    all_identical = True
    for f in filenames:
        p1 = os.path.join(dir1, f)
        p2 = os.path.join(dir2, f)
        is_same = filecmp.cmp(p1, p2, shallow=False)
        print(f"[{'MATCH' if is_same else 'DIFF'}] {f}: Byte-identical = {is_same}")
        if not is_same:
            all_identical = False

    print("\n--- STEP 3: Diffing Files (Seed 42 vs Seed 99) ---")
    all_different = True
    for f in filenames:
        p1 = os.path.join(dir1, f)
        p3 = os.path.join(dir3, f)
        is_same = filecmp.cmp(p1, p3, shallow=False)
        print(f"[{'DIFFERENT' if not is_same else 'SAME'}] {f}: Different data = {not is_same}")
        if is_same:
            all_different = False

    print(f"\nSeed Reproducibility Verification Passed: {all_identical and all_different}")

    # 2. Baseline Metrics & Spot Checks on default synthetic-data directory
    target_dir = os.path.abspath("../synthetic-data")
    gt_path = os.path.join(target_dir, "recovery_ground_truth.csv")
    pay_path = os.path.join(target_dir, "payments.csv")

    with open(gt_path, mode="r", encoding="utf-8") as f:
        gt_rows = list(csv.DictReader(f))

    with open(pay_path, mode="r", encoding="utf-8") as f:
        pay_rows = list(csv.DictReader(f))

    print("\n--- STEP 4: Total Amount at Risk & Baseline Dashboard Metrics ---")
    total_amount_at_risk = sum(float(r["amount_at_risk"]) for r in gt_rows)
    total_expected_recovery = sum(float(r["expected_recovery_amount"]) for r in gt_rows)

    by_type = {}
    by_outcome = {}
    for r in gt_rows:
        ctype = r["case_type"]
        outcome = r["expected_outcome"]
        amt = float(r["amount_at_risk"])
        rec = float(r["expected_recovery_amount"])

        if ctype not in by_type:
            by_type[ctype] = {"count": 0, "amount": 0.0, "recovered_amount": 0.0}
        by_type[ctype]["count"] += 1
        by_type[ctype]["amount"] += amt
        by_type[ctype]["recovered_amount"] += rec

        if outcome not in by_outcome:
            by_outcome[outcome] = {"count": 0, "amount": 0.0}
        by_outcome[outcome]["count"] += 1
        by_outcome[outcome]["amount"] += amt

    print(f"Total Cases at Risk: {len(gt_rows)}")
    print(f"Total Baseline Amount at Risk: ${total_amount_at_risk:,.2f}")
    print(f"Total Baseline Expected Recovery: ${total_expected_recovery:,.2f} ({total_expected_recovery/total_amount_at_risk*100:.1f}%)")

    print("\nBreakdown by Case Type:")
    for ctype, data in by_type.items():
        pct = (data['count'] / len(gt_rows)) * 100
        print(f"  - {ctype}: {data['count']} cases ({pct:.1f}%), Amount: ${data['amount']:,.2f}")

    print("\nBreakdown by Expected Outcome:")
    for outcome, data in by_outcome.items():
        pct = (data['count'] / len(gt_rows)) * 100
        print(f"  - {outcome}: {data['count']} cases ({pct:.1f}%), Amount: ${data['amount']:,.2f}")

    print("\n--- STEP 5: Spot-Checking TEMPORARY_FAILURE Rows in Ground Truth ---")
    temp_failure_cases = [r for r in gt_rows if r["case_type"] == "FAILED_PAYMENT" and r["expected_action"] == "EXECUTE_SMART_RETRY"]
    print(f"Total TEMPORARY_FAILURE cases: {len(temp_failure_cases)}")
    recovered_temp_failures = [r for r in temp_failure_cases if r["expected_outcome"] == "RECOVERED"]
    print(f"RECOVERED TEMPORARY_FAILURE cases: {len(recovered_temp_failures)} / {len(temp_failure_cases)} ({len(recovered_temp_failures)/len(temp_failure_cases)*100:.1f}%)")

    print("\nSample TEMPORARY_FAILURE Spot-Check Rows (First 5):")
    for r in temp_failure_cases[:5]:
        print(f"  Case #{r['case_id']}: Action={r['expected_action']}, Outcome={r['expected_outcome']}, Risk=${float(r['amount_at_risk']):.2f}, Expected Recovery=${float(r['expected_recovery_amount']):.2f}")

    # Cleanup temporary diff directories
    shutil.rmtree(dir1, ignore_errors=True)
    shutil.rmtree(dir2, ignore_errors=True)
    shutil.rmtree(dir3, ignore_errors=True)
    print("\nCleaned up temporary comparison directories.")

if __name__ == "__main__":
    run_verification()
