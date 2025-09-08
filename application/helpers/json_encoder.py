import json
from datetime import date, datetime
from decimal import Decimal

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()   # "2025-09-08"
        if isinstance(obj, Decimal):
            return float(obj)        # Convert Decimal -> float
        return super().default(obj)
