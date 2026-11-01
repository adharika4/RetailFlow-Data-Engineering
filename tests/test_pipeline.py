"""Tests cover actual warehouse loading as well as synthetic edge-case test fixtures.
The portfolio data itself is real; tiny artificial rows below are only unit-test inputs.
"""
import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from etl import SAMPLE, load_source, transform, load_warehouse, run


class TestRealSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_source(SAMPLE)
        cls.clean, cls.stats = transform(cls.raw)
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp.name) / "test.db"
        load_warehouse(cls.clean, cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_sample_is_genuine_uci_data_shape(self):
        self.assertEqual(len(self.raw), 48)
        self.assertEqual(self.raw.iloc[0]["InvoiceNo"], "536365")
        self.assertEqual(self.raw.iloc[0]["StockCode"], "85123A")

    def test_filter_postage(self):
        self.assertEqual(self.stats["excluded_postage_lines"], 1)
        self.assertEqual(self.stats["valid_sale_lines"], 47)
        self.assertNotIn("POST", self.clean["StockCode"].values)

    def test_positive_revenue_and_unique_source_ids(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            cnt, unique_cnt, invalid = con.execute(
                "SELECT COUNT(*), COUNT(DISTINCT source_row_id),"
                " SUM(CASE WHEN revenue_pence <= 0 OR quantity <= 0 THEN 1 ELSE 0 END) FROM fact_sales"
            ).fetchone()
        self.assertEqual(cnt, unique_cnt)
        self.assertEqual(invalid, 0)

    def test_foreign_keys(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_source_and_warehouse_revenue_reconcile(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            amount = con.execute("SELECT SUM(revenue_pence) FROM fact_sales").fetchone()[0]
        self.assertEqual(amount, int(self.clean["revenue_pence"].sum()))
        self.assertEqual(amount, 154191)

    def test_rerun_is_idempotent_full_refresh(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            before = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
        load_warehouse(self.clean, self.db_path)
        with closing(sqlite3.connect(self.db_path)) as con:
            after = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
        self.assertEqual(before, after)

    def test_invoice_distinct_from_item_lines(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            invoices, lines = con.execute(
                "SELECT COUNT(DISTINCT invoice_no), COUNT(*) FROM fact_sales"
            ).fetchone()
        self.assertEqual(invoices, 8)
        self.assertGreater(lines, invoices)


class TestCleaningEdgeCases(unittest.TestCase):
    def test_cancellations_guests_and_negative_quantities(self):
        source = load_source(SAMPLE).head(1)
        cancelled = source.copy(); cancelled.loc[:, "source_row_id"] = 49; cancelled.loc[:, "InvoiceNo"] = "C536365"
        bad_qty = source.copy(); bad_qty.loc[:, "source_row_id"] = 50; bad_qty.loc[:, "Quantity"] = -3
        guest = source.copy(); guest.loc[:, "source_row_id"] = 51; guest.loc[:, "CustomerID"] = float("nan")
        rows = pd.concat([source, cancelled, bad_qty, guest], ignore_index=True)
        cleaned, metrics = transform(rows)
        self.assertEqual(metrics["excluded_cancellations"], 1)
        self.assertEqual(metrics["excluded_nonpositive_quantity"], 1)
        self.assertEqual(metrics["valid_sale_lines"], 2)
        self.assertEqual(metrics["unidentified_customer_lines"], 1)
        self.assertIn("UNKNOWN", cleaned["customer_id"].tolist())

    def test_reject_missing_dates(self):
        source = load_source(SAMPLE).head(1)
        source.loc[:, "InvoiceDate"] = "bad timestamp"
        cleaned, metrics = transform(source)
        self.assertTrue(cleaned.empty)
        self.assertEqual(metrics["excluded_invalid_dates"], 1)


if __name__ == "__main__":
    unittest.main()
