# Product Review Scraper

A comprehensive Python script to scrape product reviews from major SaaS review platforms including G2, Capterra, and TrustRadius. This tool allows you to extract reviews for a specific company within a defined time period and export them to JSON format.

## Features

- **Multi-Platform Support**: Scrapes reviews from G2, Capterra, and TrustRadius.
- **Real Website Scraping**: Successfully extracts actual reviews from G2.
- **Advanced Anti-Detection**: Implements human-like browsing behavior to bypass bot detectors.
- **Robust and Resilient**: Handles errors gracefully and provides informative feedback.
- **Clean Code Architecture**: Organized into logical modules for maintainability.

## How It Works

The scraper uses **Selenium** to automate a real web browser, allowing it to handle dynamic, JavaScript-heavy websites. To avoid being blocked, it simulates human behavior by:

- **Running in a visible browser window** instead of headless mode.
- **Using realistic user-agent strings** to mimic a real browser.
- **Adding randomized delays and scrolling** to avoid predictable, bot-like patterns.
- **Implementing multiple selectors** to find review elements even if the site structure changes.

## Current Scraping Status

- ✅ **G2**: **Working**. Successfully extracts real review content.
- ⚠️ **Capterra & TrustRadius**: **Blocked**. These sites have more aggressive anti-bot measures that require advanced solutions like proxy rotation or CAPTCHA-solving services. The scraper can find the product pages but is blocked from extracting reviews.

## Installation

### Prerequisites

- Python 3.7+
- Google Chrome

### Setup

1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd scraping_project
    ```

2.  **Run the Setup Script**:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    This script will:
    - Create a Python virtual environment.
    - Install the required dependencies from `requirements.txt`.

## Usage

1.  **Activate the Virtual Environment**:
    ```bash
    source venv/bin/activate
    ```

2.  **Run the Scraper**:
    ```bash
    python review_scraper.py --company "Slack" --start-date "2023-01-01" --end-date "2023-12-31" --source "g2"
    ```

### Command-Line Arguments

| Argument | Required | Description | Example |
|---|---|---|---|
| `--company` | **Yes** | Name of the company to scrape. | `"Salesforce"` |
| `--start-date` | **Yes** | Start of the review period (YYYY-MM-DD). | `"2023-01-01"` |
| `--end-date` | **Yes** | End of the review period (YYYY-MM-DD). | `"2023-12-31"` |
| `--source` | **Yes** | Review platform (`g2`, `capterra`, `trustradius`). | `"g2"` |
| `--output` | No | Directory for JSON results (default: `output`). | `"my_reviews"` |
| `--max-reviews` | No | Max number of reviews to scrape (default: 100). | `50` |
| `--verbose` | No | Enable detailed logging. | |
