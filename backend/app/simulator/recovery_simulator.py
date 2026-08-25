import os
import csv
import json
import logging
from typing import Dict, Any, Optional, Union, Tuple
from datetime import datetime, timezone
from sqlmodel import Session
from app.models import RecoveryCase, RecoveryAction, CaseStatus

logger = logging.getLogger(__name__)

# Ground truth lookup caches
_GROUND_TRUTH_BY_KEY: Dict[Tuple[str, int], Dict[str, Any]] = {}
_GROUND_TRUTH_BY_CASE_ID: Dict[int, Dict[str, Any]] = {}
_IS_LOADED = False

def find_synthetic_data_dir() -> str:
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../synthetic-data")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../synthetic-data")),
        os.path.abspath("synthetic-data"),
        os.path.abspath("../synthetic-data"),
    ]
    for p in possible_paths:
        if os.path.isdir(p):
            return p
    return os.path.abspath("../synthetic-data")

def _load_ground_truth_map():
    global _IS_LOADED, _GROUND_TRUTH_BY_KEY, _GROUND_TRUTH_BY_CASE_ID
    if _IS_LOADED:
        return

    data_dir = find_synthetic_data_dir()
    csv_path = os.path.join(data_dir, "recovery_ground_truth.csv")

    if not os.path.isfile(csv_path):
        logger.warning(f"Ground truth CSV not found at '{csv_path}'. Using fallback outcomes.")
        _IS_LOADED = True
        return

    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    case_id = int(row.get("case_id", 0))
                    source_id = int(row.get("source_id", 0))
                    case_type = row.get("case_type", "").strip()
                    amount = float(row.get("amount_at_risk", 0.0))
                    recovery_amt = float(row.get("expected_recovery_amount", 0.0))
                    expected_outcome = row.get("expected_outcome", "RECOVERED").strip()
                    expected_action = row.get("expected_action", "").strip()

                    record = {
                        "case_id": case_id,
                        "case_type": case_type,
                        "source_id": source_id,
                        "amount_at_risk": amount,
                        "expected_action": expected_action,
                        "expected_outcome": expected_outcome,
                        "expected_recovery_amount": recovery_amt
                    }

                    if case_id > 0:
                        _GROUND_TRUTH_BY_CASE_ID[case_id] = record
                    if case_type and source_id > 0:
                        _GROUND_TRUTH_BY_KEY[(case_type, source_id)] = record
                except (ValueError, TypeError):
                    continue

        _IS_LOADED = True
        logger.info(f"Loaded {len(_GROUND_TRUTH_BY_CASE_ID)} ground truth cases into simulator lookup cache.")
    except Exception as e:
        logger.error(f"Error loading ground truth CSV: {e}")
        _IS_LOADED = True

def _get_ground_truth(case: Union[RecoveryCase, dict]) -> Dict[str, Any]:
    _load_ground_truth_map()

    if isinstance(case, dict):
        case_id = case.get("id") or case.get("case_id")
        case_type = str(case.get("case_type", ""))
        source_id = case.get("source_id")
        amount = float(case.get("amount_at_risk", 0.0))
    else:
        case_id = case.id
        case_type = str(case.case_type.value if hasattr(case.case_type, "value") else case.case_type)
        source_id = case.source_id
        amount = float(case.amount_at_risk)

    if case_id and case_id in _GROUND_TRUTH_BY_CASE_ID:
        return _GROUND_TRUTH_BY_CASE_ID[case_id]

    if case_type and source_id and (case_type, int(source_id)) in _GROUND_TRUTH_BY_KEY:
        return _GROUND_TRUTH_BY_KEY[(case_type, int(source_id))]

    # Default fallback ground truth if case is not present in CSV
    return {
        "case_id": case_id or 0,
        "case_type": case_type,
        "source_id": source_id or 0,
        "amount_at_risk": amount,
        "expected_action": "RETRY_PAYMENT",
        "expected_outcome": "RECOVERED",
        "expected_recovery_amount": amount
    }

# ----------------------------------------------------------------------
# SIMULATION FUNCTIONS (All include "simulated": True)
# ----------------------------------------------------------------------

def simulate_retry_payment(case: Union[RecoveryCase, dict]) -> Dict[str, Any]:
    gt = _get_ground_truth(case)
    outcome = gt["expected_outcome"]
    recovery_amt = gt["expected_recovery_amount"]

    status = "EXECUTED" if outcome == "RECOVERED" else ("FAILED" if outcome == "UNRECOVERABLE" else "EXECUTED")

    return {
        "simulated": True,
        "action_type": "RETRY_PAYMENT",
        "status": status,
        "outcome": outcome,
        "recovered_amount": recovery_amt,
        "message": f"Simulated payment retry executed. Outcome: {outcome}."
    }

def simulate_send_reminder(case: Union[RecoveryCase, dict]) -> Dict[str, Any]:
    gt = _get_ground_truth(case)
    outcome = gt["expected_outcome"]
    recovery_amt = gt["expected_recovery_amount"]

    status = "EXECUTED"

    return {
        "simulated": True,
        "action_type": "SEND_REMINDER",
        "status": status,
        "outcome": outcome,
        "recovered_amount": recovery_amt,
        "message": f"Simulated payment/checkout reminder notice dispatched. Outcome: {outcome}."
    }

def simulate_update_payment_method(case: Union[RecoveryCase, dict]) -> Dict[str, Any]:
    gt = _get_ground_truth(case)
    outcome = gt["expected_outcome"]
    recovery_amt = gt["expected_recovery_amount"]

    status = "EXECUTED" if outcome in ["RECOVERED", "ESCALATED"] else "FAILED"

    return {
        "simulated": True,
        "action_type": "UPDATE_PAYMENT_METHOD",
        "status": status,
        "outcome": outcome,
        "recovered_amount": recovery_amt,
        "message": f"Simulated payment method update link dispatched to customer. Outcome: {outcome}."
    }

def simulate_track_promise_to_pay(case: Union[RecoveryCase, dict]) -> Dict[str, Any]:
    gt = _get_ground_truth(case)
    outcome = gt["expected_outcome"]
    recovery_amt = gt["expected_recovery_amount"]

    status = "EXECUTED"

    return {
        "simulated": True,
        "action_type": "TRACK_PROMISE_TO_PAY",
        "status": status,
        "outcome": outcome,
        "recovered_amount": recovery_amt,
        "message": f"Simulated promise to pay tracked on customer account. Outcome: {outcome}."
    }

# ----------------------------------------------------------------------
# DISPATCHER & RECOVERY ACTION EXECUTION MANAGER
# ----------------------------------------------------------------------

def execute_recovery_action(
    case: Union[RecoveryCase, dict],
    approved_action: str,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Dispatches approved recovery action to the appropriate simulation function,
    updates RecoveryCase status and resolved_at timestamp, and creates a RecoveryAction row.
    """
    action_str = str(approved_action).upper().strip()

    # Dispatch to specific simulator function
    if action_str in ["RETRY_PAYMENT", "EXECUTE_SMART_RETRY", "SCHEDULE_PAYDAY_RETRY"]:
        sim_res = simulate_retry_payment(case)
        channel = "SIMULATED_PAYMENT_GATEWAY"
    elif action_str in ["SEND_REMINDER", "SEND_CART_REMINDER", "SEND_PAYMENT_REMINDER", "SEND_FINAL_NOTICE"]:
        sim_res = simulate_send_reminder(case)
        channel = "SIMULATED_EMAIL"
    elif action_str in ["UPDATE_PAYMENT_METHOD", "SEND_CARD_UPDATE_LINK"]:
        sim_res = simulate_update_payment_method(case)
        channel = "SIMULATED_SMS_EMAIL"
    elif action_str in ["TRACK_PROMISE_TO_PAY", "ACCOUNT_MANAGER_OUTREACH"]:
        sim_res = simulate_track_promise_to_pay(case)
        channel = "SIMULATED_CRM"
    elif action_str in ["ESCALATE", "ESCALATE_TO_COLLECTIONS"]:
        gt = _get_ground_truth(case)
        sim_res = {
            "simulated": True,
            "action_type": "ESCALATE",
            "status": "EXECUTED",
            "outcome": "ESCALATED",
            "recovered_amount": gt.get("expected_recovery_amount", 0.0),
            "message": "Simulated escalation to collections/finance team."
        }
        channel = "SIMULATED_COLLECTIONS_QUEUE"
    else:  # STOP_RECOVERY or unknown
        gt = _get_ground_truth(case)
        sim_res = {
            "simulated": True,
            "action_type": "STOP_RECOVERY",
            "status": "EXECUTED",
            "outcome": "UNRECOVERABLE",
            "recovered_amount": 0.0,
            "message": "Simulated recovery halt."
        }
        channel = "SIMULATED_SYSTEM"

    outcome = sim_res.get("outcome", "RECOVERED")
    now_utc = datetime.now(timezone.utc)

    # Determine updated RecoveryCase status
    if outcome == "RECOVERED":
        new_status = CaseStatus.RECOVERED
    elif outcome == "ESCALATED":
        new_status = CaseStatus.ESCALATED
    elif outcome == "UNRECOVERABLE":
        new_status = CaseStatus.UNRECOVERABLE
    else:
        new_status = CaseStatus.PROCESSING

    # Update RecoveryCase and persist RecoveryAction if DB session & instance exist
    action_id = None
    if session is not None:
        try:
            db_case = None
            if isinstance(case, RecoveryCase):
                db_case = case
            elif isinstance(case, dict) and case.get("id"):
                db_case = session.get(RecoveryCase, case["id"])

            if db_case is not None:
                db_case.status = new_status
                if new_status in [CaseStatus.RECOVERED, CaseStatus.ESCALATED, CaseStatus.UNRECOVERABLE]:
                    db_case.resolved_at = now_utc

                # Create RecoveryAction audit record
                action_record = RecoveryAction(
                    case_id=db_case.id,
                    action_type=action_str,
                    channel=channel,
                    payload=json.dumps(sim_res),
                    status=sim_res.get("status", "EXECUTED"),
                    executed_at=now_utc,
                    created_at=now_utc
                )
                session.add(action_record)
                session.commit()
                session.refresh(action_record)
                session.refresh(db_case)
                action_id = action_record.id

        except Exception as e:
            logger.error(f"Failed to persist RecoveryAction and update RecoveryCase: {e}")
            if session:
                session.rollback()

    sim_res["action_id"] = action_id
    sim_res["case_status"] = new_status.value if hasattr(new_status, "value") else str(new_status)
    sim_res["resolved_at"] = now_utc.isoformat() if new_status in [CaseStatus.RECOVERED, CaseStatus.ESCALATED, CaseStatus.UNRECOVERABLE] else None

    logger.info(f"Executed action '{action_str}' for case: outcome={outcome}, status={new_status}, action_id={action_id}")

    return sim_res
