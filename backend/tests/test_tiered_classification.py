import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.openrouter_client import classify_case, _rule_table_classify
from app.models import RecoveryCase, CaseType, CaseStatus, DecisionSource
from app.services.guardrails import validate_action

def test_tier1_primary_success():
    """
    Tier 1 Test: Primary model returns valid tool call -> decision_source = AI_PRIMARY.
    """
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = '{"root_cause": "Card expired", "recommended_action": "UPDATE_PAYMENT_METHOD", "confidence": 0.95, "reason": "Card expiry", "requires_human_approval": false}'

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(tool_calls=[mock_tool_call]))]

    with patch("app.ai.openrouter_client.OpenRouter") as mock_openrouter:
        mock_instance = MagicMock()
        mock_instance.chat.send.return_value = mock_completion
        mock_openrouter.return_value = mock_instance

        case_payload = {
            "case_id": 1,
            "case_type": "FAILED_PAYMENT",
            "amount_at_risk": 150.0,
            "failure_reason": "EXPIRED_CARD"
        }

        res = classify_case(case_payload)
        assert res["decision_source"] == "AI_PRIMARY"
        assert res["recommended_action"] == "UPDATE_PAYMENT_METHOD"
        assert res["confidence"] == 0.95

def test_tier2_secondary_fallback(caplog):
    """
    Tier 2 Test: Primary model fails (429/Exception) -> fallback to secondary model succeeds -> decision_source = AI_SECONDARY.
    Loud warning must be logged.
    """
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = '{"root_cause": "Insufficient balance", "recommended_action": "RETRY_PAYMENT", "confidence": 0.85, "reason": "Soft decline", "requires_human_approval": false}'

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(tool_calls=[mock_tool_call]))]

    def mock_send(model, **kwargs):
        from app.ai.openrouter_client import MODEL_NAME, FALLBACK_MODEL_NAME
        print(f"DEBUG MOCK_SEND: model={model!r}, MODEL_NAME={MODEL_NAME!r}, FALLBACK={FALLBACK_MODEL_NAME!r}")
        if model == MODEL_NAME or model == "openrouter/free":
            raise RuntimeError("HTTP 429: Too Many Requests (Rate Limited)")
        return mock_completion

    with patch("app.ai.openrouter_client.OpenRouter") as mock_openrouter:
        mock_instance = MagicMock()
        mock_instance.chat.send.side_effect = mock_send
        mock_openrouter.return_value = mock_instance

        case_payload = {
            "case_id": 2,
            "case_type": "FAILED_PAYMENT",
            "amount_at_risk": 200.0,
            "failure_reason": "INSUFFICIENT_FUNDS"
        }

        res = classify_case(case_payload)
        assert res["decision_source"] == "AI_SECONDARY"
        assert res["recommended_action"] == "RETRY_PAYMENT"
        assert res["confidence"] == 0.85
        assert "[AI CLASSIFY FALLBACK WARNING]" in caplog.text

def test_tier3_rule_table_fallback(caplog):
    """
    Tier 3 Test: Both primary and secondary models fail -> fallback to rule table -> decision_source = FALLBACK_RULE.
    Verifies confidence = 0.5, requires_human_approval = True, and rule table action mappings.
    """
    with patch("app.ai.openrouter_client.OpenRouter") as mock_openrouter:
        mock_instance = MagicMock()
        mock_instance.chat.send.side_effect = RuntimeError("OpenRouter Service Unavailable")
        mock_openrouter.return_value = mock_instance

        # Test EXPIRED_CARD mapping
        res1 = classify_case({"case_id": 3, "case_type": "FAILED_PAYMENT", "failure_reason": "EXPIRED_CARD"})
        assert res1["decision_source"] == "FALLBACK_RULE"
        assert res1["recommended_action"] == "UPDATE_PAYMENT_METHOD"
        assert res1["confidence"] == 0.5
        assert res1["requires_human_approval"] is True

        # Test INSUFFICIENT_FUNDS mapping
        res2 = classify_case({"case_id": 4, "case_type": "FAILED_PAYMENT", "failure_reason": "INSUFFICIENT_FUNDS"})
        assert res2["decision_source"] == "FALLBACK_RULE"
        assert res2["recommended_action"] == "RETRY_PAYMENT"
        assert res2["confidence"] == 0.5
        assert res2["requires_human_approval"] is True

        # Test UNKNOWN failure reason -> ESCALATE
        res3 = classify_case({"case_id": 5, "case_type": "FAILED_PAYMENT", "failure_reason": "SOME_UNKNOWN_CODE"})
        assert res3["decision_source"] == "FALLBACK_RULE"
        assert res3["recommended_action"] == "ESCALATE"
        assert res3["confidence"] == 0.5
        assert res3["requires_human_approval"] is True

        assert "[CRITICAL CLASSIFY FALLBACK WARNING]" in caplog.text

def test_fallback_rule_triggers_guardrail_human_review():
    """
    Guardrail Test: Confirms that a FALLBACK_RULE decision (confidence=0.5, requires_human_approval=True)
    triggers safety guardrails and routes decision to BLOCKED (HUMAN_REVIEW / ESCALATE) rather than auto-executing.
    """
    ai_decision = {
        "root_cause": "Insufficient funds in customer account",
        "recommended_action": "RETRY_PAYMENT",
        "confidence": 0.5,
        "reason": "Rule-based fallback triggered",
        "requires_human_approval": True,
        "decision_source": "FALLBACK_RULE"
    }

    case = RecoveryCase(
        id=10,
        case_type=CaseType.FAILED_PAYMENT,
        customer_id=1,
        amount_at_risk=100.0,
        status=CaseStatus.DETECTED,
        decision_source=DecisionSource.FALLBACK_RULE
    )

    res = validate_action(case, ai_decision, attempt_count=0)
    assert res["decision"] == "BLOCKED"
    assert res["route"] in ["HUMAN_REVIEW", "ESCALATE"]
    assert "RULE_2" in res["rule_triggered"] or "RULE_4" in res["rule_triggered"]

def test_multiple_tool_calls_sanitation(caplog):
    """
    Sanitation Test: When model returns multiple tool calls (len > 1), uses tool_calls[0] and logs warning.
    """
    mock_tool1 = MagicMock()
    mock_tool1.function.arguments = '{"root_cause": "Primary cause", "recommended_action": "RETRY_PAYMENT", "confidence": 0.9, "reason": "First call", "requires_human_approval": false}'

    mock_tool2 = MagicMock()
    mock_tool2.function.arguments = '{"root_cause": "Extra cause", "recommended_action": "SEND_REMINDER", "confidence": 0.5, "reason": "Second call", "requires_human_approval": true}'

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(tool_calls=[mock_tool1, mock_tool2]))]

    with patch("app.ai.openrouter_client.OpenRouter") as mock_openrouter:
        mock_instance = MagicMock()
        mock_instance.chat.send.return_value = mock_completion
        mock_openrouter.return_value = mock_instance

        res = classify_case({"case_id": 99, "case_type": "FAILED_PAYMENT"})
        assert res["recommended_action"] == "RETRY_PAYMENT"
        assert "[MULTIPLE TOOL CALLS WARNING]" in caplog.text
