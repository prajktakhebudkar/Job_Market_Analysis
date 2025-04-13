from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
import time
import os
import json
import pandas as pd
import random
import logging
import argparse
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("naukri_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class NaukriScraper:
    def __init__(self, headless=True, wait_time=15):
        """Initialize the scraper with options"""
        self.wait_time = wait_time
        
        # Set up Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        
        # Add user agent to appear more like a real browser
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-notifications")
        
        # Initialize the driver
        self.driver = None
        
        # Storage for job data
        self.job_listings = []
        
    def start_driver(self):
        """Start the Chrome driver"""
        if self.driver is None:
            try:
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options)
                logger.info("Chrome driver started successfully")
            except Exception as e:
                logger.error(f"Failed to start Chrome driver: {e}")
                raise
    
    def close_driver(self):
        """Close the Chrome driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome driver closed")
    
    def load_page(self, url, retry_count=3):
        """Load a page with retries"""
        for attempt in range(retry_count):
            try:
                self.driver.get(url)
                logger.info(f"Accessing URL: {url}")
                
                # Wait for the page to load using WebDriverWait
                wait = WebDriverWait(self.driver, self.wait_time)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'job')] | //article[contains(@class, 'job')]")))
                logger.info("Page loaded successfully")
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout on attempt {attempt+1}/{retry_count}, retrying...")
                time.sleep(2 * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error loading page on attempt {attempt+1}/{retry_count}: {e}")
                time.sleep(2 * (attempt + 1))
        
        logger.error(f"Failed to load page after {retry_count} attempts")
        return False
    
    def random_sleep(self, min_seconds=2, max_seconds=5):
        """Sleep for a random time to avoid rate limiting"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
    
    def extract_job_listings(self, max_jobs_per_page=20):
        """Extract job listings from the current page"""
        page_jobs = []
        
        try:
            # Try different XPaths to find job cards
            job_cards = self.driver.find_elements(By.XPATH, "//article[contains(@class, 'job')] | //div[contains(@class, 'jobTuple')] | //div[contains(@class, 'nI-gNb-job')]")
            
            logger.info(f"Found {len(job_cards)} potential job listings on this page")
            
            # Limit the number of jobs to extract per page
            job_cards = job_cards[:max_jobs_per_page]
            
            for i, card in enumerate(job_cards):
                try:
                    job_info = self.extract_job_details(card)
                    
                    # Check if we can parse the date correctly
                    post_date = self.parse_posting_date(job_info["posted_date"])
                    job_info["parsed_date"] = post_date.strftime("%Y-%m-%d") if post_date else "Unknown"
                    
                    page_jobs.append(job_info)
                    logger.debug(f"Extracted job {i+1}/{len(job_cards)}: {job_info.get('title', 'Unknown title')}")
                except StaleElementReferenceException:
                    logger.warning("Stale element encountered, skipping job card")
                    continue
                except Exception as e:
                    logger.error(f"Error extracting job details: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Error in job extraction: {e}")
        
        return page_jobs
    
    def parse_posting_date(self, date_text):
        """Parse the posting date from text like 'Posted 2 days ago', 'Posted on 12 Apr' etc."""
        try:
            if not date_text or date_text == "Posted date not found":
                return None
                
            today = datetime.now()
            
            # Pattern for "Posted X days ago" or "Few hours ago"
            if "day" in date_text.lower():
                match = re.search(r'(\d+)\s*day', date_text.lower())
                if match:
                    days = int(match.group(1))
                    return today - timedelta(days=days)
            
            if "hour" in date_text.lower() or "hr" in date_text.lower():
                return today.replace(hour=0, minute=0, second=0, microsecond=0)  # Same day
                
            # Pattern for "Posted X weeks ago"
            if "week" in date_text.lower():
                match = re.search(r'(\d+)\s*week', date_text.lower())
                if match:
                    weeks = int(match.group(1))
                    return today - timedelta(weeks=weeks)
            
            # Pattern for "Posted X months ago"
            if "month" in date_text.lower():
                match = re.search(r'(\d+)\s*month', date_text.lower())
                if match:
                    months = int(match.group(1))
                    # Approximate months as 30 days
                    return today - timedelta(days=30 * months)
            
            # Pattern for specific date format like "Posted on 12 Apr"
            date_pattern = re.search(r'(\d{1,2})\s+([A-Za-z]{3})', date_text)
            if date_pattern:
                day = int(date_pattern.group(1))
                month = date_pattern.group(2)
                
                # Convert month abbreviation to number
                month_dict = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                
                month_num = month_dict.get(month.lower(), None)
                if month_num:
                    # Determine the year (assume current year, but if the date would be in the future, use last year)
                    year = today.year
                    date_with_current_year = datetime(year, month_num, day)
                    
                    if date_with_current_year > today:
                        year -= 1
                        
                    return datetime(year, month_num, day)
            
            return None
        except Exception as e:
            logger.error(f"Error parsing date '{date_text}': {e}")
            return None
    
    def extract_job_details(self, card):
        """Extract details from a job card"""
        job_info = {}
        
        # Use a helper function to extract text with multiple XPath attempts
        job_info["title"] = self.extract_with_xpath(card, [
            ".//a[contains(@class, 'title')]",
            ".//a[contains(@class, 'jobTitle')]",
            ".//a[contains(@title, 'Job Details')]",
            ".//h2",
            ".//a[1]"
        ], "Title")
        
        job_info["company"] = self.extract_with_xpath(card, [
            ".//a[contains(@class, 'company')]",
            ".//a[contains(@class, 'companyName')]",
            ".//span[contains(@class, 'company')]",
            ".//span[contains(@class, 'org')]"
        ], "Company")
        
        job_info["location"] = self.extract_with_xpath(card, [
            ".//span[contains(@class, 'location')]",
            ".//span[contains(@class, 'loc')]",
            ".//span[contains(@class, 'locWdth')]",
            ".//div[contains(@class, 'location')]",
            ".//span[contains(text(), 'Location')]/following-sibling::span"
        ], "Location")
        
        job_info["experience"] = self.extract_with_xpath(card, [
            ".//span[contains(@class, 'experience')]",
            ".//span[contains(@class, 'exp')]",
            ".//li[contains(text(), 'Yrs')]",
            ".//span[contains(text(), 'Experience')]/following-sibling::span"
        ], "Experience")
        
        job_info["salary"] = self.extract_with_xpath(card, [
            ".//span[contains(@class, 'salary')]",
            ".//span[contains(@class, 'sal')]",
            ".//span[contains(text(), 'PA')]",
            ".//span[contains(text(), 'CTC')]/parent::*"
        ], "Salary")
        
        job_info["description"] = self.extract_with_xpath(card, [
            ".//div[contains(@class, 'job-description')]",
            ".//div[contains(@class, 'description')]",
            ".//ul[contains(@class, 'description')]",
            ".//div[contains(@class, 'jobDesc')]"
        ], "Description")
        
        job_info["skills"] = self.extract_with_xpath(card, [
            ".//span[contains(@class, 'skill')]",
            ".//ul[contains(@class, 'skill')]/li",
            ".//div[contains(@class, 'skill')]",
            ".//span[contains(text(), 'Skills')]/following-sibling::*"
        ], "Skills")
        
        # Extract job link
        try:
            link_elem = card.find_element(By.XPATH, ".//a[contains(@class, 'title')] | .//a[contains(@class, 'jobTitle')] | .//a[1]")
            job_info["link"] = link_elem.get_attribute("href")
        except NoSuchElementException:
            job_info["link"] = "Link not found"
        
        job_info["posted_date"] = self.extract_with_xpath(card, [
            ".//span[contains(@class, 'date')]",
            ".//div[contains(@class, 'date')]",
            ".//span[contains(text(), 'day')]",
            ".//span[contains(text(), 'Posted')]",
            ".//span[contains(text(), 'hour')]"
        ], "Posted date")
        
        # Additional fields
        job_info["job_id"] = self.extract_attribute(card, "id", "job-card-id")
        job_info["extracted_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return job_info
    
    def extract_with_xpath(self, element, xpath_list, field_name):
        """Try multiple XPaths to extract text"""
        for xpath in xpath_list:
            try:
                found_element = element.find_element(By.XPATH, xpath)
                text = found_element.text.strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.debug(f"Error extracting {field_name} with XPath {xpath}: {e}")
                continue
        
        return f"{field_name} not found"
    
    def extract_attribute(self, element, attribute, default):
        """Extract an attribute from an element with a default value"""
        try:
            value = element.get_attribute(attribute)
            return value if value else default
        except:
            return default
    
    def navigate_to_next_page(self):
        """Click on the next page button"""
        try:
            # Find the next page button - try multiple potential selectors
            next_button = None
            for xpath in [
                "//a[contains(@class, 'next')]",
                "//a[contains(text(), 'Next')]",
                "//a[contains(@class, 'page-next')]",
                "//li[contains(@class, 'next')]/a",
                "//div[contains(@class, 'pagination')]/a[contains(text(), '>')]"
            ]:
                try:
                    next_button = self.driver.find_element(By.XPATH, xpath)
                    break
                except NoSuchElementException:
                    continue
            
            if next_button and "disabled" not in next_button.get_attribute("class").lower():
                # Scroll to the button first to make it visible
                self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                self.random_sleep(1, 2)
                
                # Try to click with different methods
                try:
                    logger.info("Clicking next page button")
                    next_button.click()
                except ElementClickInterceptedException:
                    logger.info("Regular click failed, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", next_button)
                
                # Wait for page to load
                wait = WebDriverWait(self.driver, self.wait_time)
                wait.until(EC.staleness_of(next_button))
                self.random_sleep(2, 4)
                return True
            else:
                logger.info("Next page button not found or disabled - reached the end of pagination")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def apply_date_filter(self, time_frame):
        """Apply date filter to search results
        time_frame: 'day', 'week', 'month', '3months', '6months', 'year' or 'all'
        """
        try:
            if time_frame == 'all':
                logger.info("No date filter applied, showing all time results")
                return True
                
            logger.info(f"Attempting to apply date filter: {time_frame}")
            
            # Look for date filter dropdown
            filter_element = None
            
            # Try different potential selectors for the date filter dropdown
            for xpath in [
                "//div[contains(text(), 'Date Posted')]/parent::*",
                "//div[contains(@class, 'datePosted')]",
                "//div[contains(@class, 'filter') and contains(text(), 'Date')]",
                "//span[contains(text(), 'Date Posted')]",
                "//a[contains(text(), 'Date Posted')]",
                "//div[contains(@class, 'filter-item')]//div[contains(text(), 'Date')]"
            ]:
                try:
                    filter_element = self.driver.find_element(By.XPATH, xpath)
                    logger.info(f"Found date filter element with XPath: {xpath}")
                    break
                except NoSuchElementException:
                    continue
            
            if not filter_element:
                logger.warning("Could not find date filter element, taking a screenshot for diagnosis")
                self.driver.save_screenshot("date_filter_not_found.png")
                return False
            
            # Click on the filter to expand it
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", filter_element)
                self.random_sleep(1, 2)
                filter_element.click()
                logger.info("Clicked on date filter dropdown")
                self.random_sleep(1, 2)
            except Exception as e:
                logger.error(f"Error clicking on date filter: {e}")
                try:
                    self.driver.execute_script("arguments[0].click();", filter_element)
                    logger.info("Used JavaScript click on date filter")
                    self.random_sleep(1, 2)
                except Exception as e:
                    logger.error(f"JavaScript click also failed: {e}")
                    return False
            
            # Take a screenshot after clicking the filter
            self.driver.save_screenshot("date_filter_dropdown.png")
            
            # Select the appropriate time frame
            time_frame_mapping = {
                'day': ['Today', '1 Day', 'Past 24 hours', 'Last 24 hours'],
                'week': ['Past Week', 'Last 7 days', '7 Days', 'One Week'],
                'month': ['Past Month', 'Last 30 days', '30 Days', 'One Month'],
                '3months': ['Past 3 Months', 'Last 90 days', '90 Days', 'Three Months'],
                '6months': ['Past 6 Months', 'Last 180 days', '180 Days', 'Six Months'],
                'year': ['Past Year', 'Last 365 days', '365 Days', 'One Year']
            }
            
            # Get the list of labels to try for the selected time frame
            labels_to_try = time_frame_mapping.get(time_frame, [time_frame])
            
            # Try each possible label for the time frame
            selected = False
            for label in labels_to_try:
                try:
                    option_xpath = f"//label[contains(text(), '{label}')] | //div[contains(text(), '{label}')] | //a[contains(text(), '{label}')]"
                    logger.info(f"Looking for option with XPath: {option_xpath}")
                    
                    option_element = self.driver.find_element(By.XPATH, option_xpath)
                    self.driver.execute_script("arguments[0].scrollIntoView();", option_element)
                    self.random_sleep(1, 2)
                    option_element.click()
                    logger.info(f"Selected time frame: {label}")
                    self.random_sleep(2, 3)
                    selected = True
                    break
                except NoSuchElementException:
                    logger.debug(f"Option '{label}' not found with direct xpath")
                    continue
                except Exception as e:
                    logger.error(f"Error selecting time frame '{label}': {e}")
                    continue
            
            if not selected:
                # Try to find all available options and log them for debugging
                try:
                    available_options = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'filter')]/div/label | //div[contains(@class, 'dropdown')]/div")
                    option_texts = [opt.text.strip() for opt in available_options if opt.text.strip()]
                    logger.info(f"Available filter options: {option_texts}")
                    
                    # Take a screenshot showing the dropdown
                    self.driver.save_screenshot("date_filter_options.png")
                    
                    # Try clicking the first date-related option if any exists
                    for opt in available_options:
                        text = opt.text.strip().lower()
                        if ('day' in text or 'week' in text or 'month' in text) and text:
                            logger.info(f"Attempting to click found option: {text}")
                            self.driver.execute_script("arguments[0].scrollIntoView();", opt)
                            opt.click()
                            self.random_sleep(2, 3)
                            selected = True
                            break
                except Exception as e:
                    logger.error(f"Error finding alternative date options: {e}")
            
            if not selected:
                logger.warning(f"Could not select any time frame option for '{time_frame}'")
                # Try to close the dropdown if we couldn't select anything
                try:
                    # Try clicking elsewhere on the page to close the dropdown
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    ActionChains(self.driver).move_to_element_with_offset(body, 10, 10).click().perform()
                except:
                    pass
                return False
            
            # Wait for results to refresh
            self.random_sleep(3, 5)
            return True
                
        except Exception as e:
            logger.error(f"Error applying date filter: {e}")
            return False
    
    def construct_search_url(self, job_title=None, location=None):
        """Construct the search URL based on parameters"""
        base_url = "https://www.naukri.com"
        
        if job_title and location:
            # Replace spaces with hyphens and make lowercase for the URL
            formatted_job_title = job_title.lower().replace(" ", "-")
            formatted_location = location.lower().replace(" ", "-")
            
            # Construct the URL based on Naukri's URL pattern
            search_url = f"{base_url}/{formatted_job_title}-jobs-in-{formatted_location}"
        elif job_title:
            formatted_job_title = job_title.lower().replace(" ", "-")
            search_url = f"{base_url}/{formatted_job_title}-jobs"
        elif location:
            formatted_location = location.lower().replace(" ", "-")
            search_url = f"{base_url}/jobs-in-{formatted_location}"
        else:
            # Default URL for all jobs
            search_url = f"{base_url}/jobs"
        
        return search_url
    
    def scrape_jobs(self, job_title=None, location=None, time_frame="month", pages=5, max_jobs_per_page=20):
        """Scrape multiple pages of job listings with filters"""
        try:
            self.start_driver()
            
            # Format the search URL
            search_url = self.construct_search_url(job_title, location)
            
            # Initialize tracker for total jobs
            total_jobs_scraped = 0
            current_page = 1
            
            # Load the initial page
            page_loaded = self.load_page(search_url)
            if not page_loaded:
                logger.error("Failed to load the initial search page")
                return self.job_listings
            
            # Take a screenshot of the initial page
            self.driver.save_screenshot("naukri_initial_page.png")
            
            # Apply date filter if specified and not 'all'
            if time_frame and time_frame.lower() != 'all':
                filter_applied = self.apply_date_filter(time_frame)
                if filter_applied:
                    logger.info(f"Successfully applied {time_frame} filter")
                else:
                    logger.warning(f"Could not apply {time_frame} filter, continuing with default results")
            
            # Scrape the specified number of pages
            while current_page <= pages:
                logger.info(f"Scraping page {current_page} of {pages}")
                
                # Take a screenshot of each page (for debugging)
                screenshot_path = f"naukri_page_{current_page}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved to {screenshot_path}")
                
                # Extract jobs from the current page
                page_jobs = self.extract_job_listings(max_jobs_per_page)
                
                # Add to our total job listings
                self.job_listings.extend(page_jobs)
                total_jobs_scraped += len(page_jobs)
                logger.info(f"Extracted {len(page_jobs)} jobs from page {current_page}")
                
                # Save incremental results every 2 pages to prevent data loss
                if current_page % 2 == 0:
                    self.save_incremental_data(job_title, location, time_frame, current_page)
                
                # Random delay to avoid detection
                self.random_sleep(3, 7)
                
                # Navigate to the next page if we're not at the last requested page
                if current_page < pages:
                    next_page_available = self.navigate_to_next_page()
                    if not next_page_available:
                        logger.info("No more pages available")
                        break
                
                current_page += 1
            
            logger.info(f"Total jobs scraped: {total_jobs_scraped} from {current_page-1} pages")
            return self.job_listings
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return self.job_listings
        
        finally:
            self.close_driver()
    
    def save_incremental_data(self, job_title, location, time_frame, current_page):
        """Save the data incrementally to prevent data loss"""
        if not self.job_listings:
            return
            
        try:
            # Create a filename based on the search parameters
            job_title_str = job_title.replace(' ', '_') if job_title else "all"
            location_str = location.replace(' ', '_') if location else "all"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
            
            # Save to JSON
            json_path = f"data/incremental_{job_title_str}_{location_str}_{time_frame}_page{current_page}_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.job_listings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved incremental data to {json_path}")
        except Exception as e:
            logger.error(f"Error saving incremental data: {e}")
    
    def save_data(self, job_title=None, location=None, time_frame=None, formats=None):
        """Save the scraped data in multiple formats"""
        if formats is None:
            formats = ["json", "csv", "excel"]
        
        if not self.job_listings:
            logger.warning("No job listings to save")
            return None
            
        # Create a filename based on the search parameters
        job_title_str = job_title.replace(' ', '_') if job_title else "all"
        location_str = location.replace(' ', '_') if location else "all"
        time_frame_str = time_frame if time_frame else "all_time"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        base_filename = f"{job_title_str}_{location_str}_{time_frame_str}_{timestamp}"
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        if "json" in formats:
            json_path = f"data/{base_filename}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.job_listings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON data to {json_path}")
        
        if ("csv" in formats or "excel" in formats):
            # Convert to pandas DataFrame
            df = pd.DataFrame(self.job_listings)
            
            if "csv" in formats:
                csv_path = f"data/{base_filename}.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8")
                logger.info(f"Saved CSV data to {csv_path}")
            
            if "excel" in formats:
                excel_path = f"data/{base_filename}.xlsx"
                df.to_excel(excel_path, index=False)
                logger.info(f"Saved Excel data to {excel_path}")
        
        # Print summary statistics
        self.print_data_summary()
        
        return base_filename
    
    def print_data_summary(self):
        """Print a summary of the data collected"""
        if not self.job_listings:
            logger.info("No job listings to summarize")
            return
            
        try:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(self.job_listings)
            
            # Number of jobs
            total_jobs = len(df)
            logger.info(f"Total jobs collected: {total_jobs}")
            
            # Companies breakdown
            companies_count = df['company'].value_counts().head(10)
            logger.info("Top 10 companies:")
            for company, count in companies_count.items():
                logger.info(f"  - {company}: {count} jobs")
            
            # Locations breakdown
            locations_count = df['location'].value_counts().head(10)
            logger.info("Top 10 locations:")
            for location, count in locations_count.items():
                logger.info(f"  - {location}: {count} jobs")
            
            # Job titles breakdown (partial matches)
            common_roles = ['Data', 'Engineer', 'Developer', 'Manager', 'Analyst', 'Sales', 'Marketing']
            for role in common_roles:
                role_count = df[df['title'].str.contains(role, case=False, na=False)].shape[0]
                if role_count > 0:
                    logger.info(f"  - Jobs with '{role}' in title: {role_count}")
            
            # Date posted summary
            if 'parsed_date' in df.columns:
                valid_dates = df[df['parsed_date'] != 'Unknown']
                if not valid_dates.empty:
                    min_date = valid_dates['parsed_date'].min()
                    max_date = valid_dates['parsed_date'].max()
                    logger.info(f"Date range: {min_date} to {max_date}")
            
            logger.info("Data summary complete")
        except Exception as e:
            logger.error
    def filter_by_date(self, max_days=30):
        """Filter job listings based on posting date - useful when date filter on site doesn't work
    
        Args:
            max_days: Maximum age of job postings in days
    
        Returns:
            Filtered list of job listings
        """
        if not self.job_listings:
            return []
        
        today = datetime.now()
        filtered_jobs = []

        for job in self.job_listings:
            try:
                # Skip jobs with unknown posting date
                if job.get('parsed_date') == 'Unknown':
                    continue
            
                # Convert the parsed date to datetime
                job_date = datetime.strptime(job.get('parsed_date'), "%Y-%m-%d")
        
                # Calculate the age of the job in days
                age_days = (today - job_date).days
        
                # Include jobs that are within the specified time frame
                if age_days <= max_days:
                    filtered_jobs.append(job)
            except Exception as e:
                logger.error(f"Error filtering job by date: {e}")
                continue
            
        logger.info(f"Filtered {len(self.job_listings)} jobs down to {len(filtered_jobs)} within {max_days} days")
        return filtered_jobs
        
def main():
    """Main function to run the scraper from command line"""
    parser = argparse.ArgumentParser(description="Advanced Naukri.com Job Scraper")
    parser.add_argument("--job_title", type=str, help="Job title to search for (optional)")
    parser.add_argument("--location", type=str, help="Location to search in (optional)")
    parser.add_argument("--time_frame", type=str, default="month", 
                        choices=["day", "week", "month", "3months", "6months", "year", "all"],
                        help="Time frame filter for job postings (default: month)")
    parser.add_argument("--pages", type=int, default=10, help="Number of pages to scrape (default: 10)")
    parser.add_argument("--jobs_per_page", type=int, default=20, help="Maximum jobs to extract per page (default: 20)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--formats", type=str, default="json,csv,excel", help="Output formats (comma-separated)")
    parser.add_argument("--post_filter_days", type=int, help="Additional filter to only include jobs posted within X days")
    
    args = parser.parse_args()
    
    # Create a scraper instance
    scraper = NaukriScraper(headless=args.headless)
    
    # Run the scraper
    job_title_str = args.job_title if args.job_title else "all jobs"
    location_str = args.location if args.location else "any location"
    logger.info(f"Starting job search for {job_title_str} in {location_str} from the past {args.time_frame}")
    
    # Scrape the jobs
    jobs = scraper.scrape_jobs(
        job_title=args.job_title,
        location=args.location,
        time_frame=args.time_frame,
        pages=args.pages,
        max_jobs_per_page=args.jobs_per_page
    )
    
    # Apply additional date filtering if specified
    if args.post_filter_days and jobs:
        logger.info(f"Applying additional date filtering: Jobs within {args.post_filter_days} days")
        filtered_jobs = scraper.filter_by_date(max_days=args.post_filter_days)
        if filtered_jobs:
            scraper.job_listings = filtered_jobs
            logger.info(f"Filtered to {len(filtered_jobs)} jobs within {args.post_filter_days} days")
    
    # Save the data
    formats = args.formats.split(",")
    scraper.save_data(
        job_title=args.job_title, 
        location=args.location, 
        time_frame=args.time_frame, 
        formats=formats
    )
    
    logger.info(f"Scraping complete! Collected {len(jobs)} job listings.")
    logger.info("Check the 'data' directory for the output files.")


if __name__ == "__main__":
    main()