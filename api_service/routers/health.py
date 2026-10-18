from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def health_check(conn = Depends(get_db)):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return HealthResponse(status="healthy", version="1.0.0", database="connected")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")