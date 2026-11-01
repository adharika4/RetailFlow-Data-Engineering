PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id TEXT PRIMARY KEY,
    is_identified INTEGER NOT NULL CHECK(is_identified IN (0,1))
);
CREATE TABLE IF NOT EXISTS dim_product (
    stock_code TEXT PRIMARY KEY,
    product_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_country (
    country TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    weekday TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_sales (
    source_row_id INTEGER PRIMARY KEY,
    invoice_no TEXT NOT NULL,
    invoice_timestamp TEXT NOT NULL,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_id TEXT NOT NULL REFERENCES dim_customer(customer_id),
    stock_code TEXT NOT NULL REFERENCES dim_product(stock_code),
    country TEXT NOT NULL REFERENCES dim_country(country),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_gbp REAL NOT NULL CHECK (unit_price_gbp > 0),
    revenue_pence INTEGER NOT NULL CHECK (revenue_pence > 0)
);
CREATE INDEX IF NOT EXISTS idx_sales_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_sales_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_stock ON fact_sales(stock_code);
CREATE INDEX IF NOT EXISTS idx_sales_country ON fact_sales(country);
CREATE INDEX IF NOT EXISTS idx_sales_invoice ON fact_sales(invoice_no);
