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
    dashboard_data = {
        "mode": mode,
        "stats": stats,
        "monthly": json.loads(results["monthly_revenue"].to_json(orient="records")),
        "countries": json.loads(results["country_revenue"].to_json(orient="records")),
        "products": json.loads(results["top_products"].to_json(orient="records")),
    }
    template = (ROOT / "src" / "dashboard_template.html").read_text(encoding="utf-8")
    embedded_json = json.dumps(dashboard_data, ensure_ascii=False).replace("<", "\\u003c")
    html = template.replace("__DASHBOARD_DATA__", embedded_json)
    (REPORTS / "dashboard.html").write_text(html, encoding="utf-8")
    print("Generated:", ", ".join(f"reports/{n}.csv" for n in REPORT_NAMES))
    print("Open reports/dashboard.html to see the dashboard")
    print("Warehouse metrics:", stats)

if __name__ == "__main__":
    build()
