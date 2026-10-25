-- 05_repeat_failures_by_asset.sql
-- Question: which assets keep breaking, and what do they cost us?
-- "Repeat" = a reactive job on the same asset within 30 days of the previous one.

WITH reactive AS (
    SELECT
        asset_id,
        building,
        trade,
        reopened,
        cost_aed,
        julianday(created_at) - julianday(
            LAG(created_at) OVER (PARTITION BY asset_id ORDER BY created_at)
        ) AS days_since_prev_job
    FROM work_orders
    WHERE job_type = 'Reactive'
)
SELECT
    asset_id,
    building,
    trade,
    COUNT(*) AS reactive_jobs,
    SUM(CASE WHEN days_since_prev_job <= 30 THEN 1 ELSE 0 END) AS repeat_within_30d,
    SUM(reopened) AS reopened_jobs,
    SUM(cost_aed) AS total_cost_aed
FROM reactive
GROUP BY asset_id, building, trade
ORDER BY repeat_within_30d DESC, reactive_jobs DESC
LIMIT 10;