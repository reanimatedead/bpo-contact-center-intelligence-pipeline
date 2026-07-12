# Architecture

This pipeline follows a standard **Extract → Transform → Load → Analytics** flow,
orchestrated by a single linear runner. The structure is deliberately conservative
and follows mainstream industry practice.

## Layer responsibilities

### 1. Extract (`src/extract.py`)

Pulls raw case data from CSV files in `data/synthetic/`. The extractor validates
the input schema (required columns) and rejects malformed input loudly so failures
surface at the boundary, not deep inside analytics.

### 2. Transform (`src/transform.py`) — the GRC layer

Two things happen here, and both happen **before** anything reaches the warehouse:

1. **PII pseudonymization**
   - `customer_name`  → keyed HMAC-SHA256 (deterministic; first 12 hex chars retained)
   - `customer_phone` → preserve last 4 digits only: `***-***-9876`
   - `customer_email` → HMAC the local part, preserve the domain: `a1b2c3@example.com`

   The HMAC key is read from the `BPO_PII_HMAC_KEY` environment variable.
   If it is unset or empty, the transform raises `MissingPIIKeyError` and the
   pipeline stops — there is no silent fallback to unkeyed hashing.

   **Threat model — this is pseudonymization, not anonymization.**
   Under a given key, identical inputs map to identical outputs, which keeps
   records linkable across cases (useful for repeat-contact analysis). The
   trade-off: if the key leaks, low-entropy fields (names, common email local
   parts) can be recovered by dictionary attack — hash candidates under the
   leaked key and match. Residual risks that remain even with a secret key:
   the phone's plaintext last-4 digits and the email's plaintext domain are
   both linkable to external datasets. Treat the key as a rotating secret and
   never commit it to the repository.

2. **Data quality checks**
   - missing values per column
   - range violations (`resolution_time >= 1`, `qa_score ∈ [1, 5]`)
   - masking distinct counts (raw → masked) per PII column

All findings land in `output/quality_report.csv`.

**Why does this layer come before Load?**
Because raw PII should never persist in the warehouse, even briefly. Masking after
load means raw PII has already touched storage — and depending on the storage
medium, may sit in backups, replicas, or transaction logs. Masking before load
makes the warehouse incapable of leaking raw PII because it never had any.

### 3. Load (`src/load.py`)

Writes the cleaned, pseudonymized DataFrame to a local SQLite warehouse at
`data/warehouse.db`. Idempotent: re-running the pipeline replaces the `cases`
table rather than appending.

### 4. Analytics (`src/analytics.py`)

Computes a small set of standard contact-center KPIs from the warehouse:

- total case count
- AHT (average handling time, minutes)
- escalation rate (% T2 + T3)
- SLA hit rate (% resolved under the SLA target)
- average QA score
- case count by symptom category
- case count by purchase source
- weekly case-count trend

### 5. Dashboard (`src/dashboard.py`)

Renders the KPI tables as `output/dashboard.html` (a plain HTML table — no plotly
bundle) and exports the same data as `output/kpi_summary.csv` for downstream tools.

### 6. Orchestration (`pipeline/run_pipeline.py`)

A single linear runner. Each step is named; on failure, the runner prints which
named step failed before re-raising. No DAG library is used — for a five-step
pipeline, that would be overkill.

## Why this order matters

In many tutorials you'll see **E → L → T**: load raw data, then transform. That
works for low-stakes analytics but is a poor fit when the data contains PII or
payment-relevant fields. **Transform-before-Load** means the warehouse never sees
raw identifiers.

This is the same reason production-grade contact-center stacks separate "ingest
landing zones" from analytical warehouses — except here we make the same point
with a single in-memory DataFrame, which keeps the example small enough for one
person to read in fifteen minutes.

## What is intentionally NOT here

- **No DAG framework.** Airflow / Prefect / Dagster all make sense at scale, but
  for a five-step pipeline they add operational surface without analytical value.
- **No speech-to-text model.** Audio transcription is a real concern in contact
  centers, but bundling Whisper (or any other model) would push the install over
  a gigabyte and make "anyone can run it" untrue.
- **No cloud warehouse.** BigQuery / Snowflake / Redshift would all work — but
  they make the example impossible to run without an account. SQLite gives the
  same ETL shape with zero setup.
