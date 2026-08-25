import random
from scripts.generate_synthetic_data import decide_ground_truth

def test_decide_ground_truth_expired_card():
    rng = random.Random(42)
    case = {
        "case_id": 1,
        "case_type": "FAILED_PAYMENT",
        "source_id": 10,
        "customer_id": 5,
        "amount_at_risk": 150.0,
        "failure_reason": "EXPIRED_CARD",
        "customer_type": "INDIVIDUAL"
    }
    result = decide_ground_truth(case, rng)
    print("Test Result:", result)
    assert result["expected_action"] == "SEND_CARD_UPDATE_LINK"
    assert result["expected_outcome"] in ["RECOVERED", "ESCALATED", "UNRECOVERABLE"]
    assert "expected_recovery_amount" in result
    print("Assertion passed successfully!")

if __name__ == "__main__":
    test_decide_ground_truth_expired_card()
