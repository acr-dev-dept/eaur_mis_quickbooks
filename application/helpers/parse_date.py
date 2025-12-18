from datetime import datetime

def parse_date(date_str, formats=None):
    """
    Parse a date string using multiple common date formats.
    
    Args:
        date_str: String representation of a date
        formats: List of date format strings to try (optional)
        
    Returns:
        date: Parsed date object
        
    Raises:
        ValueError: If date string cannot be parsed with any format
    """
    if formats is None:
        formats = [
            '%Y-%m-%d',      # 2025-01-06
            '%Y/%m/%d',      # 2025/01/06
            '%Y.%m.%d',      # 2025.01.06
            '%d-%m-%Y',      # 06-01-2025
            '%d/%m/%Y',      # 06/01/2025
            '%m/%d/%Y',      # 01/06/2025 (US format)
            '%d.%m.%Y',      # 06.01.2025
        ]
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date '{date_str}'. Expected formats: YYYY-MM-DD, YYYY/MM/DD, etc.")