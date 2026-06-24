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
make seed   # generate 200 synthetic cases → data/synthetic/cases.csv
make run    # E → T → L → A → dashboard
make test   # pytest on the transform layer
```

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
