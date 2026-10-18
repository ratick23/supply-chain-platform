from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models import RouteStatsResponse

router = APIRouter(prefix="/routes", tags=["Routes"])

@router.get("/{origin}/{destination}/stats", response_model=RouteStatsResponse)
def get_route_stats(origin: str, destination: str, conn = Depends(get_db)):
    route_key = f"{origin.upper()}->{destination.upper()}"
    cursor = conn.cursor()

    query = """
        SELECT 
            frs.route_key,
            dp_orig.port_code AS origin_port,
            dp_dest.port_code AS destination_port,
            frs.shipment_count,
            frs.average_delay_hours,
            frs.on_time_rate_pct
        FROM fact_route_stats frs
        JOIN dim_port dp_orig ON frs.origin_port_sk = dp_orig.port_sk
        JOIN dim_port dp_dest ON frs.destination_port_sk = dp_dest.port_sk
        WHERE frs.route_key = %s;
    """
    cursor.execute(query, (route_key,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        raise HTTPException(
            status_code=404, 
            detail=f"No route statistics found for route '{route_key}'"
        )

    return RouteStatsResponse(
        route_key=row[0],
        origin_port=row[1],
        destination_port=row[2],
        shipment_count=row[3],
        average_delay_hours=float(row[4]) if row[4] is not None else None,
        on_time_rate_pct=float(row[5]) if row[5] is not None else None
    )