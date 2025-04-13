from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os

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
        
        # Wait for the page to load - longer wait time
        print("Waiting for page to load...")
        time.sleep(10)
        
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
        job_related_divs = driver.find_elements("xpath", "//div[contains(@class, 'job')]")
        print(f"Found {len(job_related_divs)} divs with 'job' in class name")
        
        # List all article elements
        articles = driver.find_elements("tag name", "article")
        print(f"Found {len(articles)} article elements")
        
        # List common container elements
        containers = driver.find_elements("xpath", "//div[@id='root' or @id='content' or @id='main' or @id='app']")
        for container in containers:
            print(f"Found container: {container.get_attribute('id')}")
        
        # Print first few div elements with class attributes
        print("\nFirst 5 divs with class attributes:")
        divs_with_class = driver.find_elements("xpath", "//div[@class]")
        for i, div in enumerate(divs_with_class[:5]):
            class_name = div.get_attribute("class")
            print(f"{i+1}. Class: {class_name}")
            # Also print first child element if any
            children = div.find_elements("xpath", "./*")
            if children:
                print(f"   First child: <{children[0].tag_name}> with class '{children[0].get_attribute('class')}'")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        # Close the browser
        driver.quit()

# URL for data analyst jobs in India
url = "https://www.naukri.com/data-analyst-jobs-in-india"

# Run the analysis
analyze_naukri_page(url)