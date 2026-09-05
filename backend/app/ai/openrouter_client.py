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
    from openrouter.errors import TooManyRequestsResponseError, OpenRouterError
except ImportError:
    OpenRouter = None
    class TooManyRequestsResponseError(Exception): pass
    class OpenRouterError(Exception): pass

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openrouter/free")
FALLBACK_MODEL_NAME = os.getenv("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.2-1b-instruct:free")

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

Decision Guidelines Table:
1. EXPIRED_CARD (Payment or Subscription):
   - Recommended Action: UPDATE_PAYMENT_METHOD
   - Reason: Payment card is expired on file; customer must provide updated card details.

2. INSUFFICIENT_FUNDS (Soft decline / insufficient balance):
   - Recommended Action: RETRY_PAYMENT (Schedule payday / smart retry).
   - If customer_type is ENTERPRISE or amount_at_risk >= 500.0: RETRY_PAYMENT or SEND_REMINDER with requires_human_approval = True.

3. GATEWAY_ERROR / NETWORK_TIMEOUT / PROCESSING_ERROR:
   - Recommended Action: RETRY_PAYMENT
   - Reason: Temporary payment processor or network glitch; execute smart retry.

4. ABANDONED_CHECKOUT:
   - Recommended Action: SEND_REMINDER
   - Reason: Customer abandoned cart during checkout; send cart recovery reminder.

5. FAILED_SUBSCRIPTION:
   - If failure_reason is EXPIRED_CARD: UPDATE_PAYMENT_METHOD
   - Otherwise: RETRY_PAYMENT

6. OVERDUE_INVOICE:
   - If days_overdue <= 30: SEND_REMINDER
   - If 30 < days_overdue <= 60: SEND_REMINDER or TRACK_PROMISE_TO_PAY
   - If days_overdue > 60 or amount_at_risk >= 500.0: ESCALATE (requires_human_approval = True)

Base your reasoning strictly on the facts provided in the input case payload. You MUST call the classify_recovery_case tool with strict adherence to the schema.
"""

def _is_api_key_valid() -> bool:
    return bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("your_openrouter"))

def _rule_table_classify(case: dict) -> Dict[str, Any]:
    """
    Tier 3 Fallback Classifier: Deterministic rule table executed when both primary and secondary AI models fail.
    Never guesses on unknown failure reasons — escalates to human review. Sets confidence=0.5 and requires_human_approval=True.
    """
    failure_reason = str(case.get("failure_reason", "")).upper()
    case_type = str(case.get("case_type", "")).upper()

    if failure_reason == "EXPIRED_CARD":
        action = "UPDATE_PAYMENT_METHOD"
        root_cause = "Payment card expired on file"
    elif failure_reason == "INSUFFICIENT_FUNDS":
        action = "RETRY_PAYMENT"
        root_cause = "Insufficient funds in customer account"
    elif failure_reason in ["TEMPORARY_FAILURE", "GATEWAY_ERROR", "PROCESSING_ERROR", "NETWORK_TIMEOUT"]:
        action = "RETRY_PAYMENT"
        root_cause = "Temporary payment gateway failure"
    elif case_type == "ABANDONED_CHECKOUT":
        action = "SEND_REMINDER"
        root_cause = "Checkout abandoned at payment step"
    else:
        action = "ESCALATE"
        root_cause = f"Unknown failure reason ('{failure_reason}') - escalated for human review"

    return {
        "root_cause": root_cause,
        "recommended_action": action,
        "confidence": 0.5,
        "reason": f"Rule-based fallback triggered for failure_reason='{failure_reason}' (AI models unavailable).",
        "requires_human_approval": True,
        "decision_source": "FALLBACK_RULE"
    }

def _call_openrouter_model(case: dict, model_name: str) -> Dict[str, Any]:
    """
    Helper to execute an OpenRouter model call and parse the single tool call (tool_calls[0]).
    """
    case_id = case.get("case_id", "UNKNOWN")
    client = OpenRouter(api_key=OPENROUTER_API_KEY)
    user_content = f"Classify this at-risk recovery case: {json.dumps(case)}"

    completion = client.chat.send(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        tools=[CLASSIFY_CASE_TOOL],
        tool_choice={"type": "function", "function": {"name": "classify_recovery_case"}}
    )

    tool_calls = completion.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError(f"OpenRouter model '{model_name}' response did not contain expected tool_calls payload")

    if len(tool_calls) > 1:
        logger.warning(
            f"[MULTIPLE TOOL CALLS WARNING] Model '{model_name}' returned {len(tool_calls)} tool calls for Case #{case_id}. Using tool_calls[0]."
        )

    args = json.loads(tool_calls[0].function.arguments)
    return {
        "root_cause": str(args.get("root_cause", "")),
        "recommended_action": str(args.get("recommended_action", "SEND_REMINDER")),
        "confidence": float(args.get("confidence", 0.8)),
        "reason": str(args.get("reason", "")),
        "requires_human_approval": bool(args.get("requires_human_approval", False))
    }

def _is_daily_quota_error(e: Exception) -> bool:
    err_msg = str(e).lower()
    quota_indicators = [
        "free-models-per-day",
        "daily quota",
        "daily-quota",
        "free model requests per day",
        "per-day",
        "quota exceeded"
    ]
    return any(indicator in err_msg for indicator in quota_indicators)

def classify_case(case: dict, force_fallback: bool = False) -> Dict[str, Any]:
    """
    Tiered 3-Level Classification Flow:
    1. Tier 1 (AI_PRIMARY): Tries primary model (OPENROUTER_MODEL). Retries once with backoff on error.
       * Fast-fails immediately to Tier 3 if error is daily quota exhaustion ("free-models-per-day").
    2. Tier 2 (AI_SECONDARY): Tries secondary model (OPENROUTER_FALLBACK_MODEL) if Tier 1 fails.
    3. Tier 3 (FALLBACK_RULE): Deterministic rule table if both AI models fail.
    Guaranteed NEVER to raise an unhandled exception to the caller.
    """
    case_id = case.get("case_id", "UNKNOWN")

    try:
        if force_fallback:
            logger.warning(f"[AI CLASSIFY FALLBACK WARNING] Explicit force_fallback=True requested for Case #{case_id}; executing Tier 3 Fallback Rule table.")
            return _rule_table_classify(case)

        # Validate client prerequisites before API calls
        if not _is_api_key_valid() or OpenRouter is None:
            logger.warning(f"[AI CLASSIFY FALLBACK WARNING] OpenRouter client unconfigured/invalid for Case #{case_id}; executing Tier 3 Fallback Rule table.")
            return _rule_table_classify(case)

        # ------------------------------------------------------------------
        # TIER 1: Primary Model Attempt (AI_PRIMARY)
        # ------------------------------------------------------------------
        logger.info(f"[AI CLASSIFY START] Case #{case_id} attempting Tier 1 Primary Model '{MODEL_NAME}'")
        tier1_error = None

        for attempt in range(2):
            try:
                res = _call_openrouter_model(case, MODEL_NAME)
                res["decision_source"] = "AI_PRIMARY"
                logger.info(f"[AI CLASSIFY SUCCESS] Case #{case_id} classified via Tier 1 Primary Model '{MODEL_NAME}' (source=AI_PRIMARY)")
                return res
            except (TooManyRequestsResponseError, OpenRouterError, Exception) as e:
                tier1_error = e
                if _is_daily_quota_error(e):
                    logger.warning(
                        f"[AI CLASSIFY FAST-FAIL] Daily quota limit detected for Case #{case_id} ('{e}'). "
                        f"Skipping retry and Tier 2 secondary model attempts. Executing Tier 3 Fallback Rule table immediately."
                    )
                    return _rule_table_classify(case)

                if attempt == 0:
                    logger.warning(f"[AI CLASSIFY RETRY] Case #{case_id} Tier 1 Primary Model attempt 1 failed ({type(e).__name__}: {e}). Retrying after 1.0s backoff...")
                    import time
                    time.sleep(1.0)

        # ------------------------------------------------------------------
        # TIER 2: Secondary Model Attempt (AI_SECONDARY)
        # ------------------------------------------------------------------
        logger.warning(
            f"[AI CLASSIFY FALLBACK WARNING] Case #{case_id} Tier 1 Primary Model '{MODEL_NAME}' failed after retry ({type(tier1_error).__name__}: {tier1_error}). "
            f"Attempting Tier 2 Secondary Model '{FALLBACK_MODEL_NAME}'..."
        )

        try:
            res = _call_openrouter_model(case, FALLBACK_MODEL_NAME)
            res["decision_source"] = "AI_SECONDARY"
            logger.warning(f"[AI CLASSIFY FALLBACK SUCCESS] Case #{case_id} classified via Tier 2 Secondary Model '{FALLBACK_MODEL_NAME}' (source=AI_SECONDARY)")
            return res
        except (TooManyRequestsResponseError, OpenRouterError, Exception) as tier2_error:
            # ------------------------------------------------------------------
            # TIER 3: Deterministic Fallback Rule Table (FALLBACK_RULE)
            # ------------------------------------------------------------------
            logger.warning(
                f"[CRITICAL CLASSIFY FALLBACK WARNING] Both primary ('{MODEL_NAME}') and secondary ('{FALLBACK_MODEL_NAME}') AI models failed for Case #{case_id} "
                f"(Tier 1 error: {tier1_error}; Tier 2 error: {tier2_error}). Executing Tier 3 Fallback Rule table."
            )
            return _rule_table_classify(case)

    except Exception as fatal_err:
        logger.warning(
            f"[CRITICAL CLASSIFY UNHANDLED FALLBACK] Unexpected exception in classify_case for Case #{case_id}: {fatal_err}. Executing Tier 3 Fallback Rule table."
        )
        return _rule_table_classify(case)

async def classify_case_async(case: dict) -> Dict[str, Any]:
    """
    Asynchronously classifies an at-risk case using OpenRouter client.
    """
    import asyncio
    return await asyncio.to_thread(classify_case, case)
