"""
Test script for Website 1 Scraper with specific parcel numbers
"""

from scraper import Website1Scraper
import json

def main():
    # Initialize scraper
    # If login is required, provide credentials:
    # scraper = Website1Scraper(username="your_username", password="your_password")
    scraper = Website1Scraper()
    
    # Test parcel numbers
    parcel_numbers = [
        "6000350000",
        "6000350100",
        "006000360000",
        "6000360100",
        "006000400000",
        "6000400000"
    ]
    
    print("=" * 60)
    print("Testing Website 1 Scraper")
    print("=" * 60)
    print(f"\nTesting with {len(parcel_numbers)} parcel numbers:")
    for i, pn in enumerate(parcel_numbers, 1):
        print(f"  {i}. {pn}")
    
    # Scrape parcels
    print("\n" + "=" * 60)
    print("Starting scraping...")
    print("=" * 60 + "\n")
    
    results = scraper.scrape(parcel_numbers)
    
    if results:
        # Save to CSV
        csv_filename = "greenlake_parcels_test.csv"
        scraper.save_to_csv(results, csv_filename)
        
        # Save to Excel
        excel_filename = "greenlake_parcels_test.xlsx"
        scraper.save_to_excel(results, excel_filename)
        
        # Save raw JSON for debugging
        json_filename = "greenlake_parcels_test.json"
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Raw data saved to {json_filename}")
        
        print("\n" + "=" * 60)
        print(f"SUCCESS: Scraped {len(results)} parcel record(s)")
        print("=" * 60)
        
        print("\nDetailed Results:")
        print("-" * 60)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Parcel Number: {result.get('ParcelNumber')}")
            
            # Show search data summary
            search_data = result.get('SearchData', [])
            if search_data and len(search_data) > 0:
                first_result = search_data[0]
                print(f"   Parcel ID: {first_result.get('ParcelId', 'N/A')}")
                print(f"   Owner: {first_result.get('OwnerName', 'N/A')}")
                print(f"   District: {first_result.get('DistrictName', 'N/A')}")
            
            # Show tax bill data summary
            tax_data = result.get('TaxBillData', {})
            if tax_data:
                print(f"   Tax Bill Data Available: Yes")
                if isinstance(tax_data, list) and len(tax_data) > 0:
                    print(f"   Number of Tax Bills: {len(tax_data)}")
                elif isinstance(tax_data, dict):
                    print(f"   Tax Bill Keys: {list(tax_data.keys())[:5]}...")
            
            # Show error if present
            if 'Error' in result:
                print(f"   Error: {result.get('Error')}")
        
        print("\n" + "=" * 60)
        print(f"Files saved:")
        print(f"  - {csv_filename}")
        print(f"  - {excel_filename}")
        print(f"  - {json_filename}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("WARNING: No results found for any parcel numbers")
        print("=" * 60)
        print("\nPossible reasons:")
        print("  1. Parcel numbers may not exist in the database")
        print("  2. Login may be required (provide credentials)")
        print("  3. API endpoints may have changed")
        print("  4. Network/connection issues")

if __name__ == "__main__":
    main()

