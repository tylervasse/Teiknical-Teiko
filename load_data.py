"""
Part 1 — Initialize the SQLite database and load cell-count.csv.

Usage:
    python load_data.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "files"))

import db_creation

db_creation.DATA_PATH = os.path.join(ROOT, "files", "cell-count.csv")
db_creation.DB_PATH   = os.path.join(ROOT, "cell_counts.db")

if __name__ == "__main__":
    db_creation.main()
