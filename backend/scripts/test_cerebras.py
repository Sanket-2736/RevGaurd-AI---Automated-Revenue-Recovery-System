import sys
import os
import json

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.openrouter_client import classify_case

def run_test():
    sample_cases = [
        {
            "case_id": 101,
            "case_type": "FAILED_PAYMENT",
            "customer_id": 12,
            "amount_at_risk": 49.00,
            "failure_reason": "EXPIRED_CARD",
            "customer_type": "INDIVIDUAL"
        },
        {
            "case_id": 102,
            "case_type": "ABANDONED_CHECKOUT",
            "customer_id": 45,
            "amount_at_risk": 1200.00,
            "abandoned_step": "PAYMENT_METHOD",
            "customer_type": "BUSINESS"
        },
        {
            "case_id": 103,
            "case_type": "FAILED_SUBSCRIPTION",
            "customer_id": 88,
            "amount_at_risk": 199.00,
            "plan_name": "PRO",
            "customer_type": "INDIVIDUAL"
        },
        {
            "case_id": 104,
            "case_type": "OVERDUE_INVOICE",
            "customer_id": 105,
            "amount_at_risk": 4500.00,
            "days_overdue": 75,
            "customer_type": "BUSINESS"
        },
        {
            "case_id": 105,
            "case_type": "FAILED_PAYMENT",
            "customer_id": 201,
            "amount_at_risk": 85.00,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "customer_type": "INDIVIDUAL"
        }
    ]

    print("=== TESTING OPENROUTER CASE CLASSIFICATION ENGINE (openrouter/free) ===\n")

    for idx, case in enumerate(sample_cases, start=1):
        print(f"--- Case #{idx}: {case['case_type']} (${case['amount_at_risk']:,.2f}) ---")
        print(f"Input: {json.dumps(case, indent=2)}")
        result = classify_case(case)
        print("Output Result:")
        print(f"  • Root Cause:             {result.get('root_cause')}")
        print(f"  • Recommended Action:     {result.get('recommended_action')}")
        print(f"  • Confidence:             {result.get('confidence')}")
        print(f"  • Requires Human Approval: {result.get('requires_human_approval')}")
        print(f"  • Reason:                 {result.get('reason')}\n")

    print("=== ALL 5 SAMPLE CASES PROCESSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_test()
