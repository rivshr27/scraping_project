"""
Date utility functions for the review scraper.
"""

from datetime import datetime
from dateutil import parser as date_parser


def parse_date_string(date_string: str) -> datetime:
    """Parse a date string into a datetime object."""
    try:
        return date_parser.parse(date_string)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Could not parse date '{date_string}': {str(e)}")


def format_date_for_url(date_obj: datetime) -> str:
    """Format datetime object for URL parameters."""
    return date_obj.strftime("%Y-%m-%d")


def parse_review_date(date_string: str) -> str:
    """Parse various date formats found in reviews and return ISO format."""
    if not date_string:
        return ""
    
    # Common date formats found on review sites
    formats_to_try = [
        "%B %d, %Y",      # January 1, 2023
        "%b %d, %Y",      # Jan 1, 2023
        "%m/%d/%Y",       # 01/01/2023
        "%Y-%m-%d",       # 2023-01-01
        "%d/%m/%Y",       # 01/01/2023 (European)
        "%B %Y",          # January 2023
        "%b %Y",          # Jan 2023
    ]
    
    # Clean the date string
    date_string = date_string.strip()
    
    # Try each format
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_string, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # If all formats fail, try dateutil parser as fallback
    try:
        parsed_date = date_parser.parse(date_string)
        return parsed_date.strftime("%Y-%m-%d")
    except:
        # Return original string if all parsing fails
        return date_string


def is_date_in_range(review_date_str: str, start_date: datetime, end_date: datetime) -> bool:
    """Check if a review date falls within the specified range."""
    try:
        review_date = date_parser.parse(review_date_str)
        return start_date <= review_date <= end_date
    except:
        # If we can't parse the date, include it (better to have false positives)
        return True
