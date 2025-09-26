"""
TrustRadius scraper for product reviews.

This scraper extracts reviews from TrustRadius.com for a specific company within a date range.
TrustRadius is a popular platform for business software reviews.
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


class TrustRadiusScraper(BaseScraper):
    """Scraper for TrustRadius.com reviews."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.trustradius.com"
        self.search_url = "https://www.trustradius.com/search"
    
    def search_company(self, company_name: str) -> Optional[str]:
        """Search for a company on TrustRadius and return the URL to its reviews page."""
        try:
            driver = self.setup_selenium_driver()
            
            # Search for the company
            search_url = f"{self.search_url}?query={quote(company_name)}"
            print(f"🔍 Searching TrustRadius for: {company_name}")
            
            driver.get(search_url)
            self.random_delay(2, 4)
            
            # Look for product results
            wait = WebDriverWait(driver, 10)
            
            # Try different selectors for search results
            result_selectors = [
                "a[href*='/products/']",
                ".search-result a",
                ".product-card a",
                ".listing-card a",
                ".product-listing a"
            ]
            
            for selector in result_selectors:
                try:
                    results = driver.find_elements(By.CSS_SELECTOR, selector)
                    if results:
                        # Get the first result that looks like a product page
                        for result in results[:3]:  # Check first 3 results
                            href = result.get_attribute('href')
                            if href and '/products/' in href:
                                print(f" Found TrustRadius product page: {href}")
                                return href
                except:
                    continue
            
            # If no direct product links found, try alternative approach
            print("  No direct product links found, trying alternative search...")
            
            # Try a more specific search
            alternative_query = f"{company_name} software"
            alt_search_url = f"{self.search_url}?query={quote(alternative_query)}"
            driver.get(alt_search_url)
            self.random_delay(2, 4)
            
            # Look for any links that might lead to products
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute('href')
                if href and '/products/' in href and 'trustradius.com' in href:
                    link_text = link.get_attribute('text') or link.text
                    if company_name.lower() in link_text.lower():
                        print(f" Found alternative TrustRadius product page: {href}")
                        return href
            
            print(f" Could not find TrustRadius page for company: {company_name}")
            return None
            
        except Exception as e:
            print(f"Error searching for company on TrustRadius: {str(e)}")
            return None
    
    def get_reviews_url(self, product_url: str) -> str:
        """Convert product URL to reviews URL."""
        # TrustRadius reviews are typically at /products/[product]/reviews
        if not product_url.endswith('/reviews'):
            if product_url.endswith('/'):
                return product_url + 'reviews'
            else:
                return product_url + '/reviews'
        return product_url
    
    def scrape_reviews(self, company: str, start_date: datetime, end_date: datetime, 
                      max_reviews: int = 100, verbose: bool = False) -> List[Dict[str, Any]]:
        """Scrape reviews from TrustRadius for the specified company and date range."""
        try:
            # Search for the company
            product_url = self.search_company(company)
            if not product_url:
                print(f" Could not find TrustRadius page for {company}")
                return []
            
            # Get reviews URL
            reviews_url = self.get_reviews_url(product_url)
            
            driver = self.setup_selenium_driver()
            reviews = []
            page = 1
            
            print(f" Starting TrustRadius review scraping for {company}...")
            
            while len(reviews) < max_reviews:
                # Construct URL with pagination
                current_url = f"{reviews_url}?page={page}"
                if verbose:
                    print(f" Scraping page {page}: {current_url}")
                
                driver.get(current_url)
                self.random_delay(2, 4)
                
                # Wait for reviews to load
                try:
                    wait = WebDriverWait(driver, 15)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
                        ".review, .review-item, .review-card, .user-review")))
                except TimeoutException:
                    print(f"  Timeout waiting for reviews on page {page}")
                    break
                
                # Extract reviews from current page
                page_reviews = self.extract_reviews_from_page(driver, start_date, end_date, verbose)
                
                if not page_reviews:
                    print(f"  No more reviews found on page {page}")
                    break
                
                reviews.extend(page_reviews)
                
                if verbose:
                    print(f"Page {page}: Found {len(page_reviews)} reviews (Total: {len(reviews)})")
                
                # Check if we've reached the maximum
                if len(reviews) >= max_reviews:
                    reviews = reviews[:max_reviews]
                    break
                
                # Check if there's a next page
                if not self.has_next_page(driver):
                    print("  Reached last page of reviews")
                    break
                
                page += 1
                
                # Safety break to avoid infinite loops
                if page > 50:
                    print("  Reached maximum page limit (50)")
                    break
            
            # Filter reviews by date range
            filtered_reviews = self.filter_reviews_by_date(reviews, start_date, end_date)
            
            print(f" TrustRadius scraping completed: {len(filtered_reviews)} reviews found")
            return filtered_reviews
            
        except Exception as e:
            print(f" Error scraping TrustRadius reviews: {str(e)}")
            return []
        finally:
            self.close_driver()
    
    def extract_reviews_from_page(self, driver, start_date: datetime, end_date: datetime, 
                                 verbose: bool = False) -> List[Dict[str, Any]]:
        """Extract all reviews from the current page."""
        reviews = []
        
        # Multiple selectors to try for review containers
        review_selectors = [
            ".review",
            ".review-item",
            ".review-card",
            ".user-review",
            "[data-testid*='review']",
            ".review-container",
            "article.review"
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
                    print(f"  Error extracting review {i+1}: {str(e)}")
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
                "[data-testid*='title']",
                ".review-summary"
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
                ".review-details",
                "[data-testid*='review-body']"
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
                ".publication-date",
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
                "[aria-label*='star']",
                ".score"
            ]
            
            rating = self.extract_rating(review_element, rating_selectors)
            
            # Extract reviewer name
            reviewer_selectors = [
                ".reviewer-name",
                ".review-author",
                ".author-name",
                ".user-name",
                ".reviewer",
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
                ".reviewer-info",
                ".company-size",
                ".industry"
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
            
            # Extract TrustRadius-specific fields
            # Overall rating
            overall_rating = None
            overall_rating_selectors = [".overall-rating", ".total-score", ".overall-score"]
            for selector in overall_rating_selectors:
                try:
                    rating_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    rating_text = rating_element.text.strip()
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if match:
                        overall_rating = float(match.group(1))
                        break
                except:
                    continue
            
            # Extract likes/pros
            likes = ""
            likes_selectors = [".likes", ".pros", ".positives", "[data-testid*='likes']"]
            for selector in likes_selectors:
                try:
                    likes_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    likes = likes_element.text.strip()
                    if likes:
                        break
                except:
                    continue
            
            # Extract dislikes/cons
            dislikes = ""
            dislikes_selectors = [".dislikes", ".cons", ".negatives", "[data-testid*='dislikes']"]
            for selector in dislikes_selectors:
                try:
                    dislikes_element = review_element.find_element(By.CSS_SELECTOR, selector)
                    dislikes = dislikes_element.text.strip()
                    if dislikes:
                        break
                except:
                    continue
            
            # Only include review if we have minimum required data
            if title or content:
                review_data = {
                    "title": self.clean_review_text(title),
                    "description": self.clean_review_text(content),
                    "date": date,
                    "rating": rating or overall_rating,
                    "reviewer_name": reviewer,
                    "reviewer_info": company_info,
                    "likes": self.clean_review_text(likes),
                    "dislikes": self.clean_review_text(dislikes),
                    "source": "TrustRadius"
                }
                
                return review_data
            
            return None
            
        except Exception as e:
            if verbose:
                print(f" Error extracting review data: {str(e)}")
            return None
    
    def has_next_page(self, driver) -> bool:
        """Check if there's a next page of reviews."""
        next_page_selectors = [
            "a[aria-label='Next']",
            ".pagination .next",
            ".pagination a[rel='next']",
            "button[aria-label*='next']",
            ".next-page"
        ]
        
        for selector in next_page_selectors:
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                if next_button and next_button.is_enabled():
                    return True
            except:
                continue
        
        return False
