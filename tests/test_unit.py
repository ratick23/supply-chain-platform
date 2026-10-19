import pytest
from datetime import datetime

def compute_actual_delay_hours(actual_arrival: str, planned_arrival: str) -> float:
    if not actual_arrival or not planned_arrival:
        return None
    act = datetime.fromisoformat(actual_arrival)
    plan = datetime.fromisoformat(planned_arrival)
    return round((act - plan).total_seconds() / 3600.0, 2)

def compute_on_time_flag(delay_hours: float) -> bool:
    if delay_hours is None:
        return False
    return delay_hours <= 24.0

def standardize_status(raw_status: str) -> str:
    if not raw_status:
        return "UNKNOWN"
    cleaned = raw_status.strip().upper()
    if cleaned in ("DELIVERED", "COMPLETE", "COMPLETED"):
        return "COMPLETED"
    if cleaned == "DELAYED":
        return "DELAYED"
    if cleaned == "CANCELLED":
        return "CANCELLED"
    return "UNKNOWN"

def test_delay_hours_calculation():
    act = "2026-05-10T18:00:00"
    plan = "2026-05-10T06:00:00"
    assert compute_actual_delay_hours(act, plan) == 12.0

def test_on_time_flag_threshold():
    assert compute_on_time_flag(24.0) is True
    assert compute_on_time_flag(24.1) is False
    assert compute_on_time_flag(-5.0) is True
    assert compute_on_time_flag(None) is False

def test_status_standardization():
    assert standardize_status("delivered") == "COMPLETED"
    assert standardize_status("Complete") == "COMPLETED"
    assert standardize_status("DELAYED") == "DELAYED"
    assert standardize_status(None) == "UNKNOWN"
    assert standardize_status("N/A") == "UNKNOWN"

def test_route_key_generation():
    orig, dest = "CNSHA", "NLRTM"
    assert f"{orig}->{dest}" == "CNSHA->NLRTM"