import re
from typing import Optional, Tuple
from assistant.prompts import GUARDRAIL_REFUSAL_MESSAGE, TOOL_BUDGET_EXCEEDED_MESSAGE

# Comprehensive conceptual supply chain & maritime logistics vocabulary
ALLOWED_TOPIC_KEYWORDS = {
    # Core entities & assets
    "shipment", "shipments", "shp-", "cargo", "container", "containers", 
    "vessel", "vessels", "ship", "ships", "fleet", "booking", "bookings",
    
    # Geography & infrastructure
    "port", "ports", "harbor", "terminal", "origin", "destination", 
    "route", "routes", "lane", "lanes", "region", "timezone", "country",
    
    # Operational metrics & status
    "delay", "delayed", "delays", "on-time", "ontime", "punctuality", 
    "congestion", "score", "status", "eta", "transit", "duration", 
    "weight", "tons", "count", "stats", "statistics", "performance",
    
    # Data & auditing intent
    "quality", "audit", "report", "check", "checks", "risk", "risks", 
    "probability", "predict", "prediction", "analysis", "metrics",
    
    # Query actions
    "list", "find", "show", "query", "search", "track", "history"
}

def is_domain_allowed(query: str) -> bool:
    """
    Refuses off-domain queries by checking for conceptual supply chain 
    and logistics terminology rather than hardcoded city names.
    """
    normalized = query.lower()
    
    # Tokenize query into words and alphanumeric fragments (handling IDs like SHP-00123)
    tokens = set(re.findall(r"\b[a-z0-9\-]+\b", normalized))
    
    # Check if any token matches our conceptual vocabulary or contains an ID prefix like 'shp-'
    for token in tokens:
        if token in ALLOWED_TOPIC_KEYWORDS or token.startswith("shp-"):
            return True
            
    # Also check for multi-word conceptual phrases if needed
    for keyword in ALLOWED_TOPIC_KEYWORDS:
        if keyword in normalized:
            return True
            
    return False

def check_guardrails(query: str, current_tool_calls: int, max_budget: int = 4) -> Tuple[bool, Optional[str]]:
    """
    Evaluates session guardrails:
    1. Domain relevance check.
    2. Tool call recursion budget check.
    """
    if not is_domain_allowed(query):
        return False, GUARDRAIL_REFUSAL_MESSAGE
    if current_tool_calls >= max_budget:
        return False, TOOL_BUDGET_EXCEEDED_MESSAGE
    return True, None