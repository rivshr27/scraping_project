#!/usr/bin/env python3
"""
Debug script to understand the actual structure of G2 reviews.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def debug_g2_structure():
    """Debug the actual structure of G2 reviews."""
    
    chrome_options = Options()
    # Run with browser visible to see what's happening
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    realistic_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"--user-agent={realistic_user_agent}")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(" Loading G2 Slack reviews page...")
        driver.get('https://www.g2.com/products/slack/reviews')
        time.sleep(8)  # Wait longer for full page load
        
        # Simulate human behavior
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(3)
        
        print(" Looking for review elements...")
        
        # Try different selectors to find reviews
        selectors_to_test = [
            "article",
            "[data-testid*='review']",
            ".review",
            ".paper",
            "[class*='Paper']",
            "[class*='review']",
            "[class*='Review']"
        ]
        
        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"\nSelector '{selector}': Found {len(elements)} elements")
                
                if elements and len(elements) > 0:
                    # Examine the first element
                    first_element = elements[0]
                    print(f"First element HTML preview:")
                    element_html = first_element.get_attribute('outerHTML')[:500]
                    print(f"   {element_html}...")
                    
                    # Try to find text content
                    text_content = first_element.text
                    if text_content:
                        print(f" Text content preview: {text_content[:200]}...")
                    else:
                        print("  No text content found")
                
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
        
        # Save full page source for analysis
        page_source = driver.page_source
        print(f"\n💾 Saving page source ({len(page_source)} chars) to debug_page.html")
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        
        # Parse with BeautifulSoup to find patterns
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Look for text that might be review content
        review_keywords = ['review', 'star', 'rating', 'recommend', 'experience']
        for keyword in review_keywords:
            elements_with_keyword = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            if elements_with_keyword:
                print(f"\n🔎 Found {len(elements_with_keyword)} text nodes containing '{keyword}'")
                for i, text in enumerate(elements_with_keyword[:3]):  # Show first 3
                    print(f"   {i+1}. {text.strip()[:100]}...")
        
    except Exception as e:
        print(f" Debug failed: {e}")
    finally:
        if driver:
            print("🔍 Browser will close automatically in 3 seconds...")
            time.sleep(3)
            driver.quit()

if __name__ == "__main__":
    debug_g2_structure()
