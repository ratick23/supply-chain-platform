import json
import os
from datetime import datetime

LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "assistant_audit.log")

def log_interaction(prompt_sent: str, tools_called: list, tool_responses: list, final_output: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "genai_assistant",
        "prompt_sent": prompt_sent,
        "tools_called": tools_called,
        "tool_responses": tool_responses,
        "final_output": final_output
    }
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")