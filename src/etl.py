"""Deterministic full-refresh ETL for the UCI Online Retail dataset.

Model grain: one *source transaction line*, represented by its original 1-based row number.
Sales metrics reflect positive, non-cancelled merchandise lines, NOT net revenue after returns.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "raw" / "online_retail_sample.csv"
FULL = ROOT / "data" / "raw" / "Online Retail.xlsx"
DATABASE = ROOT / "data" / "retail_warehouse.db"
REPORTS = ROOT / "reports"
REQUIRED = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]


def load_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        data = pd.read_excel(path, engine="openpyxl", dtype={"InvoiceNo": str, "StockCode": str})
    else:
        data = pd.read_csv(path, dtype={"InvoiceNo": str, "StockCode": str}, low_memory=False)
    missing = set(REQUIRED) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    data = data[REQUIRED].copy()
    data.insert(0, "source_row_id", range(1, len(data) + 1))
    return data


def transform(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    data = raw.copy()
    count = {"raw_rows": len(data)}

    data["InvoiceNo"] = data["InvoiceNo"].astype("string").str.strip().fillna("")
    data["StockCode"] = data["StockCode"].astype("string").str.strip().fillna("")
    data["Description"] = data["Description"].astype("string").fillna("Unknown product").str.strip()
    data.loc[data["Description"].eq(""), "Description"] = "Unknown product"
    data["Country"] = data["Country"].astype("string").fillna("Unknown country").str.strip()
    data.loc[data["Country"].eq(""), "Country"] = "Unknown country"
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["UnitPrice"] = pd.to_numeric(data["UnitPrice"], errors="coerce")
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")

    def apply_filter(key, mask):
        nonlocal data
        count[key] = int((~mask).sum())
        data = data.loc[mask].copy()

    apply_filter("excluded_cancellations", ~data["InvoiceNo"].str.upper().str.startswith("C"))
    apply_filter("excluded_invalid_identifiers", data["InvoiceNo"].ne("") & data["StockCode"].ne(""))
    apply_filter("excluded_invalid_dates", data["InvoiceDate"].notna())
    apply_filter("excluded_nonpositive_quantity", data["Quantity"].gt(0) & data["Quantity"].mod(1).eq(0))
    apply_filter("excluded_nonpositive_price", data["UnitPrice"].gt(0))
    # A distinct POST row describes shipping fees, not a merchandise product.
    apply_filter("excluded_postage_lines", data["StockCode"].str.upper().ne("POST"))

    ids = pd.to_numeric(data["CustomerID"], errors="coerce")
    data["customer_id"] = ids.astype("Int64").astype("string").fillna("UNKNOWN")
    data["timestamp"] = data["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")
    data["date_key"] = data["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    data["Quantity"] = data["Quantity"].astype(int)

    # Round each merchandise line to the nearest penny (GBP), not a floating-point sum.
    data["revenue_pence"] = [
        int((Decimal(str(p)) * Decimal(int(q)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        for p, q in zip(data["UnitPrice"], data["Quantity"])
    ]
    apply_filter("excluded_zero_rounded_revenue", data["revenue_pence"].gt(0))
    count["valid_sale_lines"] = len(data)
    count["identified_customer_lines"] = int(data["customer_id"].ne("UNKNOWN").sum())
    count["unidentified_customer_lines"] = int(data["customer_id"].eq("UNKNOWN").sum())
    count["distinct_invoices"] = int(data["InvoiceNo"].nunique())
    count["revenue_gbp"] = f"{sum(data['revenue_pence']) / 100:.2f}"
    assert count["raw_rows"] == count["valid_sale_lines"] + sum(v for k,v in count.items() if k.startswith("excluded_"))
    return data, count


def make_dimensions(df):
    customers = df[["customer_id"]].drop_duplicates().rename(columns={"customer_id": "customer_id"})
    customers["is_identified"] = (customers["customer_id"] != "UNKNOWN").astype(int)

    # Product descriptions can vary for one StockCode; choose the most frequent non-empty name.
    product_counts = (df.groupby(["StockCode", "Description"], dropna=False)
                      .size().reset_index(name="frequency")
                      .sort_values(["StockCode", "frequency", "Description"], ascending=[True, False, True]))
    products = (product_counts.drop_duplicates("StockCode")
                [["StockCode", "Description"]].rename(columns={"StockCode":"stock_code", "Description":"product_name"}))
    countries = df[["Country"]].drop_duplicates().rename(columns={"Country":"country"})

    day = df[["date_key", "InvoiceDate"]].drop_duplicates("date_key")
    date = day["InvoiceDate"].dt
    dates = pd.DataFrame({
        "date_key": day["date_key"], "full_date": date.strftime("%Y-%m-%d"),
        "day": date.day, "month": date.month, "year": date.year,
        "quarter": date.quarter, "weekday": date.day_name(),
    })
    return customers, products, countries, dates


def load_warehouse(df: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(".building.db")
    tmp.unlink(missing_ok=True)
    customers, products, countries, dates = make_dimensions(df)
    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        customers.to_sql("dim_customer", con, if_exists="append", index=False, chunksize=10000)
        products.to_sql("dim_product", con, if_exists="append", index=False, chunksize=10000)
        countries.to_sql("dim_country", con, if_exists="append", index=False, chunksize=10000)
        dates.to_sql("dim_date", con, if_exists="append", index=False, chunksize=10000)
        fact = df[["source_row_id", "InvoiceNo", "timestamp", "date_key", "customer_id",
                   "StockCode", "Country", "Quantity", "UnitPrice", "revenue_pence"]].copy()
        fact.columns = ["source_row_id", "invoice_no", "invoice_timestamp", "date_key", "customer_id",
                        "stock_code", "country", "quantity", "unit_price_gbp", "revenue_pence"]
        fact.to_sql("fact_sales", con, if_exists="append", index=False, chunksize=10000)
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise RuntimeError(f"Foreign key violations: {fk[:5]}")
        total = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
        if total != len(df):
            raise RuntimeError(f"Loaded {total} rows, expected {len(df)}")
        con.commit()
    finally:
        con.close()
    os.replace(tmp, destination)  # deterministic full refresh; rerunning does not duplicate rows


def run(path: Path, database: Path = DATABASE, metrics_path: Path | None = None):
    raw = load_source(path)
    sales, metrics = transform(raw)
    if sales.empty:
        raise ValueError("No valid merchandise sale lines remain after cleaning")
    load_warehouse(sales, database)
    metrics.update({"source_file": path.name, "data_source": "UCI Online Retail (Chen, 2015)",
                    "mode": "FULL DATASET" if path.suffix.lower() == ".xlsx" else "SMALL REAL SAMPLE"})
    if metrics_path:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=FULL if FULL.exists() else SAMPLE,
                    help="CSV or UCI Online Retail XLSX; defaults to full file if downloaded")
    ap.add_argument("--database", type=Path, default=DATABASE)
    args = ap.parse_args()
    run(args.source, args.database, REPORTS / "pipeline_metrics.json")

if __name__ == "__main__":
    main()
