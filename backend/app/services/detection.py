import logging
from typing import Dict, Any, Set, Tuple
from sqlmodel import Session, select
from app.models import Payment, Checkout, Subscription, Invoice, RecoveryCase, CaseType, CaseStatus

logger = logging.getLogger(__name__)

def detect_revenue_at_risk(session: Session) -> Dict[str, Any]:
    """
    Scans payments, checkouts, subscriptions, and invoices tables for at-risk records.
    Creates RecoveryCase records with status=DETECTED idempotently.
    Returns summary dict: {"cases_created": N, "total_at_risk": X}
    """
    # Fetch all existing cases to ensure idempotency across multiple runs
    existing_cases: Set[Tuple[CaseType, int]] = set()
    existing_records = session.exec(select(RecoveryCase.case_type, RecoveryCase.source_id)).all()
    for c_type, s_id in existing_records:
        if c_type and s_id:
            existing_cases.add((c_type, s_id))

    new_cases = []

    # 1. Scan Failed Payments
    failed_payments = session.exec(select(Payment).where(Payment.status == "FAILED")).all()
    for pay in failed_payments:
        key = (CaseType.FAILED_PAYMENT, pay.id)
        if key not in existing_cases:
            new_cases.append(
                RecoveryCase(
                    case_type=CaseType.FAILED_PAYMENT,
                    source_id=pay.id,
                    customer_id=pay.customer_id,
                    amount_at_risk=pay.amount,
                    status=CaseStatus.DETECTED
                )
            )
            existing_cases.add(key)

    # 2. Scan Abandoned Checkouts
    abandoned_checkouts = session.exec(select(Checkout).where(Checkout.status == "ABANDONED")).all()
    for chk in abandoned_checkouts:
        key = (CaseType.ABANDONED_CHECKOUT, chk.id)
        if key not in existing_cases:
            new_cases.append(
                RecoveryCase(
                    case_type=CaseType.ABANDONED_CHECKOUT,
                    source_id=chk.id,
                    customer_id=chk.customer_id,
                    amount_at_risk=chk.cart_value,
                    status=CaseStatus.DETECTED
                )
            )
            existing_cases.add(key)

    # 3. Scan Failed Subscriptions
    failed_subscriptions = session.exec(select(Subscription).where(Subscription.status == "FAILED")).all()
    for sub in failed_subscriptions:
        key = (CaseType.FAILED_SUBSCRIPTION, sub.id)
        if key not in existing_cases:
            new_cases.append(
                RecoveryCase(
                    case_type=CaseType.FAILED_SUBSCRIPTION,
                    source_id=sub.id,
                    customer_id=sub.customer_id,
                    amount_at_risk=sub.amount,
                    status=CaseStatus.DETECTED
                )
            )
            existing_cases.add(key)

    # 4. Scan Overdue Invoices
    overdue_invoices = session.exec(select(Invoice).where(Invoice.status == "OVERDUE")).all()
    for inv in overdue_invoices:
        key = (CaseType.OVERDUE_INVOICE, inv.id)
        if key not in existing_cases:
            new_cases.append(
                RecoveryCase(
                    case_type=CaseType.OVERDUE_INVOICE,
                    source_id=inv.id,
                    customer_id=inv.customer_id,
                    amount_at_risk=inv.amount_due,
                    status=CaseStatus.DETECTED
                )
            )
            existing_cases.add(key)

    # Persist newly detected cases
    if new_cases:
        session.add_all(new_cases)
        session.commit()

    # Calculate overall total_at_risk across all RecoveryCases in the database
    all_cases = session.exec(select(RecoveryCase)).all()
    total_at_risk = round(sum(c.amount_at_risk for c in all_cases), 2)

    logger.info(f"Detection complete: {len(new_cases)} cases created. Total revenue at risk: ${total_at_risk:,.2f}")

    return {
        "cases_created": len(new_cases),
        "total_at_risk": total_at_risk
    }
