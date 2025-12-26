from datetime import datetime, date

def parse_date(date_str, formats=None):
    """
    Parse a date or datetime string using multiple common formats.

    Args:
        date_str: String or date/datetime representation
        formats: List of date format strings to try (optional)

    Returns:
        date: Parsed date object

    Raises:
        ValueError: If date string cannot be parsed with any format
    """

    # Already a date/datetime object
    if isinstance(date_str, date):
        return date_str if not isinstance(date_str, datetime) else date_str.date()

    if not date_str:
        raise ValueError("Date value is empty or None")

    if formats is None:
        formats = [
            # Date-only formats
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d.%m.%Y',

            # Datetime formats (NEW)
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y/%m/%d %H:%M:%S',
        ]

    date_str = str(date_str).strip()

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"Unable to parse date '{date_str}'. Expected formats include "
        f"YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
    )
