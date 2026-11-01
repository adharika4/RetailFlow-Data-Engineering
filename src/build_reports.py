"""Execute SQL analytics queries, generate CSV reports and a lightweight static dashboard."""
import json
import sqlite3
from pathlib import Path
from html import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DB = ROOT / "data" / "retail_warehouse.db"
REPORT_NAMES = ["monthly_revenue", "top_products", "country_revenue", "top_customers", "repeat_customers", "rfm_customers"]


def build():
    if not DB.exists():
        raise FileNotFoundError("Warehouse not found. First run: python src/etl.py")
    REPORTS.mkdir(parents=True, exist_ok=True)
    sql = (ROOT / "sql" / "analytics.sql").read_text(encoding="utf-8")
    statements = [q.strip() for q in sql.split(";") if q.strip()]
    assert len(statements) == len(REPORT_NAMES), "Number of SQL statements changed; update REPORT_NAMES"
    with sqlite3.connect(DB) as con:
        results = {}
        for name, statement in zip(REPORT_NAMES, statements):
            result = pd.read_sql_query(statement, con)
            result.to_csv(REPORTS / f"{name}.csv", index=False)
            results[name] = result
        n_sales, n_orders, n_cust, n_products, revenue_pence = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT invoice_no), COUNT(DISTINCT NULLIF(customer_id,'UNKNOWN'))," 
            " COUNT(DISTINCT stock_code), SUM(revenue_pence) FROM fact_sales").fetchone()
    pipeline = json.loads((REPORTS / "pipeline_metrics.json").read_text(encoding="utf-8")) if (REPORTS / "pipeline_metrics.json").exists() else {}
    mode = pipeline.get("mode", "unknown source")
    suffix = " (48-row genuine UCI sample)" if mode == "SMALL REAL SAMPLE" else " (full UCI dataset)"
    monthly = results["monthly_revenue"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(monthly["month"].astype(str), monthly["revenue_gbp"])
    ax.set(ylabel="Merchandise sales (£)", title="Monthly gross merchandise revenue" + suffix)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(REPORTS / "monthly_revenue.png", dpi=155)
    plt.close(fig)

    countries = results["country_revenue"].head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(countries["country"], countries["revenue_gbp"])
    ax.set(xlabel="Merchandise sales (£)", title="Top 10 countries by revenue" + suffix)
    fig.tight_layout()
    fig.savefig(REPORTS / "country_revenue.png", dpi=155)
    plt.close(fig)

    stats = {"sale_lines": n_sales, "invoices": n_orders, "identified_customers": n_cust,
             "products": n_products, "revenue_gbp": f"{revenue_pence/100:,.2f}"}
    (REPORTS / "dashboard_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>RetailFlow | Data Warehouse Report</title><style>
body{{font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#192638;max-width:1100px;margin:0 auto;padding:30px}}
header{{background:#172e55;color:white;padding:34px;border-radius:16px}}header p{{color:#d6e2f8}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:22px 0}}
.kpis article,section{{background:white;border-radius:13px;padding:22px;box-shadow:0 2px 8px #1122440f}}
.kpis strong{{font-size:27px;display:block;color:#173f88;margin-top:7px}}
.kpis small{{color:#5f6c7c}}.charts{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
img{{width:100%;max-height:360px;object-fit:contain}}.notice{{padding:14px 18px;background:#fff3db;border-radius:8px;margin:18px 0}}
@media(max-width:750px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body><header><h1>RetailFlow</h1><p>UCI Online Retail · ETL · SQLite star schema · SQL analytics</p></header>
<div class="notice">Input mode: <b>{escape(mode)}</b>. Currency is GBP. Positive merchandise sales only; cancellations/returns and postage excluded. The bundled sample covers only the first transactions, so use the full file for meaningful trends.</div>
<div class="kpis"><article><small>Valid merchandise lines</small><strong>{n_sales:,}</strong></article><article><small>Invoices</small><strong>{n_orders:,}</strong></article><article><small>Known customers</small><strong>{n_cust:,}</strong></article><article><small>Gross merchandise revenue</small><strong>£{stats['revenue_gbp']}</strong></article></div>
<div class="charts"><section><h2>Monthly revenue</h2><img src="monthly_revenue.png" alt="Monthly revenue chart"></section><section><h2>Geographical breakdown</h2><img src="country_revenue.png" alt="Revenue by country chart"></section></div>
<section><h2>Methods</h2><p>Extracted real transaction records; filtered cancelled invoices, invalid quantities/prices, and postage; retained unknown customer IDs without inventing identities; loaded fact_sales and four dimensions into SQLite; produced SQL aggregates and an RFM report.</p>
<p>Data source: Chen, D. (2015), UCI Online Retail, <a href="https://doi.org/10.24432/C5BW33">DOI: 10.24432/C5BW33</a> (CC BY 4.0).</p></section></body></html>'''
    (REPORTS / "dashboard.html").write_text(html, encoding="utf-8")
    print("Generated:", ", ".join(f"reports/{n}.csv" for n in REPORT_NAMES))
    print("Open reports/dashboard.html to see the dashboard")
    print("Warehouse metrics:", stats)

if __name__ == "__main__":
    build()
