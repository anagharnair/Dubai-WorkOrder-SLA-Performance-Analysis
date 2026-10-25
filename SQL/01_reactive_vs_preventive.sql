-- 01_reactive_vs_preventive.sql
-- Question: what share of work orders are reactive vs preventive?

SELECT
    job_type,
    COUNT(*) AS work_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total
FROM work_orders
GROUP BY job_type
ORDER BY work_orders DESC;