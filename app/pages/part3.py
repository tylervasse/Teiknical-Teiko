import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from constants import DB_PATH, POP_LABELS, POP_ORDER
from db import load_filter_options, norm, query_part3_frequencies


def _default_index(options: list[str], preferred: str) -> int:
    lo = [str(x).lower() for x in options]
    return lo.index(preferred.lower()) if preferred.lower() in lo else 0



def _rgba_with_alpha(rgba: str, alpha: float) -> str:
    s = rgba.strip().lower()
    if s.startswith("rgba") or s.startswith("rgb"):
        inner = s[s.find("(") + 1:s.find(")")]
        parts = [p.strip() for p in inner.split(",")]
        r, g, b = parts[0], parts[1], parts[2]
        return f"rgba({r},{g},{b},{alpha})"
    return rgba


def _whiskers_iqr(series: pd.Series):
    s = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if len(s) == 0:
        return None
    q1 = float(s.quantile(0.25))
    med = float(s.quantile(0.50))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    lo_fence = q1 - 1.5 * iqr
    hi_fence = q3 + 1.5 * iqr
    lo = float(s[s >= lo_fence].min())
    hi = float(s[s <= hi_fence].max())
    return q1, med, q3, lo, hi


def render_part3():
    st.header("Part 3 - Statistical Analysis")
    st.caption(
        "Compare **responders** (response = yes) vs **non-responders** (response = no) "
        "using **relative frequencies (%)** per immune population."
    )

    try:
        opts = load_filter_options(DB_PATH)
    except Exception as e:
        st.error(f"Could not load DB options from {DB_PATH}. Did you run Part 1?\n\nError: {e}")
        st.stop()

    with st.sidebar:
        st.header("Controls (Part 3)")

        project3 = st.selectbox("Project", ["(All)"] + opts["projects"], key="p3_project")

        condition_list = ["(All)"] + opts["conditions"]
        condition3 = st.selectbox(
            "Condition",
            condition_list,
            index=_default_index(condition_list, "melanoma"),
            key="p3_condition",
        )

        treatment_list = ["(All)"] + opts["treatments"]
        treatment3 = st.selectbox(
            "Treatment",
            treatment_list,
            index=_default_index(treatment_list, "miraclib"),
            key="p3_treatment",
        )

        sample_type_list = ["(All)"] + opts["sample_types"]
        sample_type3 = st.selectbox(
            "Sample Type",
            sample_type_list,
            index=_default_index(sample_type_list, "PBMC"),
            key="p3_sample_type",
        )

        times_available = sorted([int(x) for x in opts.get("times", []) if x is not None])
        time_filter = st.multiselect(
            "Timepoints (empty = all)",
            options=times_available,
            default=[],
            key="p3_timepoints",
        )

        show_points = st.checkbox("Overlay individual sample points", value=True, key="p3_show_points")

        st.divider()
        alpha = st.number_input(
            "Significance level (α)",
            min_value=0.001,
            max_value=0.20,
            value=0.05,
            step=0.01,
            key="p3_alpha",
        )

    time_arg = tuple(int(t) for t in time_filter) if time_filter else None

    with st.spinner("Querying database for Part 3..."):
        df3 = query_part3_frequencies(
            DB_PATH,
            norm(project3),
            norm(condition3),
            None,
            norm(treatment3),
            norm(sample_type3),
            time_from_start=time_arg,
        )

    if df3.empty:
        st.warning("No rows match your Part 3 filters.")
        st.stop()

    df3["response"] = df3["response"].astype(str).str.strip().str.lower()
    df3 = df3[df3["response"].isin(["yes", "no"])].copy()

    if df3.empty:
        st.warning("After filtering to response ∈ {yes, no}, no rows remain.")
        st.stop()

    n_samples = df3["sample"].nunique()
    n_yes = df3.loc[df3["response"] == "yes", "sample"].nunique()
    n_no = df3.loc[df3["response"] == "no", "sample"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Samples", n_samples)
    c2.metric("Responders (yes)", n_yes)
    c3.metric("Non-responders (no)", n_no)

    if n_yes < 2 or n_no < 2:
        st.warning("Not enough samples in one group for reliable stats/boxplots (need at least 2 per group).")

    st.divider()
    st.subheader("Responder vs non-responder relative frequencies (boxplots)")

    df3["population"] = df3["population"].astype(str)
    df3["percentage"] = pd.to_numeric(df3["percentage"], errors="coerce")

    pops_present = sorted(df3["population"].unique().tolist())
    pop_order = [p for p in POP_ORDER if p in pops_present] + [p for p in pops_present if p not in POP_ORDER]
    pop_labels = [POP_LABELS.get(p, p) for p in pop_order]

    df_plot = df3[["sample", "response", "population", "percentage"]].dropna(subset=["percentage"]).copy()
    df_plot["response"] = df_plot["response"].astype(str).str.strip().str.lower()
    df_plot = df_plot[df_plot["response"].isin(["yes", "no"])].copy()

    df_plot["population_label"] = df_plot["population"].map(lambda p: POP_LABELS.get(p, p))
    df_plot["population_label"] = pd.Categorical(df_plot["population_label"], categories=pop_labels, ordered=True)

    x_map = {lab: i for i, lab in enumerate(pop_labels)}
    df_plot["_x_base"] = df_plot["population_label"].map(x_map).astype(float)

    GROUP_OFFSET = {"yes": -0.18, "no": 0.18}
    JITTER = 0.10
    BOX_COLORS = {
        "yes": "rgba(31,119,180,1)",
        "no":  "rgba(174,199,232,1)",
    }
    POINT_COLORS = {
        "yes": "rgba(31,119,180,0.18)",
        "no":  "rgba(174,199,232,0.18)",
    }
    BOX_HALF_WIDTH = 0.15
    FILL_ALPHA = 0.75

    fig = go.Figure()

    if show_points:
        for resp in ["yes", "no"]:
            d = df_plot[df_plot["response"] == resp]
            if d.empty:
                continue
            x_jit = (
                d["_x_base"]
                + GROUP_OFFSET[resp]
                + (np.random.rand(len(d)) - 0.5) * (2 * JITTER)
            )
            fig.add_trace(
                go.Scatter(
                    x=x_jit,
                    y=d["percentage"],
                    mode="markers",
                    marker=dict(color=POINT_COLORS[resp], size=7, line=dict(width=0)),
                    showlegend=False,
                    hovertemplate=(
                        "Population: %{customdata[0]}<br>"
                        "Response: %{customdata[1]}<br>"
                        "Sample: %{customdata[2]}<br>"
                        "Percent: %{y:.2f}%<extra></extra>"
                    ),
                    customdata=np.stack(
                        [
                            d["population_label"].astype(str),
                            d["response"].astype(str),
                            d["sample"].astype(str),
                        ],
                        axis=1,
                    ),
                )
            )

    shapes = []
    legend_added = {"yes": False, "no": False}

    for resp in ["yes", "no"]:
        for lab in pop_labels:
            d = df_plot[
                (df_plot["response"] == resp) & (df_plot["population_label"].astype(str) == str(lab))
            ]
            if d.empty:
                continue

            stats = _whiskers_iqr(d["percentage"])
            if stats is None:
                continue
            q1, med, q3, wlo, whi = stats

            x_center = float(x_map[lab]) + GROUP_OFFSET[resp]
            x0 = x_center - BOX_HALF_WIDTH
            x1 = x_center + BOX_HALF_WIDTH
            fill = _rgba_with_alpha(BOX_COLORS[resp], FILL_ALPHA)
            outline = "rgba(0,0,0,0.65)"

            shapes.append(dict(type="rect", xref="x", yref="y", x0=x0, x1=x1, y0=q1, y1=q3,
                               fillcolor=fill, line=dict(color=outline, width=1.5), layer="above"))
            shapes.append(dict(type="line", xref="x", yref="y", x0=x0, x1=x1, y0=med, y1=med,
                               line=dict(color="rgba(0,0,0,0.75)", width=2), layer="above"))
            shapes.append(dict(type="line", xref="x", yref="y", x0=x_center, x1=x_center, y0=wlo, y1=q1,
                               line=dict(color=outline, width=1.5), layer="above"))
            shapes.append(dict(type="line", xref="x", yref="y", x0=x_center, x1=x_center, y0=q3, y1=whi,
                               line=dict(color=outline, width=1.5), layer="above"))
            cap = BOX_HALF_WIDTH * 0.65
            shapes.append(dict(type="line", xref="x", yref="y",
                               x0=x_center - cap, x1=x_center + cap, y0=wlo, y1=wlo,
                               line=dict(color=outline, width=1.5), layer="above"))
            shapes.append(dict(type="line", xref="x", yref="y",
                               x0=x_center - cap, x1=x_center + cap, y0=whi, y1=whi,
                               line=dict(color=outline, width=1.5), layer="above"))

    for resp in ["yes", "no"]:
        if not legend_added[resp]:
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=BOX_COLORS[resp]),
                name=("Responders (yes)" if resp == "yes" else "Non-responders (no)"),
                showlegend=True,
            ))
            legend_added[resp] = True

    fig.update_layout(
        shapes=shapes,
        title=dict(text="Responders (yes) vs Non-responders (no)", font=dict(size=22), x=0.5, xanchor="center"),
        legend=dict(font=dict(size=16), itemsizing="constant"),
        legend_title_text="",
        boxmode="group",
        margin=dict(l=40, r=40, t=70, b=90),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(len(pop_labels))),
            ticktext=pop_labels,
            tickangle=25,
            tickfont=dict(size=16),
            title=dict(text="", font=dict(size=18)),
        ),
        yaxis=dict(
            title=dict(text="Relative frequency (%)", font=dict(size=18)),
            tickfont=dict(size=16),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # ------- Significance testing -------
    st.subheader("Significance testing by population")

    # Determine test: LMEM for 0 or multiple timepoints, Mann-Whitney U for exactly 1
    use_lmem = len(time_filter) != 1

    try:
        from scipy.stats import mannwhitneyu
        have_scipy = True
    except Exception:
        have_scipy = False

    try:
        import statsmodels.formula.api as smf
        have_statsmodels = True
    except Exception:
        have_statsmodels = False

    if use_lmem and not have_statsmodels:
        st.error(
            "statsmodels is required for LMEM (multiple timepoints). "
            "Install it with `pip install statsmodels`, or select exactly one timepoint to use Mann-Whitney U instead."
        )
    if not use_lmem and not have_scipy:
        st.error(
            "SciPy is required for Mann-Whitney U. Install it with `pip install scipy`."
        )

    results = []

    with st.spinner("Running significance tests - please wait..."):
        for p in pop_order:
            grp = df3[df3["population"] == p].copy()
            yv = grp[grp["response"] == "yes"]["percentage"].dropna().astype(float)
            nv = grp[grp["response"] == "no"]["percentage"].dropna().astype(float)

            med_yes = float(yv.median()) if len(yv) else float("nan")
            med_no = float(nv.median()) if len(nv) else float("nan")

            pval = float("nan")
            test_name = None

            if use_lmem and have_statsmodels:
                test_name = "LMEM"
                grp["response_bin"] = grp["response"].map({"yes": 1, "no": 0})
                if grp["response_bin"].nunique() == 2 and grp["subject"].nunique() > 1:
                    try:
                        model = smf.mixedlm("percentage ~ response_bin", grp, groups=grp["subject"])
                        fit = model.fit(disp=False)
                        p_raw = fit.pvalues.get("response_bin", None)
                        if p_raw is not None:
                            pval = float(p_raw)
                    except Exception:
                        pass

            elif not use_lmem and have_scipy:
                test_name = "Mann-Whitney U"
                if len(yv) >= 2 and len(nv) >= 2:
                    pval = float(mannwhitneyu(yv, nv, alternative="two-sided").pvalue)

            results.append(dict(
                population=POP_LABELS.get(p, p),
                n_yes=int(len(yv)),
                n_no=int(len(nv)),
                median_yes=round(med_yes, 3) if not math.isnan(med_yes) else None,
                median_no=round(med_no, 3) if not math.isnan(med_no) else None,
                test=test_name,
                p_value=None if math.isnan(pval) else pval,
            ))

    for r in results:
        r["significant"] = r["p_value"] is not None and r["p_value"] < float(alpha)
    out_df = pd.DataFrame(results).sort_values(["p_value"], ascending=[True], na_position="last", kind="stable")

    test_label = "LMEM (subject as random effect)" if use_lmem else "Mann-Whitney U (single timepoint)"
    st.caption(f"Statistical test: **{test_label}**")

    st.dataframe(
        out_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "p_value": st.column_config.NumberColumn(format="%.4f"),
        },
    )

    sig = out_df[out_df["significant"] == True]
    if (have_statsmodels or have_scipy) and len(sig) > 0:
        st.success(
            "Significant populations: " + ", ".join(sig["population"].tolist())
            + f" (p < {alpha})."
        )
    elif have_statsmodels or have_scipy:
        st.info("No populations reached significance at the selected threshold.")
