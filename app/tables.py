import html
import json

import pandas as pd
import streamlit as st

from constants import REQUIRED_COLS


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


def render_required_long_table_html(
    df: pd.DataFrame,
    height_px: int = 600,
    sort_key: str = "sample",
    sort_dir: str = "asc",
):
    COL_WIDTHS_PCT = [8, 24, 17, 17, 14, 20]
    NUM_COLS_SET = {2, 4, 5}
    RIGHT_ALIGN_COLS = {2, 3, 4, 5}
    KEY_TO_COL = {"sample": 1, "total_count": 2, "population": 3, "count": 4, "percentage": 5}
    sort_col_idx = KEY_TO_COL.get(sort_key, 1)
    N_COLS = 6

    HEADER_DEFS = [
        ("",            "",             False),
        ("sample",      "sample",       False),
        ("total_count", "total_count",  True),
        ("population",  "population",   False),
        ("count",       "count",        True),
        ("percentage",  "percentage",   True),
    ]

    def fmt_val(j: int, val) -> str:
        if pd.isna(val):
            return "—"
        if j in (2, 4):
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

    rows_data = []
    for row in df.itertuples(index=False, name=None):
        formatted = [fmt_val(j, v) for j, v in enumerate(row)]
        raw = []
        for j, v in enumerate(row):
            if j in NUM_COLS_SET:
                try:
                    raw.append(None if pd.isna(v) else float(v))
                except Exception:
                    raw.append(None)
            else:
                raw.append("" if pd.isna(v) else str(v))
        rows_data.append({"f": formatted, "r": raw})

    rows_json        = json.dumps(rows_data, ensure_ascii=False)
    right_align_json = json.dumps(list(RIGHT_ALIGN_COLS))

    colgroup = "<colgroup>" + "".join([f'<col style="width:{p}%">' for p in COL_WIDTHS_PCT]) + "</colgroup>"

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
        height: 37px;
        box-sizing: border-box;
      }}
      table.req tbody td:last-child {{ border-right: none; }}
      table.req tbody tr:hover td {{ background: #fafafa; }}
      table.req tbody td.idx {{ color: #999; text-align: right; }}
      table.req tbody td.num {{ text-align: right; }}
      table.req tbody td.spacer {{ border: none; padding: 0; }}
    </style>
    """

    js = f"""
    <script>
    var allRows      = {rows_json};
    var sortCol      = {sort_col_idx};
    var sortDir      = '{sort_dir}';
    var ROW_HEIGHT   = 37;
    var BUFFER       = 25;
    var N_COLS       = {N_COLS};
    var rightAlign   = new Set({right_align_json});

    var container  = document.querySelector('.req-wrap');
    var tbody      = document.querySelector('table.req tbody');

    var topTd      = document.createElement('td');
    var bottomTd   = document.createElement('td');
    topTd.colSpan    = N_COLS;
    bottomTd.colSpan = N_COLS;
    topTd.className    = 'spacer';
    bottomTd.className = 'spacer';
    var topRow     = document.createElement('tr');
    var bottomRow  = document.createElement('tr');
    topRow.appendChild(topTd);
    bottomRow.appendChild(bottomTd);
    tbody.appendChild(topRow);
    tbody.appendChild(bottomRow);

    function makeRow(rowData) {{
      var tr = document.createElement('tr');
      rowData.f.forEach(function(val, j) {{
        var td = document.createElement('td');
        if (j === 0)              td.className = 'idx';
        else if (rightAlign.has(j)) td.className = 'num';
        td.textContent = val;
        tr.appendChild(td);
      }});
      return tr;
    }}

    function renderWindow() {{
      var scrollTop = container.scrollTop;
      var startIdx  = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER);
      var endIdx    = Math.min(allRows.length,
                       Math.ceil((scrollTop + container.clientHeight) / ROW_HEIGHT) + BUFFER);

      topTd.style.height    = (startIdx * ROW_HEIGHT) + 'px';
      bottomTd.style.height = Math.max(0, (allRows.length - endIdx) * ROW_HEIGHT) + 'px';

      while (tbody.children.length > 2) tbody.removeChild(tbody.children[1]);

      var frag = document.createDocumentFragment();
      for (var i = startIdx; i < endIdx; i++) frag.appendChild(makeRow(allRows[i]));
      tbody.insertBefore(frag, bottomRow);
    }}

    function updateArrows() {{
      document.querySelectorAll('table.req thead th.sortable').forEach(function(th) {{
        th.querySelector('.arrow').textContent =
          parseInt(th.dataset.col) === sortCol
            ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
      }});
    }}

    function sortByCol(th) {{
      var colIdx = parseInt(th.dataset.col);
      var isNum  = th.dataset.num === '1';
      sortDir = (sortCol === colIdx && sortDir === 'asc') ? 'desc' : 'asc';
      sortCol = colIdx;

      allRows.sort(function(a, b) {{
        var av = a.r[colIdx], bv = b.r[colIdx];
        var cmp = isNum
          ? ((av === null ? -Infinity : av) - (bv === null ? -Infinity : bv))
          : String(av).localeCompare(String(bv));
        return sortDir === 'asc' ? cmp : -cmp;
      }});

      container.scrollTop = 0;
      renderWindow();
      updateArrows();
    }}

    container.addEventListener('scroll', renderWindow);
    updateArrows();
    renderWindow();
    </script>
    """

    st.iframe(
        f"""
        {css}
        <div class="req-wrap">
          <table class="req">
            {colgroup}
            {thead}
            <tbody></tbody>
          </table>
        </div>
        {js}
        """,
        height=height_px + 20,
    )


def render_html_table(df: pd.DataFrame, max_height_px: int = 500, gray_first_col: bool = False):
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
