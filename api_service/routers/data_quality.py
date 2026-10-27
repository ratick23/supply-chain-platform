from fastapi import APIRouter, HTTPException
import duckdb
import glob
import os

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])

# Explicitly target the shared volume path inside the Docker container
# Fallback to local relative path if running outside Docker
if os.path.exists("/app/data"):
    log_dir = "/app/data/dq_logs"
else:
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "dq_logs"))

# Allow environment variable override
log_dir = os.getenv("DQ_LOG_DIR", log_dir)

@router.get("/report")
def get_dq_report():
    parquet_pattern = os.path.join(log_dir, "*", "*.parquet")
    files = glob.glob(parquet_pattern)

    if not files:
        raise HTTPException(status_code=404, detail=f"No data quality report found in {log_dir}")

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