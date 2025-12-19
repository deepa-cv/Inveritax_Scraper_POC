"""
Test script for La Crosse County Scraper
"""

from lacrosse_scraper import LaCrosseScraper
import json

def main():
    # Initialize scraper
    scraper = LaCrosseScraper()
    
    # Test parcel IDs (example format from the Postman collection)
    parcel_ids = [
        "01-00023-010",
        "01-00257-000",
        # Add more parcel IDs as needed
    ]
    
    print("=" * 60)
    print("Testing La Crosse County Scraper")
    print("=" * 60)
    print(f"\nTesting with {len(parcel_ids)} parcel ID(s):")
    for i, pid in enumerate(parcel_ids, 1):
        print(f"  {i}. {pid}")
    
    # Scrape parcels
    print("\n" + "=" * 60)
    print("Starting scraping workflow...")
    print("=" * 60 + "\n")
    
    try:
        results = scraper.scrape(parcel_ids, tax_year="2025")
        
        if results:
            # Save to CSV
            csv_filename = "lacrosse_parcels_test.csv"
            scraper.save_to_csv(results, csv_filename)
            
            # Save to Excel
            excel_filename = "lacrosse_parcels_test.xlsx"
            scraper.save_to_excel(results, excel_filename)
            
            # Save raw JSON for debugging
            json_filename = "lacrosse_parcels_test.json"
            with open(json_filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✓ Raw data saved to {json_filename}")
            
            print("\n" + "=" * 60)
            print(f"SUCCESS: Processed {len(results)} parcel record(s)")
            print("=" * 60)
            
            print("\nDetailed Results:")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Parcel ID: {result.get('parcel_id')}")
                
                # Show search data summary
                search_data = result.get('search_data')
                if search_data:
                    print(f"   Search Data Available: Yes")
                    if isinstance(search_data, dict):
                        if 'data' in search_data:
                            print(f"   Search Results Count: {len(search_data.get('data', []))}")
                        elif 'html' in search_data:
                            print(f"   Search Response: HTML (Status {search_data.get('status_code', 'N/A')})")
                        else:
                            print(f"   Search Data Keys: {list(search_data.keys())[:5]}")
                
                # Show tax data summary
                tax_data = result.get('tax_data')
                if tax_data:
                    print(f"   Tax Data Available: Yes")
                    if isinstance(tax_data, dict):
                        print(f"   Tax Data Keys: {list(tax_data.keys())[:5]}")
                
                # Show error if present
                if result.get('error'):
                    print(f"   Error: {result.get('error')}")
            
            print("\n" + "=" * 60)
            print(f"Files saved:")
            print(f"  - {csv_filename}")
            print(f"  - {excel_filename}")
            print(f"  - {json_filename}")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("WARNING: No results found")
            print("=" * 60)
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
