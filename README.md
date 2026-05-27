# Teiko-Technical
Interactive Streamlit dashboard for analyzing immune cell population dynamics in mock clinical trial data, integrating SQLite-backed queries, statistical testing, and visualization.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Repository Contents](#repository-contents)
- [How to Run the Project (GitHub Codespaces)](#how-to-run-the-project-github-codespaces)
  - [Install Python Dependencies](#install-python-dependencies)
  - [Build the SQLite Database (Part 1)](#build-the-sqlite-database-part-1)
  - [Launch the Dashboard (Parts 2–4)](#launch-the-dashboard-parts-24)
- [Database Schema Design and Scalability](#database-schema-design-and-scalability)
- [Code Structure Overview](#code-structure-overview)
- [Dashboard Features](#dashboard-features)
- [Link to the Dashboard](#link-to-the-dashboard)
- [Requirements](#requirements)

---

## Project Overview

The goal of this project is to analyze immune cell population data from clinical samples and present the results through an interactive dashboard. The workflow mirrors a real-world analytical pipeline:

1. Load and normalize raw CSV data into a relational SQLite database  
2. Query and aggregate data for analysis  
3. Visualize results through a client-facing dashboard  

---

## Repository Contents

- `cell-count.csv`  
  Original CSV file provided for the assignment

- `cell_counts.db`  
  Pre-built SQLite database generated from `cell-count.csv`

- `db_creation.py`  
  Script for database schema creation and data loading  
  (optional: the database is already provided, but can be rebuilt if desired)

- `streamlit_dashboard.py`  
  Main Streamlit entry point; handles page navigation and global layout

- `db.py`  
  Cached database connection and all SQL query functions

- `tables.py`  
  Custom HTML table renderers (required long table, generic styled table)

- `components.py`  
  Pagination controls and shared UI components

- `constants.py`  
  Shared constants (column definitions, population order, layout widths)

- `pages/part2.py`, `pages/part3.py`, `pages/part4.py`  
  Page-level render functions for each dashboard section

- `requirements.txt`  
  Python dependencies required to run the project

---

## How to Run the Project (GitHub Codespaces)

These steps assume you are running the project in GitHub Codespaces.

### Install Python Dependencies

From the Codespaces terminal, run:

```bash
pip install -r requirements.txt
```

If you prefer to install dependencies manually:

```bash
pip install streamlit pandas numpy plotly scipy statsmodels
```

---

### SQLite Database (Part 1)

A pre-built SQLite database (`cell_counts.db`) is included in the repository to ensure:

- Immediate execution in GitHub Codespaces
- Reproducible results
- Consistent SQL-based analytics

**You do not need to rebuild the database to run the dashboard.**

If you wish to regenerate the database from the original CSV for verification purposes, you may optionally run:

```bash
python db_creation.py
```

You should see console output reporting the number of projects, subjects, samples, and cell count records inserted. This serves as a basic sanity check that the database was built successfully.

---

### Launch the Dashboard (Parts 2–4)

Start the Streamlit application:

```bash
streamlit run streamlit_dashboard.py
```

GitHub Codespaces will detect the running server and prompt you to open the forwarded port. Open it in your browser to view the dashboard.

---

## Database Schema Design and Scalability

The database uses a normalized relational schema that separates core entities from sample-specific details.

### Schema Overview

**projects**  
Stores one row per clinical project.

- `project_id` (primary key)

**subjects**  
Stores one row per subject or patient.

- `subject_id` (primary key)
- `project_id` (foreign key to `projects`)
- `treatment_id` (foreign key to `treatments`)
- `condition`, `age`, `sex`, `response`

Treatment is stored at the subject level because all samples from a subject share the same treatment. Subjects with no treatment have `treatment_id = NULL`. Subjects with no recorded response also store `NULL` rather than a blank string.

**treatments**  
Lookup table for treatment names. Only real treatments are stored — "none" is represented by `treatment_id = NULL` on the subject rather than a dedicated row.

- `treatment_id` (primary key)
- `name` (unique)

**samples**  
Stores one row per biological sample.

- `sample_id` (primary key)
- `subject_id` (foreign key to `subjects`)
- `sample_type`, `time_from_treatment_start`

**cell_populations**  
Lookup table for immune cell populations.

- `population_id` (primary key)
- `name` (unique)

**cell_counts**  
Fact table storing observed counts.

- `sample_id` (foreign key to `samples`)
- `population_id` (foreign key to `cell_populations`)
- `count` (non-negative)

### Rationale and Scalability

- Normalization prevents duplicated metadata and inconsistent values
- Treatment at the subject level reflects the biological reality that subjects — not individual samples — receive treatments
- Foreign keys enforce referential integrity
- Long-format measurement storage supports aggregation and statistical analysis

This design scales well to hundreds of projects and thousands of samples. New immune populations or additional studies can be added without schema changes, and indexing supports efficient filtering by project, condition, response, treatment, timepoint, and population.

---

## Code Structure Overview

The project is organized into several focused modules.

### `db_creation.py`

Handles database creation and data loading. Defines the SQLite schema, validates the input CSV, inserts normalized data into relational tables, and performs basic sanity checks. Skips inserting "none" as a treatment row; maps it to `NULL` on the subject instead.

### `db.py`

Contains all database access logic. Uses `@st.cache_resource` for the connection and `@st.cache_data` for query results to avoid redundant computation. Query functions support flexible filtering by project, condition, response, treatment, sample type, and timepoint.

### `tables.py`

Provides two HTML table renderers using `st.components.v1.html`:

- `render_required_long_table_html` — paginated table for the overview with sortable columns, red sticky header, and per-column formatting
- `render_html_table` — generic renderer for any DataFrame with the same red-header styling, sortable columns, and an optional gray first column

### `components.py`

Provides the pagination control widget (page number input, prev/next buttons, total pages display) used by the overview table.

### `streamlit_dashboard.py`

Main entry point. Defines the section list, handles arrow-based navigation between pages via `st.session_state`, and injects global CSS (including suppression of Streamlit's auto-generated sidebar page navigation).

---

## Dashboard Features

The dashboard contains three sections navigable using the ◀ ▶ arrows in the sidebar.

### Overview (Part 2)

- Sidebar filters: project, condition, response, treatment, sample type, sample name search (multiselect with autocomplete), sample range input (e.g. `s001-s050`), and a **Clear all filters** button
- Custom HTML table with red sticky header, sortable columns, vertical separator lines, and right-aligned numeric/population columns
- Full-precision percentage values (not rounded before display)
- Paginated output with configurable page size
- CSV export for both the filtered view and the full dataset

### Response Group Comparison (Part 3)

- Sidebar filters: project, condition, treatment, sample type, timepoints multiselect, significance level (α), and individual sample point overlay toggle
- Custom side-by-side boxplots (responders vs non-responders) built with Plotly, using IQR whiskers and jittered point overlay
- Statistical test selected automatically based on timepoint selection:
  - **LMEM** (linear mixed effects model, subject as random effect) when all timepoints or multiple timepoints are selected
  - **Mann-Whitney U** when exactly one timepoint is selected
- Spinner shown while significance tests are running
- Results table sorted by p-value; significant populations highlighted in a summary banner

### Subset Analysis (Part 4)

- Sidebar filters: condition, sample type, treatment, time from treatment start
- Matching samples table with sample column first and gray first-column styling; styled to match the overview table
- Subset summary tables (samples by project, subjects by response, subjects by sex) displayed at reduced width with the same red-header styling and sortable columns
- Required question: average B cell count for melanoma male responders at time = 0, with expandable contributing rows table

---

## Link to the Dashboard

The dashboard is an internal Streamlit application intended to run in a controlled environment such as GitHub Codespaces.

After running:

```bash
streamlit run streamlit_dashboard.py
```

GitHub Codespaces will expose the application on a forwarded port. Opening that port in the browser provides access to the dashboard.

The URL will look similar to:

```text
https://<codespace-name>-8501.app.github.dev
```

This URL is generated dynamically by GitHub Codespaces and will change between sessions.

---

## Requirements

- Python 3.10+
- streamlit >= 1.31
- pandas >= 1.5
- numpy >= 1.23
- plotly >= 5.18
- scipy >= 1.10
- statsmodels >= 0.14
