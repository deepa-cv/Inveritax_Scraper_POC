"""
Configuration file for Brown County Scraper tests
"""

# Test parcel numbers
TEST_PARCEL_NUMBERS = [
    "1-1360-1",
    # Add more test parcel numbers here
]

# Output file names
OUTPUT_CSV_FILE = "brown_county_parcels_test.csv"
OUTPUT_EXCEL_FILE = "brown_county_parcels_test.xlsx"
OUTPUT_JSON_FILE = "brown_county_parcels_test.json"

# Scraper configuration
SCRAPER_BASE_URL = "https://prod-landrecords.browncountywi.gov"
SCRAPER_HEADLESS = True  # Set to False to see browser actions
SCRAPER_SELENIUM_TIMEOUT = 30  # Timeout in seconds for Selenium operations
