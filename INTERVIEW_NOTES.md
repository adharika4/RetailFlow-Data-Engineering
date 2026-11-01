# RetailFlow: 10-minute interview preparation

These notes explain the delivered code; don't present this as work you personally implemented until you've run it, read it, and can discuss changes you made.

## 1. What problem does it solve?
It turns raw historical retail transaction lines into a queryable analytical data warehouse for merchandise revenue, product demand, geography, and repeat-customer analysis.

## 2. ETL = Extract, Transform, Load
- Extract Excel (full dataset) or CSV (small genuine sample).
- Transform: normalize columns; parse timestamps; exclude cancelled invoices, nonpositive quantities/prices, and postage lines; handle missing customer IDs; compute line revenue in pennies.
- Load: write fact and dimension tables into SQLite using a deterministic full refresh.

## 3. Why a star schema?
One large fact table (`fact_sales`) stores quantities and revenue. Four smaller dimensions (`dim_product`, `dim_customer`, `dim_country`, `dim_date`) store searchable attributes. This allows simple SQL JOINs and grouped analytics.

## 4. What is the fact table's grain?
One cleaned *source item row*. One `InvoiceNo` can occur on multiple rows. For an order count, use `COUNT(DISTINCT invoice_no)` instead of `COUNT(*)`.

## 5. Is this a Big Data / distributed Spark project?
No. It is a local Python/Pandas + SQLite ETL and dimensional-modeling project. The full source has ~542k rows, which is useful for practice but not a distributed processing workload. Don't claim Spark, Hadoop, AWS Glue or streaming.

## 6. What about cancellations and returns?
`InvoiceNo` beginning `C` is a cancellation according to UCI. Cancellations and negative quantity lines are excluded from the **positive merchandise revenue** metric; this is NOT full net revenue adjusted for returns. A future enhancement would retain cancellation facts and link to original invoices.

## 7. Why preserve missing CustomerID?
Some genuine sales have missing customer IDs. They remain in revenue data with `UNKNOWN`, but are excluded from unique-identified-customer analytics so they're not mistaken for one person.

## 8. What does idempotent mean here?
A second ETL run with identical input produces the same warehouse and counts. This project achieves it with a complete rebuild and atomic database file replacement, not incremental upserts.

## 9. SQL concepts to know
- INNER JOIN: attach dimension attributes to fact sales.
- GROUP BY: monthly or country-level aggregation.
- HAVING: filter customer groups with at least 2 distinct invoices.
- CTE: break down RFM recency/frequency/monetary calculations.
- Foreign keys: ensure fact entries reference existing dimension rows.
- Indexes: accelerate searches and joins, but add insert/update overhead.

## 10. Important honest sample/full distinction
The ZIP has 48 genuine transactions for offline reproducibility and included sample reports. The full UCI dataset has 541,909 source rows, but the full dataset was **not downloaded or run in the creation environment**. You can run the full dataset locally with `python src/download_data.py` and `python src/run_pipeline.py`. Add your *actual* processed row count to your resume only after that full run.

## Suggested practical enhancements
- Build a distinct cancellations/returns fact table and calculate net revenue.
- Move warehouse from SQLite to MySQL/Postgres.
- Add incremental ingestion + late-arrival handling, with duplicate detection.
- Compare query time with and without an index.
- Build a top-country interactive filter on the dashboard.
