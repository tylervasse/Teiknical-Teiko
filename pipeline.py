"""
Full pipeline: build database (Part 1) + generate static output tables and
plots (Parts 2–4).  All outputs are written to the output/ directory.

Usage:
    python pipeline.py
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu

ROOT    = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(ROOT, "files"))
import db_creation

DB_PATH = os.path.join(ROOT, "cell_counts.db")

POP_ORDER  = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS = {
    "b_cell":      "B Cells",
    "cd8_t_cell":  "CD8 T Cells",
    "cd4_t_cell":  "CD4 T Cells",
    "nk_cell":     "NK Cells",
    "monocyte":    "Monocytes",
}


# ── Part 1: build database ────────────────────────────────────────────────────
print("Part 1: Building database...")
db_creation.DATA_PATH = os.path.join(ROOT, "files", "cell-count.csv")
db_creation.DB_PATH   = DB_PATH
db_creation.main()
print("Part 1: Done.\n")

import sqlite3
conn = sqlite3.connect(DB_PATH)


# ── Part 2: relative frequency summary ───────────────────────────────────────
print("Part 2: Generating frequency summary...")
df_p2 = pd.read_sql_query("""
    SELECT
        sa.sample_id AS sample,
        SUM(cc.count) OVER (PARTITION BY sa.sample_id) AS total_count,
        cp.name      AS population,
        cc.count,
        100.0 * cc.count / SUM(cc.count) OVER (PARTITION BY sa.sample_id) AS percentage
    FROM cell_counts cc
    JOIN samples sa         ON sa.sample_id    = cc.sample_id
    JOIN cell_populations cp ON cp.population_id = cc.population_id
    ORDER BY sa.sample_id, cp.name
""", conn)

df_p2.to_csv(os.path.join(OUT_DIR, "part2_frequency_summary.csv"), index=False)
print(f"  Saved part2_frequency_summary.csv  ({len(df_p2):,} rows)\n")


# ── Part 3: responders vs non-responders ─────────────────────────────────────
print("Part 3: Running statistical analysis...")
df_p3 = pd.read_sql_query("""
    SELECT
        sa.sample_id AS sample,
        sub.subject_id AS subject,
        LOWER(COALESCE(sub.response,'')) AS response,
        cp.name AS population,
        cc.count,
        100.0 * cc.count / SUM(cc.count) OVER (PARTITION BY sa.sample_id) AS percentage
    FROM cell_counts cc
    JOIN samples sa          ON sa.sample_id     = cc.sample_id
    JOIN subjects sub        ON sub.subject_id   = sa.subject_id
    LEFT JOIN treatments t   ON t.treatment_id   = sub.treatment_id
    JOIN cell_populations cp ON cp.population_id = cc.population_id
    WHERE LOWER(sub.condition)           = 'melanoma'
      AND LOWER(sa.sample_type)          = 'pbmc'
      AND LOWER(COALESCE(t.name,''))     = 'miraclib'
      AND LOWER(COALESCE(sub.response,'')) IN ('yes','no')
""", conn)

# Boxplot
pops = [p for p in POP_ORDER if p in df_p3["population"].unique()]
fig, axes = plt.subplots(1, len(pops), figsize=(4 * len(pops), 6), sharey=False)
if len(pops) == 1:
    axes = [axes]

for ax, pop in zip(axes, pops):
    grp    = df_p3[df_p3["population"] == pop]
    yes_v  = grp[grp["response"] == "yes"]["percentage"].dropna().tolist()
    no_v   = grp[grp["response"] == "no"]["percentage"].dropna().tolist()
    bp     = ax.boxplot([yes_v, no_v], labels=["Responders\n(yes)", "Non-responders\n(no)"],
                        patch_artist=True)
    bp["boxes"][0].set_facecolor("#AEC6E8")
    bp["boxes"][1].set_facecolor("#FFB3B3")
    ax.set_title(POP_LABELS.get(pop, pop), fontsize=11, fontweight="bold")
    if pop == pops[0]:
        ax.set_ylabel("Relative frequency (%)", fontsize=10)
    ax.tick_params(axis="x", labelsize=9)

fig.suptitle("Melanoma PBMC (miraclib) — Responders vs Non-responders",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "part3_boxplot.png"), dpi=150, bbox_inches="tight")
plt.close()

# Significance table (Mann-Whitney U, single-timepoint default)
stats_rows = []
for pop in pops:
    grp   = df_p3[df_p3["population"] == pop]
    yes_v = grp[grp["response"] == "yes"]["percentage"].dropna()
    no_v  = grp[grp["response"] == "no"]["percentage"].dropna()
    pval  = float("nan")
    if len(yes_v) >= 2 and len(no_v) >= 2:
        pval = float(mannwhitneyu(yes_v, no_v, alternative="two-sided").pvalue)
    stats_rows.append({
        "population":           POP_LABELS.get(pop, pop),
        "n_responders":         int(len(yes_v)),
        "n_non_responders":     int(len(no_v)),
        "median_responders":    round(float(yes_v.median()), 4) if len(yes_v) else None,
        "median_non_responders":round(float(no_v.median()), 4)  if len(no_v)  else None,
        "p_value":              round(pval, 4) if not math.isnan(pval) else None,
        "significant_p0.05":   (not math.isnan(pval) and pval < 0.05),
    })

df_stats = pd.DataFrame(stats_rows).sort_values("p_value", na_position="last")
df_stats.to_csv(os.path.join(OUT_DIR, "part3_statistics.csv"), index=False)
print(f"  Saved part3_boxplot.png")
print(f"  Saved part3_statistics.csv  ({len(df_stats)} populations)\n")


# ── Part 4: subset analysis ───────────────────────────────────────────────────
print("Part 4: Running subset analysis...")
df_p4 = pd.read_sql_query("""
    SELECT DISTINCT
        p.project_id,
        sa.sample_id AS sample,
        sub.subject_id,
        sub.sex,
        LOWER(COALESCE(sub.response,'')) AS response
    FROM samples sa
    JOIN subjects sub      ON sub.subject_id = sa.subject_id
    JOIN projects p        ON p.project_id   = sub.project_id
    LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
    WHERE LOWER(sub.condition)         = 'melanoma'
      AND LOWER(sa.sample_type)        = 'pbmc'
      AND LOWER(COALESCE(t.name,''))   = 'miraclib'
      AND sa.time_from_treatment_start = 0
""", conn)

df_p4.to_csv(os.path.join(OUT_DIR, "part4_matching_samples.csv"), index=False)

by_project = (
    df_p4.groupby("project_id", as_index=False)
    .agg(n_samples=("sample", "nunique"))
    .sort_values("n_samples", ascending=False)
)
by_project.to_csv(os.path.join(OUT_DIR, "part4_samples_by_project.csv"), index=False)

by_response = (
    df_p4.groupby("response", as_index=False)
    .agg(n_subjects=("subject_id", "nunique"))
)
by_response.to_csv(os.path.join(OUT_DIR, "part4_subjects_by_response.csv"), index=False)

by_sex = (
    df_p4.groupby("sex", as_index=False)
    .agg(n_subjects=("subject_id", "nunique"))
)
by_sex.to_csv(os.path.join(OUT_DIR, "part4_subjects_by_sex.csv"), index=False)

avg_b = pd.read_sql_query("""
    SELECT AVG(cc.count) AS avg_b_cells
    FROM cell_counts cc
    JOIN samples sa          ON sa.sample_id     = cc.sample_id
    JOIN subjects sub        ON sub.subject_id   = sa.subject_id
    JOIN cell_populations cp ON cp.population_id = cc.population_id
    LEFT JOIN treatments t   ON t.treatment_id   = sub.treatment_id
    WHERE LOWER(cp.name)                  = 'b_cell'
      AND LOWER(sub.condition)            = 'melanoma'
      AND TRIM(sub.sex)                   = 'M'
      AND LOWER(COALESCE(sub.response,''))= 'yes'
      AND sa.time_from_treatment_start    = 0
      AND LOWER(COALESCE(t.name,''))      = 'miraclib'
""", conn).iloc[0, 0]

conn.close()

answer = f"{avg_b:.2f}" if avg_b is not None else "N/A"
with open(os.path.join(OUT_DIR, "part4_avg_b_cells.txt"), "w") as f:
    f.write(f"Average B cells (melanoma, male, responders, time=0, miraclib): {answer}\n")

print(f"  Saved part4_matching_samples.csv  ({len(df_p4)} rows)")
print(f"  Saved part4_samples_by_project.csv")
print(f"  Saved part4_subjects_by_response.csv")
print(f"  Saved part4_subjects_by_sex.csv")
print(f"  Saved part4_avg_b_cells.txt")
print(f"\n  Average B cells (melanoma, M, responders, time=0, miraclib): {answer}")
print(f"\nAll outputs written to: {OUT_DIR}/")
