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
        
        # Wait for the page to load using WebDriverWait
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

        # Extract job listings data
        print("\nAttempting to extract job listings:")
        job_data = extract_naukri_job_listings(driver)
        
        # Save job data to JSON file
        with open("job_listings.json", "w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        print(f"Extracted {len(job_data)} job listings and saved to job_listings.json")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        # Close the browser
        driver.quit()

def extract_naukri_job_listings(driver, max_jobs=20):
    """Extract job listings specifically from Naukri.com"""
    job_listings = []
    
    try:
        # Naukri.com typically uses job cards/tuples
        # Based on the terminal output, we can see job-related divs were found
        job_cards = driver.find_elements(By.XPATH, "//article[contains(@class, 'job')] | //div[contains(@class, 'job')]")
        
        if not job_cards:
            # Try alternative selector specific to Naukri
            job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'jobTuple')]")
            
        if not job_cards:
            # Another alternative based on Naukri's structure from the screenshot
            job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'nI-gNb-job')]")
        
        print(f"Found {len(job_cards)} potential job listings")
        
        # Limit the number of jobs to extract
        job_cards = job_cards[:max_jobs]
        
        for card in job_cards:
            job_info = {}
            
            # Extract title (based on Naukri's structure)
            try:
                title_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'title')] | .//a[contains(@class, 'jobTitle')] | .//a[contains(@title, 'Job Details')] | .//a[contains(@href, '/job-listings')]")
                job_info["title"] = title_elem.text.strip()
            except NoSuchElementException:
                try:
                    # Another common pattern in Naukri
                    title_elem = card.find_element(By.XPATH, ".//a")
                    job_info["title"] = title_elem.text.strip()
                except NoSuchElementException:
                    job_info["title"] = "Title not found"
            
            # Extract company name (based on Naukri's structure)
            try:
                company_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'company')] | .//a[contains(@class, 'companyName')] | .//span[contains(@class, 'company')] | .//span[contains(@class, 'org')]")
                job_info["company"] = company_elem.text.strip()
            except NoSuchElementException:
                job_info["company"] = "Company not found"
                
            # Extract location (based on Naukri's structure)
            try:
                location_elem = card.find_element(By.XPATH, ".//span[contains(@class, 'location')] | .//span[contains(@class, 'loc')] | .//span[contains(@class, 'locWdth')] | .//div[contains(@class, 'location')]")
                job_info["location"] = location_elem.text.strip()
            except NoSuchElementException:
                try:
                    # Try another common pattern for location on Naukri
                    location_elem = card.find_element(By.XPATH, ".//span[contains(text(), 'Location')]/following-sibling::span")
                    job_info["location"] = location_elem.text.strip()
                except NoSuchElementException:
                    job_info["location"] = "Location not found"
                
            # Extract experience (Naukri specific)
            try:
                exp_elem = card.find_element(By.XPATH, ".//span[contains(@class, 'experience')] | .//span[contains(@class, 'exp')] | .//li[contains(text(), 'Yrs')]")
                job_info["experience"] = exp_elem.text.strip()
            except NoSuchElementException:
                job_info["experience"] = "Experience not found"
                
            # Extract salary (Naukri specific)
            try:
                salary_elem = card.find_element(By.XPATH, ".//span[contains(@class, 'salary')] | .//span[contains(@class, 'sal')] | .//span[contains(text(), 'PA')]")
                job_info["salary"] = salary_elem.text.strip()
            except NoSuchElementException:
                job_info["salary"] = "Salary not found"
            
            # Extract job description/snippet (Naukri specific)
            try:
                desc_elem = card.find_element(By.XPATH, ".//div[contains(@class, 'job-description')] | .//div[contains(@class, 'description')] | .//ul[contains(@class, 'description')]")
                job_info["description"] = desc_elem.text.strip()
            except NoSuchElementException:
                job_info["description"] = "Description not found"
                
            # Extract job link
            try:
                link_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'title')] | .//a[contains(@class, 'jobTitle')] | .//a[1]")
                job_info["link"] = link_elem.get_attribute("href")
            except NoSuchElementException:
                job_info["link"] = "Link not found"
                
            # Extract posted date (Naukri specific)
            try:
                date_elem = card.find_element(By.XPATH, ".//span[contains(@class, 'date')] | .//div[contains(@class, 'date')] | .//span[contains(text(), 'day')]")
                job_info["posted_date"] = date_elem.text.strip()
            except NoSuchElementException:
                job_info["posted_date"] = "Date not found"
            
            # Add to our results
            job_listings.append(job_info)
            
    except Exception as e:
        print(f"Error in job extraction: {e}")
    
    return job_listings

# URL for data analyst jobs in India
url = "https://www.naukri.com/data-analyst-jobs-in-india"

# Run the analysis
analyze_naukri_page(url)