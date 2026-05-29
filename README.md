# Teiko Teiknical
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

The goal of this project is to analyze immune cell population data from clinical samples and present the results through an interactive dashboard. The workflow mirrors a real-world analytical pipeline.

---

<br>

## How to Run the Project (GitHub Codespaces)

**Step 1 - Open in GitHub Codespaces**

Click **Code → Codespaces → Create codespace on main** from the repository page.

**Step 2 - Run the following from the terminal**

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

1. **`load_data.py`** - initializes the SQLite schema and loads `cell-count.csv` into the database (Part 1)
2. **`pipeline.py`** - produces static output files for Parts 2–4 in the `output/` directory:

| File | Contents |
|------|----------|
| `output/part2_frequency_summary.csv` | Relative frequency of each cell population per sample |
| `output/part3_boxplot.png` | Boxplot comparing responders vs non-responders per population |
| `output/part3_statistics.csv` | LMEM p-values and group medians per population |
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

- **Normalization eliminates redundancy and prevents inconsistency.** Subject metadata (condition, sex, age, response, treatment) is stored once per subject rather than repeated across every sample row. At scale, with thousands of samples spread across hundreds of projects, a denormalized design would make cohort-level updates error-prone and inflate storage significantly. The four-level hierarchy (project → subject → sample → cell count) maps naturally to how analytical questions are asked: response rates at the project level, longitudinal trends at the subject level, population frequencies at the sample level. Each are addressable with a simple GROUP BY at the appropriate level.

- **Long-format cell count storage and lookup tables absorb new data without migration.** Each `(sample_id, population_id)` pair occupies its own row rather than spreading populations across columns, so filtering, grouping, and aggregating by population is uniform regardless of how many populations exist. Adding new populations, treatments, or projects is a row insert and no columns change and no existing queries break.

- **Foreign keys and indexes maintain correctness and performance at scale.** Referential integrity constraints ensure no cell count can reference a sample that doesn't exist and no sample can reference an unknown subject, preventing silent data corruption across many ingestion runs. Indexes on `subject_id`, `sample_id`, `population_id`, and `time_from_treatment_start` prevent full table scans when filtering by project, condition, timepoint, or population as rows scale into the millions.

### Analytics This Schema Supports

- **Linear mixed-effects modelling (LMEM)** - model population frequencies as the outcome with response as a fixed effect and subject as a random effect, correctly accounting for repeated measures across timepoints as the number of subjects and visits grows
- **Mann-Whitney U / Wilcoxon rank-sum** - non-parametric comparison of population frequencies between responders and non-responders at a single timepoint (e.g. baseline), with no normality assumption
- **Logistic regression** - predict binary treatment response from baseline cell population frequencies, with sex, age, and condition as covariates, joinable directly from the subjects table
- **Delta analysis** - compute the change in each cell population frequency from baseline (time = 0) to a later timepoint for each subject, then compare those deltas between responders and non-responders; this characterises what an immunological response looks like over the course of treatment without requiring an explicit response onset timepoint, since the `response` label in the dataset is a clinical endpoint that may lag behind the underlying immune changes
- **Spearman correlation** - pivot cell counts into a wide per-sample matrix and compute rank-based correlations between populations to identify co-varying immune phenotypes (e.g. whether high CD8 T cell frequency is consistently associated with low B cell frequency across samples); PCA is not used here as there is no meaningful dimensionality to reduce with only five populations, but would scale naturally if a broader immune panel were captured

---

<br>

## Code Structure Overview

```
Teiknical-Teiko/
├── app/
│   ├── pages/
│   │   ├── part2.py
│   │   ├── part3.py
│   │   └── part4.py
│   ├── components.py
│   ├── constants.py
│   ├── db.py
│   ├── db_creation.py
│   ├── streamlit_dashboard.py
│   └── tables.py
├── cell-count.csv
├── cell_counts.db        ← generated by make pipeline
├── output/               ← generated by make pipeline
├── load_data.py
├── Makefile
├── pipeline.py
├── requirements.txt
└── README.md
```


<br>

#### Root

| File | Description |
|------|-------------|
| `load_data.py` | Entry point for Part 1 - initializes the SQLite schema and loads `cell-count.csv` into the database |
| `pipeline.py` | Generates all static output files for Parts 2–4 (frequency CSV, boxplot PNG, statistics CSV, subset CSVs) |
| `cell-count.csv` | Raw input data containing cell counts and sample metadata |
| `Makefile` | Defines the three graded targets: `setup`, `pipeline`, and `dashboard` |
| `requirements.txt` | Python dependencies installed by `make setup` |

#### `app/`

| File | Description |
|------|-------------|
| `streamlit_dashboard.py` | Main entry point - defines section list, handles sidebar navigation, and injects global CSS |
| `db_creation.py` | Defines the SQLite schema, validates the CSV, and loads normalized data into the database; maps `"none"` treatment to `NULL` |
| `db.py` | All database access logic - cached connection via `@st.cache_resource`, cached query results via `@st.cache_data`, with flexible filtering by project, condition, treatment, sample type, and timepoint |
| `tables.py` | HTML table renderers using `st.iframe` for the sortable red-header tables used across all three pages |
| `constants.py` | Shared constants - column definitions, population order and labels, and the database path |
| `pages/part2.py` | Overview page - frequency table with sidebar filters, stacked bar chart, and CSV export |
| `pages/part3.py` | Response comparison page - Plotly boxplots and LMEM / Mann-Whitney U significance testing |
| `pages/part4.py` | Subset analysis page - filtered sample table, summary breakdowns, and average B cell count |

### Design Rationale

The `app/` directory separates the dashboard logic from the pipeline scripts at the root, keeping the two concerns independent - `load_data.py` and `pipeline.py` can be run headlessly by the grader without touching any Streamlit code. Within `app/`, database access is isolated in `db.py` so that all caching, connection management, and query logic lives in one place and pages never open their own connections. Each page is a single render function in its own file, which makes the sections independently readable and testable. Shared state (constants and table renderers) is extracted into `constants.py` and `tables.py` to avoid duplication across the three pages.

---

<br>

## Dashboard Features

The dashboard contains three sections navigable using the ◀ ▶ arrows in the sidebar.

### Overview (Part 2)

- Interactive frequency table showing relative frequency (%) of each cell population per sample, with sortable columns, full-precision percentages, and a scrollable view
- Sidebar filters for project, condition, response, treatment, sample type, and sample name search with range input (e.g. `s001-s050`)
- CSV export of the filtered view

### Response Group Comparison (Part 3)

- Side-by-side boxplots (responders vs non-responders) per cell population with IQR whiskers and jittered point overlay
- Statistical test selected automatically: **LMEM** (subject as random effect) for multiple timepoints (models within-subject correlation across repeated measures) and **Mann-Whitney U** for a single timepoint
- Results table sorted by p-value with significant populations highlighted in a summary banner

### Subset Analysis (Part 4)

- Filterable sample table (condition, sample type, treatment, timepoint) with summary breakdowns by project, response, and sex
- Average B cell count for melanoma male responders at time = 0 with expandable contributing rows

---

<br>

## Link to the Dashboard

The dashboard is publicly hosted on Streamlit Community Cloud and can be accessed at:

**[https://teiknical-tyler.streamlit.app/](https://teiknical-tyler.streamlit.app/)**
