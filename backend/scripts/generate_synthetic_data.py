import os
import csv
import random
import argparse
from datetime import datetime, timedelta, timezone

def utc_now():
    return datetime.now(timezone.utc)

def decide_ground_truth(case: dict, rng: random.Random) -> dict:
    """
    Determines expected recovery action, expected outcome (RECOVERED / ESCALATED / UNRECOVERABLE),
    and expected recovery amount for an at-risk case deterministically using rng.
    """
    case_type = case.get("case_type")
    amount = float(case.get("amount_at_risk", 0.0))
    customer_type = case.get("customer_type", "INDIVIDUAL")
    failure_reason = case.get("failure_reason", "")
    days_overdue = int(case.get("days_overdue", 0))
    abandoned_step = case.get("abandoned_step", "")

    expected_action = "SEND_GENERIC_REMINDER"
    outcome_weights = {"RECOVERED": 0.70, "ESCALATED": 0.15, "UNRECOVERABLE": 0.15}

    if case_type == "FAILED_PAYMENT":
        if failure_reason == "EXPIRED_CARD":
            expected_action = "SEND_CARD_UPDATE_LINK"
            outcome_weights = {"RECOVERED": 0.85, "ESCALATED": 0.05, "UNRECOVERABLE": 0.10}
        elif failure_reason == "INSUFFICIENT_FUNDS":
            expected_action = "SCHEDULE_PAYDAY_RETRY"
            outcome_weights = {"RECOVERED": 0.65, "ESCALATED": 0.20, "UNRECOVERABLE": 0.15}
        elif failure_reason == "TEMPORARY_FAILURE":
            expected_action = "EXECUTE_SMART_RETRY"
            outcome_weights = {"RECOVERED": 0.90, "ESCALATED": 0.02, "UNRECOVERABLE": 0.08}

    elif case_type == "ABANDONED_CHECKOUT":
        if amount > 500.0:
            expected_action = "SEND_VIP_DISCOUNT_NUDGE"
            outcome_weights = {"RECOVERED": 0.65, "ESCALATED": 0.00, "UNRECOVERABLE": 0.35}
        else:
            expected_action = "SEND_CART_REMINDER"
            outcome_weights = {"RECOVERED": 0.55, "ESCALATED": 0.00, "UNRECOVERABLE": 0.45}

    elif case_type == "FAILED_SUBSCRIPTION":
        if customer_type == "BUSINESS":
            expected_action = "ACCOUNT_MANAGER_OUTREACH"
            outcome_weights = {"RECOVERED": 0.80, "ESCALATED": 0.15, "UNRECOVERABLE": 0.05}
        else:
            expected_action = "SUBSCRIPTION_RECOVERY_EMAIL"
            outcome_weights = {"RECOVERED": 0.70, "ESCALATED": 0.10, "UNRECOVERABLE": 0.20}

    elif case_type == "OVERDUE_INVOICE":
        if days_overdue > 60:
            expected_action = "ESCALATE_TO_COLLECTIONS"
            outcome_weights = {"RECOVERED": 0.10, "ESCALATED": 0.60, "UNRECOVERABLE": 0.30}
        elif days_overdue > 30:
            expected_action = "SEND_FINAL_NOTICE"
            outcome_weights = {"RECOVERED": 0.60, "ESCALATED": 0.30, "UNRECOVERABLE": 0.10}
        else:
            expected_action = "SEND_PAYMENT_REMINDER"
            outcome_weights = {"RECOVERED": 0.85, "ESCALATED": 0.05, "UNRECOVERABLE": 0.10}

    outcomes = list(outcome_weights.keys())
    weights = list(outcome_weights.values())
    expected_outcome = rng.choices(outcomes, weights=weights, k=1)[0]

    if expected_outcome == "RECOVERED":
        expected_recovery_amount = amount
    elif expected_outcome == "ESCALATED":
        expected_recovery_amount = round(amount * rng.uniform(0.3, 0.7), 2)
    else:
        expected_recovery_amount = 0.0

    return {
        "case_id": case.get("case_id"),
        "case_type": case_type,
        "source_id": case.get("source_id"),
        "customer_id": case.get("customer_id"),
        "amount_at_risk": amount,
        "expected_action": expected_action,
        "expected_outcome": expected_outcome,
        "expected_recovery_amount": expected_recovery_amount
    }

def generate_customers(rng: random.Random, count: int = 200) -> list:
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Dakota",
                   "Elena", "Marcus", "Siddharth", "Aisha", "Liam", "Sophia", "Noah", "Emma", "Oliver", "Ava"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Patel", "Sharma", "Chen", "Kim", "Singh", "Wong", "Kowalski", "Mueller", "Novak", "Takahashi"]
    company_prefixes = ["Apex", "Vertex", "Nexus", "Quantum", "Synergy", "Acme", "Starlight", "Hyperion", "Pinnacle", "Vanguard"]
    company_suffixes = ["Tech", "Labs", "Solutions", "Global", "Systems", "Corp", "Inc", "Ventures", "Group", "Logistics"]

    customers = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=180)


    for i in range(1, count + 1):
        is_business = (i % 3 == 0)
        customer_type = "BUSINESS" if is_business else "INDIVIDUAL"
        
        if is_business:
            name = f"{rng.choice(company_prefixes)} {rng.choice(company_suffixes)}"
            email = f"contact@{name.lower().replace(' ', '')}.com"
        else:
            fn = rng.choice(first_names)
            ln = rng.choice(last_names)
            name = f"{fn} {ln}"
            email = f"{fn.lower()}.{ln.lower()}{rng.randint(10,99)}@example.com"

        phone = f"+1-{rng.randint(200,999)}-{rng.randint(100,999)}-{rng.randint(1000,9999)}"
        risk_score = round(rng.uniform(0.05, 0.95), 2)
        created_at = (base_time + timedelta(days=rng.randint(0, 150))).isoformat()

        customers.append({
            "id": i,
            "external_id": f"cust_{i}",
            "name": name,
            "email": email,
            "phone": phone,
            "customer_type": customer_type,
            "risk_score": risk_score,
            "created_at": created_at
        })
    return customers

def generate_payments(rng: random.Random, customers: list, count: int = 350) -> list:
    failure_reasons = ["TEMPORARY_FAILURE", "EXPIRED_CARD", "INSUFFICIENT_FUNDS"]
    payment_methods = ["CREDIT_CARD", "DEBIT_CARD", "ACH", "PAYPAL"]
    payments = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=60)

    for i in range(1, count + 1):
        cust = rng.choice(customers)
        status = "FAILED" if (rng.random() < 0.40) else "SUCCESS"
        failure_reason = rng.choice(failure_reasons) if status == "FAILED" else ""
        amount = round(rng.uniform(15.0, 1500.0), 2)
        payment_method = rng.choice(payment_methods)
        created_at = (base_time + timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))).isoformat()

        payments.append({
            "id": i,
            "external_id": f"pay_{i}",
            "customer_id": cust["id"],
            "amount": amount,
            "currency": "USD",
            "status": status,
            "failure_reason": failure_reason,
            "payment_method": payment_method,
            "created_at": created_at
        })
    return payments

def generate_checkouts(rng: random.Random, customers: list, count: int = 250) -> list:
    abandoned_steps = ["PAYMENT_METHOD", "SHIPPING_ADDRESS", "CART_REVIEW"]
    checkouts = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=45)

    for i in range(1, count + 1):
        cust = rng.choice(customers)
        status = "ABANDONED" if (rng.random() < 0.45) else "COMPLETED"
        abandoned_step = rng.choice(abandoned_steps) if status == "ABANDONED" else ""
        cart_value = round(rng.uniform(25.0, 1200.0), 2)
        created_at = (base_time + timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))).isoformat()

        checkouts.append({
            "id": i,
            "external_id": f"chk_{i}",
            "customer_id": cust["id"],
            "cart_value": cart_value,
            "currency": "USD",
            "status": status,
            "abandoned_step": abandoned_step,
            "created_at": created_at
        })
    return checkouts

def generate_subscriptions(rng: random.Random, customers: list, count: int = 200) -> list:
    plans = [("STARTER", 29.0), ("BASIC", 79.0), ("PRO", 199.0), ("ENTERPRISE", 599.0)]
    subscriptions = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=90)

    for i in range(1, count + 1):
        cust = rng.choice(customers)
        plan_name, amount = rng.choice(plans)
        status = "FAILED" if (rng.random() < 0.35) else "ACTIVE"
        created_at_dt = base_time + timedelta(days=rng.randint(0, 60))
        next_billing_dt = created_at_dt + timedelta(days=30)

        subscriptions.append({
            "id": i,
            "external_id": f"sub_{i}",
            "customer_id": cust["id"],
            "plan_name": plan_name,
            "amount": amount,
            "currency": "USD",
            "status": status,
            "next_billing_date": next_billing_dt.isoformat(),
            "created_at": created_at_dt.isoformat()
        })
    return subscriptions

def generate_invoices(rng: random.Random, customers: list, count: int = 200) -> list:
    invoices = []
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=90)


    for i in range(1, count + 1):
        cust = rng.choice(customers)
        status = "OVERDUE" if (rng.random() < 0.40) else "PAID"
        days_overdue = rng.randint(1, 90) if status == "OVERDUE" else 0
        amount_due = round(rng.uniform(150.0, 5000.0), 2)
        created_at_dt = base_time + timedelta(days=rng.randint(0, 30))
        due_date_dt = created_at_dt + timedelta(days=30)

        invoices.append({
            "id": i,
            "external_id": f"inv_{i}",
            "customer_id": cust["id"],
            "amount_due": amount_due,
            "currency": "USD",
            "status": status,
            "days_overdue": days_overdue,
            "due_date": due_date_dt.isoformat(),
            "created_at": created_at_dt.isoformat()
        })
    return invoices

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data CSVs for AI Revenue Recovery Agent")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument("--output-dir", type=str, default="../synthetic-data", help="Target directory for generated CSVs")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Determine absolute output path
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating synthetic data with seed={args.seed} into '{output_dir}'...")

    # Generate primary datasets
    customers = generate_customers(rng, count=200)
    customer_map = {c["id"]: c for c in customers}

    payments = generate_payments(rng, customers, count=350)
    checkouts = generate_checkouts(rng, customers, count=250)
    subscriptions = generate_subscriptions(rng, customers, count=200)
    invoices = generate_invoices(rng, customers, count=200)

    # Compile at-risk cases for recovery ground truth mapping
    ground_truth_records = []
    case_counter = 1

    # 1. Failed Payments
    for p in payments:
        if p["status"] == "FAILED":
            cust = customer_map[p["customer_id"]]
            case_data = {
                "case_id": case_counter,
                "case_type": "FAILED_PAYMENT",
                "source_id": p["id"],
                "customer_id": p["customer_id"],
                "amount_at_risk": p["amount"],
                "customer_type": cust["customer_type"],
                "failure_reason": p["failure_reason"],
                "days_overdue": 0,
                "abandoned_step": ""
            }
            ground_truth_records.append(decide_ground_truth(case_data, rng))
            case_counter += 1

    # 2. Abandoned Checkouts
    for c in checkouts:
        if c["status"] == "ABANDONED":
            cust = customer_map[c["customer_id"]]
            case_data = {
                "case_id": case_counter,
                "case_type": "ABANDONED_CHECKOUT",
                "source_id": c["id"],
                "customer_id": c["customer_id"],
                "amount_at_risk": c["cart_value"],
                "customer_type": cust["customer_type"],
                "failure_reason": "",
                "days_overdue": 0,
                "abandoned_step": c["abandoned_step"]
            }
            ground_truth_records.append(decide_ground_truth(case_data, rng))
            case_counter += 1

    # 3. Failed Subscriptions
    for s in subscriptions:
        if s["status"] == "FAILED":
            cust = customer_map[s["customer_id"]]
            case_data = {
                "case_id": case_counter,
                "case_type": "FAILED_SUBSCRIPTION",
                "source_id": s["id"],
                "customer_id": s["customer_id"],
                "amount_at_risk": s["amount"],
                "customer_type": cust["customer_type"],
                "failure_reason": "",
                "days_overdue": 0,
                "abandoned_step": ""
            }
            ground_truth_records.append(decide_ground_truth(case_data, rng))
            case_counter += 1

    # 4. Overdue Invoices
    for inv in invoices:
        if inv["status"] == "OVERDUE":
            cust = customer_map[inv["customer_id"]]
            case_data = {
                "case_id": case_counter,
                "case_type": "OVERDUE_INVOICE",
                "source_id": inv["id"],
                "customer_id": inv["customer_id"],
                "amount_at_risk": inv["amount_due"],
                "customer_type": cust["customer_type"],
                "failure_reason": "",
                "days_overdue": inv["days_overdue"],
                "abandoned_step": ""
            }
            ground_truth_records.append(decide_ground_truth(case_data, rng))
            case_counter += 1

    # Function to write dict list to CSV
    def write_csv(filename, data):
        if not data:
            return
        filepath = os.path.join(output_dir, filename)
        fieldnames = list(data[0].keys())
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Wrote {len(data)} rows to {filepath}")

    write_csv("customers.csv", customers)
    write_csv("payments.csv", payments)
    write_csv("checkouts.csv", checkouts)
    write_csv("subscriptions.csv", subscriptions)
    write_csv("invoices.csv", invoices)
    write_csv("recovery_ground_truth.csv", ground_truth_records)

    print("Synthetic data generation completed successfully!")

if __name__ == "__main__":
    main()
