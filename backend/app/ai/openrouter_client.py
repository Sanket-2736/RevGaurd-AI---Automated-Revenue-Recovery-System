import os
import json
import logging
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv

# Search for .env starting from cwd upwards to ensure root or backend .env is found
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv(override=True)

logger = logging.getLogger(__name__)

# OpenRouter SDK imports
try:
    from openrouter import OpenRouter
except ImportError:
    OpenRouter = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openrouter/free")

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
Your mission is to evaluate an at-risk revenue case payload and classify the underlying root cause and recommended recovery action.

Guidelines:
1. Base your reasoning strictly on the facts provided in the input case payload. Do not invent, assume, or cite numbers, dates, or amounts not present in the input.
2. For expired payment cards, recommend UPDATE_PAYMENT_METHOD.
3. For temporary payment gateway or network failures, recommend RETRY_PAYMENT.
4. For abandoned checkouts, recommend SEND_REMINDER.
5. For severely overdue invoices or high-value/risky transactions requiring human sign-off, set requires_human_approval = True or recommend ESCALATE.
6. You MUST call the classify_recovery_case tool with strict adherence to the schema.
"""

def _is_api_key_valid() -> bool:
    return bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("your_openrouter"))

def _fallback_classify_case(case: dict) -> Dict[str, Any]:
    """
    Deterministic fallback heuristic classifier used ONLY when force_fallback=True is explicitly set.
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
    Classifies an at-risk case using OpenRouter client (openrouter/free) with tool calling.
    If force_fallback is True, uses deterministic fallback classifier directly.
    """
    if force_fallback:
        logger.info("[FALLBACK PATH] Explicit force_fallback=True requested; using fallback classifier.")
        return _fallback_classify_case(case)

    if not _is_api_key_valid():
        msg = "[CRITICAL ERROR] OPENROUTER_API_KEY is missing or invalid! Live API call required."
        logger.error(msg)
        print(f"\n[ERROR] {msg}\n")
        raise ValueError(msg)

    if OpenRouter is None:
        msg = "[CRITICAL ERROR] openrouter SDK package is not imported!"
        logger.error(msg)
        print(f"\n[ERROR] {msg}\n")
        raise RuntimeError(msg)

    case_id = case.get("case_id", "UNKNOWN")
    logger.info(f"[AI CLASSIFY START] Processing Case #{case_id} using model '{MODEL_NAME}'")
    print(f"\n======================================================================")
    print(f" [OPENROUTER LLM REQUEST]")
    print(f" Model: {MODEL_NAME}")
    print(f" Case Payload: {json.dumps(case)}")
    print(f"======================================================================")

    try:
        client = OpenRouter(api_key=OPENROUTER_API_KEY)
        user_content = f"Classify this at-risk recovery case: {json.dumps(case)}"

        completion = client.chat.send(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            tools=[CLASSIFY_CASE_TOOL],
            tool_choice={"type": "function", "function": {"name": "classify_recovery_case"}}
        )

        tool_calls = completion.choices[0].message.tool_calls
        print(f"----------------------------------------------------------------------")
        print(f" [OPENROUTER RAW RESPONSE]")
        print(f" Tool Calls: {tool_calls}")
        print(f"----------------------------------------------------------------------")

        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            result = {
                "root_cause": str(args.get("root_cause", "")),
                "recommended_action": str(args.get("recommended_action", "SEND_REMINDER")),
                "confidence": float(args.get("confidence", 0.8)),
                "reason": str(args.get("reason", "")),
                "requires_human_approval": bool(args.get("requires_human_approval", False))
            }
            logger.info(f"[AI CLASSIFY COMPLETE] Case #{case_id} -> root_cause='{result['root_cause']}', recommended_action='{result['recommended_action']}', confidence={result['confidence']}")
            print(f" [OPENROUTER PARSED RESULT]: {result}\n")
            return result
        else:
            raise ValueError("OpenRouter response did not contain expected tool_calls payload")

    except Exception as e:
        logger.error(f"[CRITICAL ERROR] OpenRouter API call failed: {e}")
        print(f"\n[OPENROUTER API CALL FAILED]: {e}\n")
        raise e

async def classify_case_async(case: dict) -> Dict[str, Any]:
    """
    Asynchronously classifies an at-risk case using OpenRouter client.
    """
    return await asyncio.to_thread(classify_case, case)
