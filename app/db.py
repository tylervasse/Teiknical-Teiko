import sqlite3

import pandas as pd
import streamlit as st

from constants import DB_PATH


@st.cache_resource
def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@st.cache_data(show_spinner=False)
def load_filter_options(db_path: str) -> dict:
    conn = get_conn(db_path)

    def col(sql: str):
        return [r[0] for r in conn.execute(sql).fetchall()]

    return dict(
        projects=col("SELECT project_id FROM projects ORDER BY project_id"),
        conditions=col(
            "SELECT DISTINCT condition FROM subjects WHERE condition IS NOT NULL ORDER BY condition"
        ),
        responses=col(
            "SELECT DISTINCT response FROM subjects WHERE response IS NOT NULL ORDER BY response"
        ),
        treatments=col("SELECT name FROM treatments ORDER BY name"),
        sample_types=col(
            "SELECT DISTINCT sample_type FROM samples WHERE sample_type IS NOT NULL ORDER BY sample_type"
        ),
        times=col(
            "SELECT DISTINCT time_from_treatment_start FROM samples "
            "WHERE time_from_treatment_start IS NOT NULL ORDER BY CAST(time_from_treatment_start AS INTEGER)"
        ),
    )


@st.cache_data(show_spinner=False)
def query_part2_frequencies(
    db_path: str,
    project: str | None,
    condition: str | None,
    response: str | None,
    treatment: str | None,
    sample_type: str | None,
) -> pd.DataFrame:
    where, params = [], []
    if project:
        where.append("p.project_id = ?")
        params.append(project)
    if condition:
        where.append("sub.condition = ?")
        params.append(condition)
    if response:
        where.append("sub.response = ?")
        params.append(response)
    if treatment:
        where.append("t.name = ?")
        params.append(treatment)
    if sample_type:
        where.append("sa.sample_type = ?")
        params.append(sample_type)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    WITH filtered_counts AS (
        SELECT
            sa.sample_id AS sample,
            cp.name AS population,
            cc.count AS count
        FROM cell_counts cc
        JOIN samples sa ON sa.sample_id = cc.sample_id
        JOIN subjects sub ON sub.subject_id = sa.subject_id
        JOIN projects p ON p.project_id = sub.project_id
        LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
        JOIN cell_populations cp ON cp.population_id = cc.population_id
        {where_sql}
    ),
    sample_totals AS (
        SELECT sample, SUM(count) AS total_count
        FROM filtered_counts
        GROUP BY sample
    )
    SELECT
        fc.sample AS sample,
        st.total_count AS total_count,
        fc.population AS population,
        fc.count AS count,
        CASE
            WHEN st.total_count > 0 THEN 100.0 * fc.count / st.total_count
            ELSE NULL
        END AS percentage
    FROM filtered_counts fc
    JOIN sample_totals st ON st.sample = fc.sample
    ORDER BY fc.sample, fc.population;
    """
    return pd.read_sql_query(sql, get_conn(db_path), params=params)


@st.cache_data(show_spinner=False)
def query_part3_frequencies(
    db_path: str,
    project: str | None,
    condition: str | None,
    response: str | None,
    treatment: str | None,
    sample_type: str | None,
    time_from_start: tuple[int, ...] | None = None,
) -> pd.DataFrame:
    """Returns: sample | subject | response | total_count | population | count | percentage"""
    conn = get_conn(db_path)

    where, params = [], []
    if project:
        where.append("p.project_id = ?")
        params.append(project)
    if condition:
        where.append("sub.condition = ?")
        params.append(condition)
    if response:
        where.append("sub.response = ?")
        params.append(response)
    if treatment:
        where.append("t.name = ?")
        params.append(treatment)
    if sample_type:
        where.append("sa.sample_type = ?")
        params.append(sample_type)
    if time_from_start:
        placeholders = ",".join("?" * len(time_from_start))
        where.append(f"sa.time_from_treatment_start IN ({placeholders})")
        params.extend(time_from_start)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    WITH filtered_counts AS (
        SELECT
            sa.sample_id AS sample,
            sub.subject_id AS subject,
            LOWER(COALESCE(sub.response,'')) AS response,
            cp.name AS population,
            cc.count AS count
        FROM cell_counts cc
        JOIN samples sa ON sa.sample_id = cc.sample_id
        JOIN subjects sub ON sub.subject_id = sa.subject_id
        JOIN projects p ON p.project_id = sub.project_id
        LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
        JOIN cell_populations cp ON cp.population_id = cc.population_id
        {where_sql}
    ),
    sample_totals AS (
        SELECT sample, SUM(count) AS total_count
        FROM filtered_counts
        GROUP BY sample
    )
    SELECT
        fc.sample AS sample,
        fc.subject AS subject,
        fc.response AS response,
        st.total_count AS total_count,
        fc.population AS population,
        fc.count AS count,
        CASE
            WHEN st.total_count > 0 THEN (100.0 * fc.count / st.total_count)
            ELSE NULL
        END AS percentage
    FROM filtered_counts fc
    JOIN sample_totals st ON st.sample = fc.sample
    ORDER BY fc.population, fc.sample;
    """
    return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(show_spinner=False)
def query_part4_samples(
    db_path: str,
    condition: str,
    sample_type: str,
    treatment: str | None,
    time_from_start: int | None,
) -> pd.DataFrame:
    """
    Returns one row per (sample, population):
    project_id | subject_id | condition | sex | response | treatment | sample |
    sample_type | time_from_treatment_start | population | count
    """
    conn = get_conn(db_path)

    where = [
        "LOWER(sub.condition) = LOWER(?)",
        "LOWER(sa.sample_type) = LOWER(?)",
    ]
    params: list = [condition, sample_type]

    if treatment:
        where.append("LOWER(t.name) = LOWER(?)")
        params.append(treatment)

    if time_from_start is not None:
        where.append("sa.time_from_treatment_start = ?")
        params.append(int(time_from_start))

    where_sql = "WHERE " + " AND ".join(where)

    sql = f"""
    SELECT
        p.project_id AS project_id,
        sub.subject_id AS subject_id,
        sub.condition AS condition,
        sub.sex AS sex,
        LOWER(COALESCE(sub.response,'')) AS response,
        COALESCE(t.name,'') AS treatment,
        sa.sample_id AS sample,
        sa.sample_type AS sample_type,
        sa.time_from_treatment_start AS time_from_treatment_start,
        cp.name AS population,
        cc.count AS count
    FROM cell_counts cc
    JOIN samples sa ON sa.sample_id = cc.sample_id
    JOIN subjects sub ON sub.subject_id = sa.subject_id
    JOIN projects p ON p.project_id = sub.project_id
    LEFT JOIN treatments t ON t.treatment_id = sub.treatment_id
    JOIN cell_populations cp ON cp.population_id = cc.population_id
    {where_sql}
    ORDER BY p.project_id, sub.subject_id, sa.sample_id, cp.name;
    """
    return pd.read_sql_query(sql, conn, params=params)


def norm(v: str) -> str | None:
    return None if v == "(All)" else v
