# Supply Chain Intelligence Mini-Platform

## 1. Project Overview
This repository contains a lightweight, end-to-end Supply Chain Intelligence platform designed to ingest raw shipment data, ensure data integrity, and serve analytical insights via a REST API and a Generative AI assistant. 

The architecture is deliberately modular, divided into three decoupled stages:
1. **Data Quality (Pre-Ingestion):** A standalone engine that evaluates raw files and prevents corrupt data from entering the system.
2. **Data Pipeline (ETL):** Transforms raw CSVs into curated, queryable Parquet files (Bronze -> Silver -> Gold).
3. **Serving & AI:** A FastAPI backend that exposes shipment tracking, route statistics, ML-driven delay predictions, and a LangChain-powered LLM assistant.

---

## 2. Data Quality Engine: Design & Tradeoffs

The assignment required a standalone data quality module that evaluates raw CSVs *before* any data enters a database. To solve this, I implemented a Quality Engine** using Python and DuckDB.

## Code Architecture & Modularity
To ensure the codebase remains maintainable and extensible, the Data Quality module follows a domain-driven design pattern, strictly separating configuration, orchestration, and business logic:

settings.config (Centralized Configuration): Completely eliminates hardcoded file paths and view names. It allows the pipeline to easily adapt to different environments (e.g., local testing vs. Docker paths) without altering the Python code.

dq_check.py (The Orchestrator): Acts as the main entry point. It parses the configuration, initializes the in-memory DuckDB instance, creates the virtual views over the raw CSVs, and loops through the domain processors. Finally, it aggregates the issues, exports the .parquet log, and executes the system exit logic based on Hard vs. Soft failures.

Domain Processors (ports_processor.py, shipments_processor.py, events_processor.py): Each dataset has a dedicated processor file encapsulating its specific SQL rules, foreign key constraints, and dynamic reference checks (like the UN/LOCODE cross-referencing). This separation of concerns means adding new checks—or entirely new data sources—is trivial and won't bloat a single monolithic file.

### Why DuckDB?
* **Zero-Ingestion SQL:** DuckDB’s `read_csv_auto()` function allows us to map raw CSV files to virtual views and execute complex relational SQL queries (like cross-file foreign key joins) entirely in-memory. This perfectly satisfies the constraint of evaluating data *without* physical ingestion.
* **No Infrastructure Overhead:** Unlike PostgreSQL, DuckDB requires no dedicated server container, port mapping, or volume initialization, allowing the pipeline to spin up instantly in CI/CD environments.
* **Native Parquet Export:** DuckDB natively exports the audit logs to Parquet format, seamlessly bridging the gap between local execution and production data lake architectures.

### The "Hard vs. Soft" Check Architecture
To ensure pipeline resilience, the rules are categorized by severity:
* **Hard Checks (Critical):** Identify fatal data corruption (e.g., conflicting duplicate IDs, invalid foreign keys mapping shipments to non-existent ports, or UN/LOCODE reference mismatches). **Action:** The script safely halts with an exit code of `1` to prevent poisoning downstream storage.
* **Soft Checks (Warnings):** Identify dirty but recoverable data (e.g., negative weights, casing inconsistencies, missing countries). **Action:** The script logs the anomaly and passes, allowing the downstream ETL pipeline to automatically clean, impute, or drop the specific rows in the Silver layer.

Scaling to Production: What Happens When Data Grows?
While DuckDB is exceptionally fast for local, in-memory processing of gigabyte-scale data, a true production environment handling millions of global shipment records per day requires a distributed approach.

**If the files grow too large for a single machine's memory:**
1. **Compute Shift:** I would migrate the DuckDB SQL logic to **PySpark** running on a distributed cluster (e.g., Databricks or AWS EMR). PySpark can execute the exact same rule-based logic in parallel across hundreds of worker nodes.
2. **Storage Shift:** Instead of reading flat CSVs from a local disk, the pipeline would read from an **Amazon S3** landing zone. 
3. **Log Centralization:** Instead of saving the Parquet DQ logs locally, they would be written to a dedicated `s3://data-quality-logs/` bucket partitioned by `year/month/day`, allowing tools like Amazon Athena to query historical data quality trends over time.


###  Running the Data Quality Module
You can run the Data Quality engine either directly on your local machine or isolated within a Docker container. In both cases, the resulting Parquet logs will be saved to the data/dq_logs/YYYY-MM-DD/ directory.

**Option A: Running Locally (Python)**
Ensure you have Python 3.11+ installed and your virtual environment activated.

Install Dependencies:

Bash
pip install -r requirements.txt
Execute the Script:
Navigate to the module's directory and run the orchestrator. It will automatically read the settings.config file in that folder.

Bash
cd Data_engineering/Data_quality
python dq_check.py

**Option B: Running via Docker (Recommended)**
Running via Docker guarantees a clean environment and strictly tests the containerization requirement. The docker-compose.yml mounts your local raw_file and data directories so the outputs persist on your host machine.

Execute the Container:
Run the following command from the root of your project (where docker-compose.yml is located):

Bash
docker compose up --build dq-check
Reviewing Logs:
The container will stream the pipeline execution steps to your terminal. Once the checks finish (and either pass or halt due to hard failures), the container will cleanly exit. You can view previous execution logs using:

Bash
docker compose logs dq-check