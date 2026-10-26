import duckdb
import os
import sys
import argparse
import configparser
from datetime import datetime

import ports_processor
import shipments_processor
import events_processor
import logging

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
DQ_LOG_FILE = os.path.join(LOG_DIR, "data_quality.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [DataQuality]: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DQ_LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger("DataQuality")

def load_config(config_path="settings.config"):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def setup_virtual_tables(conn, config):
    data_dir = config["paths"]["raw_data_dir"]
    files = config["input_files"]
    views = config["views"]

    ports_path = os.path.join(data_dir, files['ports'])
    shipments_path = os.path.join(data_dir, files['shipments'])
    events_path = os.path.join(data_dir, files['events'])

    conn.execute(f"CREATE OR REPLACE VIEW {views['ports']} AS SELECT * FROM read_csv_auto('{ports_path}')")
    conn.execute(f"CREATE OR REPLACE VIEW {views['shipments']} AS SELECT * FROM read_csv_auto('{shipments_path}')")
    conn.execute(f"CREATE OR REPLACE VIEW {views['events']} AS SELECT * FROM read_csv_auto('{events_path}')")

def main():
    parser = argparse.ArgumentParser(description="Run standalone data quality checks using DuckDB.")
    parser.add_argument("--config", default="settings.config", help="Path to configuration file")
    args = parser.parse_args()

    config = load_config(args.config)
    data_dir = config["paths"]["raw_data_dir"]

    conn = duckdb.connect(database=':memory:')

    logger.info(f"Setting up virtual tables reading from: {data_dir}...")
    setup_virtual_tables(conn, config)

    all_issues = []

    logger.info("Executing Ports module...")
    all_issues.extend(
        ports_processor.check_ports(
            conn,
            config["views"]["ports"],
            config["views"]["unlocode"],
            data_dir,
            config["input_files"]["unlocode_pattern"]
        )
    )

    logger.info("Executing Shipments module...")
    all_issues.extend(
        shipments_processor.check_shipments(
            conn,
            config["views"]["shipments"],
            config["views"]["ports"]
        )
    )

    logger.info("Executing Events module...")
    all_issues.extend(
        events_processor.check_events(
            conn,
            config["views"]["events"],
            config["views"]["ports"],
            config["views"]["shipments"]
        )
    )

    # Date-based output folder
    log_base_dir = config["paths"]["log_dir"]
    date_folder = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join(log_base_dir, date_folder)
    os.makedirs(output_dir, exist_ok=True)

    base_filename = config["settings"].get("output_file", "dq_report.parquet")
    if base_filename.endswith(".json"):
        base_filename = base_filename.replace(".json", ".parquet")
    parquet_path = os.path.join(output_dir, base_filename)

    # Create DQ log table and write to Parquet directly inside DuckDB
    run_timestamp = datetime.now().isoformat()
    conn.execute("""
        CREATE OR REPLACE TABLE dq_results (
            run_timestamp VARCHAR,
            check_name VARCHAR,
            rows_affected BIGINT,
            percentage DOUBLE,
            check_type VARCHAR,
            severity VARCHAR,
            action VARCHAR
        )
    """)

    for issue in all_issues:
        conn.execute("""
            INSERT INTO dq_results VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            run_timestamp,
            issue['check_name'],
            issue['rows_affected'],
            issue['percentage'],
            issue['check_type'],
            issue['severity'],
            issue['action']
        ])

    conn.execute(f"COPY dq_results TO '{parquet_path}' (FORMAT PARQUET)")

    logger.info(f"\nData Quality checks finished. Found {len(all_issues)} issues.")
    logger.info(f"Logged directly to Parquet via DuckDB: {parquet_path}")

    # Evaluate Hard vs Soft Checks
    hard_failures = [issue for issue in all_issues if issue.get("check_type") == "hard"]
    if hard_failures:
        logger.info(f"\nCRITICAL: {len(hard_failures)} hard check(s) failed. Halting pipeline execution.")
        sys.exit(1)
    else:
        logger.info("\nSUCCESS: All hard checks passed. Ready for ingestion.")
        sys.exit(0)

if __name__ == "__main__":
    main()