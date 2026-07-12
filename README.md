# BPO Contact Center Intelligence Pipeline

> **This repository uses synthetic (dummy) data only.**
> No real client data, no real cases, and no proprietary code from any production system
> is included. Any resemblance to specific products, companies, or platforms is incidental.
> This exists as an industry-standard ETL reconstruction for portfolio purposes.
>
> **本リポは合成（ダミー）データのみを使用します。**
> 実案件のデータ・コード・固有名（クライアント・製品・店舗）は一切含みません。
> 業界標準のETL構成を再現したポートフォリオ用の自作実装です。

## What this is

An industry-standard ETL pipeline for contact-center analytics, built end-to-end with
synthetic data so anyone can run it locally — no SaaS access, no audio models, no cloud
warehouse credentials required.

The point isn't the dataset. It's the **structure**:
Extract → Transform → Load → Analytics, with PII pseudonymization and data quality
checks deliberately placed *before* the load step. That ordering is the GRC observation
embedded in the design.

## Architecture

```
generate_data ─► extract ─► transform ─► load ─► analytics ─► dashboard
                            (PII mask    (SQLite)            (HTML + CSV)
                             + DQ checks)
```

See [`docs/architecture.md`](docs/architecture.md) for the rationale behind each layer
(in particular, **why Transform comes before Load**).

## Quick start

```bash
pip install -r requirements.txt
export BPO_PII_HMAC_KEY="$(openssl rand -hex 32)"  # required: PII pseudonymization key
make seed   # generate 200 synthetic cases → data/synthetic/cases.csv
make run    # E → T → L → A → dashboard
make test   # pytest on the transform layer
```

The pipeline refuses to run without `BPO_PII_HMAC_KEY` (see
[PII masking threat model](#pii-masking-threat-model)). Copy `.env.example`
for the expected format; never commit a real key.

Cleanup:

```bash
make clean
```

## Outputs

| Path | What it is |
|---|---|
| `output/dashboard.html` | KPI dashboard (plain HTML table — no plotly bundle) |
| `output/kpi_summary.csv` | Summary KPIs (total cases, AHT, escalation rate, SLA hit rate, category mix, weekly trend) |
| `output/quality_report.csv` | Column-level missing rate, type violations, range violations, masking pre/post distinct counts |
| `data/warehouse.db` | SQLite warehouse with masked records only |

## PII masking threat model

The masking in the transform layer is **pseudonymization, not anonymization**:

- `customer_name` and the local part of `customer_email` are replaced with a
  keyed **HMAC-SHA256** digest (truncated to 12 hex chars). The key comes from
  the `BPO_PII_HMAC_KEY` environment variable and is mandatory — an unkeyed
  hash of low-entropy identifiers is trivially reversible by dictionary attack.
- Under the same key, the same input always maps to the same output. This is
  deliberate: it keeps records **linkable** for repeat-contact analysis. The
  flip side is that if the key leaks, an attacker can mount a dictionary attack
  (hash candidate names/emails under the leaked key) to re-identify customers.
  Treat the key as a secret: rotate it if exposed, and never commit it.
- `customer_phone` keeps the **last 4 digits in plaintext** (`***-***-9876`).
  This is a residual linkage risk: combined with external data (another leaked
  dataset, a call log), last-4 digits can narrow candidates significantly.
- `customer_email` keeps the **domain in plaintext**, which reveals employer or
  provider information for small/corporate domains.

If your use case requires anonymization (no re-identification even by the key
holder), this design is insufficient — you would need suppression or
generalization instead of deterministic keyed hashing.

## Why these design choices

| Choice | Reason |
|---|---|
| Transform *before* Load | PII pseudonymization and quality checks must occur **before** persistence. Storing raw PII first and masking later means raw PII has already touched storage — a GRC failure. The ordering is the control. |
| SQLite warehouse | Lightweight, file-based, no service to manage. Anyone can run it. |
| Pandas + plain HTML output | No heavy SaaS, no plotly bundle, no model downloads. `make run` finishes in seconds. |
| YAML rules in `rules/classification.yaml` | Classification logic lives as configuration, not code. Easier to review for compliance. |
| `pytest` focused on `transform` | The transform step is the GRC-critical layer; it gets the tests. |

## Tech stack

- Python 3.11+
- `pandas` — DataFrame I/O and analytics
- `pyyaml` — rules configuration
- `pytest` — test runner
- `faker` — synthetic data generation
- `sqlite3` — standard library (no extra dependency)

## License

MIT.
