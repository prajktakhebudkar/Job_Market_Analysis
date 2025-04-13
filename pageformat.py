from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import json

def analyze_naukri_page(url):
    # Set up Chrome options
    chrome_options = Options()
    # Uncomment for headless mode if needed
    # chrome_options.add_argument("--headless")
    
    # Set up the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Load the page
        driver.get(url)
        print(f"Accessing URL: {url}")
        
        # Wait for the page to load using WebDriverWait instead of sleep
        print("Waiting for page to load...")
        wait = WebDriverWait(driver, 15)  # 15 seconds timeout
        try:
            # Wait for a common element that indicates the page has loaded
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'job')]")))
            print("Page loaded successfully")
        except TimeoutException:
            print("Timeout waiting for page to load, continuing anyway...")
        
        # Take a screenshot
        screenshot_path = "naukri_page.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Get the page source
        html_source = driver.page_source
        
        # Save the HTML to a file
        with open("naukri_source.html", "w", encoding="utf-8") as f:
            f.write(html_source)
        
        print("HTML source saved to naukri_source.html")
        
        # Print page title
        print(f"Page title: {driver.title}")
        
        # Check for common elements
        print("\nChecking for common elements:")
        
        # List all div elements with classes containing 'job'
        job_related_divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'job')]")
        print(f"Found {len(job_related_divs)} divs with 'job' in class name")
        
        # List all article elements
        articles = driver.find_elements(By.TAG_NAME, "article")
        print(f"Found {len(articles)} article elements")
        
        # List common container elements
        containers = driver.find_elements(By.XPATH, "//div[@id='root' or @id='content' or @id='main' or @id='app']")
        for container in containers:
            print(f"Found container: {container.get_attribute('id')}")
        
        # Print first few div elements with class attributes
        print("\nFirst 5 divs with class attributes:")
        divs_with_class = driver.find_elements(By.XPATH, "//div[@class]")
        for i, div in enumerate(divs_with_class[:5]):
            class_name = div.get_attribute("class")
            print(f"{i+1}. Class: {class_name}")
            # Also print first child element if any
            children = div.find_elements(By.XPATH, "./*")
            if children:
                print(f"   First child: <{children[0].tag_name}> with class '{children[0].get_attribute('class')}'")

        # NEW FEATURE: Extract job listings data
        try:
            print("\nAttempting to extract job listings:")
            job_data = extract_job_listings(driver)
            
            # Save job data to JSON file
            with open("job_listings.json", "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2)
            
            print(f"Extracted {len(job_data)} job listings and saved to job_listings.json")
        except Exception as e:
            print(f"Error extracting job listings: {e}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        # Close the browser
        driver.quit()

def extract_job_listings(driver):
    """Extract job listings data based on page structure identified"""
    job_listings = []
    
    # Based on the identified page structure, try different selectors
    # Starting with the most common patterns seen in job boards
    
    # Try pattern 1: Job cards in container
    try:
        # First attempt - look for job cards with nI-gNb prefix as seen in the output
        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'job') or contains(@class, 'jobTuple')]")
        
        if not job_cards:
            # Alternative selector if the first one doesn't work
            job_cards = driver.find_elements(By.XPATH, "//article | //div[contains(@class, 'card')]")
        
        print(f"Found {len(job_cards)} potential job listings")
        
        for i, card in enumerate(job_cards[:10]):  # Limit to first 10 for testing
            job_info = {}
            
            # Extract title - try multiple possible selectors
            try:
                title_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'title')] | .//h2 | .//h3 | .//div[contains(@class, 'title')]")
                job_info["title"] = title_elem.text.strip()
            except NoSuchElementException:
                job_info["title"] = "Title not found"
            
            # Extract company name
            try:
                company_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'company')] | .//span[contains(@class, 'company')] | .//div[contains(@class, 'company')]")
                job_info["company"] = company_elem.text.strip()
            except NoSuchElementException:
                job_info["company"] = "Company not found"
                
            # Extract location
            try:
                location_elem = card.find_element(By.XPATH, ".//span[contains(@class, 'location')] | .//div[contains(@class, 'location')] | .//span[contains(text(), 'Location')]")
                job_info["location"] = location_elem.text.strip()
            except NoSuchElementException:
                job_info["location"] = "Location not found"
                
            # Extract link
            try:
                link_elem = card.find_element(By.XPATH, ".//a[1]")
                job_info["link"] = link_elem.get_attribute("href")
            except NoSuchElementException:
                job_info["link"] = "Link not found"
            
            # Add to our results
            job_listings.append(job_info)
            
    except Exception as e:
        print(f"Error in job extraction pattern: {e}")
    
    return job_listings

# URL for data analyst jobs in India
url = "https://www.naukri.com/data-analyst-jobs-in-india"

# Run the analysis
analyze_naukri_page(url)