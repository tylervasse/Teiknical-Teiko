import html

import pandas as pd
import streamlit as st

from components import init_state, set_sort
from constants import (
    COL_PCTS,
    OPT_LEFT_PAD,
    OPT_RIGHT_PAD,
    POP_LABELS,
    POP_ORDER,
    REQ_BODY_COL_PCTS,
    REQ_LEFT_PAD,
    REQ_RIGHT_PAD,
    REQUIRED_COLS,
)


def make_required_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()

    sample_order = out["sample"].drop_duplicates().tolist()
    out["sample"] = pd.Categorical(out["sample"], categories=sample_order, ordered=True)

    out["population"] = out["population"].astype(str)
    for c in ["total_count", "count", "percentage"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.sort_values(["sample", "population"], kind="stable").reset_index(drop=True)
    out["idx"] = out.index + 1
    return out[["idx"] + REQUIRED_COLS]


def render_required_sort_header(page_key: str):
    init_state(page_key)

    sort_key = st.session_state.global_sort_key
    sort_dir = st.session_state.global_sort_dir
    arrow = "▲" if sort_dir == "asc" else "▼"

    def label(k: str, text: str):
        return f"{text} {arrow}" if sort_key == k else text

    st.markdown(
        f"""
        <style>
        div:has(.req-sort-anchor-{page_key}) [data-testid="stHorizontalBlock"] {{ gap: 0.45rem !important; }}
        div:has(.req-sort-anchor-{page_key}) [data-testid="stButton"] {{ padding-left: 0 !important; padding-right: 0 !important; }}
        div:has(.req-sort-anchor-{page_key}) [data-testid="stButton"] > button {{
          width: 100% !important;
          border-radius: 10px !important;
          border: 1px solid #e6bcbc !important;
          background: #FFE1E1 !important;
          color: #333 !important;
          padding: 10px 12px !important;
          font-size: 16px !important;
          font-weight: 700 !important;
          text-align: center !important;
          box-shadow: none !important;
          white-space: nowrap !important;
          overflow: hidden !important;
          text-overflow: ellipsis !important;
        }}
        div:has(.req-sort-anchor-{page_key}) [data-testid="stButton"] > button:hover {{ filter: brightness(0.98); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="req-sort-anchor-{page_key}"></div>', unsafe_allow_html=True)

    outer = st.columns([REQ_LEFT_PAD, 100, REQ_RIGHT_PAD], gap="small")
    with outer[0]:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    with outer[1]:
        cols = st.columns(REQ_BODY_COL_PCTS, gap="medium")

        with cols[0]:
            st.markdown("&nbsp;", unsafe_allow_html=True)
        with cols[1]:
            st.button(label("sample", "sample"), on_click=set_sort, args=("sample", page_key), use_container_width=True, key=f"{page_key}_h_sample")
        with cols[2]:
            st.button(label("total_count", "total_count"), on_click=set_sort, args=("total_count", page_key), use_container_width=True, key=f"{page_key}_h_total")
        with cols[3]:
            st.button(label("population", "population"), on_click=set_sort, args=("population", page_key), use_container_width=True, key=f"{page_key}_h_population")
        with cols[4]:
            st.button(label("count", "count"), on_click=set_sort, args=("count", page_key), use_container_width=True, key=f"{page_key}_h_count")
        with cols[5]:
            st.button(label("percentage", "percentage"), on_click=set_sort, args=("percentage", page_key), use_container_width=True, key=f"{page_key}_h_percentage")

    with outer[2]:
        st.markdown("&nbsp;", unsafe_allow_html=True)


def render_required_long_table_html(
    df_required_page: pd.DataFrame,
    height_px: int = 560,
    sort_key: str = "sample",
    sort_dir: str = "asc",
):
    # Adjust these percentages to change column widths (must sum to ~100)
    # Order: [idx, sample, total_count, population, count, percentage]
    COL_WIDTHS_PCT = [8, 24, 17, 17, 14, 20]

    colgroup = "<colgroup>" + "".join([f'<col style="width:{p}%">' for p in COL_WIDTHS_PCT]) + "</colgroup>"

    # j indices: 0=idx, 1=sample, 2=total_count, 3=population, 4=count, 5=percentage
    NUM_COLS = {2, 4, 5}       # numeric JS sort
    RIGHT_ALIGN_COLS = {2, 3, 4, 5}  # right-aligned body cells (includes population)

    KEY_TO_COL = {"sample": 1, "total_count": 2, "population": 3, "count": 4, "percentage": 5}
    sort_col_idx = KEY_TO_COL.get(sort_key, 1)

    def fmt_val(j: int, val) -> str:
        if pd.isna(val):
            return "—"
        if j == 2 or j == 4:
            try:
                return f"{int(val):,}"
            except Exception:
                return str(val)
        if j == 5:
            try:
                return f"{float(val):.4f}"
            except Exception:
                return str(val)
        return str(val)

    # (col_key, display_text, is_num) — empty col_key = non-sortable idx column
    HEADER_DEFS = [
        ("",            "",             False),
        ("sample",      "sample",       False),
        ("total_count", "total_count",  True),
        ("population",  "population",   False),
        ("count",       "count",        True),
        ("percentage",  "percentage",   True),
    ]

    header_cells = []
    for i, (col_key, col_text, is_num) in enumerate(HEADER_DEFS):
        if not col_key:
            header_cells.append('<th class="th-idx"></th>')
        else:
            right_align = is_num or col_key == "population"
            align_cls = "th-num sortable" if right_align else "sortable"
            header_cells.append(
                f'<th class="{align_cls}" data-col="{i}" data-num="{"1" if is_num else "0"}"'
                f' onclick="sortByCol(this)">'
                f'{html.escape(col_text)}<span class="arrow"></span>'
                f'</th>'
            )
    thead = f"<thead><tr>{''.join(header_cells)}</tr></thead>"

    css = f"""
    <style>
      .req-wrap {{
        height: {int(height_px)}px;
        overflow: auto;
        scrollbar-gutter: stable;
        border: 1px solid #e8e8e8;
        border-radius: 4px;
        background: white;
      }}
      table.req {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 15px;
        color: #262730;
      }}
      table.req thead th {{
        position: sticky;
        top: 0;
        z-index: 1;
        background: #FFE1E1;
        border-bottom: 2px solid #e6bcbc;
        border-right: 1px solid #f0f0f0;
        color: #333;
        font-weight: 700;
        font-size: 16px;
        padding: 10px 10px;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        user-select: none;
      }}
      table.req thead th:last-child {{ border-right: none; }}
      table.req thead th.sortable {{ cursor: pointer; }}
      table.req thead th.sortable:hover {{ background: #ffd0d0; }}
      table.req thead th.th-idx {{ text-align: right; }}
      table.req thead th.th-num {{ text-align: right; }}
      table.req thead th .arrow {{ font-size: 11px; margin-left: 2px; }}
      table.req tbody td {{
        text-align: left;
        padding: 8px 10px;
        border-bottom: 1px solid #f0f0f0;
        border-right: 1px solid #f0f0f0;
        vertical-align: middle;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      table.req tbody td:last-child {{ border-right: none; }}
      table.req tbody tr:hover td {{ background: #fafafa; }}
      table.req tbody td.idx {{ color: #999; text-align: right; }}
      table.req tbody td.num {{ text-align: right; }}
    </style>
    """

    js = f"""
    <script>
    var sortCol = {sort_col_idx};
    var sortDir = '{sort_dir}';

    function updateArrows() {{
      document.querySelectorAll('table.req thead th.sortable').forEach(function(th) {{
        var arrow = th.querySelector('.arrow');
        arrow.textContent = parseInt(th.dataset.col) === sortCol
          ? (sortDir === 'asc' ? ' ▲' : ' ▼')
          : '';
      }});
    }}

    function sortByCol(th) {{
      var colIdx = parseInt(th.dataset.col);
      var isNum  = th.dataset.num === '1';
      sortDir = (sortCol === colIdx && sortDir === 'asc') ? 'desc' : 'asc';
      sortCol = colIdx;

      var tbody = document.querySelector('table.req tbody');
      var rows  = Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a, b) {{
        var aRaw = a.cells[colIdx].textContent.trim().replace(/,/g, '');
        var bRaw = b.cells[colIdx].textContent.trim().replace(/,/g, '');
        var cmp;
        if (isNum) {{
          var an = parseFloat(aRaw), bn = parseFloat(bRaw);
          cmp = (isNaN(an) ? -Infinity : an) - (isNaN(bn) ? -Infinity : bn);
        }} else {{
          cmp = aRaw.localeCompare(bRaw);
        }}
        return sortDir === 'asc' ? cmp : -cmp;
      }});
      rows.forEach(function(r) {{ tbody.appendChild(r); }});
      updateArrows();
    }}

    updateArrows();
    </script>
    """

    body_rows = []
    for row in df_required_page.itertuples(index=False, name=None):
        tds = []
        for j, val in enumerate(row):
            if j == 0:
                cls = "idx"
            elif j in RIGHT_ALIGN_COLS:
                cls = "num"
            else:
                cls = ""
            tds.append(f'<td class="{cls}">{html.escape(fmt_val(j, val))}</td>')
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    st.iframe(
        f"""
        {css}
        <div class="req-wrap">
          <table class="req">
            {colgroup}
            {thead}
            <tbody>
              {''.join(body_rows)}
            </tbody>
          </table>
        </div>
        {js}
        """,
        height=height_px + 20,
    )


def render_html_table(df: pd.DataFrame, max_height_px: int = 500, gray_first_col: bool = False):
    """Render any DataFrame with the same visual style as the required long table, with sortable columns."""
    if df.empty:
        st.info("No data to display.")
        return

    cols = list(df.columns)
    n_cols = len(cols)
    col_pct = round(100 / n_cols, 4)
    colgroup = "<colgroup>" + "".join([f'<col style="width:{col_pct}%">' for _ in cols]) + "</colgroup>"

    numeric_cols = {c for c in cols if pd.api.types.is_numeric_dtype(df[c])}

    header_cells = []
    for i, c in enumerate(cols):
        align_cls = "th-num sortable" if c in numeric_cols else "sortable"
        is_num = "1" if c in numeric_cols else "0"
        header_cells.append(
            f'<th class="{align_cls}" data-col="{i}" data-num="{is_num}" onclick="sortByCol(this)">'
            f'{html.escape(str(c))}<span class="arrow"></span>'
            f'</th>'
        )
    thead = f"<thead><tr>{''.join(header_cells)}</tr></thead>"

    def fmt(col, val):
        if pd.isna(val):
            return "—"
        if col in numeric_cols:
            try:
                iv = int(val)
                return f"{iv:,}" if iv == val else str(val)
            except Exception:
                return str(val)
        return str(val)

    body_rows = []
    for _, row in df.iterrows():
        tds = []
        for i, c in enumerate(cols):
            classes = []
            if c in numeric_cols:
                classes.append("num")
            if gray_first_col and i == 0:
                classes.append("first-col")
            cls = " ".join(classes)
            tds.append(f'<td class="{cls}">{html.escape(fmt(c, row[c]))}</td>')
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    # Height: fit content up to max_height_px
    row_px = 37
    header_px = 47
    height_px = min(header_px + len(df) * row_px + 4, max_height_px)

    first_col_css = "table.gen tbody td.first-col { background: #f0f0f0; color: #555; }" if gray_first_col else ""

    css = f"""
    <style>
      .gen-wrap {{
        height: {height_px}px;
        overflow: auto;
        scrollbar-gutter: stable;
        border: 1px solid #e8e8e8;
        border-radius: 4px;
        background: white;
      }}
      table.gen {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 15px;
        color: #262730;
      }}
      table.gen thead th {{
        position: sticky;
        top: 0;
        z-index: 1;
        background: #FFE1E1;
        border-bottom: 2px solid #e6bcbc;
        border-right: 1px solid #f0f0f0;
        color: #333;
        font-weight: 700;
        font-size: 16px;
        padding: 10px 10px;
        text-align: left;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        user-select: none;
      }}
      table.gen thead th:last-child {{ border-right: none; }}
      table.gen thead th.sortable {{ cursor: pointer; }}
      table.gen thead th.sortable:hover {{ background: #ffd0d0; }}
      table.gen thead th.th-num {{ text-align: right; }}
      table.gen thead th .arrow {{ font-size: 11px; margin-left: 2px; }}
      table.gen tbody td {{
        text-align: left;
        padding: 8px 10px;
        border-bottom: 1px solid #f0f0f0;
        border-right: 1px solid #f0f0f0;
        vertical-align: middle;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      table.gen tbody td:last-child {{ border-right: none; }}
      table.gen tbody tr:hover td {{ background: #fafafa; }}
      table.gen tbody td.num {{ text-align: right; }}
      {first_col_css}
    </style>
    """

    js = """
    <script>
    var sortCol = -1;
    var sortDir = 'asc';

    function updateArrows() {
      document.querySelectorAll('table.gen thead th.sortable').forEach(function(th) {
        var arrow = th.querySelector('.arrow');
        arrow.textContent = parseInt(th.dataset.col) === sortCol
          ? (sortDir === 'asc' ? ' ▲' : ' ▼')
          : '';
      });
    }

    function sortByCol(th) {
      var colIdx = parseInt(th.dataset.col);
      var isNum  = th.dataset.num === '1';
      sortDir = (sortCol === colIdx && sortDir === 'asc') ? 'desc' : 'asc';
      sortCol = colIdx;

      var tbody = document.querySelector('table.gen tbody');
      var rows  = Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a, b) {
        var aRaw = a.cells[colIdx].textContent.trim().replace(/,/g, '');
        var bRaw = b.cells[colIdx].textContent.trim().replace(/,/g, '');
        var cmp;
        if (isNum) {
          var an = parseFloat(aRaw), bn = parseFloat(bRaw);
          cmp = (isNaN(an) ? -Infinity : an) - (isNaN(bn) ? -Infinity : bn);
        } else {
          cmp = aRaw.localeCompare(bRaw);
        }
        return sortDir === 'asc' ? cmp : -cmp;
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
      updateArrows();
    }

    updateArrows();
    </script>
    """

    st.iframe(
        f"""
        {css}
        <div class="gen-wrap">
          <table class="gen">
            {colgroup}
            {thead}
            <tbody>{''.join(body_rows)}</tbody>
          </table>
        </div>
        {js}
        """,
        height=height_px + 20,
    )


def render_optional_sort_header(page_key: str):
    init_state(page_key)

    sort_key = st.session_state.global_sort_key
    sort_dir = st.session_state.global_sort_dir
    arrow = "▲" if sort_dir == "asc" else "▼"

    def label_for(key: str, base: str):
        return f"{base} {arrow}" if sort_key == key else base

    st.markdown(
        """
        <style>
        div:has(.sort-anchor) [data-testid="stHorizontalBlock"]{ gap: 0.45rem !important; }
        div:has(.sort-anchor) [data-testid="stButton"]{ padding-left: 0 !important; padding-right: 0 !important; }
        div:has(.sort-anchor) [data-testid="stButton"] > button{
          width: 100% !important;
          border-radius: 10px !important;
          border: 1px solid #e6bcbc !important;
          background: #FFE1E1 !important;
          color: #333 !important;
          padding: 8px 10px !important;
          font-size: 14px !important;
          font-weight: 700 !important;
          text-align: center !important;
          box-shadow: none !important;
          white-space: nowrap !important;
          overflow: hidden;
          text-overflow: ellipsis !important;
        }
        div:has(.sort-anchor) [data-testid="stButton"] > button:hover{ filter: brightness(0.98); }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sort-anchor"></div>', unsafe_allow_html=True)

    outer = st.columns([OPT_LEFT_PAD, 100, OPT_RIGHT_PAD], gap="small")
    with outer[0]:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    with outer[1]:
        cols = st.columns(COL_PCTS, gap="medium")

        with cols[0]:
            st.button(
                label_for("sample", "Sample"),
                on_click=set_sort,
                args=("sample", page_key),
                use_container_width=True,
                key=f"{page_key}_sortbtn_sample",
            )

        for i, p in enumerate(POP_ORDER, start=1):
            with cols[i]:
                st.button(
                    label_for(p, POP_LABELS.get(p, p)),
                    on_click=set_sort,
                    args=(p, page_key),
                    use_container_width=True,
                    key=f"{page_key}_sortbtn_{p}",
                )

        with cols[-1]:
            st.button(
                label_for("total_count", "Total count"),
                on_click=set_sort,
                args=("total_count", page_key),
                use_container_width=True,
                key=f"{page_key}_sortbtn_total",
            )

    with outer[2]:
        st.markdown("&nbsp;", unsafe_allow_html=True)


def render_pretty_rows(df_long: pd.DataFrame, height_px: int = 560):
    if df_long.empty:
        st.info("No data to display.")
        return

    totals = (
        df_long[["sample", "total_count"]]
        .drop_duplicates(subset=["sample"])
        .set_index("sample")["total_count"]
    )

    wide = df_long.pivot(index="sample", columns="population", values=["count", "percentage"])
    wide_count = wide.get("count")
    wide_pct = wide.get("percentage")

    samples = pd.Index(df_long["sample"]).drop_duplicates().tolist()
    colgroup = "<colgroup>" + "".join([f'<col style="width:{p}%">' for p in COL_PCTS]) + "</colgroup>"

    css = f"""
    <style>
    :root {{
        --pad-x: clamp(6px, 1.0vw, 12px);
        --pad-y: clamp(8px, 1.1vw, 12px);
        --radius: clamp(8px, 1.1vw, 10px);
        --box-min-w: clamp(86px, 10vw, 120px);
        --row-gap: clamp(6px, 1.0vw, 10px);
        --pct-size: clamp(15px, 2.0vw, 22px);
        --count-size: clamp(10px, 1.1vw, 12px);
        --pill-text: clamp(14px, 1.6vw, 20px);
        --tile-min-h: clamp(54px, 6.0vw, 76px);
        --accent-red: #FF4747;
    }}
    .wrap {{ height: {int(height_px)}px; overflow-y: auto; padding-right: 6px; }}
    table.pretty {{
        width: 100%;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing: 0 var(--row-gap);
        margin: 0;
    }}
    tbody td {{ background: white; padding: 6px var(--pad-x); vertical-align: middle; overflow: hidden; }}
    tbody td:first-child {{ border-top-left-radius: 16px; border-bottom-left-radius: 16px; }}
    tbody td:last-child {{ border-top-right-radius: 16px; border-bottom-right-radius: 16px; }}

    .sample-pill, .total-pill {{
        border: 1px solid #e6e6e6;
        background: #F5F5F5;
        border-radius: var(--radius);
        padding: var(--pad-y) var(--pad-x);
        font-weight: 650;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-height: var(--tile-min-h);
        display: flex;
        align-items: center;
    }}
    .sample-pill {{ justify-content: flex-start; font-size: var(--pill-text); }}
    .total-pill {{ justify-content: flex-end; font-size: var(--pill-text); }}

    .box {{
        background: #FFF0F0;
        color: var(--accent-red);
        border-radius: var(--radius);
        padding: var(--pad-y) var(--pad-x);
        text-align: center;
        min-width: var(--box-min-w);
        min-height: var(--tile-min-h);
        overflow: hidden;
        border: 2px solid var(--accent-red);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .pct {{ font-size: var(--pct-size); font-weight: 800; line-height: 1.05; color: var(--accent-red); }}
    .count {{
        margin-top: clamp(4px, 0.5vw, 6px);
        font-size: var(--count-size);
        opacity: 0.9;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: var(--accent-red);
    }}
    </style>
    """

    body_rows = []
    for s in samples:
        total = totals.get(s, None)
        row = ["<tr>"]
        row.append(f'<td><div class="sample-pill">{html.escape(str(s))}</div></td>')

        for p in POP_ORDER:
            pct_val = None
            cnt_val = None

            if wide_pct is not None and p in getattr(wide_pct, "columns", []) and s in wide_pct.index:
                pv = wide_pct.at[s, p]
                if pd.notna(pv):
                    pct_val = float(pv)

            if wide_count is not None and p in getattr(wide_count, "columns", []) and s in wide_count.index:
                cv = wide_count.at[s, p]
                if pd.notna(cv):
                    cnt_val = cv

            if pct_val is None:
                pct_str, count_str = "—", ""
            else:
                pct_str = f"{pct_val:.2f}%"
                if cnt_val is None:
                    count_str = ""
                else:
                    try:
                        count_str = f"{int(cnt_val):,} cells"
                    except Exception:
                        count_str = f"{cnt_val} cells"

            row.append(
                f'<td><div class="box">'
                f'<div class="pct">{pct_str}</div>'
                f'<div class="count">{html.escape(count_str)}</div>'
                f"</div></td>"
            )

        total_str = "" if total is None or (isinstance(total, float) and pd.isna(total)) else f"{int(total):,}"
        row.append(f'<td><div class="total-pill">{total_str}</div></td>')
        row.append("</tr>")
        body_rows.append("".join(row))

    st.iframe(
        f"""
        {css}
        <div class="wrap">
          <table class="pretty">
            {colgroup}
            <tbody>
              {''.join(body_rows)}
            </tbody>
          </table>
        </div>
        """,
        height=height_px,
    )
