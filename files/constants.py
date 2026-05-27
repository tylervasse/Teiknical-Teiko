DB_PATH = "cell_counts.db"

POP_ORDER = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS = {
    "b_cell": "B Cells",
    "cd8_t_cell": "CD8 T Cells",
    "cd4_t_cell": "CD4 T Cells",
    "nk_cell": "NK Cells",
    "monocyte": "Monocytes",
}

# Alternative table column widths: Sample, 5 pops, Total (sum=100)
COL_PCTS = [16, 14, 14, 14, 14, 14, 14]

# Required header/body widths (sum=100): idx | sample | total_count | population | count | percentage
REQ_IDX_PCT = 8
REQ_COL_PCTS = [24, 17, 17, 14, 20]  # sample...percentage (sum=92)
REQ_BODY_COL_PCTS = [REQ_IDX_PCT] + REQ_COL_PCTS

REQUIRED_COLS = ["sample", "total_count", "population", "count", "percentage"]

# Header-only horizontal buffers (pads affect header buttons, not the body tables)
OPT_LEFT_PAD, OPT_RIGHT_PAD = 1, 3.5
REQ_LEFT_PAD, REQ_RIGHT_PAD = 1, 3.5

PAGER_PULL_UP_PX = 80
