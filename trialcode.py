from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def analyze_with_selenium(url):
    # Set up Chrome options
    chrome_options = Options()
    # Uncomment the next line if you want to run headless
    # chrome_options.add_argument("--headless")
    
    # Set up the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Load the page
        driver.get(url)
        
        # Wait for the page to load completely
        time.sleep(5)
        
        # Let's examine what's actually on the page
        print("Page title:", driver.title)
        
        # Look for any job listing elements using common patterns
        job_listings = driver.find_elements(By.CSS_SELECTOR, "div.jobTuple") or \
                      driver.find_elements(By.CSS_SELECTOR, "article") or \
                      driver.find_elements(By.CSS_SELECTOR, "div[class*='job']")
        
        if job_listings:
            print(f"Found {len(job_listings)} potential job listings")
            
            # Print the outer HTML of the first listing to examine structure
            if len(job_listings) > 0:
                first_job = job_listings[0]
                print("\nFirst job listing HTML structure:")
                print(first_job.get_attribute('outerHTML')[:1000])  # First 1000 chars
                
                # Try to identify common elements within
                print("\nAttempting to extract job details from first listing:")
                
                # Looking for potential title elements
                title_elements = first_job.find_elements(By.CSS_SELECTOR, "a") or \
                               first_job.find_elements(By.CSS_SELECTOR, "h2") or \
                               first_job.find_elements(By.CSS_SELECTOR, "div[class*='title']")
                
                for i, elem in enumerate(title_elements[:3]):  # First 3 potential title elements
                    print(f"Potential title element {i+1}: {elem.text}")
        else:
            print("Could not find job listings with common selectors")
            
            # Let's print all the div elements with class attributes to see structure
            divs_with_class = driver.find_elements(By.CSS_SELECTOR, "div[class]")
            print(f"\nFound {len(divs_with_class)} divs with class attributes")
            
            # Print class names of first 10 div elements
            for i, div in enumerate(divs_with_class[:10]):
                print(f"Div {i+1} class: {div.get_attribute('class')}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
    
    finally:
        # Close the browser
        driver.quit()

# Run the analysis
analyze_with_selenium("https://www.naukri.com/data-analyst-jobs-in-india")