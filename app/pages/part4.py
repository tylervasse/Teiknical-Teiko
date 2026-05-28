import pandas as pd
import streamlit as st

from constants import DB_PATH
from db import get_conn, load_filter_options, query_part4_samples
from tables import render_html_table


def _default_index(options: list[str], preferred: str) -> int:
    lo = [str(x).lower() for x in options]
    return lo.index(preferred.lower()) if preferred.lower() in lo else 0


def render_part4():
    st.header("Part 4 - Data Subset Analysis")

    try:
        opts = load_filter_options(DB_PATH)
    except Exception:
        opts = None

    with st.sidebar:
        st.header("Controls (Part 4)")

        condition4 = st.selectbox(
            "Condition",
            ["melanoma", "carcinoma", "healthy"],
            index=0,
            key="p4_condition",
        )

        sample_type4 = st.selectbox(
            "Sample Type",
            ["PBMC", "Tumor", "Serum", "Plasma"],
            index=0,
            key="p4_sample_type",
        )

        if opts and "treatments" in opts and opts["treatments"]:
            treatment_list = ["(All)"] + opts["treatments"]
            treatment4 = st.selectbox(
                "Treatment",
                treatment_list,
                index=_default_index(treatment_list, "miraclib"),
                key="p4_treatment",
            )
            treatment4 = None if treatment4 == "(All)" else treatment4
        else:
            treatment4 = (
                st.text_input("Treatment (blank = all)", value="miraclib", key="p4_treatment_text").strip()
                or None
            )

        if opts and "times" in opts and opts["times"]:
            times = sorted({int(x) for x in opts["times"]})
            time_choices = ["(All)"] + times
            time4 = st.selectbox(
                "Time from treatment start",
                time_choices,
                index=(1 if 0 in times else 0),
                key="p4_time",
            )
            time4 = None if time4 == "(All)" else int(time4)
        else:
            time4 = st.selectbox(
                "Time from treatment start",
                ["(All)", 0, 7, 14],
                index=1,
                key="p4_time_fallback",
            )
            time4 = None if time4 == "(All)" else int(time4)

    with st.spinner("Querying database for Part 4 subset..."):
        df4 = query_part4_samples(
            DB_PATH,
            condition=str(condition4),
            sample_type=str(sample_type4),
            treatment=treatment4,
            time_from_start=time4,
        )

    if df4.empty:
        st.warning("No rows match the Part 4 subset filters.")
        st.stop()

    # ------- 1) Matching samples -------
    st.subheader("1) Matching samples (one row per sample)")
    samples_df = (
        df4[
            [
                "sample", "project_id", "subject_id", "condition", "sex", "response",
                "treatment", "sample_type", "time_from_treatment_start",
            ]
        ]
        .drop_duplicates()
        .sort_values(["project_id", "subject_id", "sample"], kind="stable")
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Samples", int(samples_df["sample"].nunique()))
    c2.metric("Subjects", int(samples_df["subject_id"].nunique()))
    c3.metric("Projects", int(samples_df["project_id"].nunique()))
    render_html_table(samples_df, max_height_px=500, gray_first_col=True)

    st.divider()

    # ------- 2) Subset summaries -------
    st.subheader("2) Subset summaries")

    st.markdown("**2.1 Samples by project**")
    by_project = (
        samples_df.groupby("project_id", as_index=False)
        .agg(n_samples=("sample", "nunique"))
        .sort_values(["n_samples", "project_id"], ascending=[False, True], kind="stable")
    )
    _col, _ = st.columns([2, 3])
    with _col:
        render_html_table(by_project)

    st.markdown("**2.2 Subjects by response (yes/no)**")
    resp_df = samples_df.copy()
    resp_df["response"] = resp_df["response"].astype(str).str.strip().str.lower()
    resp_df.loc[~resp_df["response"].isin(["yes", "no"]), "response"] = "unknown"
    by_response = (
        resp_df.groupby("response", as_index=False)
        .agg(n_subjects=("subject_id", "nunique"))
        .sort_values(["response"], kind="stable")
    )
    _col, _ = st.columns([2, 3])
    with _col:
        render_html_table(by_response)

    st.markdown("**2.3 Subjects by sex**")
    sex_df = samples_df.copy()
    sex_df["sex"] = sex_df["sex"].astype(str).str.strip()
    sex_df.loc[~sex_df["sex"].isin(["M", "F"]), "sex"] = "Unknown"
    by_sex = (
        sex_df.groupby("sex", as_index=False)
        .agg(n_subjects=("subject_id", "nunique"))
        .sort_values(["sex"], kind="stable")
    )
    _col, _ = st.columns([2, 3])
    with _col:
        render_html_table(by_sex)

    st.divider()

    # ------- Required question -------
    st.subheader("Required question")

    conn = get_conn(DB_PATH)
    params = [treatment4, treatment4]

    avg_sql = """
    SELECT AVG(cc.count) AS avg_b_cells
    FROM cell_counts cc
    JOIN samples sa ON sa.sample_id = cc.sample_id
    JOIN subjects sub ON sub.subject_id = sa.subject_id
    JOIN cell_populations cp ON cp.population_id = cc.population_id
    LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
    WHERE LOWER(cp.name) = 'b_cell'
      AND LOWER(sub.condition) = 'melanoma'
      AND TRIM(sub.sex) = 'M'
      AND LOWER(COALESCE(sub.response,'')) = 'yes'
      AND sa.time_from_treatment_start = 0
      AND (? IS NULL OR LOWER(t.name) = LOWER(?));
    """

    avg_df = pd.read_sql_query(avg_sql, conn, params=params)
    avg_b = avg_df.loc[0, "avg_b_cells"]

    if pd.isna(avg_b):
        st.warning(
            "No rows found for: melanoma + males (M) + responders (yes) + time=0 + B Cells "
            f"{'(and treatment filter applied)' if treatment4 else '(any treatment)'}."
        )
    else:
        st.success(
            f"**Average # of B cells (melanoma, M, responders, time=0"
            f"{', ' + str(treatment4) if treatment4 else ''}): {avg_b:.2f}**"
        )

        rows_sql = """
        SELECT
            sub.subject_id,
            sa.sample_id AS sample,
            cc.count
        FROM cell_counts cc
        JOIN samples sa ON sa.sample_id = cc.sample_id
        JOIN subjects sub ON sub.subject_id = sa.subject_id
        JOIN cell_populations cp ON cp.population_id = cc.population_id
        LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
        WHERE LOWER(cp.name) = 'b_cell'
          AND LOWER(sub.condition) = 'melanoma'
          AND TRIM(sub.sex) = 'M'
          AND LOWER(COALESCE(sub.response,'')) = 'yes'
          AND sa.time_from_treatment_start = 0
          AND (? IS NULL OR LOWER(t.name) = LOWER(?))
        ORDER BY sub.subject_id, sa.sample_id;
        """

        rows_df = pd.read_sql_query(rows_sql, conn, params=params)
        with st.expander("Show contributing rows"):
            render_html_table(rows_df)
