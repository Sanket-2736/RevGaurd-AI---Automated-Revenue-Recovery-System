import os
import csv
import sys
import random
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import SQLModel, Session, select, text
from app.db import engine
from app.models import RecoveryCase, GuardrailEvent, RecoveryAction, GuardrailDecision
from app.routers.ingestion import ingest_all_synthetic_data
from app.routers.metrics import get_live_metrics
from app.services.detection import detect_revenue_at_risk
from app.ai import classify_case
from app.services.guardrails import validate_action
from app.simulator.recovery_simulator import execute_recovery_action, find_synthetic_data_dir

# Configure logging to write to demo-run-log.txt at repo root
log_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo-run-log.txt"))

class LoggerTee:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log_file = open(filename, "w", encoding="utf-8")

    def write(self, message):
        try:
            self.terminal.write(message)
        except UnicodeEncodeError:
            # Fallback for Windows CMD cp1252 encoding
            self.terminal.write(message.encode("ascii", errors="replace").decode("ascii"))
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

def load_ground_truth_map() -> Dict[int, str]:
    data_dir = find_synthetic_data_dir()
    csv_path = os.path.join(data_dir, "recovery_ground_truth.csv")
    gt_map = {}
    if os.path.isfile(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = int(row.get("case_id", 0))
                gt_map[cid] = row.get("expected_action", "").strip()
    return gt_map

def run_full_demo(seed: int = 42):
    tee = LoggerTee(log_file_path)
    sys.stdout = tee

    # Set deterministic random seed
    random.seed(seed)

    print("==========================================================================")
    print(f"  AI REVENUE RECOVERY AGENT - FULL END-TO-END DEMO RUN (SEED={seed})")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("==========================================================================")

    # 1. Reset DB
    print("\n[Step 1/5] Resetting database tables...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("Database reset complete.")

    # 2. Re-seed Synthetic Data
    print("\n[Step 2/5] Ingesting synthetic datasets (Payments, Checkouts, Subscriptions, Invoices)...")
    ingest_res = ingest_all_synthetic_data()
    print(f"Ingestion complete: Processed records: {ingest_res}")

    # 3. Detection Run
    print("\n[Step 3/5] Executing Revenue-at-Risk Detection engine...")
    with Session(engine) as session:
        detect_res = detect_revenue_at_risk(session)
        print(f"Detection complete: Created {detect_res['cases_created']} cases representing ${detect_res['total_at_risk']:,.2f} at risk.")

    # Load Ground Truth Map
    ground_truth_map = load_ground_truth_map()

    # Action synonym equivalents for ground truth accuracy scoring
    ACTION_EQUIVALENTS = {
        "RETRY_PAYMENT": ["RETRY_PAYMENT", "EXECUTE_SMART_RETRY", "SCHEDULE_PAYDAY_RETRY"],
        "SEND_REMINDER": ["SEND_REMINDER", "SEND_CART_REMINDER", "SEND_PAYMENT_REMINDER", "SEND_FINAL_NOTICE", "SEND_VIP_DISCOUNT_NUDGE", "SEND_GENERIC_REMINDER"],
        "UPDATE_PAYMENT_METHOD": ["UPDATE_PAYMENT_METHOD", "SEND_CARD_UPDATE_LINK", "SUBSCRIPTION_RECOVERY_EMAIL"],
        "TRACK_PROMISE_TO_PAY": ["TRACK_PROMISE_TO_PAY", "ACCOUNT_MANAGER_OUTREACH"],
        "ESCALATE": ["ESCALATE", "ESCALATE_TO_COLLECTIONS"],
        "STOP_RECOVERY": ["STOP_RECOVERY"],
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

    # 4. Process all cases synchronously through full pipeline
    max_live_ai_calls = 5
    print(f"\n[Step 4/5] Processing all detected cases (First {max_live_ai_calls} live Cerebras AI calls -> Bulk deterministic run -> Guardrails -> Simulator)...")

    gt_correct = 0
    gt_total = 0
    cat_gt_correct = defaultdict(int)
    cat_gt_total = defaultdict(int)

    with Session(engine) as session:
        cases = session.exec(select(RecoveryCase)).all()
        print(f"Retrieved {len(cases)} detected recovery cases from database.\n")

        for idx, case in enumerate(cases, start=1):
            c_type_str = case.case_type.value if hasattr(case.case_type, 'value') else str(case.case_type)
            payload = {
                "case_id": case.id,
                "case_type": c_type_str,
                "customer_id": case.customer_id,
                "amount_at_risk": float(case.amount_at_risk),
                "status": case.status.value if hasattr(case.status, 'value') else str(case.status)
            }

            # Step 4a: Classify (Live Cerebras AI for first N cases, deterministic fallback for remaining bulk run)
            use_fallback = (idx > max_live_ai_calls)
            ai_decision = classify_case(payload, force_fallback=use_fallback)
            rec_action = ai_decision.get("recommended_action", "SEND_REMINDER")

            # Evaluate ground truth match per category
            gt_expected = ground_truth_map.get(case.id, "")
            if gt_expected:
                gt_total += 1
                cat_gt_total[c_type_str] += 1

                allowed = ACTION_EQUIVALENTS.get(gt_expected, [gt_expected])
                if rec_action in allowed or gt_expected in ACTION_EQUIVALENTS.get(rec_action, [rec_action]):
                    gt_correct += 1
                    cat_gt_correct[c_type_str] += 1

            # Step 4b: Validate Guardrails
            g_eval = validate_action(case, ai_decision, attempt_count=1, session=session)
            route = g_eval["route"]
            decision = g_eval["decision"]

            # Log audit line to output
            log_line = f"Case #{case.id:03d} | Type={payload['case_type']:<18} | Amount=${payload['amount_at_risk']:>8.2f} | Action={rec_action:<21} | Route={route:<12} | Decision={decision:<8} | Reason: {g_eval['reason']}"
            print(log_line)

            # Step 4c: Execute Simulator if approved
            if decision == "APPROVED":
                sim_res = execute_recovery_action(case, rec_action, session=session)

    # 5. Compute Final Metrics matching /api/metrics
    print("\n[Step 5/5] Computing final live database metrics report...")
    with Session(engine) as session:
        metrics = get_live_metrics(session)
        all_guardrails = session.exec(select(GuardrailEvent)).all()
        all_cases = session.exec(select(RecoveryCase)).all()

        total_at_risk = metrics["total_at_risk"]
        total_recovered = metrics["total_recovered"]
        recovery_rate = metrics["recovery_rate"]

        gt_accuracy_pct = (gt_correct / gt_total * 100.0) if gt_total > 0 else 0.0

        closed_blocks = sum(1 for g in all_guardrails if "CLOSED" in g.rule_triggered)
        human_review_blocks = sum(1 for g in all_guardrails if "HUMAN_REVIEW" in g.rule_triggered or "MAX_AUTO_APPROVAL" in g.rule_triggered or "LOW_CONFIDENCE" in g.rule_triggered)
        escalate_blocks = sum(1 for g in all_guardrails if "ESCALATE" in g.rule_triggered or "MAX_RETRIES" in g.rule_triggered)
        total_blocked = sum(1 for g in all_guardrails if g.decision == GuardrailDecision.BLOCKED)
        approved_count = sum(1 for g in all_guardrails if g.decision == GuardrailDecision.APPROVED)

    # Print Dashboard Metrics Summary Report (ASCII-only box formatting for Windows CP1252 compatibility)
    print("\n" + "=" * 80)
    print("                 AI REVENUE RECOVERY AGENT - DEMO METRICS REPORT                ")
    print("=" * 80)
    print(f" Total Revenue At Risk:      ${total_at_risk:,.2f}")
    print(f" Total Revenue Recovered:    ${total_recovered:,.2f}")
    print(f" Overall Recovery Rate:      {recovery_rate:.1f}%")
    print(f" Ground Truth AI Accuracy:  {gt_accuracy_pct:.1f}% ({gt_correct}/{gt_total} matches)")
    print("-" * 80)
    print(" Ground Truth AI Accuracy Breakdown by Category:")
    for ct, tot in cat_gt_total.items():
        corr = cat_gt_correct[ct]
        acc_pct = (corr / tot * 100.0) if tot > 0 else 0.0
        print(f"   |- {ct:<20}: {acc_pct:5.1f}% ({corr:>3}/{tot:<3} matches)")
    print("-" * 80)
    print(f" Total Cases Evaluated:      {len(all_cases)}")
    print(f" Auto-Executed / Approved:   {approved_count}")
    print(f" Total Guardrail Blocks:     {total_blocked}")
    print(f"   |- CLOSED Route:          {closed_blocks}")
    print(f"   |- HUMAN_REVIEW Route:    {human_review_blocks}")
    print(f"   +- ESCALATE Route:        {escalate_blocks}")
    print(f" Total Human Escalations:    {metrics['human_escalations']}")
    print("=" * 80 + "\n")

    # 6. Execute Hand SQL Reconciliation Queries against raw DB tables
    print("=" * 80)
    print("      DATABASE RECONCILIATION VERIFICATION (RAW SQL VS API METRICS)")
    print("=" * 80)
    with Session(engine) as session:
        sql_approved = session.exec(text("SELECT COUNT(*) FROM guardrailevent WHERE decision='APPROVED'")).one()[0]
        sql_blocked = session.exec(text("SELECT COUNT(*) FROM guardrailevent WHERE decision='BLOCKED'")).one()[0]
        sql_action_count = session.exec(text("SELECT COUNT(*) FROM recoveryaction")).one()[0]
        sql_recovered_sum = session.exec(text("SELECT SUM(amount_at_risk) FROM recoverycase WHERE status='RECOVERED'")).one()[0] or 0.0

        print(f" Query 1: Approved Guardrail Events (SQL)   : {sql_approved:>6} (Expected: {approved_count})")
        print(f" Query 2: Blocked Guardrail Events (SQL)    : {sql_blocked:>6} (Expected: {total_blocked})")
        print(f" Query 3: Total Guardrail Events (A + B)    : {sql_approved + sql_blocked:>6} (Expected: {len(all_cases)})")
        print(f" Query 4: Total Recovery Actions (SQL)      : {sql_action_count:>6} (Expected: {approved_count})")
        print(f" Query 5: Sum Recovered Amount (SQL)        : ${sql_recovered_sum:>10,.2f} (Expected: ${total_recovered:,.2f})")
        print("-" * 80)

        # Assert zero divergence between SQL DB truth and reported metrics
        assert sql_approved == approved_count, f"Approved count mismatch: SQL {sql_approved} != Reported {approved_count}"
        assert sql_blocked == total_blocked, f"Blocked count mismatch: SQL {sql_blocked} != Reported {total_blocked}"
        assert sql_approved + sql_blocked == len(all_cases), "Sum of approved + blocked does not equal total cases!"
        assert sql_action_count == approved_count, f"Action count mismatch: SQL {sql_action_count} != Reported {approved_count}"
        assert round(sql_recovered_sum, 2) == round(total_recovered, 2), f"Recovered sum mismatch: SQL {sql_recovered_sum} != Reported {total_recovered}"
        print(" RECONCILIATION STATUS: 100% MATCH (ZERO DB DIVERGENCE PASSED!)")
        print("=" * 80 + "\n")

    sys.stdout = tee.terminal
    tee.log_file.close()
    print(f"Full demo run log saved to: {log_file_path}")

if __name__ == "__main__":
    run_full_demo(seed=42)
