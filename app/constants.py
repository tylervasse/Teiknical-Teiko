import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cell_counts.db")

POP_ORDER = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS = {
    "b_cell": "B Cells",
    "cd8_t_cell": "CD8 T Cells",
    "cd4_t_cell": "CD4 T Cells",
    "nk_cell": "NK Cells",
    "monocyte": "Monocytes",
}

REQUIRED_COLS = ["sample", "total_count", "population", "count", "percentage"]
