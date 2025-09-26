#!/usr/bin/env python3
"""
Product Review Scraper

This script scrapes product reviews from various sources (G2, Capterra, TrustRadius)
for a specific company and time period.

Usage:
    python review_scraper.py --company "Slack" --start-date "2023-01-01" --end-date "2023-12-31" --source "g2"

Author: AI Assistant
Date: September 2025
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from scrapers.g2_scraper import G2Scraper
from scrapers.capterra_scraper import CapterraScraper
from scrapers.trustradius_scraper import TrustRadiusScraper
from utils.validator import validate_inputs
from utils.date_helper import parse_date_string


def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Scrape product reviews from G2, Capterra, or TrustRadius",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python review_scraper.py --company "Slack" --start-date "2023-01-01" --end-date "2023-12-31" --source "g2"
  python review_scraper.py --company "HubSpot" --start-date "2023-06-01" --end-date "2023-06-30" --source "capterra"
  python review_scraper.py --company "Salesforce" --start-date "2023-01-01" --end-date "2023-03-31" --source "trustradius"
        """
    )
    
    parser.add_argument(
        "--company", 
        type=str, 
        required=True,
        help="Name of the company whose product reviews to scrape"
    )
    
    parser.add_argument(
        "--start-date", 
        type=str, 
        required=True,
        help="Start date for review period (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str, 
        required=True,
        help="End date for review period (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--source", 
        type=str, 
        required=True,
        choices=["g2", "capterra", "trustradius"],
        help="Source platform to scrape reviews from"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default="output",
        help="Output directory for JSON results (default: output)"
    )
    
    parser.add_argument(
        "--max-reviews", 
        type=int, 
        default=100,
        help="Maximum number of reviews to scrape (default: 100)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


def get_scraper(source: str):
    """Get the appropriate scraper based on source."""
    scrapers = {
        "g2": G2Scraper,
        "capterra": CapterraScraper,
        "trustradius": TrustRadiusScraper
    }
    
    scraper_class = scrapers.get(source.lower())
    if not scraper_class:
        raise ValueError(f"Unsupported source: {source}")
    
    return scraper_class()


def save_reviews_to_json(reviews, output_dir, company, source, start_date, end_date):
    """Save reviews to a JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company.replace(' ', '_').lower()}_{source}_{start_date}_{end_date}_{timestamp}.json"
    filepath = output_path / filename
    
    # Prepare output data
    output_data = {
        "metadata": {
            "company": company,
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "total_reviews": len(reviews),
            "scraped_at": datetime.now().isoformat()
        },
        "reviews": reviews
    }
    
    # Save to JSON file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f" Reviews saved to: {filepath}")
    return filepath


def main():
    """Main function to orchestrate the scraping process."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    print(" Product Review Scraper")
    print("=" * 50)
    
    try:
        # Validate inputs
        print(" Validating inputs...")
        validate_inputs(args.company, args.start_date, args.end_date, args.source)
        
        # Parse dates
        start_date = parse_date_string(args.start_date)
        end_date = parse_date_string(args.end_date)
        
        print(f" Company: {args.company}")
        print(f" Date Range: {args.start_date} to {args.end_date}")
        print(f" Source: {args.source.upper()}")
        print(f" Max Reviews: {args.max_reviews}")
        print()
        
        # Get appropriate scraper
        print(f"Initializing {args.source.upper()} scraper...")
        scraper = get_scraper(args.source)
        
        # Scrape reviews
        print(" Starting review scraping...")
        reviews = scraper.scrape_reviews(
            company=args.company,
            start_date=start_date,
            end_date=end_date,
            max_reviews=args.max_reviews,
            verbose=args.verbose
        )
        
        if not reviews:
            print(" No reviews found for the specified criteria.")
            print(" This might be due to anti-bot protection or site changes.")
            return
        
        print(f" Successfully scraped {len(reviews)} reviews")
        
        # Save results
        print("💾 Saving results to JSON...")
        output_file = save_reviews_to_json(
            reviews, 
            args.output, 
            args.company, 
            args.source, 
            args.start_date, 
            args.end_date
        )
        
        print()
        print("Scraping completed successfully!")
        print(f" Output file: {output_file}")
        
    except KeyboardInterrupt:
        print("\n Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f" Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
