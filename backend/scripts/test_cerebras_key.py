import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from app.ai.openrouter_client import classify_case

def test_key():
    print("Testing live OpenRouter LLM API call with updated key...")
    sample_case = {
        "case_id": 1,
        "case_type": "FAILED_PAYMENT",
        "customer_id": 101,
        "amount_at_risk": 120.0,
        "failure_reason": "card_expired",
        "days_overdue": 2,
        "status": "DETECTED"
    }

    res = classify_case(sample_case)
    print("\nLive OpenRouter AI Classification Result:")
    print(res)

if __name__ == "__main__":
    test_key()
