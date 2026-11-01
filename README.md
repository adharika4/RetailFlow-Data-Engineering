# RetailFlow — Real Retail ETL & SQL Data Warehouse

**An end-to-end data engineering portfolio project on authentic UCI Online Retail transactions**. Builds a Python + Pandas ETL pipeline, a SQLite relational **star-schema warehouse**, automated data quality tests, SQL analytics, and a local HTML dashboard.

> **Important size distinction:** The ZIP contains **48 original (unaltered) rows** of the UCI dataset to work completely offline. The full public dataset contains **541,909 transaction lines** and is downloaded separately. When the original UCI workbook is present, the code automatically processes that entire dataset. Results bundled in `reports/` were generated using the **48-row genuine sample**, not the full dataset. This is not Amazon data and is not a production-scale distributed system.

## Dataset and attribution

- **Dataset:** Online Retail (UCI Machine Learning Repository, dataset ID 352)
- **Citation:** Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5BW33>
- **Source:** <https://archive.ics.uci.edu/dataset/352/online+retail>
- **License:** Creative Commons Attribution 4.0 (CC BY 4.0), <https://creativecommons.org/licenses/by/4.0/>
- **Contents:** Historical transactions from an anonymous UK-based online retailer between **2010-12-01 and 2011-12-09**. Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country.
- **Bundled sample provenance:** First 48 transaction lines copied from a publicly shared raw extract of the UCI workbook: <https://raw.githubusercontent.com/rkharwar-nv/dataset_analysis/main/samples/uci-online-retail-sample.csv>. This is *real historical retail data*, not artificially generated transactions. The tiny sample only includes transactions on 2010-12-01 and should not be used for month-to-month conclusions.

## Architecture

```text
UCI Online Retail XLSX  (541,909 actual lines, full mode)
           OR
Small authentic CSV sample (48 lines, works offline)
                          │
                          ▼
                    Python / Pandas
         Extract, validate, normalize, transform
           - parse InvoiceDate, customer IDs
           - exclude cancelled InvoiceNos starting C
           - exclude invalid qty / price / dates
           - separate POST postage from merchandise sales
           - preserve anonymous sales as UNKNOWN customer
           - calculate line-level sales (GBP pence)
                          │
                          ▼
                 SQLite data warehouse
                dim_date     dim_product
                dim_country  dim_customer
                          │
                       fact_sales
                   (1 original sales line)
                          │
                          ▼
                 SQL analytic reports
         Monthly sales, products, countries, RFM,
         repeat buyers, top customers
                          │
                          ▼
         CSV reports + PNG graphs + HTML dashboard
```

### Modeling choices

**Fact grain:** one *original merchandise transaction line*; one invoice can have many lines. `source_row_id` preserves the original row position as a reproducible key.

**Primary keys / foreign keys:** `fact_sales` stores invoice number, quantity, original price, line revenue, and foreign keys to customer/product/country/date dimensions. Indexed columns improve joins.

**Unknown customer IDs:** Genuine UCI data has missing CustomerID values; these are retained with customer key `UNKNOWN`. SQL customer-level analyses exclude `UNKNOWN` rather than presenting all anonymous orders as one person.

**Cancellation handling:** Invoice numbers starting `C` represent cancellations and are excluded from gross positive merchandise revenue. Negative quantities and invalid/zero prices are also filtered. This is **not net revenue after returns**. A complete refunds model would retain and reconcile cancellations separately. `POST` postage lines are excluded from the merchandise metric. Other adjustment codes are not comprehensively classified.

**Money:** `revenue_pence` stores monetary values as integer pennies, rounding every line to a penny. Original price is retained as a floating point GBP field; financial reconciliation with invoices at finer precision may vary slightly.

**Refresh semantics:** rerunning ETL rebuilds the warehouse deterministically. It is a **full refresh**, not incremental ingestion / CDC / streaming, and does not use Spark or AWS.

## Quick start (Windows, Mac, Linux)

Requires **Python 3.10+**, internet only for full dataset download.

### 1. Open terminal in this folder

```bash
python -m pip install -r requirements.txt
```

### 2A. Run instantly on included **real 48-row sample** (no download)

```bash
python src/run_pipeline.py --sample
python -m unittest discover -s tests -v
```

### 2B. Run on the **complete real 541,909-row UCI dataset**

```bash
python src/download_data.py
python src/run_pipeline.py
python -m unittest discover -s tests -v
```

You can also use `python src/run_pipeline.py --download` for a one-step download-and-run.

**Manual download fallback:** Open the [official UCI dataset page](https://archive.ics.uci.edu/dataset/352/online+retail), download and unzip the provided archive, and place its file as exactly `data/raw/Online Retail.xlsx`. `python src/run_pipeline.py` then detects it automatically. The full workbook is deliberately not inside this ZIP, so its size stays manageable.

### 3. View the results

- Open **`reports/dashboard.html`** in any browser (static report, no server required).
- View `reports/monthly_revenue.png` and `reports/country_revenue.png`.
- Query the actual warehouse: `data/retail_warehouse.db` with **DB Browser for SQLite** or Python `sqlite3`.
- Explore the six queries in `sql/analytics.sql` (JOIN, GROUP BY, HAVING, COUNT(DISTINCT), CTE).
- Check `reports/pipeline_metrics.json` for filtered raw-row counts and **`mode` = FULL DATASET or SMALL REAL SAMPLE**.

## Folder structure

```text
RetailFlow_Real_Retail_ETL/
├── data/
│   ├── raw/online_retail_sample.csv    # bundled genuine UCI source extract (48 lines)
│   ├── raw/Online Retail.xlsx          # optional full source downloaded by script
│   └── retail_warehouse.db             # generated SQLite relational star schema
├── sql/schema.sql                      # DDL and indexes
├── sql/analytics.sql                   # 6 reporting queries
├── src/download_data.py               # official UCI download / extraction
├── src/etl.py                         # cleaning, dimensional modeling and load
├── src/build_reports.py               # SQL reports, graphs and HTML dashboard
├── src/run_pipeline.py                # one-command orchestrator
├── tests/test_pipeline.py             # automated tests including cancellations
├── reports/                           # generated outputs (sample in this ZIP)
├── requirements.txt
└── README.md
```

## Verified sample run

Sample-specific numbers, **NOT full-dataset metrics**:

- Input: **48 genuine source lines**
- Excluded: **1 POST postage line**
- Loaded: **47 positive merchandise lines**, **8 distinct invoices**, **4 known customers**
- Sample positive merchandise revenue: **£1,541.91**
- `unittest`: see test output after running. Tests include cancellations, missing dates, anonymous customers, integrity, idempotence and reconciliation.

Your local full run produces much larger results in the same JSON reports. Do **not** describe the bundled 47-line run as a 541k-line warehouse in an interview.

## Six useful analytics questions

1. Monthly revenue, units and `COUNT(DISTINCT invoice_no)` purchases.
2. Which actual products earn the most revenue?
3. What are the top countries by merchandise revenue?
4. Who are the highest-spending identified customers?
5. Who are repeat buyers (2+ **invoices**, not 2+ line items)?
6. How do recency, frequency and monetary value (RFM) differ by customer?

## How to practice and make it your own

1. Run the full UCI dataset, check `pipeline_metrics.json`, and write down **actual** counts.
2. Read `src/etl.py` and explain one data-cleaning rule and why it exists.
3. Open `sql/analytics.sql` and execute the `JOIN` and repeat-buyer `HAVING` query yourself.
4. Edit one report, such as top products in France; check your output.
5. Explain star schema vs normalized transactional schema; why `fact_sales` is line-level.

## Resume guidance (after you actually run the complete dataset)

**RetailFlow — E-Commerce ETL Pipeline & Sales Data Warehouse | Python, SQL, Pandas, SQLite**

- Built a Python/Pandas ETL pipeline on real UCI online retail transactions to validate and transform sales records into a SQLite star-schema warehouse with date, customer, product, and geography dimensions.
- Implemented foreign-key integrity checks, idempotent full refreshes, and SQL reports for monthly revenue, top products, geographic performance, and customer RFM analytics.

**Only add a row-count metric once you have run the full dataset and seen your actual post-filter counts.** This is a learning project; review the implementation before claiming personal engineering ownership.
