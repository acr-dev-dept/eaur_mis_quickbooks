
import json
import logging
import datetime
logger = logging.getLogger(__name__)

def safe_stringify(value, field_name=""):
    """
    Convert values to a JSON-safe string.
    - datetime/date → ISO format
    - dict/list → JSON string
    - None → empty string
    - other types → str()
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    elif isinstance(value, dict):
        if field_name == "Intake":  # special case
            month = value.get("intake_month")
            start = value.get("intake_start")
            year = start.year if isinstance(start, datetime.date) else ""
            return f"{month} {year}".strip()
        return json.dumps(value, default=str)  # fallback
    elif isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif value is None:
        return ""
    return str(value)