"""
G2 scraper for product reviews.

This scraper extracts reviews from G2.com for a specific company within a date range.
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


class G2Scraper(BaseScraper):
    """Scraper for G2.com reviews."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.g2.com"
        self.search_url = "https://www.g2.com/search"
    
    def search_company(self, company_name: str) -> Optional[str]:
        """Search for a company on G2 and return the URL to its reviews page."""
        try:
            # For testing purposes, we'll use a more direct approach
            # Many modern review sites block automated scraping, so let's provide
            # a fallback for common companies
            
            common_companies = {
                "slack": "https://www.g2.com/products/slack",
                "zoom": "https://www.g2.com/products/zoom",
                "salesforce": "https://www.g2.com/products/salesforce-sales-cloud",
                "hubspot": "https://www.g2.com/products/hubspot-marketing-hub",
                "microsoft teams": "https://www.g2.com/products/microsoft-teams",
                "asana": "https://www.g2.com/products/asana",
                "trello": "https://www.g2.com/products/trello"
            }
            
            company_lower = company_name.lower()
            if company_lower in common_companies:
                print(f"sing known G2 URL for {company_name}")
                return common_companies[company_lower]
            
            driver = self.setup_selenium_driver()
            
            # Search for the company
            search_url = f"{self.search_url}?query={quote(company_name)}"
            print(f"🔍 Searching G2 for: {company_name}")
            
            driver.get(search_url)
            self.random_delay(3, 6)
            
            # Look for product results with more specific selectors
            wait = WebDriverWait(driver, 15)
            
            # Updated selectors based on current G2 structure
            result_selectors = [
                "a[href*='/products/']",
                "[data-testid*='product'] a",
                ".product-listing a",
                ".search-result a",
                "h3 a[href*='/products/']"
            ]
            
            for selector in result_selectors:
                try:
                    results = driver.find_elements(By.CSS_SELECTOR, selector)
                    if results:
                        # Get the first result that looks like a product page
                        for result in results[:5]:  # Check first 5 results
                            href = result.get_attribute('href')
                            if href and '/products/' in href and 'g2.com' in href:
                                print(f"Found G2 product page: {href}")
                                return href
                except Exception as e:
                    continue
            
            print(f"  Could not find G2 page for company: {company_name}")
            print("You can try manually finding the G2 URL and updating the common_companies dict")
            return None
            
        except Exception as e:
            print(f"Error searching for company on G2: {str(e)}")
            return None
    
    def get_reviews_url(self, product_url: str) -> str:
        """Convert product URL to reviews URL."""
        if not product_url.endswith('/reviews'):
            if product_url.endswith('/'):
                return product_url + 'reviews'
            else:
                return product_url + '/reviews'
        return product_url
    
    def scrape_reviews(self, company: str, start_date: datetime, end_date: datetime, 
                      max_reviews: int = 100, verbose: bool = False) -> List[Dict[str, Any]]:
        """Scrape reviews from G2 for the specified company and date range."""
        try:
            # Search for the company
            product_url = self.search_company(company)
            if not product_url:
                print(f" Could not find G2 page for {company}")
                return []
            
            # Get reviews URL
            reviews_url = self.get_reviews_url(product_url)
            
            driver = self.setup_selenium_driver()
            reviews = []
            page = 1
            
            print(f" Starting G2 review scraping for {company}...")
            
            while len(reviews) < max_reviews:
                # Construct URL with pagination
                current_url = f"{reviews_url}?page={page}"
                if verbose:
                    print(f" Scraping page {page}: {current_url}")
                
                driver.get(current_url)
                print(f" Loaded page, simulating human behavior...")
                self.simulate_human_behavior(driver)
                self.random_delay(3, 8)
                
                # Wait for page to load and handle dynamic content
                try:
                    wait = WebDriverWait(driver, 20)
                    # Try multiple possible review selectors
                    review_loaded = False
                    selectors_to_try = [
                        "div[data-testid='review']",
                        ".review-item", 
                        ".review-card", 
                        ".review",
                        "[data-cy='review']",
                        ".paper",
                        "article",
                        ".border.border-gray-300"
                    ]
                    
                    for selector in selectors_to_try:
                        try:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                            print(f" Found reviews with selector: {selector}")
                            review_loaded = True
                            break
                        except TimeoutException:
                            continue
                    
                    if not review_loaded:
                        print(f"  No review elements found on page {page}, trying to scroll and wait...")
                        # Try scrolling to trigger lazy loading
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                        self.random_delay(3, 5)
                        
                        # Check if any content loaded after scrolling
                        page_content = driver.page_source
                        if len(page_content) < 5000:  # Very small page, likely blocked
                            print("  Page seems to be blocked or have minimal content")
                            break
                            
                except TimeoutException:
                    print(f"  Timeout waiting for reviews on page {page}")
                    if page == 1:  # If first page fails, try to continue with what we have
                        print(" Continuing with available content...")
                    else:
                        break
                
                # Extract reviews from current page
                page_reviews = self.extract_reviews_from_page(driver, start_date, end_date, verbose)
                
                if not page_reviews:
                    print(f" No more reviews found on page {page}")
                    break
                
                reviews.extend(page_reviews)
                
                if verbose:
                    print(f" Page {page}: Found {len(page_reviews)} reviews (Total: {len(reviews)})")
                
                # Check if we've reached the maximum
                if len(reviews) >= max_reviews:
                    reviews = reviews[:max_reviews]
                    break
                
                # Check if there's a next page
                if not self.has_next_page(driver):
                    print(" Reached last page of reviews")
                    break
                
                page += 1
                
                # Safety break to avoid infinite loops
                if page > 50:
                    print(" Reached maximum page limit (50)")
                    break
            
            # Filter reviews by date range
            filtered_reviews = self.filter_reviews_by_date(reviews, start_date, end_date)
            
            print(f" G2 scraping completed: {len(filtered_reviews)} reviews found")
            return filtered_reviews
            
        except Exception as e:
            print(f" Error scraping G2 reviews: {str(e)}")
            return []
        finally:
            self.close_driver()
    
    def extract_reviews_from_page(self, driver, start_date: datetime, end_date: datetime, 
                                 verbose: bool = False) -> List[Dict[str, Any]]:
        """Extract all reviews from the current page."""
        reviews = []
        
        # Multiple selectors to try for review containers
        review_selectors = [
            "div[data-testid='review']",
            "[data-cy='review']",
            ".review-item",
            ".review-card", 
            ".review",
            ".paper",
            "article",
            ".border.border-gray-300",
            "[class*='review']",
            "div[class*='Paper']",
            "div[class*='border']"
        ]
        
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
            print(" No review elements found on page")
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
                    print(f"  Error extracting review {i+1}: {str(e)}")
                continue
        
        return reviews
    
    def extract_single_review(self, review_element, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """Extract data from a single review element."""
        try:
            review_data = {}
            
            # Extract title/headline - more generic selectors for real G2
            title_selectors = [
                "h3",
                "h4", 
                "h5",
                "[data-testid*='title']",
                "[data-testid*='header']",
                ".review-title",
                ".review-header h3",
                ".review-headline",
                ".font-weight-bold",
                "div[class*='title']",
                "div[class*='Title']",
                "div[class*='header']",
                "div[class*='Header']"
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
            
            # Extract review text/description - more generic for real G2
            content_selectors = [
                "p",
                "div p",
                "[data-testid*='body']",
                "[data-testid*='content']", 
                "[data-testid*='text']",
                ".review-content",
                ".review-text",
                ".review-body",
                "p[itemprop='reviewBody']",
                ".review-description",
                "div[class*='content']",
                "div[class*='Content']",
                "div[class*='text']",
                "div[class*='Text']",
                "div[class*='body']",
                "div[class*='Body']"
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
                "[data-testid='review-date']",
                ".review-date",
                "time",
                ".date",
                "[datetime]"
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
                "[data-testid='star-rating']",
                ".star-rating",
                ".rating",
                "[aria-label*='star']",
                ".stars"
            ]
            
            rating = self.extract_rating(review_element, rating_selectors)
            
            # Extract reviewer name
            reviewer_selectors = [
                "[data-testid='reviewer-name']",
                ".reviewer-name",
                ".review-author",
                ".author-name",
                "span[itemprop='author']"
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
                "[data-testid='reviewer-info']"
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
            
            # Be more flexible about what constitutes a valid review
            # If we don't have title or content, try to get ANY text from the element
            if not title and not content:
                try:
                    # Get all text from the review element as fallback
                    all_text = review_element.text.strip()
                    if len(all_text) > 20:  # Must have some substantial text
                        # Try to split into title and content
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        if lines:
                            title = lines[0] if len(lines[0]) < 100 else lines[0][:97] + "..."
                            content = ' '.join(lines[1:]) if len(lines) > 1 else lines[0]
                except:
                    pass
            
            # Include review if we have any meaningful content
            if title or content or (reviewer and len(str(reviewer)) > 2):
                review_data = {
                    "title": self.clean_review_text(title) or "Review",
                    "description": self.clean_review_text(content) or "No description available",
                    "date": date or "Unknown",
                    "rating": rating,
                    "reviewer_name": reviewer or "Anonymous",
                    "reviewer_info": company_info or "Not specified",
                    "source": "G2"
                }
                
                if verbose:
                    print(f" Extracted review: {review_data['title'][:50]}...")
                
                return review_data
            
            if verbose:
                print("  Skipping element - insufficient data")
            return None
            
        except Exception as e:
            if verbose:
                print(f"  Error extracting review data: {str(e)}")
            return None
    
    def has_next_page(self, driver) -> bool:
        """Check if there's a next page of reviews."""
        next_page_selectors = [
            "a[data-testid='pagination-next']",
            ".pagination .next",
            "a[aria-label='Next']",
            ".pagination a[rel='next']",
            "button[aria-label*='next']"
        ]
        
        for selector in next_page_selectors:
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                if next_button and next_button.is_enabled():
                    return True
            except:
                continue
        
        return False
