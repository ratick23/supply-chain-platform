from fastapi import APIRouter, HTTPException
import duckdb
import glob
import os
import configparser

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "..", "settings.config"))
log_dir = config["paths"]["dq_log_dir"]

@router.get("/report")
def get_dq_report():
    parquet_pattern = os.path.join(log_dir, "*", "*.parquet")
    files = glob.glob(parquet_pattern)

    if not files:
        raise HTTPException(status_code=404, detail="No data quality report found on disk")

    latest_file = max(files, key=os.path.getmtime)
    
    conn = duckdb.connect(database=":memory:")
    query = f"SELECT * FROM read_parquet('{latest_file}')"
    records = conn.execute(query).fetchall()
    columns = [desc[0] for desc in conn.description]
    
    result = [dict(zip(columns, row)) for row in records]
    return {
        "report_file": os.path.basename(latest_file),
        "total_checks": len(result),
        "issues": result
    }