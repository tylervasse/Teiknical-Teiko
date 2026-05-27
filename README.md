# Teiko-Technical
Interactive Streamlit dashboard for analyzing immune cell population dynamics in mock clinical trial data, integrating SQLite-backed queries, statistical testing, and visualization.

---

<br>

## Table of Contents

- [Project Overview](#project-overview)
- [How to Run the Project (GitHub Codespaces)](#how-to-run-the-project-github-codespaces)
- [Database Schema Design and Scalability](#database-schema-design-and-scalability)
- [Code Structure Overview](#code-structure-overview)
- [Dashboard Features](#dashboard-features)
- [Link to the Dashboard](#link-to-the-dashboard)

---

<br>

## Project Overview

The goal of this project is to analyze immune cell population data from clinical samples and present the results through an interactive dashboard. The workflow mirrors a real-world analytical pipeline:

1. Load and normalize raw CSV data into a relational SQLite database  
2. Query and aggregate data for analysis  
3. Visualize results through a client-facing dashboard  

---

<br>

## How to Run the Project (GitHub Codespaces)

The project includes a `.devcontainer` with Python 3.10 and automatic dependency setup. When opened in GitHub Codespaces, everything should be pre-installed and ready to run.

**Step 1 — Open in GitHub Codespaces**

Click **Code → Codespaces → Create codespace on main** from the repository page. The devcontainer will automatically install all dependencies on startup.

**Step 2 — Install dependencies (if needed)**

If dependencies are not already installed, run from the terminal:

```bash
pip install -r files/requirements.txt
```

**Step 3 — SQLite Database**

A pre-built SQLite database (`cell_counts.db`) is included in the repository — no setup is required. If you wish to regenerate it from the original CSV for verification purposes:

```bash
python files/db_creation.py
```

Console output will report the number of projects, subjects, samples, and cell count records inserted as a sanity check.

**Step 4 — Launch the Dashboard**

```bash
streamlit run files/streamlit_dashboard.py
```

GitHub Codespaces will detect the running server and prompt you to open the forwarded port. Open it in your browser to view the dashboard.

---

<br>

## Database Schema Design and Scalability

The database uses a normalized relational schema that separates core entities from sample-specific details.

### Schema Overview

**projects**

| Column | Type | Description |
|--------|------|-------------|
| `project_id` | TEXT | Unique project identifier (primary key) |

<br>

**subjects**

| Column | Type | Description |
|--------|------|-------------|
| `subject_id` | TEXT | Unique subject identifier (primary key) |
| `project_id` | TEXT | Project this subject belongs to (foreign key) |
| `treatment_id` | INTEGER | Treatment administered (foreign key; NULL if none) |
| `condition` | TEXT | Disease condition (melanoma, carcinoma, healthy) |
| `age` | INTEGER | Subject age |
| `sex` | TEXT | Subject sex |
| `response` | TEXT | Treatment response (yes/no; NULL if unknown) |

Treatment is stored at the subject level because all samples from a subject share the same treatment. "None" treatment is stored as `NULL` rather than a dedicated row. Blank response values are stored as `NULL` rather than empty strings.

<br>

**treatments**

| Column | Type | Description |
|--------|------|-------------|
| `treatment_id` | INTEGER | Unique treatment identifier (primary key) |
| `name` | TEXT | Treatment name (e.g. miraclib, phauximab) |

<br>

**samples**

| Column | Type | Description |
|--------|------|-------------|
| `sample_id` | TEXT | Unique sample identifier (primary key) |
| `subject_id` | TEXT | Subject this sample belongs to (foreign key) |
| `sample_type` | TEXT | Sample type (PBMC, Tumor, Serum, Plasma) |
| `time_from_treatment_start` | REAL | Time relative to treatment start (in days) |

<br>

**cell_populations**

| Column | Type | Description |
|--------|------|-------------|
| `population_id` | INTEGER | Unique population identifier (primary key) |
| `name` | TEXT | Population name (e.g. b_cell, cd8_t_cell) |

<br>

**cell_counts**

| Column | Type | Description |
|--------|------|-------------|
| `sample_id` | TEXT | Sample this count belongs to (foreign key) |
| `population_id` | INTEGER | Cell population (foreign key) |
| `count` | INTEGER | Observed cell count (non-negative) |

<br>

### Rationale and Scalability

- Normalization prevents duplicated metadata and inconsistent values
- Treatment at the subject level reflects the biological reality that subjects — not individual samples — receive treatments
- Foreign keys enforce referential integrity
- Long-format measurement storage supports aggregation and statistical analysis

This design scales well to hundreds of projects and thousands of samples. New immune populations or additional studies can be added without schema changes, and indexing supports efficient filtering by project, condition, response, treatment, timepoint, and population.

---

<br>

## Code Structure Overview

```
Teiko-Technical/
├── .devcontainer/
│   └── devcontainer.json
├── files/
│   ├── pages/
│   │   ├── part2.py
│   │   ├── part3.py
│   │   └── part4.py
│   ├── cell-count.csv
│   ├── cell_counts.db
│   ├── components.py
│   ├── constants.py
│   ├── db.py
│   ├── db_creation.py
│   ├── requirements.txt
│   ├── streamlit_dashboard.py
│   └── tables.py
└── README.md
```

<br>

#### `streamlit_dashboard.py`

Main entry point. Defines the section list, handles arrow-based navigation between pages via `st.session_state`, and injects global CSS (including suppression of Streamlit's auto-generated sidebar page navigation).

#### `db_creation.py`

Handles database creation and data loading. Defines the SQLite schema, validates the input CSV, inserts normalized data into relational tables, and performs basic sanity checks. Skips inserting "none" as a treatment row; maps it to `NULL` on the subject instead.

#### `db.py`

Contains all database access logic. Uses `@st.cache_resource` for the connection and `@st.cache_data` for query results to avoid redundant computation. Query functions support flexible filtering by project, condition, response, treatment, sample type, and timepoint.

#### `tables.py`

Provides two HTML table renderers using `st.components.v1.html`:

- `render_required_long_table_html` — paginated table for the overview with sortable columns, red sticky header, and per-column formatting
- `render_html_table` — generic renderer for any DataFrame with the same red-header styling, sortable columns, and an optional gray first column

#### `components.py`

Provides the pagination control widget (page number input, prev/next buttons, total pages display) used by the overview table.

#### `constants.py`

Shared constants including column definitions, population order and labels, layout widths, and the database path.

#### `pages/part2.py`, `pages/part3.py`, `pages/part4.py`

Page-level render functions for the Overview, Response Group Comparison, and Subset Analysis sections respectively.

---

<br>

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

<br>

## Link to the Dashboard

The dashboard is publicly hosted on Streamlit Community Cloud and can be accessed at:

**[https://tyler-teiknical.streamlit.app/](https://tyler-teiknical.streamlit.app/)**

It can also be run locally or in GitHub Codespaces:

```bash
streamlit run files/streamlit_dashboard.py
```
