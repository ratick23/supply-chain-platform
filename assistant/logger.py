import json
import os
from datetime import datetime
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "settings.config"))
LOG_FILE = config.get("paths", "log_file", fallback="assistant_audit.log")

def log_interaction(prompt_sent: str, tools_called: list, tool_responses: list, final_output: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt_sent": prompt_sent,
        "tools_called": tools_called,
        "tool_responses": tool_responses,
        "final_output": final_output
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")