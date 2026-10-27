import requests
from typing import Optional, Dict, Any
from langchain_core.tools import tool
import configparser
import os
import requests

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "settings.config"))
BASE_URL = config.get("api", "base_url", fallback="http://localhost:8000")

@tool
def query_shipments(origin: Optional[str] = None, destination: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """
    Query shipments from the curated data product with optional filters.
    Use this when the user asks to find, list, or check shipments matching origin, destination, or status.
    """
    params = {"page": page, "page_size": page_size}
    if origin:
        params["origin"] = origin
    if destination:
        params["destination"] = destination
    if status:
        params["status"] = status.upper()

    try:
        resp = requests.get(f"{BASE_URL}/shipments", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch shipments: {str(e)}"}

@tool
def get_route_stats(origin: str, destination: str) -> Dict[str, Any]:
    """
    Get aggregated route metrics: average delay hours, on-time rate percentage, and total shipment count.
    Use this when the user asks about general performance or historical statistics between two ports.
    """
    url = f"{BASE_URL}/routes/{origin.upper()}/{destination.upper()}/stats"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return {"error": f"No statistics found for route {origin}->{destination}"}
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch route stats: {str(e)}"}

@tool
def predict_delay(shipment_id: str) -> Dict[str, Any]:
    """
    Calls the predictive ML delay risk endpoint for a specific shipment ID.
    Returns delay probability, classification (delayed true/false), and model metadata.
    """
    # 1. Fetch shipment metadata first from the API
    try:
        ship_resp = requests.get(f"{BASE_URL}/shipments/{shipment_id}", timeout=10)
        if ship_resp.status_code == 404:
            return {"error": f"Shipment '{shipment_id}' does not exist in master records."}
        ship_resp.raise_for_status()
        shipment = ship_resp.json()

        # 2. Call predict-delay endpoint
        payload = {
            "shipment_id": shipment["shipment_id"],
            "origin_port": shipment.get("origin_port") or "UNKNOWN",
            "destination_port": shipment.get("destination_port") or "UNKNOWN",
            "cargo_type": "DRY",
            "weight_tons": 25.0,  # Default fallback if weight is missing from lookup
            "container_count": 5
        }
        pred_resp = requests.post(f"{BASE_URL}/predict-delay", json=payload, timeout=10)
        pred_resp.raise_for_status()
        return pred_resp.json()
    except requests.RequestException as e:
        return {"error": f"Failed to predict delay for {shipment_id}: {str(e)}"}



@tool
def get_data_quality_report() -> dict:
    """
    Fetches the latest data quality check report, inspection logs, 
    and issues found during ingestion from the backend API service.
    """
    try:
        response = requests.get("http://localhost:8000/data-quality/report")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to retrieve data quality report: {str(e)}"}