from pydantic import BaseModel, Field
from typing import Optional, List

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str

class ShipmentDetail(BaseModel):
    shipment_id: str
    customer_id: Optional[str] = None
    vessel_id: Optional[str] = None
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    status: Optional[str] = None
    actual_delay_hours: Optional[float] = None
    on_time_flag: Optional[bool] = None

class PaginatedShipmentsResponse(BaseModel):
    page: int
    page_size: int
    total_count: int
    data: List[ShipmentDetail]

class RouteStatsResponse(BaseModel):
    route_key: str
    origin_port: str
    destination_port: str
    shipment_count: int
    average_delay_hours: Optional[float] = None
    on_time_rate_pct: Optional[float] = None

class DelayPredictionRequest(BaseModel):
    shipment_id: str
    origin_port: str
    destination_port: str
    cargo_type: str = "DRY"
    weight_tons: float = Field(gt=0, description="Weight in tons")
    container_count: int = Field(gt=0, description="Number of containers")

class DelayPredictionResponse(BaseModel):
    shipment_id: str
    predicted_delayed: bool
    delay_risk_score: float
    model_version: str