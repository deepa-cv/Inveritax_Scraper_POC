"""
Test script for La Crosse County Scraper with Data Normalization
"""

from lacrosse_scraper import LaCrosseScraper
from data_normalizer import TaxDataNormalizer
import json
import os

def main():
    # Initialize scraper
    scraper = LaCrosseScraper()
    
    # Test parcel IDs
    parcel_ids = [
        "01-00023-010",
        "01-00257-000",
        # Add more parcel IDs as needed
    ]
    
    print("=" * 60)
    print("Testing La Crosse County Scraper with Normalization")
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
            # Save raw JSON for debugging
            json_filename = "lacrosse_parcels_raw.json"
            with open(json_filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n✓ Raw data saved to {json_filename}")
            
            # Normalize data
            print("\n" + "=" * 60)
            print("Normalizing data into structured format...")
            print("=" * 60 + "\n")
            
            normalizer = TaxDataNormalizer()
            normalized_data = normalizer.normalize_scraped_data(results)
            
            # Save normalized data to separate CSV files
            base_filename = "lacrosse_normalized"
            normalizer.save_to_csv_files(normalized_data, base_filename)
            
            # Also save to Excel with multiple sheets
            excel_filename = f"{base_filename}_all_tables.xlsx"
            normalizer.save_to_excel_sheets(normalized_data, excel_filename)
            
            print("\n" + "=" * 60)
            print(f"SUCCESS: Processed {len(results)} parcel record(s)")
            print("=" * 60)
            
            # Print summary
            print("\nData Summary:")
            print("-" * 60)
            print(f"Properties: {len(normalized_data['properties'])}")
            print(f"Tax Periods: {len(normalized_data['tax_periods'])}")
            print(f"Installments: {len(normalized_data['installments'])}")
            print(f"Delinquent Taxes: {len(normalized_data['delinquent_taxes'])}")
            print(f"Penalties/Interest: {len(normalized_data['penalties_interest'])}")
            
            print("\n" + "=" * 60)
            print("Files created:")
            print(f"  - {json_filename} (raw data)")
            for table_name in normalized_data.keys():
                print(f"  - {base_filename}_{table_name}.csv")
            print(f"  - {excel_filename} (all tables)")
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
