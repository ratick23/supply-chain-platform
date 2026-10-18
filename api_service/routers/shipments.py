from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from database import get_db
from models import ShipmentDetail, PaginatedShipmentsResponse

router = APIRouter(prefix="/shipments", tags=["Shipments"])

@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment_by_id(shipment_id: str, conn = Depends(get_db)):
    cursor = conn.cursor()
    query = """
        SELECT 
            fs.shipment_id, dc.customer_id, dv.vessel_id,
            dp_orig.port_code AS origin_port,
            dp_dest.port_code AS destination_port,
            fs.status, fs.actual_delay_hours, fs.on_time_flag
        FROM fact_shipment fs
        LEFT JOIN dim_customer dc ON fs.customer_sk = dc.customer_sk
        LEFT JOIN dim_vessel dv ON fs.vessel_sk = dv.vessel_sk
        LEFT JOIN dim_port dp_orig ON fs.origin_port_sk = dp_orig.port_sk
        LEFT JOIN dim_port dp_dest ON fs.destination_port_sk = dp_dest.port_sk
        WHERE fs.shipment_id = %s;
    """
    cursor.execute(query, (shipment_id,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")

    return ShipmentDetail(
        shipment_id=row[0],
        customer_id=row[1],
        vessel_id=row[2],
        origin_port=row[3],
        destination_port=row[4],
        status=row[5],
        actual_delay_hours=float(row[6]) if row[6] is not None else None,
        on_time_flag=row[7]
    )

@router.get("", response_model=PaginatedShipmentsResponse)
def list_shipments(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    conn = Depends(get_db)
):
    offset = (page - 1) * page_size
    cursor = conn.cursor()

    conditions = []
    params = []

    if origin:
        conditions.append("dp_orig.port_code = %s")
        params.append(origin)
    if destination:
        conditions.append("dp_dest.port_code = %s")
        params.append(destination)
    if status:
        conditions.append("fs.status = %s")
        params.append(status.upper())

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Count total matching rows
    count_query = f"""
        SELECT COUNT(*)
        FROM fact_shipment fs
        LEFT JOIN dim_port dp_orig ON fs.origin_port_sk = dp_orig.port_sk
        LEFT JOIN dim_port dp_dest ON fs.destination_port_sk = dp_dest.port_sk
        {where_clause};
    """
    cursor.execute(count_query, tuple(params))
    total_count = cursor.fetchone()[0]

    # Fetch paginated rows
    data_query = f"""
        SELECT 
            fs.shipment_id, dc.customer_id, dv.vessel_id,
            dp_orig.port_code AS origin_port,
            dp_dest.port_code AS destination_port,
            fs.status, fs.actual_delay_hours, fs.on_time_flag
        FROM fact_shipment fs
        LEFT JOIN dim_customer dc ON fs.customer_sk = dc.customer_sk
        LEFT JOIN dim_vessel dv ON fs.vessel_sk = dv.vessel_sk
        LEFT JOIN dim_port dp_orig ON fs.origin_port_sk = dp_orig.port_sk
        LEFT JOIN dim_port dp_dest ON fs.destination_port_sk = dp_dest.port_sk
        {where_clause}
        ORDER BY fs.shipment_id
        LIMIT %s OFFSET %s;
    """
    cursor.execute(data_query, tuple(params + [page_size, offset]))
    rows = cursor.fetchall()
    cursor.close()

    items = [
        ShipmentDetail(
            shipment_id=r[0],
            customer_id=r[1],
            vessel_id=r[2],
            origin_port=r[3],
            destination_port=r[4],
            status=r[5],
            actual_delay_hours=float(r[6]) if r[6] is not None else None,
            on_time_flag=r[7]
        )
        for r in rows
    ]

    return PaginatedShipmentsResponse(
        page=page,
        page_size=page_size,
        total_count=total_count,
        data=items
    )