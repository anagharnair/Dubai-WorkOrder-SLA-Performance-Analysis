"""
Generate a SIMULATED facility management work order dataset.

All data is synthetic. No real company data is used.
Output: data/work_orders.csv

Run from the repo root:
    python scripts/generate_work_orders.py
"""
import os
import numpy as np
import pandas as pd

SEED = 42
N_ORDERS = 6000
START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2025-12-31")
SNAPSHOT = pd.Timestamp("2026-01-15")  # jobs not closed by this date are open

rng = np.random.default_rng(SEED)

buildings = ["Tower A", "Tower B", "Retail Podium", "Residential Block 1",
             "Residential Block 2", "Office Park", "Mall East", "Warehouse Hub"]
trades = ["HVAC", "Electrical", "Plumbing", "Civil", "Fire & Safety",
          "Lifts", "Cleaning", "General"]
trade_weights = [0.28, 0.17, 0.16, 0.08, 0.07, 0.06, 0.08, 0.10]

# Priority -> (response SLA hours, resolution SLA hours, share of jobs)
priorities = {
    "P1 - Critical": (1, 4, 0.08),
    "P2 - High": (4, 24, 0.22),
    "P3 - Medium": (8, 72, 0.45),
    "P4 - Low": (24, 168, 0.25),
}

# Trades that tend to miss SLAs more often (makes the analysis interesting)
trade_delay_factor = {"HVAC": 1.35, "Lifts": 1.30, "Electrical": 1.05,
                      "Plumbing": 1.00, "Civil": 1.20, "Fire & Safety": 0.90,
                      "Cleaning": 0.80, "General": 0.95}

# Build asset register: each asset belongs to a building and a trade
asset_prefix = {"HVAC": "AHU", "Electrical": "DB", "Plumbing": "PMP",
                "Civil": "DOR", "Fire & Safety": "FAP", "Lifts": "LFT",
                "Cleaning": "CLN", "General": "GEN"}
assets = []
for b_i, b in enumerate(buildings):
    for t in trades:
        n_assets = rng.integers(4, 12)
        for k in range(n_assets):
            assets.append({
                "asset_id": f"{asset_prefix[t]}-{b_i + 1}{k + 1:02d}",
                "building": b,
                "trade": t,
                # failure proneness: a few assets fail much more than others
                "weight": rng.pareto(2.2) + 0.2,
            })
assets = pd.DataFrame(assets)

# Pick asset for each job, weighted by trade and failure proneness
rows = []
trade_choices = rng.choice(trades, size=N_ORDERS, p=trade_weights)
for i, t in enumerate(trade_choices):
    pool = assets[assets["trade"] == t]
    p = pool["weight"] / pool["weight"].sum()
    a = pool.iloc[rng.choice(len(pool), p=p.values)]
    rows.append((a["asset_id"], a["building"], t))

df = pd.DataFrame(rows, columns=["asset_id", "building", "trade"])
df.insert(0, "work_order_id", [f"WO-{100000 + i}" for i in range(N_ORDERS)])

# Job type: reactive vs preventive
df["job_type"] = rng.choice(["Reactive", "Preventive"], size=N_ORDERS, p=[0.64, 0.36])

# Priority: preventive jobs are mostly low/medium
prio_names = list(priorities.keys())
prio_p = [v[2] for v in priorities.values()]
prio = rng.choice(prio_names, size=N_ORDERS, p=prio_p)
prev_mask = df["job_type"] == "Preventive"
prio[prev_mask] = rng.choice(["P3 - Medium", "P4 - Low"],
                             size=prev_mask.sum(), p=[0.55, 0.45])
df["priority"] = prio

# Created timestamps: working hours are busier
total_seconds = int((END - START).total_seconds()) + 86400
created = START + pd.to_timedelta(rng.integers(0, total_seconds, N_ORDERS), unit="s")
created = pd.Series(created)
hour_w = np.array([1, 1, 1, 1, 1, 2, 3, 6, 9, 9, 8, 7,
                   6, 7, 8, 8, 7, 6, 4, 3, 2, 2, 1, 1], dtype=float)
hours = rng.choice(range(24), size=N_ORDERS, p=hour_w / hour_w.sum())
created = created.dt.normalize() + pd.to_timedelta(hours, unit="h") \
    + pd.to_timedelta(rng.integers(0, 3600, N_ORDERS), unit="s")
df["created_at"] = created

# SLA targets
df["response_sla_hrs"] = df["priority"].map(lambda p: priorities[p][0])
df["resolution_sla_hrs"] = df["priority"].map(lambda p: priorities[p][1])

# Actual response time (hours): lognormal around SLA with trade delay factor
factor = df["trade"].map(trade_delay_factor).values
resp_median = df["response_sla_hrs"].values * 0.7 * factor
df["response_hrs"] = rng.lognormal(np.log(resp_median), 0.55).round(2)

# Actual resolution time (hours)
res_median = df["resolution_sla_hrs"].values * 0.65 * factor
prev = (df["job_type"] == "Preventive").values
res_median = np.where(prev, res_median * 0.8, res_median)
df["resolution_hrs"] = (df["response_hrs"]
                        + rng.lognormal(np.log(res_median), 0.7)).round(2)

df["responded_at"] = df["created_at"] + pd.to_timedelta(df["response_hrs"], unit="h")
df["closed_at"] = df["created_at"] + pd.to_timedelta(df["resolution_hrs"], unit="h")

# Backlog: some jobs are still open at snapshot date (more in recent months)
age_days = (SNAPSHOT - df["created_at"]).dt.days
p_open = np.clip(0.01 + 0.004 * np.maximum(0, 120 - age_days) / 10, 0.01, 0.12)
p_open = np.where(df["trade"].isin(["HVAC", "Civil", "Lifts"]), p_open * 1.8, p_open)
is_open = rng.random(N_ORDERS) < p_open
# also add a small tail of very old stuck jobs
stuck = rng.random(N_ORDERS) < 0.008
is_open = is_open | stuck
df["status"] = np.where(is_open, "Open", "Closed")
df.loc[is_open, ["closed_at", "resolution_hrs"]] = [pd.NaT, np.nan]
# open jobs: some have not even been responded to
unresponded = is_open & (rng.random(N_ORDERS) < 0.25)
df.loc[unresponded, ["responded_at", "response_hrs"]] = [pd.NaT, np.nan]

# SLA flags
df["response_sla_met"] = np.where(df["response_hrs"].isna(), np.nan,
                                  (df["response_hrs"] <= df["response_sla_hrs"]).astype(float))
df["resolution_sla_met"] = np.where(df["resolution_hrs"].isna(), np.nan,
                                    (df["resolution_hrs"] <= df["resolution_sla_hrs"]).astype(float))

# Reopened jobs: closed reactive jobs, higher for failure-prone assets and HVAC
reopen_p = np.where(df["job_type"] == "Reactive", 0.07, 0.01)
reopen_p = np.where(df["trade"].isin(["HVAC", "Lifts"]), reopen_p * 1.6, reopen_p)
df["reopened"] = ((rng.random(N_ORDERS) < reopen_p) & (df["status"] == "Closed")).astype(int)

# Cost (AED): by trade and priority, reactive costs more
base_cost = {"HVAC": 900, "Electrical": 450, "Plumbing": 380, "Civil": 600,
             "Fire & Safety": 520, "Lifts": 1100, "Cleaning": 120, "General": 200}
prio_mult = {"P1 - Critical": 2.4, "P2 - High": 1.5, "P3 - Medium": 1.0, "P4 - Low": 0.7}
cost = (df["trade"].map(base_cost) * df["priority"].map(prio_mult)
        * np.where(prev, 0.7, 1.15) * rng.lognormal(0, 0.45, N_ORDERS))
df["cost_aed"] = cost.round(0).astype(int)

# Final tidy
cols = ["work_order_id", "asset_id", "building", "trade", "job_type", "priority",
        "created_at", "responded_at", "closed_at", "response_sla_hrs",
        "resolution_sla_hrs", "response_hrs", "resolution_hrs",
        "response_sla_met", "resolution_sla_met", "status", "reopened", "cost_aed"]
df = df[cols].sort_values("created_at").reset_index(drop=True)

os.makedirs("data", exist_ok=True)
out = os.path.join("data", "work_orders.csv")
df.to_csv(out, index=False, date_format="%Y-%m-%d %H:%M:%S")

print(f"Saved {len(df)} work orders to {out}")
print(df["job_type"].value_counts(normalize=True).round(3).to_string())
print("Resolution SLA met:", round(df["resolution_sla_met"].mean(), 3))
print("Open jobs:", (df["status"] == "Open").sum())
