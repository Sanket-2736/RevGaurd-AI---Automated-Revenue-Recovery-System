import os
import shutil
import csv
from sqlmodel import SQLModel, Session, select
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
from app.models import Customer, Payment, Checkout, Subscription, Invoice

def run_ingestion_verification():
    print("=== STARTING COMPREHENSIVE INGESTION VERIFICATION ===")

    # 1. Initialize fresh DB tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # 2. Test Fresh Ingestion
    print("\n--- TEST 1: Fresh DB Ingestion & Response Row Counts ---")
    res1 = ingest_all_synthetic_data()
    print("Response JSON:", res1)
    assert res1["customers"] == 200
    assert res1["payments"] == 350
    assert res1["checkouts"] == 250
    assert res1["subscriptions"] == 200
    assert res1["invoices"] == 200
    print("PASSED: Ingestion response row counts match CSV row counts!")

    # 3. Direct DB Spot-Checking
    print("\n--- TEST 2: Direct Database Spot-Checking ---")
    with Session(engine) as session:
        db_cust_count = len(session.exec(select(Customer)).all())
        db_pay_count = len(session.exec(select(Payment)).all())
        db_chk_count = len(session.exec(select(Checkout)).all())
        db_sub_count = len(session.exec(select(Subscription)).all())
        db_inv_count = len(session.exec(select(Invoice)).all())

        assert db_cust_count == 200
        assert db_pay_count == 350
        assert db_chk_count == 250
        assert db_sub_count == 200
        assert db_inv_count == 200

        # Spot-check Customer cust_1
        c1 = session.exec(select(Customer).where(Customer.external_id == "cust_1")).first()
        assert c1 is not None
        print(f"DB Spot-Check Customer [cust_1]: Name='{c1.name}', Email='{c1.email}', RiskScore={c1.risk_score}")

        # Spot-check Payment pay_1
        p1 = session.exec(select(Payment).where(Payment.external_id == "pay_1")).first()
        assert p1 is not None
        print(f"DB Spot-Check Payment [pay_1]: Amount=${p1.amount}, Status='{p1.status}', Method='{p1.payment_method}'")

        # Spot-check Checkout chk_1
        chk1 = session.exec(select(Checkout).where(Checkout.external_id == "chk_1")).first()
        assert chk1 is not None
        print(f"DB Spot-Check Checkout [chk_1]: CartValue=${chk1.cart_value}, Status='{chk1.status}'")

    print("PASSED: Database records verified directly in Postgres/SQLite!")

    # 4. Double Ingestion / Idempotency Test
    print("\n--- TEST 3: Double Ingestion (Idempotency Check) ---")
    res2 = ingest_all_synthetic_data()
    print("Second Ingestion Response JSON:", res2)

    with Session(engine) as session:
        db_cust_count_2 = len(session.exec(select(Customer)).all())
        db_pay_count_2 = len(session.exec(select(Payment)).all())
        db_chk_count_2 = len(session.exec(select(Checkout)).all())
        db_sub_count_2 = len(session.exec(select(Subscription)).all())
        db_inv_count_2 = len(session.exec(select(Invoice)).all())

        assert db_cust_count_2 == 200
        assert db_pay_count_2 == 350
        assert db_chk_count_2 == 250
        assert db_sub_count_2 == 200
        assert db_inv_count_2 == 200

    print("PASSED: Double ingestion executed cleanly without duplicate errors or row count inflation!")

    # 5. Corrupted Row Handling Test
    print("\n--- TEST 4: Corrupted Row Handling (Missing Required Amount) ---")
    corrupt_dir = os.path.abspath("temp_corrupt_test")
    os.makedirs(corrupt_dir, exist_ok=True)

    target_dir = os.path.abspath("../synthetic-data")
    for fname in ["customers.csv", "payments.csv", "checkouts.csv", "subscriptions.csv", "invoices.csv"]:
        shutil.copy(os.path.join(target_dir, fname), os.path.join(corrupt_dir, fname))

    # Inject corrupted row into payments.csv
    pay_corrupt_path = os.path.join(corrupt_dir, "payments.csv")
    with open(pay_corrupt_path, mode="r", encoding="utf-8") as f:
        pay_rows = list(csv.DictReader(f))

    # Corrupt payment row 0 by emptying amount
    pay_rows[0]["amount"] = ""

    with open(pay_corrupt_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(pay_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pay_rows)

    # Ingest corrupted directory
    res_corrupt = ingest_all_synthetic_data(override_data_dir=corrupt_dir)
    print("Corrupted Ingestion Response JSON:", res_corrupt)
    assert res_corrupt["payments"] == 349  # 1 corrupted row skipped, 349 ingested cleanly
    assert res_corrupt["customers"] == 200
    print("PASSED: Corrupted row with empty amount was gracefully skipped and logged!")

    shutil.rmtree(corrupt_dir, ignore_errors=True)
    print("\n=== ALL INGESTION VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_ingestion_verification()
