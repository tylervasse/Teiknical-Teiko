#!/usr/bin/env nextflow

nextflow.enable.dsl=2

/*
 * Step 1 — Build the SQLite database from cell-count.csv (Part 1)
 */
process LOAD_DATA {
    output:
    val true

    script:
    """
    cd ${projectDir}
    python load_data.py
    """
}

/*
 * Step 2 — Generate static output tables and plots (Parts 2–4)
 */
process GENERATE_OUTPUTS {
    input:
    val ready

    script:
    """
    cd ${projectDir}
    python pipeline.py
    """
}

workflow {
    LOAD_DATA()
    GENERATE_OUTPUTS(LOAD_DATA.out)
}
