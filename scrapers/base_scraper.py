"""
Base scraper class with common functionality for all review scrapers.
"""

import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from utils.date_helper import is_date_in_range, parse_review_date


class BaseScraper(ABC):
    """Base class for all review scrapers."""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.driver = None
        self.setup_session()
    
    def setup_session(self):
        """Set up the requests session with headers and settings."""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def setup_selenium_driver(self, headless: bool = False) -> webdriver.Chrome:
        """Set up Selenium Chrome driver with anti-detection measures."""
        if self.driver:
            return self.driver
        
        chrome_options = Options()
        
        # Make it less detectable as automation
        if headless:
            chrome_options.add_argument("--headless")
        else:
            print("🖥️  Running in non-headless mode for better success rate...")
            
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        
        # Realistic user agent
        realistic_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"--user-agent={realistic_user_agent}")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Additional anti-detection measures
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return self.driver
        except Exception as e:
            raise RuntimeError(f"Failed to setup Chrome driver: {str(e)}")
    
    def close_driver(self):
        """Close the Selenium driver if it exists."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def random_delay(self, min_seconds: float = 2.0, max_seconds: float = 8.0):
        """Add random delay to avoid being detected as a bot."""
        delay = random.uniform(min_seconds, max_seconds)
        print(f"⏱️  Waiting {delay:.1f} seconds to avoid detection...")
        time.sleep(delay)
    
    def simulate_human_behavior(self, driver):
        """Simulate human-like behavior on the page."""
        try:
            # Random scrolling
            scroll_height = random.randint(200, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            time.sleep(random.uniform(1, 3))
            
            # Scroll back up a bit
            driver.execute_script(f"window.scrollBy(0, -{scroll_height//3});")
            time.sleep(random.uniform(0.5, 2))
            
            # Random mouse movements (simulated)
            driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': Math.random() * window.innerWidth,
                    'clientY': Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
        except:
            pass  # Don't let simulation errors break the scraping
    
    def make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retries and error handling."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f" Request failed (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    self.random_delay(2, 5)
                else:
                    print(f" Failed to fetch URL after {retries} attempts: {url}")
                    return None
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup."""
        return BeautifulSoup(html_content, 'lxml')
    
    def extract_text_safely(self, element, selector: str = None) -> str:
        """Safely extract text from an element or selector."""
        try:
            if selector:
                target = element.select_one(selector)
                return target.get_text(strip=True) if target else ""
            else:
                return element.get_text(strip=True) if element else ""
        except:
            return ""
    
    def clean_review_text(self, text: str) -> str:
        """Clean and normalize review text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common artifacts
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2026', '...')  # Ellipsis
        
        return text.strip()
    
    def extract_rating(self, element, rating_selectors: List[str]) -> Optional[float]:
        """Extract rating from various possible selectors."""
        for selector in rating_selectors:
            try:
                rating_element = element.select_one(selector)
                if rating_element:
                    # Try different ways to extract rating
                    rating_text = rating_element.get('aria-label', '')
                    if 'star' in rating_text.lower():
                        # Extract number from "X star" or "X out of Y stars"
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                        if match:
                            return float(match.group(1))
                    
                    # Try to get rating from text content
                    rating_text = rating_element.get_text(strip=True)
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if match:
                        return float(match.group(1))
                        
                    # Try to get rating from class or data attributes
                    for attr in ['data-rating', 'data-score', 'title']:
                        if rating_element.has_attr(attr):
                            attr_value = rating_element[attr]
                            import re
                            match = re.search(r'(\d+(?:\.\d+)?)', str(attr_value))
                            if match:
                                return float(match.group(1))
            except:
                continue
        
        return None
    
    def filter_reviews_by_date(self, reviews: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
        """Filter reviews by date range."""
        filtered_reviews = []
        
        for review in reviews:
            review_date = review.get('date', '')
            if is_date_in_range(review_date, start_date, end_date):
                filtered_reviews.append(review)
        
        return filtered_reviews
    
    @abstractmethod
    def scrape_reviews(self, company: str, start_date: datetime, end_date: datetime, 
                      max_reviews: int = 100, verbose: bool = False) -> List[Dict[str, Any]]:
        """Scrape reviews for a company within the specified date range."""
        pass
    
    @abstractmethod
    def search_company(self, company_name: str) -> Optional[str]:
        """Search for a company and return the URL to its reviews page."""
        pass
    
    def __del__(self):
        """Cleanup when the scraper is destroyed."""
        self.close_driver()
