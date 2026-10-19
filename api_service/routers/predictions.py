import os
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from api_service.models import DelayPredictionRequest, DelayPredictionResponse

router = APIRouter(tags=["Predictions"])

MODEL_PATH = os.getenv("MODEL_PATH", "ml_models/delay_model.joblib")
model_pipeline = None

def get_model():
    global model_pipeline
    if model_pipeline is None:
        if os.path.exists(MODEL_PATH):
            model_pipeline = joblib.load(MODEL_PATH)
        else:
            raise RuntimeError(f"Model artifact not found at {MODEL_PATH}")
    return model_pipeline

@router.post("/predict-delay", response_model=DelayPredictionResponse)
def predict_delay_endpoint(payload: DelayPredictionRequest):
    try:
        clf = get_model()
    except Exception as err:
        raise HTTPException(status_code=503, detail=f"ML runtime unavailable: {err}")

    # Build input features strictly available at booking time[cite: 4]
    input_data = pd.DataFrame([{
        "origin_port": payload.origin_port.upper(),
        "destination_port": payload.destination_port.upper(),
        "cargo_type": payload.cargo_type.upper(),
        "weight_tons": payload.weight_tons,
        "container_count": payload.container_count,
        "planned_transit_days": 14.0,  # Benchmark average for new bookings
        "booking_lead_days": 7.0,
        "origin_congestion": 0.5,
        "dest_congestion": 0.5
    }])

    prob = float(clf.predict_proba(input_data)[0, 1])
    is_delayed = bool(prob >= 0.50)

    return DelayPredictionResponse(
        shipment_id=payload.shipment_id,
        predicted_delayed=is_delayed,
        delay_risk_score=round(prob, 4),
        model_version="logistic-regression-v1"
    )