-- 03_sla_breach_by_trade.sql
-- Question: which trades miss their resolution SLA most often?

SELECT
    trade,
    COUNT(*) AS closed_jobs,
    ROUND(AVG(response_hrs), 1) AS avg_response_hrs,
    ROUND(AVG(resolution_hrs), 1) AS avg_resolution_hrs,
    SUM(CASE WHEN resolution_sla_met = 0 THEN 1 ELSE 0 END) AS breached_jobs,
    ROUND(100.0 - 100.0 * AVG(resolution_sla_met), 1) AS resolution_breach_rate_pct
FROM work_orders
WHERE status = 'Closed'
GROUP BY trade
ORDER BY resolution_breach_rate_pct DESC;