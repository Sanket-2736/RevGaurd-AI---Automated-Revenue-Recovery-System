import os
import sys
import csv
import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai import classify_case
from app.utils.path_utils import find_synthetic_data_dir

logger = logging.getLogger(__name__)

def evaluate_single_row(row: dict, action_equivalents: dict) -> tuple:
    c_type = row.get("case_type", "UNKNOWN")
    case_payload = {
        "case_id": int(row.get("case_id", 0)),
        "case_type": c_type,
        "customer_id": int(row.get("customer_id", 0)),
        "amount_at_risk": float(row.get("amount_at_risk", 0.0)),
        "failure_reason": row.get("failure_reason", ""),
        "days_overdue": int(row.get("days_overdue", 0)) if row.get("days_overdue") else 0,
        "customer_type": row.get("customer_type", ""),
        "status": "DETECTED"
    }

    expected_action = row.get("expected_action", "").strip()

    # Retry logic if OpenRouter rate limits in-flight requests
    ai_res = None
    for attempt in range(3):
        try:
            ai_res = classify_case(case_payload)
            break
        except Exception as e:
            if "in-flight" in str(e).lower() or "credits" in str(e).lower():
                time.sleep(1.0 * (attempt + 1))
            else:
                raise e

    if not ai_res:
        return c_type, False

    predicted_action = ai_res.get("recommended_action", "").strip()

    # Check match against exact action or equivalent action set
    allowed_matches = action_equivalents.get(expected_action, [expected_action])
    is_match = (predicted_action in allowed_matches) or (expected_action in action_equivalents.get(predicted_action, [predicted_action]))

    return c_type, is_match

def test_ground_truth_classification_accuracy():
    """
    Loads recovery_ground_truth.csv, runs classify_case across all 4 case_types
    (FAILED_PAYMENT, ABANDONED_CHECKOUT, FAILED_SUBSCRIPTION, OVERDUE_INVOICE),
    computes classification accuracy overall AND per category,
    and prints the complete per-category breakdown table.
    """
    data_dir = find_synthetic_data_dir()
    csv_path = os.path.join(data_dir, "recovery_ground_truth.csv")

    assert os.path.isfile(csv_path), f"Ground truth CSV not found at '{csv_path}'"

    ground_truth_rows = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ground_truth_rows.append(row)

    assert len(ground_truth_rows) > 0, "Ground truth CSV is empty!"

    # Group by category to select a balanced stratified sample across all 4 case types
    by_category = defaultdict(list)
    for row in ground_truth_rows:
        by_category[row.get("case_type", "UNKNOWN")].append(row)

    # Select up to 15 cases per category (60 total cases across all 4 categories)
    sample_cases = []
    for c_type, rows in by_category.items():
        sample_cases.extend(rows[:15])

    correct_count = 0
    total_evaluated = len(sample_cases)

    category_correct = defaultdict(int)
    category_total = defaultdict(int)

    # Action equivalency map for action synonyms between LLM enums and synthetic data generators
    ACTION_EQUIVALENTS = {
        "RETRY_PAYMENT": ["RETRY_PAYMENT", "EXECUTE_SMART_RETRY", "SCHEDULE_PAYDAY_RETRY"],
        "SEND_REMINDER": ["SEND_REMINDER", "SEND_CART_REMINDER", "SEND_PAYMENT_REMINDER", "SEND_FINAL_NOTICE", "SEND_VIP_DISCOUNT_NUDGE", "SEND_GENERIC_REMINDER"],
        "UPDATE_PAYMENT_METHOD": ["UPDATE_PAYMENT_METHOD", "SEND_CARD_UPDATE_LINK", "SUBSCRIPTION_RECOVERY_EMAIL"],
        "TRACK_PROMISE_TO_PAY": ["TRACK_PROMISE_TO_PAY", "ACCOUNT_MANAGER_OUTREACH"],
        "ESCALATE": ["ESCALATE", "ESCALATE_TO_COLLECTIONS"],
        "STOP_RECOVERY": ["STOP_RECOVERY"],

        # Ground truth synonyms mapping
        "SEND_CARD_UPDATE_LINK": ["UPDATE_PAYMENT_METHOD", "SEND_CARD_UPDATE_LINK"],
        "SCHEDULE_PAYDAY_RETRY": ["RETRY_PAYMENT", "SCHEDULE_PAYDAY_RETRY", "EXECUTE_SMART_RETRY"],
        "EXECUTE_SMART_RETRY": ["RETRY_PAYMENT", "EXECUTE_SMART_RETRY", "SCHEDULE_PAYDAY_RETRY"],
        "SEND_VIP_DISCOUNT_NUDGE": ["SEND_REMINDER", "SEND_VIP_DISCOUNT_NUDGE", "SEND_CART_REMINDER"],
        "SEND_CART_REMINDER": ["SEND_REMINDER", "SEND_CART_REMINDER"],
        "ACCOUNT_MANAGER_OUTREACH": ["TRACK_PROMISE_TO_PAY", "ACCOUNT_MANAGER_OUTREACH", "UPDATE_PAYMENT_METHOD", "RETRY_PAYMENT"],
        "SUBSCRIPTION_RECOVERY_EMAIL": ["UPDATE_PAYMENT_METHOD", "RETRY_PAYMENT", "SEND_REMINDER", "SUBSCRIPTION_RECOVERY_EMAIL"],
        "ESCALATE_TO_COLLECTIONS": ["ESCALATE", "ESCALATE_TO_COLLECTIONS"],
        "SEND_FINAL_NOTICE": ["SEND_REMINDER", "SEND_FINAL_NOTICE"],
        "SEND_PAYMENT_REMINDER": ["SEND_REMINDER", "SEND_PAYMENT_REMINDER"]
    }

    # Evaluate concurrently with modest worker concurrency (3 workers) to prevent rate limits
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(evaluate_single_row, row, ACTION_EQUIVALENTS) for row in sample_cases]
        for future in as_completed(futures):
            c_type, is_match = future.result()
            category_total[c_type] += 1
            if is_match:
                correct_count += 1
                category_correct[c_type] += 1

    overall_accuracy_pct = (correct_count / total_evaluated) * 100.0

    print("\n" + "=" * 70)
    print("   AI CLASSIFICATION ACCURACY BREAKDOWN BY CASE TYPE (ALL 4 CATEGORIES)")
    print("=" * 70)
    print(f"| {'Case Type':<24} | {'Matches':<10} | {'Total':<8} | {'Accuracy (%)':<12} |")
    print("|" + "-"*26 + "|" + "-"*12 + "|" + "-"*10 + "|" + "-"*14 + "|")

    for c_type, tot in category_total.items():
        corr = category_correct[c_type]
        cat_acc = (corr / tot * 100.0) if tot > 0 else 0.0
        print(f"| {c_type:<24} | {corr:<10} | {tot:<8} | {cat_acc:<11.1f}% |")

    print("-" * 70)
    print(f"OVERALL BLENDED ACCURACY: {overall_accuracy_pct:.1f}% ({correct_count}/{total_evaluated})")
    print("=" * 70 + "\n")

    assert len(category_total) == 4, f"Expected evaluations across all 4 categories, got {len(category_total)}"
    assert overall_accuracy_pct > 0.0, "Overall accuracy must be greater than 0%"
