"""
Input validation utilities for the review scraper.
"""

import re
from datetime import datetime
from dateutil import parser as date_parser


def validate_company_name(company: str) -> None:
    """Validate company name input."""
    if not company or not company.strip():
        raise ValueError("Company name cannot be empty")
    
    if len(company.strip()) < 2:
        raise ValueError("Company name must be at least 2 characters long")
    
    # Check for potentially problematic characters
    if re.search(r'[<>"\\\\/]', company):
        raise ValueError("Company name contains invalid characters")


def validate_date_string(date_string: str) -> datetime:
    """Validate and parse date string."""
    if not date_string or not date_string.strip():
        raise ValueError("Date cannot be empty")
    
    try:
        # Try to parse the date
        parsed_date = date_parser.parse(date_string)
        
        # Check if date is reasonable (not too far in the past or future)
        current_year = datetime.now().year
        if parsed_date.year < 2000:
            raise ValueError(f"Date year {parsed_date.year} is too far in the past")
        if parsed_date.year > current_year + 1:
            raise ValueError(f"Date year {parsed_date.year} is in the future")
        
        return parsed_date
    
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format '{date_string}': {str(e)}")


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """Validate that the date range is logical."""
    if start_date >= end_date:
        raise ValueError("Start date must be before end date")
    
    # Check if the range is reasonable (not more than 5 years)
    date_diff = end_date - start_date
    if date_diff.days > 1825:  # ~5 years
        raise ValueError("Date range cannot exceed 5 years")


def validate_source(source: str) -> None:
    """Validate source platform."""
    valid_sources = ["g2", "capterra", "trustradius"]
    
    if not source or not source.strip():
        raise ValueError("Source cannot be empty")
    
    if source.lower() not in valid_sources:
        raise ValueError(f"Invalid source '{source}'. Must be one of: {', '.join(valid_sources)}")


def validate_inputs(company: str, start_date_str: str, end_date_str: str, source: str) -> None:
    """Validate all inputs comprehensively."""
    # Validate individual components
    validate_company_name(company)
    validate_source(source)
    
    # Validate and parse dates
    start_date = validate_date_string(start_date_str)
    end_date = validate_date_string(end_date_str)
    
    # Validate date range
    validate_date_range(start_date, end_date)
    
    print("All inputs validated successfully")
