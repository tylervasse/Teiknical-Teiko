# Teiknical-Teiko
Interactive Streamlit dashboard for analyzing immune cell population dynamics in mock clinical trial data, integrating SQLite-backed queries, statistical testing, and visualization.

---

<br>

## Table of Contents

- [Project Overview](#project-overview)
- [How to Run the Project (GitHub Codespaces)](#how-to-run-the-project-github-codespaces)
- [Makefile Targets](#makefile-targets)
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

**Step 1 — Open in GitHub Codespaces**

Click **Code → Codespaces → Create codespace on main** from the repository page.

**Step 2 — Run the following from the terminal**

```bash
make setup
make pipeline
make dashboard
```

GitHub Codespaces will detect the running server and prompt you to open the forwarded port.

---

<br>

## Makefile Targets

The project includes a `Makefile` at the repo root for automated grading and reproducibility.

| Target | Command | Description |
|--------|---------|-------------|
| Setup | `make setup` | Installs all Python dependencies |
| Pipeline | `make pipeline` | Builds the database and generates all output tables and plots |
| Dashboard | `make dashboard` | Starts the Streamlit dashboard on port 8501 |

`make pipeline` runs two steps sequentially:

1. **`files/db_creation.py`** — initializes the SQLite schema and loads `cell-count.csv` into the database (Part 1)
2. **`pipeline.py`** — produces static output files for Parts 2–4 in the `output/` directory:

| File | Contents |
|------|----------|
| `output/part2_frequency_summary.csv` | Relative frequency of each cell population per sample |
| `output/part3_boxplot.png` | Boxplot comparing responders vs non-responders per population |
| `output/part3_statistics.csv` | Mann-Whitney U p-values and group medians per population |
| `output/part4_matching_samples.csv` | All melanoma PBMC miraclib baseline samples |
| `output/part4_samples_by_project.csv` | Sample count per project |
| `output/part4_subjects_by_response.csv` | Subject count by response |
| `output/part4_subjects_by_sex.csv` | Subject count by sex |
| `output/part4_avg_b_cells.txt` | Average B cell count for melanoma male responders at time = 0 |

---

<br>

## Database Schema Design and Scalability

The database uses a normalized relational schema that separates core entities from sample-specific details.

### Schema Overview

#### `projects`

| Column | Type | Description |
|--------|------|-------------|
| `project_id` | TEXT | Unique project identifier (primary key) |


#### `subjects`

| Column | Type | Description |
|--------|------|-------------|
| `subject_id` | TEXT | Unique subject identifier (primary key) |
| `project_id` | TEXT | Project this subject belongs to (foreign key) |
| `treatment_id` | INTEGER | Treatment administered (foreign key; NULL if none) |
| `condition` | TEXT | Disease condition (melanoma, carcinoma, healthy) |
| `age` | INTEGER | Subject age |
| `sex` | TEXT | Subject sex |
| `response` | TEXT | Treatment response (yes/no; NULL if unknown) |


#### `treatments`

| Column | Type | Description |
|--------|------|-------------|
| `treatment_id` | INTEGER | Unique treatment identifier (primary key) |
| `name` | TEXT | Treatment name (e.g. miraclib, phauximab) |


#### `samples`

| Column | Type | Description |
|--------|------|-------------|
| `sample_id` | TEXT | Unique sample identifier (primary key) |
| `subject_id` | TEXT | Subject this sample belongs to (foreign key) |
| `sample_type` | TEXT | Sample type (PBMC, Tumor, Serum, Plasma) |
| `time_from_treatment_start` | REAL | Time relative to treatment start (in days) |


#### `cell_populations`

| Column | Type | Description |
|--------|------|-------------|
| `population_id` | INTEGER | Unique population identifier (primary key) |
| `name` | TEXT | Population name (e.g. b_cell, cd8_t_cell) |


#### `cell_counts`

| Column | Type | Description |
|--------|------|-------------|
| `sample_id` | TEXT | Sample this count belongs to (foreign key) |
| `population_id` | INTEGER | Cell population (foreign key) |
| `count` | INTEGER | Observed cell count (non-negative) |

<br>

### Rationale and Scalability

- **Normalization eliminates redundancy and prevents inconsistency.** Subject metadata (condition, sex, age, response, treatment) is stored once per subject rather than repeated across every sample row. At scale, this matters: with thousands of samples spread across hundreds of projects, a denormalized design would make cohort-level updates error-prone and inflate storage significantly.

- **The four-level hierarchy (project → subject → sample → cell count) mirrors the structure of the data and enables multi-level aggregation.** Analytical questions naturally fall at different levels: comparing response rates across projects, tracking cell populations over time within a subject, or computing per-sample frequencies. The schema supports all of these with simple GROUP BY queries at the appropriate level.

- **Long-format cell count storage keeps analytics flexible.** Each `(sample_id, population_id)` pair occupies its own row rather than spreading populations across columns. This means filtering, grouping, and aggregating by population is uniform regardless of how many populations exist. A wide format would require schema changes and query rewrites every time a new population was added, which breaks at scale.

- **Lookup tables decouple identity from metadata.** Populations, treatments, and projects are each stored in their own table and referenced by ID. New populations, treatment arms, or studies are added by inserting rows which means no columns change and no existing queries break. This allows the schema to absorb new data shapes without migration.

- **Foreign keys enforce referential integrity across the hierarchy.** As data volume grows across many ingestion runs, foreign key constraints ensure that no cell count can reference a sample that doesn't exist, and no sample can reference an unknown subject. This prevents silent data corruption that becomes hard to detect and clean up at scale.

- **Indexing on join and filter columns keeps queries fast at scale.** High-cardinality filter columns \(`subject_id`, `sample_id`, `population_id`, and `time_from_treatment_start`\) are natural index candidates. With thousands of samples and millions of cell count rows, indexed lookups prevent full table scans when filtering by project, condition, timepoint, or population for any analytical query.

---

<br>

## Code Structure Overview

```
Teiknical-Teiko/
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
├── output/               ← generated by make pipeline
├── cell_counts.db        ← created by make pipeline
├── Makefile
├── pipeline.py
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
