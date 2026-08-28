# AI Revenue Recovery Agent

[![Run Pytest Suite](https://github.com/Sanket-11/AI-Revenue-Recovery-Agent/actions/workflows/test.yml/badge.svg)](https://github.com/Sanket-11/AI-Revenue-Recovery-Agent/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An autonomous agentic system for recovering lost revenue, failed payments, abandoned checkouts, and overdue invoices using Cerebras LLMs, FastAPI, SQLModel, Redis RQ, and React.

---

## 📌 Problem Statement

Businesses lose up to 15% of annual recurring revenue due to involuntary churn, card expirations, soft declines, abandoned carts, and overdue invoices. Traditional recovery workflows rely on static, rigid dunning rules that either spam customers or escalate unnecessarily, increasing customer friction and operational cost.

The **AI Revenue Recovery Agent** dynamically evaluates at-risk revenue cases in real-time, leverages Cerebras LLMs (`gpt-oss-120b` / `llama3.1-8b`) for root-cause classification, enforces strict financial safety guardrails, and autonomously executes optimized recovery actions while maintaining a zero-trust audit ledger.

---

## 🏗 Architecture Diagram

```
                             [ Synthetic Data Sources ]
           (customers.csv, payments.csv, checkouts.csv, subscriptions.csv, invoices.csv)
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │ Ingestion Service API  │
                            │  POST /api/ingest/all  │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │ Revenue-at-Risk Engine │
                            │ POST /api/detection/run│
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │  Cerebras AI Engine    │
                            │ (root-cause & action)  │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │ 5-Rule Guardrails Engine│ ──► Writes GuardrailEvent Audit Log
                            │  (validate_action)     │
                            └───────────┬────────────┘
                                        │ (If APPROVED)
                                        ▼
                            ┌────────────────────────┐
                            │   Recovery Simulator   │ ──► Writes RecoveryAction Record
                            │ ("simulated": true)    │
                            └───────────┬────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
            ┌──────────────────────┐        ┌──────────────────────┐
            │ RQ Worker Queue      │        │ Live SSE & Metrics   │
            │ (Async Batch API)    │        │ GET /api/metrics     │
            └──────────────────────┘        └───────────┬──────────┘
                                                        │
                                                        ▼
                                            ┌──────────────────────┐
                                            │ React + TS Dashboard │
                                            └──────────────────────┘
```

---

## ⚡ One-Command Quickstart Setup

Clone the repository and spin up the backend service stack (Postgres, Redis, Backend FastAPI API, and Worker) using Docker Compose:

```bash
docker compose up --build
```

Access the interfaces once containers are active:
- **FastAPI OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Metrics Endpoint**: [http://localhost:8000/api/metrics](http://localhost:8000/api/metrics)

To run the React Frontend Dashboard locally:
```bash
cd frontend
npm run dev
```
Access the dashboard at **[http://localhost:5173](http://localhost:5173)**.


---

## 🛡 Table of Guardrail Thresholds

Every recovery evaluation passes through 5 sequential safety guardrails. All checks—whether approved or blocked—write a persistent `GuardrailEvent` record to the database ledger.

| Rule # | Guardrail Name | Policy Rule Condition | Action Route | Decision |
| :--- | :--- | :--- | :--- | :--- |
| **Rule 1** | `Case Already Closed` | Case status is `RECOVERED`/`UNRECOVERABLE` or `resolved_at` is set | `CLOSED` | `BLOCKED` |
| **Rule 2** | `Max Amount Threshold` | `amount_at_risk` > `$500.00` (`MAX_AUTO_APPROVAL_AMOUNT`) | `HUMAN_REVIEW` | `BLOCKED` |
| **Rule 3** | `Max Retry Attempts` | `action == RETRY_PAYMENT` and `attempt_count` $\ge$ `3` (`MAX_RETRIES`) | `ESCALATE` | `BLOCKED` |
| **Rule 4** | `Min Confidence Score` | AI model `confidence` < `0.60` (`MIN_CONFIDENCE`) | `HUMAN_REVIEW` | `BLOCKED` |
| **Rule 5** | `Safety Checks Passed` | All safety rules pass cleanly | `AUTO_EXECUTE` | `APPROVED` |

*Threshold values are fully configurable via environment variables (`MAX_AUTO_APPROVAL_AMOUNT`, `MAX_RETRIES`, `MIN_CONFIDENCE`).*

---

## 📊 Proven Demo Benchmark Metrics (from [`demo-run-log.txt`](demo-run-log.txt))

Results from our deterministic 381-case dataset evaluation run:

| Metric Category | Value |
| :--- | :--- |
| **Total Revenue At Risk** | **$376,590.00** |
| **Total Revenue Recovered** | **$269,435.19** |
| **Overall Recovery Rate** | **71.5%** |
| **Overall Ground Truth AI Accuracy** | **96.1%** (366 / 381 exact matches) |
| **Total Cases Evaluated** | **381 cases** |
| **Auto-Executed / Approved** | **301 cases** |
| **Total Guardrail Blocks** | **80 cases** |
| **Human Escalations (HUMAN_REVIEW)** | **80 cases** |

### 🎯 AI Classification Accuracy Breakdown by Category

| Risk Category | Matches / Total | Category Accuracy (%) | Ground Truth Benchmark Status |
| :--- | :--- | :--- | :--- |
| **FAILED_SUBSCRIPTION** | **100 / 100** | **100.0%** | **PASSED** ($\ge 70\%$) |
| **FAILED_PAYMENT** | **144 / 150** | **96.0%** | **PASSED** ($\ge 70\%$) |
| **ABANDONED_CHECKOUT** | **76 / 80** | **95.0%** | **PASSED** ($\ge 70\%$) |
| **OVERDUE_INVOICE** | **46 / 51** | **90.2%** | **PASSED** ($\ge 70\%$) |


---

## 🔄 How to Reproduce Our Results

To execute the complete end-to-end recovery pipeline synchronously and verify metrics against ground truth:

```bash
cd backend
python scripts/full_demo_run.py
```

For complete step-by-step instructions on running unit tests, mutation testing, load benchmarks, and API endpoint verification, see the **[End-to-End Testing Guide](TESTING.md)**.


This script:
1. Resets database tables (`SQLModel.metadata.drop_all`).
2. Ingests all synthetic CSV datasets (`customers`, `payments`, `checkouts`, `subscriptions`, `invoices`).
3. Runs revenue-at-risk detection across all ingested datasets.
4. Processes all 381 cases through LLM Classification $\rightarrow$ Safety Guardrails $\rightarrow$ Recovery Simulation.
5. Generates the exact audit log saved in [`demo-run-log.txt`](demo-run-log.txt).

Running the script multiple times with `seed=42` yields **100% identical numbers**, proving absolute system determinism and reproducibility.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
