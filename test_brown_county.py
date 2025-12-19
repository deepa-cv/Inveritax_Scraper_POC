"""
Test script for Brown County Scraper with specific parcel numbers
"""

from scraper import BrownCountyScraper
from brown_county_config import (
    TEST_PARCEL_NUMBERS,
    OUTPUT_CSV_FILE,
    OUTPUT_EXCEL_FILE,
    OUTPUT_JSON_FILE,
    SCRAPER_BASE_URL,
    SCRAPER_HEADLESS,
    SCRAPER_SELENIUM_TIMEOUT
)
from brown_county_test_helpers import (
    print_test_info,
    save_results_to_files,
    print_detailed_results,
    print_success_summary,
    print_no_results_warning
)


def main():
    # Initialize scraper
    scraper = BrownCountyScraper(
        base_url=SCRAPER_BASE_URL,
        headless=SCRAPER_HEADLESS,
        selenium_timeout=SCRAPER_SELENIUM_TIMEOUT
    )
    
    # Display test information
    print_test_info(TEST_PARCEL_NUMBERS)
    
    # Scrape parcels
    print("\n" + "=" * 60)
    print("Starting scraping...")
    print("=" * 60 + "\n")
    
    results = scraper.scrape(TEST_PARCEL_NUMBERS)
    
    if results:
        # Save results to files
        save_results_to_files(
            results,
            scraper,
            OUTPUT_CSV_FILE,
            OUTPUT_EXCEL_FILE,
            OUTPUT_JSON_FILE
        )
        
        # Display detailed results
        print_detailed_results(results)
        
        # Print success summary
        print_success_summary(
            OUTPUT_CSV_FILE,
            OUTPUT_EXCEL_FILE,
            OUTPUT_JSON_FILE
        )
    else:
        print_no_results_warning()


if __name__ == "__main__":
    main()
