"""
Capterra scraper for product reviews.

This scraper extracts reviews from Capterra.com for a specific company within a date range.
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .base_scraper import BaseScraper
from utils.date_helper import parse_review_date


class CapterraScraper(BaseScraper):
    """Scraper for Capterra.com reviews."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.capterra.com"
        self.search_url = "https://www.capterra.com/search"
    
    def search_company(self, company_name: str) -> Optional[str]:
        """Search for a company on Capterra and return the URL to its reviews page."""
        try:
            driver = self.setup_selenium_driver(headless=False)
            
            # Search for the company
            search_url = f"{self.search_url}/?query={quote(company_name)}"
            print(f"🔍 Searching Capterra for: {company_name}")
            
            driver.get(search_url)
            self.simulate_human_behavior(driver)
            self.random_delay(3, 6)
            
            # Look for product results
            wait = WebDriverWait(driver, 15)
            
            # Try different selectors for search results
            result_selectors = [
                "a[data-link-action='Product Page']",
                ".search-results a[href*='/p/']",
                ".product-card a",
                "a[href*='/p/']",
                ".listing-item a"
            ]
            
            for selector in result_selectors:
                try:
                    results = driver.find_elements(By.CSS_SELECTOR, selector)
                    if results:
                        # Get the first result that looks like a product page
                        for result in results[:3]:  # Check first 3 results
                            href = result.get_attribute('href')
                            if href and '/p/' in href:
                                print(f" Found Capterra product page: {href}")
                                return href
                except:
                    continue
            
            # If no direct product links found, try alternative approach
            print("⚠️  No direct product links found, trying alternative search...")
            
            # Look for any links that might lead to products
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute('href')
                if href and '/p/' in href and 'capterra.com' in href:
                    link_text = link.get_attribute('text') or link.text
                    if company_name.lower() in link_text.lower():
                        print(f"Found alternative Capterra product page: {href}")
                        return href
            
            print(f" Could not find Capterra page for company: {company_name}")
            return None
            
        except Exception as e:
            print(f"Error searching for company on Capterra: {str(e)}")
            return None
    
    def get_reviews_url(self, product_url: str) -> str:
        """Convert product URL to reviews URL."""
        # Capterra reviews are typically accessed via the product page with reviews section
        if '?' in product_url:
            base_url = product_url.split('?')[0]
        else:
            base_url = product_url
        
        if not base_url.endswith('/'):
            base_url += '/'
        
        return base_url + "#reviews"
    
    def scrape_reviews(self, company: str, start_date: datetime, end_date: datetime, 
                      max_reviews: int = 100, verbose: bool = False) -> List[Dict[str, Any]]:
        """Scrape reviews from Capterra for the specified company and date range."""
        try:
            # Search for the company
            product_url = self.search_company(company)
            if not product_url:
                print(f" Could not find Capterra page for {company}")
                return []
            
            # Get reviews URL
            reviews_url = self.get_reviews_url(product_url)
            
            driver = self.setup_selenium_driver(headless=False)
            reviews = []
            
            print(f"Starting Capterra review scraping for {company}...")
            
            driver.get(reviews_url)
            self.simulate_human_behavior(driver)
            self.random_delay(4, 8)
            
            # Try to navigate to reviews section
            self.navigate_to_reviews_section(driver)
            
            # Load more reviews if possible
            self.load_more_reviews(driver, max_reviews, verbose)
            
            # Extract all reviews from the page
            page_reviews = self.extract_reviews_from_page(driver, start_date, end_date, verbose)
            reviews.extend(page_reviews)
            
            # Filter reviews by date range
            filtered_reviews = self.filter_reviews_by_date(reviews, start_date, end_date)
            
            print(f" Capterra scraping completed: {len(filtered_reviews)} reviews found")
            return filtered_reviews
            
        except Exception as e:
            print(f" Error scraping Capterra reviews: {str(e)}")
            return []
        finally:
            self.close_driver()
    
    def navigate_to_reviews_section(self, driver):
        """Navigate to the reviews section on the product page."""
        review_section_selectors = [
            "a[href*='#reviews']",
            "button[data-target*='review']",
            ".reviews-tab",
            "[data-scroll-to='reviews']",
            "a[data-link-action*='Review']"
        ]
        
        for selector in review_section_selectors:
            try:
                review_tab = driver.find_element(By.CSS_SELECTOR, selector)
                if review_tab.is_displayed():
                    driver.execute_script("arguments[0].click();", review_tab)
                    self.simulate_human_behavior(driver)
                    self.random_delay(2, 4)
                    return
            except:
                continue
        
        # If no tab found, try scrolling to reviews section
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            self.simulate_human_behavior(driver)
            self.random_delay(2, 4)
        except:
            pass
    
    def load_more_reviews(self, driver, max_reviews: int, verbose: bool = False):
        """Load more reviews by clicking load more buttons or scrolling."""
        reviews_loaded = 0
        attempts = 0
        max_attempts = 10
        
        while reviews_loaded < max_reviews and attempts < max_attempts:
            attempts += 1
            
            # Try to find and click "Load more" or "Show more" buttons
            load_more_selectors = [
                "button[data-action*='load-more']",
                "button[data-action*='show-more']",
                ".load-more-reviews",
                ".show-more-reviews",
                "button:contains('Show more')",
                "button:contains('Load more')"
            ]
            
            clicked = False
            for selector in load_more_selectors:
                try:
                    load_more_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if load_more_btn.is_displayed() and load_more_btn.is_enabled():
                        driver.execute_script("arguments[0].click();", load_more_btn)
                        self.simulate_human_behavior(driver)
                        self.random_delay(3, 6)
                        clicked = True
                        if verbose:
                            print(f"📄 Clicked load more button (attempt {attempts})")
                        break
                except:
                    continue
            
            # If no button found, try scrolling
            if not clicked:
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    self.simulate_human_behavior(driver)
                    self.random_delay(2, 5)
                    if verbose:
                        print(f"📜 Scrolled to load more reviews (attempt {attempts})")
                except:
                    break
            
            # Check if we have enough reviews
            current_reviews = len(driver.find_elements(By.CSS_SELECTOR, self.get_review_selectors()[0]))
            if current_reviews >= max_reviews:
                break
            
            if current_reviews == reviews_loaded:
                # No new reviews loaded, break
                break
            
            reviews_loaded = current_reviews
    
    def get_review_selectors(self) -> List[str]:
        """Get possible selectors for review containers."""
        return [
            ".review-item",
            ".review-card",
            ".review",
            "[data-testid*='review']",
            ".user-review",
            ".review-container",
            "article[data-review-id]"
        ]
    
    def extract_reviews_from_page(self, driver, start_date: datetime, end_date: datetime, 
                                 verbose: bool = False) -> List[Dict[str, Any]]:
        """Extract all reviews from the current page."""
        reviews = []
        
        review_selectors = self.get_review_selectors()
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    review_elements = elements
                    if verbose:
                        print(f" Found {len(elements)} review elements with selector: {selector}")
                    break
            except:
                continue
        
        if not review_elements:
            print("  No review elements found on page")
            return reviews
        
        for i, review_element in enumerate(review_elements):
            try:
                review_data = self.extract_single_review(review_element, verbose)
                if review_data:
                    reviews.append(review_data)
                    if verbose and i < 3:  # Show details for first few reviews
                        print(f" Review {i+1}: {review_data.get('title', '')[:50]}...")
            except Exception as e:
                if verbose:
                    print(f" Error extracting review {i+1}: {str(e)}")
                continue
        
        return reviews
    
    def extract_single_review(self, review_element, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """Extract data from a single review element."""
        try:
            review_data = {}
            
            # Extract title/headline
            title_selectors = [
                ".review-title",
                ".review-header h3",
                ".review-headline",
                "h3",
                ".title",
                "[data-testid*='title']"
            ]
            
            title = ""
            for selector in title_selectors:
                try:
                    title_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.strip()
                    if title:
                        break
                except:
                    continue
            
            # Extract review text/description
            content_selectors = [
                ".review-content",
                ".review-text",
                ".review-body",
                ".review-description",
                ".user-review-text",
                "p[data-testid*='review-body']"
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    content_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    content = content_element.text.strip()
                    if content:
                        break
                except:
                    continue
            
            # Extract date
            date_selectors = [
                ".review-date",
                ".date",
                "time",
                "[datetime]",
                ".posted-date",
                "[data-testid*='date']"
            ]
            
            date = ""
            for selector in date_selectors:
                try:
                    date_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    date = date_element.get_attribute('datetime') or date_element.text.strip()
                    if date:
                        date = parse_review_date(date)
                        break
                except:
                    continue
            
            # Extract rating
            rating_selectors = [
                ".star-rating",
                ".rating",
                "[data-rating]",
                ".stars",
                "[aria-label*='star']"
            ]
            
            rating = self.extract_rating(review_element, rating_selectors)
            
            # Extract reviewer name
            reviewer_selectors = [
                ".reviewer-name",
                ".review-author",
                ".author-name",
                ".user-name",
                "[data-testid*='reviewer']"
            ]
            
            reviewer = ""
            for selector in reviewer_selectors:
                try:
                    reviewer_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    reviewer = reviewer_element.text.strip()
                    if reviewer:
                        break
                except:
                    continue
            
            # Extract company/role if available
            company_selectors = [
                ".reviewer-company",
                ".company-name",
                ".job-title",
                ".user-info",
                ".reviewer-info"
            ]
            
            company_info = ""
            for selector in company_selectors:
                try:
                    company_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    company_info = company_element.text.strip()
                    if company_info:
                        break
                except:
                    continue
            
            # Extract pros/cons if available
            pros = ""
            cons = ""
            
            pros_selectors = [".pros", ".review-pros", "[data-testid*='pros']"]
            for selector in pros_selectors:
                try:
                    pros_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    pros = pros_element.text.strip()
                    if pros:
                        break
                except:
                    continue
            
            cons_selectors = [".cons", ".review-cons", "[data-testid*='cons']"]
            for selector in cons_selectors:
                try:
                    cons_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    cons = cons_element.text.strip()
                    if cons:
                        break
                except:
                    continue
            
            # Only include review if we have minimum required data
            if title or content:
                review_data = {
                    "title": self.clean_review_text(title),
                    "description": self.clean_review_text(content),
                    "date": date,
                    "rating": rating,
                    "reviewer_name": reviewer,
                    "reviewer_info": company_info,
                    "pros": self.clean_review_text(pros),
                    "cons": self.clean_review_text(cons),
                    "source": "Capterra"
                }
                
                return review_data
            
            return None
            
        except Exception as e:
            if verbose:
                print(f" Error extracting review data: {str(e)}")
            return None
