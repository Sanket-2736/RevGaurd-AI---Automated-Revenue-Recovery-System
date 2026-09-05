import os
import csv
import logging
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.db import engine
from app.models import Customer, Payment, Checkout, Subscription, Invoice

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

def find_synthetic_data_dir() -> str:
    """Finds synthetic-data directory relative to backend or workspace root."""
    env_dir = os.getenv("SYNTHETIC_DATA_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir

    base_file_dir = os.path.dirname(os.path.abspath(__file__))
    cwd_dir = os.getcwd()

    possible_paths = [
        os.path.abspath(os.path.join(base_file_dir, "synthetic-data")),
        os.path.abspath(os.path.join(base_file_dir, "../synthetic-data")),
        os.path.abspath(os.path.join(base_file_dir, "../../synthetic-data")),
        os.path.abspath(os.path.join(base_file_dir, "../../../synthetic-data")),
        os.path.abspath(os.path.join(cwd_dir, "synthetic-data")),
        os.path.abspath(os.path.join(cwd_dir, "../synthetic-data")),
        os.path.abspath(os.path.join(cwd_dir, "../../synthetic-data")),
    ]

    for p in possible_paths:
        if os.path.isdir(p):
            logger.info(f"[SYNTHETIC DATA] Found synthetic-data directory at: '{p}'")
            return p

    logger.error(f"Could not locate synthetic-data directory. Checked paths: {possible_paths}")
    raise FileNotFoundError(f"Could not locate synthetic-data directory. Checked paths: {possible_paths}")

def parse_iso_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val or not val.strip():
        return None
    try:
        return datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
    except ValueError:
        return None

def read_csv_rows(filepath: str) -> List[Dict[str, str]]:
    if not os.path.isfile(filepath):
        logger.warning(f"File not found: {filepath}")
        return []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

@router.post("/all")
def ingest_all_synthetic_data(override_data_dir: Optional[str] = None):
    """
    Bulk ingests (Upserts) customers, payments, checkouts, subscriptions, and invoices
    from CSV files in a single atomic database transaction. Idempotent across multiple runs.
    """
    logger.info(f"[API] POST /api/ingest/all override_data_dir={override_data_dir}")
    if override_data_dir and os.path.isdir(override_data_dir):
        data_dir = override_data_dir
    else:
        try:
            data_dir = find_synthetic_data_dir()
        except FileNotFoundError as e:
            raise HTTPException(status_code=500, detail=str(e))

    customers_csv = os.path.join(data_dir, "customers.csv")
    payments_csv = os.path.join(data_dir, "payments.csv")
    checkouts_csv = os.path.join(data_dir, "checkouts.csv")
    subscriptions_csv = os.path.join(data_dir, "subscriptions.csv")
    invoices_csv = os.path.join(data_dir, "invoices.csv")

    raw_customers = read_csv_rows(customers_csv)
    raw_payments = read_csv_rows(payments_csv)
    raw_checkouts = read_csv_rows(checkouts_csv)
    raw_subscriptions = read_csv_rows(subscriptions_csv)
    raw_invoices = read_csv_rows(invoices_csv)

    counts = {
        "customers": 0,
        "payments": 0,
        "checkouts": 0,
        "subscriptions": 0,
        "invoices": 0,
    }

    # Execute entire bulk import inside one atomic transaction
    with Session(engine) as session:
        try:
            with session.begin():
                # 1. Parse & Upsert Customers
                existing_customers = {c.external_id: c for c in session.exec(select(Customer)).all()}
                customer_id_map: Dict[str, int] = {}
                processed_cust_count = 0

                for idx, row in enumerate(raw_customers):
                    ext_id = row.get("external_id", "").strip()
                    name = row.get("name", "").strip()
                    email = row.get("email", "").strip()

                    if not ext_id or not name or not email:
                        logger.warning(f"Skipping customer row {idx}: missing required fields (ext_id, name, or email)")
                        continue

                    try:
                        risk_score = float(row.get("risk_score", 0.0))
                    except ValueError:
                        risk_score = 0.0

                    created_at = parse_iso_datetime(row.get("created_at")) or datetime.utcnow()
                    phone = row.get("phone", "").strip() or None

                    if ext_id in existing_customers:
                        cust = existing_customers[ext_id]
                        cust.name = name
                        cust.email = email
                        cust.phone = phone
                        cust.risk_score = risk_score
                        cust.created_at = created_at
                    else:
                        cust = Customer(
                            external_id=ext_id,
                            name=name,
                            email=email,
                            phone=phone,
                            risk_score=risk_score,
                            created_at=created_at,
                        )
                        session.add(cust)
                        existing_customers[ext_id] = cust

                    processed_cust_count += 1
                    csv_id = row.get("id", "").strip()
                    if csv_id:
                        customer_id_map[csv_id] = cust

                session.flush()

                # Populate ID map with populated DB primary keys
                for csv_id, cust in customer_id_map.items():
                    customer_id_map[csv_id] = cust.id
                for ext_id, cust in existing_customers.items():
                    customer_id_map[ext_id] = cust.id

                counts["customers"] = processed_cust_count

                # 2. Parse & Upsert Payments
                existing_payments = {p.external_id: p for p in session.exec(select(Payment)).all()}
                processed_pay_count = 0

                for idx, row in enumerate(raw_payments):
                    ext_id = row.get("external_id", "").strip()
                    raw_cid = row.get("customer_id", "").strip()
                    raw_amount = row.get("amount", "").strip()
                    status = row.get("status", "").strip()

                    if not ext_id or not raw_cid or not raw_amount or not status:
                        logger.warning(f"Skipping payment row {idx}: missing required fields")
                        continue

                    db_cid = customer_id_map.get(raw_cid)
                    if not db_cid:
                        logger.warning(f"Skipping payment row {idx}: customer_id {raw_cid} not found in database")
                        continue

                    try:
                        amount = float(raw_amount)
                    except ValueError:
                        logger.warning(f"Skipping payment row {idx}: invalid amount {raw_amount}")
                        continue

                    created_at = parse_iso_datetime(row.get("created_at")) or datetime.utcnow()
                    currency = row.get("currency", "USD").strip() or "USD"
                    failure_reason = row.get("failure_reason", "").strip() or None
                    payment_method = row.get("payment_method", "").strip() or None

                    if ext_id in existing_payments:
                        pay = existing_payments[ext_id]
                        pay.customer_id = db_cid
                        pay.amount = amount
                        pay.currency = currency
                        pay.status = status
                        pay.failure_reason = failure_reason
                        pay.payment_method = payment_method
                        pay.created_at = created_at
                    else:
                        pay = Payment(
                            external_id=ext_id,
                            customer_id=db_cid,
                            amount=amount,
                            currency=currency,
                            status=status,
                            failure_reason=failure_reason,
                            payment_method=payment_method,
                            created_at=created_at,
                        )
                        session.add(pay)
                        existing_payments[ext_id] = pay

                    processed_pay_count += 1

                counts["payments"] = processed_pay_count

                # 3. Parse & Upsert Checkouts
                existing_checkouts = {c.external_id: c for c in session.exec(select(Checkout)).all()}
                processed_chk_count = 0

                for idx, row in enumerate(raw_checkouts):
                    ext_id = row.get("external_id", "").strip()
                    raw_cid = row.get("customer_id", "").strip()
                    raw_cart = row.get("cart_value", "").strip()
                    status = row.get("status", "").strip()

                    if not ext_id or not raw_cid or not raw_cart or not status:
                        logger.warning(f"Skipping checkout row {idx}: missing required fields")
                        continue

                    db_cid = customer_id_map.get(raw_cid)
                    if not db_cid:
                        logger.warning(f"Skipping checkout row {idx}: customer_id {raw_cid} not found")
                        continue

                    try:
                        cart_value = float(raw_cart)
                    except ValueError:
                        logger.warning(f"Skipping checkout row {idx}: invalid cart_value {raw_cart}")
                        continue

                    created_at = parse_iso_datetime(row.get("created_at")) or datetime.utcnow()
                    currency = row.get("currency", "USD").strip() or "USD"
                    abandoned_step = row.get("abandoned_step", "").strip() or None

                    if ext_id in existing_checkouts:
                        chk = existing_checkouts[ext_id]
                        chk.customer_id = db_cid
                        chk.cart_value = cart_value
                        chk.currency = currency
                        chk.status = status
                        chk.abandoned_step = abandoned_step
                        chk.created_at = created_at
                    else:
                        chk = Checkout(
                            external_id=ext_id,
                            customer_id=db_cid,
                            cart_value=cart_value,
                            currency=currency,
                            status=status,
                            abandoned_step=abandoned_step,
                            created_at=created_at,
                        )
                        session.add(chk)
                        existing_checkouts[ext_id] = chk

                    processed_chk_count += 1

                counts["checkouts"] = processed_chk_count

                # 4. Parse & Upsert Subscriptions
                existing_subscriptions = {s.external_id: s for s in session.exec(select(Subscription)).all()}
                processed_sub_count = 0

                for idx, row in enumerate(raw_subscriptions):
                    ext_id = row.get("external_id", "").strip()
                    raw_cid = row.get("customer_id", "").strip()
                    plan_name = row.get("plan_name", "").strip()
                    raw_amount = row.get("amount", "").strip()
                    status = row.get("status", "").strip()

                    if not ext_id or not raw_cid or not plan_name or not raw_amount or not status:
                        logger.warning(f"Skipping subscription row {idx}: missing required fields")
                        continue

                    db_cid = customer_id_map.get(raw_cid)
                    if not db_cid:
                        logger.warning(f"Skipping subscription row {idx}: customer_id {raw_cid} not found")
                        continue

                    try:
                        amount = float(raw_amount)
                    except ValueError:
                        logger.warning(f"Skipping subscription row {idx}: invalid amount {raw_amount}")
                        continue

                    next_billing_date = parse_iso_datetime(row.get("next_billing_date"))
                    created_at = parse_iso_datetime(row.get("created_at")) or datetime.utcnow()
                    currency = row.get("currency", "USD").strip() or "USD"

                    if ext_id in existing_subscriptions:
                        sub = existing_subscriptions[ext_id]
                        sub.customer_id = db_cid
                        sub.plan_name = plan_name
                        sub.amount = amount
                        sub.currency = currency
                        sub.status = status
                        sub.next_billing_date = next_billing_date
                        sub.created_at = created_at
                    else:
                        sub = Subscription(
                            external_id=ext_id,
                            customer_id=db_cid,
                            plan_name=plan_name,
                            amount=amount,
                            currency=currency,
                            status=status,
                            next_billing_date=next_billing_date,
                            created_at=created_at,
                        )
                        session.add(sub)
                        existing_subscriptions[ext_id] = sub

                    processed_sub_count += 1

                counts["subscriptions"] = processed_sub_count

                # 5. Parse & Upsert Invoices
                existing_invoices = {i.external_id: i for i in session.exec(select(Invoice)).all()}
                processed_inv_count = 0

                for idx, row in enumerate(raw_invoices):
                    ext_id = row.get("external_id", "").strip()
                    raw_cid = row.get("customer_id", "").strip()
                    raw_due = row.get("amount_due", "").strip()
                    status = row.get("status", "").strip()

                    if not ext_id or not raw_cid or not raw_due or not status:
                        logger.warning(f"Skipping invoice row {idx}: missing required fields")
                        continue

                    db_cid = customer_id_map.get(raw_cid)
                    if not db_cid:
                        logger.warning(f"Skipping invoice row {idx}: customer_id {raw_cid} not found")
                        continue

                    try:
                        amount_due = float(raw_due)
                    except ValueError:
                        logger.warning(f"Skipping invoice row {idx}: invalid amount_due {raw_due}")
                        continue

                    due_date = parse_iso_datetime(row.get("due_date")) or datetime.utcnow()
                    created_at = parse_iso_datetime(row.get("created_at")) or datetime.utcnow()
                    currency = row.get("currency", "USD").strip() or "USD"

                    if ext_id in existing_invoices:
                        inv = existing_invoices[ext_id]
                        inv.customer_id = db_cid
                        inv.amount_due = amount_due
                        inv.currency = currency
                        inv.status = status
                        inv.due_date = due_date
                        inv.created_at = created_at
                    else:
                        inv = Invoice(
                            external_id=ext_id,
                            customer_id=db_cid,
                            amount_due=amount_due,
                            currency=currency,
                            status=status,
                            due_date=due_date,
                            created_at=created_at,
                        )
                        session.add(inv)
                        existing_invoices[ext_id] = inv

                    processed_inv_count += 1

                counts["invoices"] = processed_inv_count

        except Exception as e:
            logger.error(f"Ingestion failed and transaction rolled back: {e}")
            raise HTTPException(status_code=500, detail=f"Ingestion transaction failed: {str(e)}")

    logger.info(f"[API RESPONSE] POST /api/ingest/all status=200 counts={counts}")
    return counts
