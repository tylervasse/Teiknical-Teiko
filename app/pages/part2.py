import re

import pandas as pd
import streamlit as st

from constants import DB_PATH, POP_ORDER
from db import load_filter_options, norm, query_part2_frequencies
from tables import make_required_df, render_required_long_table_html


def _expand_range(range_str: str, all_samples: list) -> list:
    text = range_str.strip()
    if not text:
        return []

    split_idx = None
    for i in range(len(text) - 1, 0, -1):
        if text[i] == "-":
            left, right = text[:i].strip(), text[i + 1 :].strip()
            if left and right and re.search(r"\d", left) and re.search(r"\d", right):
                split_idx = i
                break

    if split_idx is None:
        return []

    start_str = text[:split_idx].strip()
    end_str = text[split_idx + 1 :].strip()

    m_s = re.match(r"^(.*?)(\d+)$", start_str)
    m_e = re.match(r"^(.*?)(\d+)$", end_str)
    if not m_s or not m_e:
        return []

    pre_start, num_start = m_s.group(1), int(m_s.group(2))
    pre_end, num_end = m_e.group(1), int(m_e.group(2))

    if pre_start != pre_end:
        return []

    prefix = pre_start
    lo, hi = min(num_start, num_end), max(num_start, num_end)

    result = []
    pat = re.compile(r"^" + re.escape(prefix) + r"(\d+)$")
    for s in all_samples:
        mm = pat.match(str(s))
        if mm and lo <= int(mm.group(1)) <= hi:
            result.append(s)
    return result


def _clear_p2_filters():
    st.session_state["p2_project"] = "(All)"
    st.session_state["p2_condition"] = "(All)"
    st.session_state["p2_response"] = "(All)"
    st.session_state["p2_treatment"] = "(All)"
    st.session_state["p2_sample_type"] = "(All)"
    st.session_state["p2_sample_filter"] = []
    st.session_state["p2_sample_range"] = ""


def render_part2():
    st.caption("Part 2: Relative frequency (%) of each immune cell population per sample.")

    try:
        opts = load_filter_options(DB_PATH)
    except Exception as e:
        st.error(f"Could not load DB options from {DB_PATH}. Did you run Part 1 to create/load the DB?\n\nError: {e}")
        st.stop()

    with st.sidebar:
        st.sidebar.header("Filters (Part 2)")
        project = st.sidebar.selectbox("Project", ["(All)"] + opts["projects"], key="p2_project")
        condition = st.sidebar.selectbox("Condition", ["(All)"] + opts["conditions"], key="p2_condition")
        response = st.sidebar.selectbox("Response", ["(All)"] + opts["responses"], key="p2_response")
        treatment = st.sidebar.selectbox("Treatment", ["(All)"] + opts["treatments"], key="p2_treatment")
        sample_type = st.sidebar.selectbox("Sample Type", ["(All)"] + opts["sample_types"], key="p2_sample_type")

    with st.spinner("Querying database..."):
        df = query_part2_frequencies(
            DB_PATH,
            norm(project),
            norm(condition),
            norm(response),
            norm(treatment),
            norm(sample_type),
        )

    all_sample_options = sorted(df["sample"].unique().tolist()) if not df.empty else []

    current_filter = st.session_state.get("p2_sample_filter", [])
    valid_filter = [s for s in current_filter if s in all_sample_options]
    if valid_filter != current_filter:
        st.session_state["p2_sample_filter"] = valid_filter

    with st.sidebar:
        st.sidebar.subheader("Sample Search")
        selected_samples = st.sidebar.multiselect(
            "Sample names",
            options=all_sample_options,
            key="p2_sample_filter",
            placeholder="Type to search...",
        )
        st.sidebar.text_input(
            "Or enter range",
            key="p2_sample_range",
            placeholder="e.g. 1-50 or s001-s050",
        )
        st.sidebar.button(
            "Clear all filters",
            on_click=_clear_p2_filters,
            use_container_width=True,
        )

    range_str = st.session_state.get("p2_sample_range", "").strip()
    range_matches = _expand_range(range_str, all_sample_options) if range_str else []
    combined_filter = list(set(selected_samples) | set(range_matches))

    if combined_filter:
        df = df[df["sample"].isin(combined_filter)].copy()

    if df.empty:
        st.warning("No rows match your filters.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows (sample × population)", len(df))
    c2.metric("Unique samples", df["sample"].nunique())
    c3.metric("Populations", df["population"].nunique())

    st.divider()

    df_required = make_required_df(df)
    df_sorted = df_required.sort_values("sample", ascending=True, kind="stable")

    render_required_long_table_html(df_sorted, height_px=600, sort_key="sample", sort_dir="asc")

    csv_required = df_required.drop(columns=["idx"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Export table as CSV",
        data=csv_required,
        file_name="cell_frequencies_part2_required_long.csv",
        mime="text/csv",
    )

    st.divider()

    st.subheader("Population composition by sample (% stacked)")

    keep_samples = (
        df[["sample"]]
        .drop_duplicates()
        .sort_values("sample")["sample"]
        .tolist()
    )

    df_plot = df[df["sample"].isin(keep_samples)].copy()

    pivot = (
        df_plot.pivot(index="sample", columns="population", values="percentage")
               .fillna(0.0)
               .reindex(keep_samples)
    )
    for p in POP_ORDER:
        if p not in pivot.columns:
            pivot[p] = 0.0

    st.bar_chart(pivot[POP_ORDER])
