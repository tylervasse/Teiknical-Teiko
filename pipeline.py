"""
Generate static output tables and plots (Parts 2–4).
Expects cell_counts.db to already exist at the repo root (built by load_data.py).
All outputs are written to the output/ directory.
"""
import math
import os
import sqlite3

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import statsmodels.formula.api as smf

ROOT    = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUT_DIR, exist_ok=True)

DB_PATH = os.path.join(ROOT, "cell_counts.db")

POP_ORDER  = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS = {
    "b_cell":      "B Cells",
    "cd8_t_cell":  "CD8 T Cells",
    "cd4_t_cell":  "CD4 T Cells",
    "nk_cell":     "NK Cells",
    "monocyte":    "Monocytes",
}

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

# Boxplot — styled to match the dashboard
pops       = [p for p in POP_ORDER if p in df_p3["population"].unique()]
pop_labels = [POP_LABELS.get(p, p) for p in pops]
x_pos      = list(range(len(pops)))

RESP_COLOR    = "#1F77B4"
NONRESP_COLOR = "#AEC7E8"
GROUP_OFFSET  = 0.18
BOX_WIDTH     = 0.30
JITTER        = 0.10

fig, ax = plt.subplots(figsize=(max(8, 2.2 * len(pops)), 6))

for resp, color, label in [
    ("yes", RESP_COLOR,    "Responders (yes)"),
    ("no",  NONRESP_COLOR, "Non-responders (no)"),
]:
    offset    = -GROUP_OFFSET if resp == "yes" else GROUP_OFFSET
    positions = [x + offset for x in x_pos]
    data      = [
        df_p3[(df_p3["population"] == p) & (df_p3["response"] == resp)]["percentage"].dropna().tolist()
        for p in pops
    ]

    bp = ax.boxplot(
        data,
        positions=positions,
        widths=BOX_WIDTH,
        patch_artist=True,
        whis=1.5,
        showfliers=False,
        medianprops=dict(color="black", linewidth=2),
        whiskerprops=dict(color="black", linewidth=1.5),
        capprops=dict(color="black", linewidth=1.5),
        boxprops=dict(color="black", linewidth=1.5),
    )
    for patch in bp["boxes"]:
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    for i, pos in enumerate(positions):
        vals = data[i]
        if vals:
            jit = (np.random.rand(len(vals)) - 0.5) * (2 * JITTER)
            ax.scatter(
                [pos + j for j in jit], vals,
                color=color, alpha=0.18, s=40, zorder=3, linewidths=0,
            )

ax.set_xticks(x_pos)
ax.set_xticklabels(pop_labels, fontsize=12)
ax.set_ylabel("Relative frequency (%)", fontsize=13)
ax.set_title("Responders (yes) vs Non-responders (no)", fontsize=14, fontweight="bold", pad=12)

legend_handles = [
    mpatches.Patch(facecolor=RESP_COLOR,    alpha=0.75, edgecolor="black", label="Responders (yes)"),
    mpatches.Patch(facecolor=NONRESP_COLOR, alpha=0.75, edgecolor="black", label="Non-responders (no)"),
]
ax.legend(handles=legend_handles, fontsize=11)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "part3_boxplot.png"), dpi=150, bbox_inches="tight")
plt.close()

# Significance table (LMEM, subject as random effect — all timepoints)
stats_rows = []
for pop in pops:
    grp  = df_p3[df_p3["population"] == pop].copy()
    yv   = grp[grp["response"] == "yes"]["percentage"].dropna()
    nv   = grp[grp["response"] == "no"]["percentage"].dropna()
    pval = float("nan")
    grp["response_bin"] = grp["response"].map({"yes": 1, "no": 0})
    if grp["response_bin"].nunique() == 2 and grp["subject"].nunique() > 1:
        try:
            fit  = smf.mixedlm("percentage ~ response_bin", grp, groups=grp["subject"]).fit(disp=False)
            p_raw = fit.pvalues.get("response_bin", None)
            if p_raw is not None:
                pval = float(p_raw)
        except Exception:
            pass
    stats_rows.append({
        "population":            POP_LABELS.get(pop, pop),
        "n_responders":          int(len(yv)),
        "n_non_responders":      int(len(nv)),
        "median_responders":     round(float(yv.median()), 4) if len(yv) else None,
        "median_non_responders": round(float(nv.median()), 4) if len(nv) else None,
        "p_value":               round(pval, 4) if not math.isnan(pval) else None,
        "significant_p0.05":     (not math.isnan(pval) and pval < 0.05),
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
