# Job_Market_Analysis
Indian job market analyzed using Naukri.com

# Scrape all jobs from the past month (default)
python joblistingscraper.py

# Scrape all jobs from the past 3 months
python joblistingscraper.py --time_frame 3months

# Scrape all jobs from the past 6 months in a specific location
python joblistingscraper.py --time_frame 6months --location "Mumbai"

# Scrape all jobs with post-filtering to ensure only last 14 days jobs are included
python joblistingscraper.py --post_filter_days 14
