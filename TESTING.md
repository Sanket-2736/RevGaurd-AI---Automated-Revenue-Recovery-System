# AI Revenue Recovery Agent - End-to-End Testing Guide

This document provides complete instructions for executing, verifying, and troubleshooting all test suites, concurrency load benchmarks, end-to-end demo runs, and API validation checks for the **AI Revenue Recovery Agent** project.

---

## 📋 Testing Architecture Overview

```
                                  [ TEST SUITE OVERVIEW ]
                                             │
      ┌───────────────────┬──────────────────┼───────────────────┬──────────────────┐
      ▼                   ▼                  ▼                   ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Pytest Unit │   │  Ground Truth│   │  Full Demo   │   │ Async Load   │   │ GitHub Actions│
│ & Guardrails │   │   Accuracy   │   │  Audit Run   │   │  Benchmark   │   │   CI Build   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

The monorepo contains 4 distinct testing levels:
1. **Pytest Unit & Integration Suite**: Validates safety guardrail rules, detection idempotency, ground truth accuracy, and simulator isolation.
2. **End-to-End Synchronous Demo Audit Script**: Executes the full 381-case pipeline deterministically and generates [`demo-run-log.txt`](demo-run-log.txt).
3. **Asynchronous Load & Throughput Benchmark**: Stress tests `classify_case_async` over 1,000 cases at concurrency 5, 20, and 50 using `asyncio.Semaphore`.
4. **GitHub Actions CI Workflow**: Automatically runs the entire test suite on every git push and pull request.

---

## ⚙️ Prerequisites & Environment Setup

Before running tests, ensure your local environment is configured:

```bash
# Navigate to the backend directory
cd backend

# Activate virtual environment (Windows PowerShell / CMD)
.\venv\Scripts\activate

# Install required dependencies (if not already installed)
pip install -r requirements.txt
```

Verify your environment variables (in `.env` or exported in terminal):
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
MAX_AUTO_APPROVAL_AMOUNT=500.00
MAX_RETRIES=3
MIN_CONFIDENCE=0.60
```

---

## 🧪 1. Running the Automated Pytest Suite

Run all automated unit and integration tests from the `backend` directory:

```bash
# Run full pytest suite with verbose output
pytest tests -v
```

### Breakdown of Test Modules

| Test File | Description | Assertions Verified |
| :--- | :--- | :--- |
| **[`test_guardrails.py`](backend/tests/test_guardrails.py)** | Evaluates all 5 guardrail safety rules | - `test_rule_1_already_closed`: Resolved status $\rightarrow$ `CLOSED` route<br>- `test_rule_2_amount_threshold`: Amount > \$500 $\rightarrow$ `HUMAN_REVIEW` route<br>- `test_rule_3_retry_limit`: Attempts $\ge 3$ $\rightarrow$ `ESCALATE` route<br>- `test_rule_4_low_confidence`: Confidence < 0.6 $\rightarrow$ `HUMAN_REVIEW` route<br>- `test_rule_5_happy_path`: Safe case $\rightarrow$ `AUTO_EXECUTE` route, `APPROVED`<br>- Asserts every check creates a `GuardrailEvent` audit row |
| **[`test_detection.py`](backend/tests/test_detection.py)** | Tests revenue-at-risk detection idempotency | ### 2. Detection Engine & Idempotency Testing
```bash
pytest tests/test_detection.py -v -s
```
* **What it tests**:
  - Verifies that `detect_revenue_at_risk()` creates exactly 381 cases on the first run.
  - Verifies **idempotency**: running detection a second time creates 0 new cases (`cases_created == 0`).
  - Performs **hand SQL verification** against the database to confirm zero cross-counting or double-counted categories:
    ```sql
    SELECT COUNT(*) FROM recoverycase;  -- Exactly 381
    SELECT case_type, COUNT(*) FROM recoverycase GROUP BY case_type;
    ```
  - Exact verified distribution:
    - `FAILED_PAYMENT`: **129 cases**
    - `ABANDONED_CHECKOUT`: **100 cases**
    - `OVERDUE_INVOICE`: **79 cases**
    - `FAILED_SUBSCRIPTION`: **73 cases**
| **[`test_detection.py`](backend/tests/test_detection.py)** | Tests revenue-at-risk detection idempotency | **Detection Engine & Idempotency Testing**<br>```bash<br>pytest tests/test_detection.py -v -s<br>```<br>* **What it tests**:<br>  - Verifies that `detect_revenue_at_risk()` creates exactly 381 cases on the first run.<br>  - Verifies **idempotency**: running detection a second time creates 0 new cases (`cases_created == 0`).<br>  - Performs **hand SQL verification** against the database to confirm zero cross-counting or double-counted categories:<br>    ```sql<br>    SELECT COUNT(*) FROM recoverycase;  -- Exactly 381<br>    SELECT case_type, COUNT(*) FROM recoverycase GROUP BY case_type;<br>    ```<br>  - Exact verified distribution:<br>    - `FAILED_PAYMENT`: **129 cases**<br>    - `ABANDONED_CHECKOUT`: **100 cases**<br>    - `OVERDUE_INVOICE`: **79 cases**<br>    - `FAILED_SUBSCRIPTION`: **73 cases**<br>    - **Total**: **381 cases** |
| **[`test_ground_truth_accuracy.py`](backend/tests/test_ground_truth_accuracy.py)** | Tests AI classification against ground truth CSV | Evaluates classification accuracy against `expected_action` in `recovery_ground_truth.csv` and asserts accuracy $\ge 70\%$ |
| **[`test_simulator.py`](backend/tests/test_simulator.py)** | Tests recovery action simulation engine | - Asserts all simulator responses include `"simulated": true`<br>- Asserts blocked cases **never** reach the simulator or write `RecoveryAction` database rows |

## 📊 3. Database Reconciliation Verification (Raw SQL vs API Truth)

To ensure zero silent divergence between reported dashboard metrics and actual database records, 5 raw SQL reconciliation queries are executed during full demo runs and automated pytest suites:

```sql
-- 1. Approved Guardrail Events
SELECT COUNT(*) FROM guardrailevent WHERE decision='APPROVED';  -- Matches 301

-- 2. Blocked Guardrail Events
SELECT COUNT(*) FROM guardrailevent WHERE decision='BLOCKED';   -- Matches 80

-- 3. Total Guardrail Events (Approved + Blocked)
SELECT COUNT(*) FROM guardrailevent;                            -- Matches 381 (100% of cases)

-- 4. Recovery Actions Created (1 per Approved Case)
SELECT COUNT(*) FROM recoveryaction;                            -- Matches 301 (no orphan actions)

-- 5. Total Recovered Amount
SELECT SUM(amount_recovered) FROM recoveryaction WHERE status='RECOVERED'; -- Matches $269,435.19
```

### Reconciliation Matrix
| Verification Item | Raw SQL Query Output | Reported API Metric | Status |
| :--- | :--- | :--- | :--- |
| **Approved Guardrail Events** | `301` | `301 cases` | **100% MATCH** |
| **Blocked Guardrail Events** | `80` | `80 cases` | **100% MATCH** |
| **Total Events (Approved + Blocked)** | `381` | `381 cases` | **100% MATCH** |
| **Total Recovery Actions** | `301` | `301 actions` | **100% MATCH** |
| **Sum of Recovered Amounts** | `$269,435.19` | `$269,435.19` | **100% MATCH** |


---

## 🚀 3. End-to-End Synchronous Demo Run & Audit Log

Run the end-to-end pipeline script to reset the database, re-seed synthetic data, run detection, process all 381 cases, and generate the audit log:

```bash
python scripts/full_demo_run.py
```

### What this script verifies:
1. **Database Reset**: Drops and recreates SQLModel tables (`RecoveryCase`, `GuardrailEvent`, `RecoveryAction`).
2. **Data Ingestion**: Upserts records across `customers`, `payments`, `checkouts`, `subscriptions`, and `invoices`.
3. **Revenue Detection**: Detects **381 cases** representing **\$376,590.00** at risk.
4. **Full Pipeline Execution**: Processes every case through LLM Classification $\rightarrow$ Safety Guardrails $\rightarrow$ Recovery Simulation.
5. **Audit Logging**: Writes complete evaluation logs to [`demo-run-log.txt`](demo-run-log.txt) in root directory.

### Reproducibility Check:
Run the command twice in a row:
```bash
python scripts/full_demo_run.py
```
**Expected Outcome**: Both runs produce **100% identical numbers** (Recovery Rate: **71.5%**, Ground Truth AI Accuracy: **96.1%**, Guardrail Blocks: **80**), proving deterministic execution.

---

## ⚡ 4. Asynchronous Concurrency Load Benchmark

Test the throughput and latency of `classify_case_async` under concurrent load over 1,000 synthetic cases:

```bash
python scripts/load_test.py
```

### Benchmark Metrics Evaluated:
- Runs tests across concurrency levels **5**, **20**, and **50** bounded by `asyncio.Semaphore`.
- Prints comparison table displaying wall-clock time, average latency per case, throughput (cases/sec), and error count.

---

## 🌐 5. Testing REST API Endpoints & Live SSE Stream

Spin up the backend service locally:
```bash
uvicorn app.main:app --reload --port 8000
```

### Endpoint Verification Commands (curl / PowerShell)

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```
   *Response*: `{"status": "ok", "service": "ai-revenue-recovery-backend"}`

2. **Data Ingestion**:
   ```bash
   curl -X POST http://localhost:8000/api/ingest/all
   ```

3. **Detection Engine**:
   ```bash
   curl -X POST http://localhost:8000/api/detection/run
   ```

4. **Live Metrics**:
   ```bash
   curl http://localhost:8000/api/metrics
   ```
   *Response*: Returns live database stats including `total_at_risk`, `total_recovered`, `recovery_rate`, `guardrail_blocks`, and `human_escalations`.

5. **Server-Sent Events (SSE) Live Stream**:
   ```bash
   curl -N http://localhost:8000/api/batch/demo_batch_1/stream
   ```
   *Response*: Pushes real-time JSON event stream as cases process.

---

## 🛠 6. Docker Compose End-to-End Stack Verification

Test full containerized deployment including Postgres, Redis, FastAPI Backend, RQ Worker, and React Frontend:

```bash
# Spin up all container microservices
docker compose up --build

# Verify container status
docker compose ps
```

Verify services in browser:
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔄 7. GitHub Actions CI Verification

The CI workflow is defined in [`.github/workflows/test.yml`](.github/workflows/test.yml).

To test CI locally or on push:
1. Push any commit to `main` or `master` branch.
2. Navigate to your GitHub repository's **Actions** tab.
3. Confirm the **Run Pytest Suite** workflow turns green.
