import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Cerebras SDK imports
try:
    from cerebras.cloud.sdk import Cerebras, AsyncCerebras
except ImportError:
    Cerebras = None
    AsyncCerebras = None

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
MODEL_NAME = "gpt-oss-120b"

CLASSIFY_CASE_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_recovery_case",
        "description": "Classifies an at-risk revenue recovery case and determines root cause, recommended recovery action, confidence score, and human approval flag.",
        "parameters": {
            "type": "object",
            "properties": {
                "root_cause": {
                    "type": "string",
                    "description": "Identified underlying cause of payment failure or revenue risk."
                },
                "recommended_action": {
                    "type": "string",
                    "enum": [
                        "RETRY_PAYMENT",
                        "SEND_REMINDER",
                        "UPDATE_PAYMENT_METHOD",
                        "TRACK_PROMISE_TO_PAY",
                        "ESCALATE",
                        "STOP_RECOVERY"
                    ],
                    "description": "Recommended recovery action."
                },
                "confidence": {
                    "type": "number",
                    "description": "AI confidence score between 0.0 and 1.0."
                },
                "reason": {
                    "type": "string",
                    "description": "Detailed reasoning for the decision."
                },
                "requires_human_approval": {
                    "type": "boolean",
                    "description": "Flag indicating if human sign-off is required due to high amount, high risk score, or sensitive action."
                }
            },
            "required": ["root_cause", "recommended_action", "confidence", "reason", "requires_human_approval"]
        }
    }
}

SYSTEM_PROMPT = """You are an expert AI Revenue Recovery Decision Agent.
Your mission is to classify at-risk payment, checkout, subscription, and invoice cases to maximize recovery while minimizing customer friction.

Guidelines & Guardrails:
1. Be conservative on high amounts (e.g., amount_at_risk >= $500.0) or repeated failures by setting requires_human_approval = True or recommending ESCALATE.
2. For expired cards, recommend UPDATE_PAYMENT_METHOD.
3. For temporary failures or soft declines, recommend RETRY_PAYMENT.
4. For overdue invoices under 30 days, recommend SEND_REMINDER. For invoices >60 days overdue, recommend ESCALATE.
5. You MUST call the classify_recovery_case tool with strict adherence to the schema.
"""

def _is_api_key_valid() -> bool:
    return bool(CEREBRAS_API_KEY and not CEREBRAS_API_KEY.startswith("your_cerebras_api_key"))

def _fallback_classify_case(case: dict) -> Dict[str, Any]:
    """
    Deterministic fallback heuristic classifier used when CEREBRAS_API_KEY is missing,
    placeholder, or network call is unavailable.
    """
    case_type = case.get("case_type", "FAILED_PAYMENT")
    amount = float(case.get("amount_at_risk", 0.0))
    failure_reason = case.get("failure_reason", "")
    days_overdue = int(case.get("days_overdue", 0))

    requires_human_approval = (amount >= 500.0)

    if case_type == "FAILED_PAYMENT":
        if failure_reason == "EXPIRED_CARD":
            return {
                "root_cause": "Payment card expired on file",
                "recommended_action": "UPDATE_PAYMENT_METHOD",
                "confidence": 0.95,
                "reason": "Card expiry detected; requesting updated payment method details from customer.",
                "requires_human_approval": requires_human_approval
            }
        elif failure_reason == "INSUFFICIENT_FUNDS":
            return {
                "root_cause": "Insufficient funds in customer account",
                "recommended_action": "RETRY_PAYMENT",
                "confidence": 0.82,
                "reason": "Soft decline due to insufficient funds; schedule payment retry near payday.",
                "requires_human_approval": requires_human_approval
            }
        else:
            return {
                "root_cause": "Temporary payment gateway failure",
                "recommended_action": "RETRY_PAYMENT",
                "confidence": 0.90,
                "reason": "Network or temporary gateway glitch; smart retry recommended.",
                "requires_human_approval": requires_human_approval
            }

    elif case_type == "ABANDONED_CHECKOUT":
        return {
            "root_cause": "Checkout abandoned at payment step",
            "recommended_action": "SEND_REMINDER",
            "confidence": 0.85,
            "reason": "Customer left active cart; send cart recovery reminder email.",
            "requires_human_approval": requires_human_approval
        }

    elif case_type == "FAILED_SUBSCRIPTION":
        return {
            "root_cause": "Recurring subscription billing failure",
            "recommended_action": "UPDATE_PAYMENT_METHOD" if failure_reason == "EXPIRED_CARD" else "RETRY_PAYMENT",
            "confidence": 0.88,
            "reason": "Subscription renewal payment failed; retry billing or request card update.",
            "requires_human_approval": requires_human_approval
        }

    elif case_type == "OVERDUE_INVOICE":
        if days_overdue > 60:
            return {
                "root_cause": f"Invoice overdue by {days_overdue} days",
                "recommended_action": "ESCALATE",
                "confidence": 0.92,
                "reason": f"Invoice severely overdue ({days_overdue} days); escalating to finance/collections team.",
                "requires_human_approval": True
            }
        else:
            return {
                "root_cause": f"Invoice overdue by {days_overdue} days",
                "recommended_action": "SEND_REMINDER",
                "confidence": 0.87,
                "reason": f"Invoice overdue by {days_overdue} days; send payment reminder notice.",
                "requires_human_approval": requires_human_approval
            }

    return {
        "root_cause": "Generic revenue risk detected",
        "recommended_action": "SEND_REMINDER",
        "confidence": 0.75,
        "reason": "Standard recovery process initiated.",
        "requires_human_approval": requires_human_approval
    }

def classify_case(case: dict, force_fallback: bool = False) -> Dict[str, Any]:
    """
    Synchronously classifies an at-risk case using Cerebras client (gpt-oss-120b) with tool calling.
    If force_fallback is True, uses deterministic fallback classifier directly for high-throughput bulk runs.
    """
    if force_fallback or not _is_api_key_valid() or Cerebras is None:
        return _fallback_classify_case(case)

    try:
        client = Cerebras(api_key=CEREBRAS_API_KEY)
        user_content = f"Classify this at-risk recovery case: {json.dumps(case)}"

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            tools=[CLASSIFY_CASE_TOOL],
            tool_choice={"type": "function", "function": {"name": "classify_recovery_case"}},
            reasoning_effort="low"
        )

        tool_calls = completion.choices[0].message.tool_calls
        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            return {
                "root_cause": str(args.get("root_cause", "")),
                "recommended_action": str(args.get("recommended_action", "SEND_REMINDER")),
                "confidence": float(args.get("confidence", 0.8)),
                "reason": str(args.get("reason", "")),
                "requires_human_approval": bool(args.get("requires_human_approval", False))
            }

    except Exception as e:
        logger.warning(f"Cerebras API call failed ({e}); switching to fallback classifier")

    return _fallback_classify_case(case)

async def classify_case_async(case: dict) -> Dict[str, Any]:
    """
    Asynchronously classifies an at-risk case using AsyncCerebras client (gpt-oss-120b).
    """
    if not _is_api_key_valid() or AsyncCerebras is None:
        return _fallback_classify_case(case)

    try:
        async_client = AsyncCerebras(api_key=CEREBRAS_API_KEY)
        user_content = f"Classify this at-risk recovery case: {json.dumps(case)}"

        completion = await async_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            tools=[CLASSIFY_CASE_TOOL],
            tool_choice={"type": "function", "function": {"name": "classify_recovery_case"}},
            reasoning_effort="low"
        )

        tool_calls = completion.choices[0].message.tool_calls
        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            return {
                "root_cause": str(args.get("root_cause", "")),
                "recommended_action": str(args.get("recommended_action", "SEND_REMINDER")),
                "confidence": float(args.get("confidence", 0.8)),
                "reason": str(args.get("reason", "")),
                "requires_human_approval": bool(args.get("requires_human_approval", False))
            }

    except Exception as e:
        logger.warning(f"Async Cerebras API call failed ({e}); switching to fallback classifier")

    return _fallback_classify_case(case)
