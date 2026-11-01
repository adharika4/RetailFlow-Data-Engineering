# RetailFlow — Retail ETL & Sales Data Warehouse

An end-to-end data engineering project that transforms real-world e-commerce transactions into a relational SQL warehouse and generates sales analytics reports.

**Tech stack:** Python, Pandas, SQLite, SQL, Matplotlib, HTML

## Overview

RetailFlow processes the [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail), which contains 541,909 transaction lines from a UK-based online retailer (December 2010–December 2011). The pipeline validates records, builds a star-schema data warehouse, and produces SQL-based reporting and an HTML dashboard.

### Full-dataset results

| Metric | Result |
| --- | ---: |
| Source transaction lines | 541,909 |
| Valid merchandise sales lines | 528,974 |
| Distinct invoices | 19,884 |
| Identified customers | 4,338 |
| Distinct products | 3,920 |
| Positive merchandise revenue | £10,588,582.66 |

These results come from a completed full-dataset run. Revenue represents **positive merchandise sales**, not net sales after refunds; cancellation invoices and postage lines are excluded.

## Interactive dashboard

The generated [sales dashboard](reports/dashboard.html) uses a responsive, dark interface and works locally without a web server or external JavaScript libraries.

- KPI cards for positive line revenue, invoices, validated sales lines, and identified customers
- Interactive monthly chart: switch between revenue, invoice counts, and units sold
- Top markets ranked by revenue, with percentage-share bars
- Searchable top-revenue stock-code table and downloadable CSV reports
- Full-dataset results embedded in the checked-in dashboard; rerunning the pipeline refreshes the dashboard from SQL reports

After running the pipeline, open `reports/dashboard.html` in your browser. GitHub displays HTML files as code, so open the downloaded file locally to interact with it.

## Data pipeline

```text
UCI Online Retail (.xlsx)
           |
           v
Python / Pandas ETL
  - validate dates, quantities and prices
  - exclude cancellations and postage
  - standardize customer/product fields
  - calculate line-level revenue
           |
           v
SQLite star-schema warehouse
  dim_date     dim_customer
  dim_product  dim_country
           \   |   /
            fact_sales
               |
               v
SQL analytics + reports
  revenue, products, countries,
  repeat customers, RFM segments
               |
               v
CSV reports + charts + HTML dashboard
```

### Data model

- **Fact table:** `fact_sales`, with one row per valid source merchandise line and foreign keys to the dimensions.
- **Dimension tables:** `dim_date`, `dim_product`, `dim_customer`, `dim_country`.
- **Data quality:** checks for valid transaction fields, referential integrity, revenue reconciliation and repeatable full-refresh loads.
- **Reporting:** monthly revenue, product and country performance, customer rankings, repeat purchases, and recency-frequency-monetary (RFM) analysis.

The pipeline uses batch full refreshes; it does not implement streaming, distributed processing, or incremental change-data capture.

## Project structure

```text
├── data/raw/online_retail_sample.csv  # small authentic sample for offline testing
├── src/
│   ├── download_data.py
│   ├── etl.py
│   ├── build_reports.py
│   └── run_pipeline.py
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── tests/test_pipeline.py
├── reports/                        # full-data reports and dashboard
├── requirements.txt
└── README.md
```

The full Excel dataset and generated SQLite database are intentionally excluded from Git. They are downloaded or built locally.

## Run locally

Requires Python 3.10+.

```bash
python -m pip install -r requirements.txt
python src/download_data.py
python src/run_pipeline.py
python -m unittest discover -s tests -v
```

Open `reports/dashboard.html` in a browser to view the generated analytics.

For a quick offline run using the included 48-row genuine transaction sample:

```bash
python src/run_pipeline.py --sample
```

The sample run regenerates `reports/` locally with sample-only results. Use the full dataset to reproduce the metrics above. The SQL queries are in `sql/analytics.sql`.

## Dataset attribution

Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33). Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

The offline sample consists of the first 48 original rows from a [publicly shared extract](https://github.com/rkharwar-nv/dataset_analysis/blob/main/samples/uci-online-retail-sample.csv) of that dataset.
