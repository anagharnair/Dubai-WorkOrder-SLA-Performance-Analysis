-- 04_backlog_ageing.sql
-- Question: how old are our open jobs, and how many are high priority?
-- Snapshot date = 15 Jan 2026 (the date the dataset was "extracted")

SELECT
    CASE
        WHEN age_days <= 7   THEN '1) 0-7 days'
        WHEN age_days <= 30  THEN '2) 8-30 days'
        WHEN age_days <= 90  THEN '3) 31-90 days'
        WHEN age_days <= 180 THEN '4) 91-180 days'
        ELSE '5) 180+ days'
    END AS age_bucket,
    COUNT(*) AS open_jobs,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_backlog,
    SUM(CASE WHEN priority IN ('P1 - Critical', 'P2 - High') THEN 1 ELSE 0 END) AS high_priority_jobs
FROM (
    SELECT
        priority,
        CAST(julianday('2026-01-15') - julianday(created_at) AS INTEGER) AS age_days
    FROM work_orders
    WHERE status = 'Open'
)
GROUP BY age_bucket
ORDER BY age_bucket;