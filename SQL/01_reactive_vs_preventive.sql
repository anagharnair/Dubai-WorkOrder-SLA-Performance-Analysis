-- 02_sla_performance_by_priority.sql
-- Question: how fast do we respond and resolve, and how often do we breach SLA?

SELECT
    priority,
    COUNT(*) AS closed_jobs,
    ROUND(AVG(response_hrs), 1) AS avg_response_hrs,
    ROUND(AVG(resolution_hrs), 1) AS avg_resolution_hrs,
    ROUND(100.0 * AVG(response_sla_met), 1) AS pct_response_sla_met,
    ROUND(100.0 * AVG(resolution_sla_met), 1) AS pct_resolution_sla_met,
    ROUND(100.0 - 100.0 * AVG(resolution_sla_met), 1) AS resolution_breach_rate_pct
FROM work_orders
WHERE status = 'Closed'
GROUP BY priority
ORDER BY priority;