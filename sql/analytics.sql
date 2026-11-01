-- All revenue amounts are GBP unless otherwise stated.
-- Revenue excludes cancellations, nonpositive prices/quantities, and POST postage lines.

-- 1) Monthly merchandise revenue & distinct invoices
SELECT d.year || '-' || printf('%02d', d.month) AS month,
       ROUND(SUM(s.revenue_pence)/100.0, 2) AS revenue_gbp,
       COUNT(DISTINCT s.invoice_no) AS orders,
       SUM(s.quantity) AS units_sold
FROM fact_sales s JOIN dim_date d USING(date_key)
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- 2) Top-selling merchandise
SELECT p.stock_code, p.product_name, SUM(s.quantity) AS units_sold,
       ROUND(SUM(s.revenue_pence)/100.0, 2) AS revenue_gbp
FROM fact_sales s JOIN dim_product p USING(stock_code)
GROUP BY p.stock_code, p.product_name
ORDER BY revenue_gbp DESC LIMIT 10;

-- 3) Revenue by country
SELECT s.country, COUNT(DISTINCT s.invoice_no) AS invoices,
       ROUND(SUM(s.revenue_pence)/100.0, 2) AS revenue_gbp
FROM fact_sales s GROUP BY s.country ORDER BY revenue_gbp DESC;

-- 4) Top known customers
SELECT s.customer_id, COUNT(DISTINCT s.invoice_no) AS orders,
       ROUND(SUM(s.revenue_pence)/100.0, 2) AS lifetime_revenue_gbp
FROM fact_sales s WHERE s.customer_id != 'UNKNOWN'
GROUP BY s.customer_id ORDER BY lifetime_revenue_gbp DESC LIMIT 10;

-- 5) Repeat buyers by customer: distinct invoice count avoids counting item rows as orders
SELECT s.customer_id, COUNT(DISTINCT s.invoice_no) AS order_count,
       ROUND(SUM(s.revenue_pence)/100.0, 2) AS revenue_gbp
FROM fact_sales s WHERE s.customer_id != 'UNKNOWN'
GROUP BY s.customer_id HAVING COUNT(DISTINCT s.invoice_no) >= 2
ORDER BY order_count DESC LIMIT 25;

-- 6) RFM metrics for identified customers
WITH rfm AS (
    SELECT customer_id,
           CAST(julianday((SELECT MAX(full_date) FROM dim_date)) -
                julianday(MAX(substr(invoice_timestamp, 1, 10))) AS INT) AS recency_days,
           COUNT(DISTINCT invoice_no) AS frequency_orders,
           ROUND(SUM(revenue_pence)/100.0, 2) AS monetary_gbp
    FROM fact_sales WHERE customer_id != 'UNKNOWN' GROUP BY customer_id
)
SELECT * FROM rfm ORDER BY monetary_gbp DESC LIMIT 25;
