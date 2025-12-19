"""
Helper functions for Brown County Scraper tests
"""

import json
from typing import List, Dict, Any


def print_header(title: str, width: int = 60):
    """Print a formatted header"""
    print("=" * width)
    print(title)
    print("=" * width)


def print_test_info(parcel_numbers: List[str]):
    """Print test information"""
    print_header("Testing Brown County Scraper")
    print(f"\nTesting with {len(parcel_numbers)} parcel numbers:")
    for i, pn in enumerate(parcel_numbers, 1):
        print(f"  {i}. {pn}")


def print_step_info(step_number: int, step_name: str):
    """Print step information"""
    print(f"\n{'='*60}")
    print(f"Step {step_number}: {step_name}")
    print(f"{'='*60}")


def save_results_to_files(results: List[Dict[str, Any]], scraper, csv_filename: str, 
                          excel_filename: str, json_filename: str):
    """
    Save results to CSV, Excel, and JSON files
    
    Args:
        results: List of result dictionaries
        scraper: Scraper instance with save methods
        csv_filename: CSV output filename
        excel_filename: Excel output filename
        json_filename: JSON output filename
    """
    # Save to CSV
    scraper.save_to_csv(results, csv_filename)
    
    # Save to Excel
    scraper.save_to_excel(results, excel_filename)
    
    # Save raw JSON for debugging
    with open(json_filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Raw data saved to {json_filename}")


def print_detailed_results(results: List[Dict[str, Any]]):
    """
    Print detailed results for each parcel
    
    Args:
        results: List of result dictionaries
    """
    print_header(f"SUCCESS: Scraped {len(results)} parcel record(s)")
    
    print("\nDetailed Results:")
    print("-" * 60)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Parcel Number: {result.get('ParcelNumber')}")
        
        # Show Property Details
        property_details = result.get('PropertyDetails', {})
        if property_details:
            print(f"\n   Property Details:")
            for key, value in property_details.items():
                if value:
                    print(f"     - {key.replace('_', ' ').title()}: {value}")
        
        # Show Installments
        installments = result.get('Installments', [])
        if installments:
            print(f"\n   Installments ({len(installments)}):")
            for inst in installments:
                print(f"     - Due Date: {inst.get('due_date', 'N/A')}, Amount: ${inst.get('amount', 'N/A')}")
        else:
            print(f"\n   Installments: None found")
        
        # Show Tax History
        tax_history = result.get('TaxHistory', [])
        if tax_history:
            print(f"\n   Tax History ({len(tax_history)} years):")
            for hist in tax_history[:5]:  # Show first 5 years
                print(f"     - Year: {hist.get('year', 'N/A')}, "
                      f"Amount: ${hist.get('amount', 'N/A')}, "
                      f"Paid: ${hist.get('paid', 'N/A')}, "
                      f"Status: {hist.get('status', 'N/A')}")
            if len(tax_history) > 5:
                print(f"     ... and {len(tax_history) - 5} more years")
        else:
            print(f"\n   Tax History: None found")
        
        # Show error if present
        if 'Error' in result:
            print(f"\n   Error: {result.get('Error')}")


def print_success_summary(csv_filename: str, excel_filename: str, json_filename: str):
    """Print success summary with file locations"""
    print("\n" + "=" * 60)
    print(f"Files saved:")
    print(f"  - {csv_filename}")
    print(f"  - {excel_filename}")
    print(f"  - {json_filename}")
    print("=" * 60)


def print_no_results_warning():
    """Print warning when no results are found"""
    print("\n" + "=" * 60)
    print("WARNING: No results found for any parcel numbers")
    print("=" * 60)
    print("\nPossible reasons:")
    print("  1. Parcel numbers may not exist in the database")
    print("  2. Website structure may have changed")
    print("  3. Network/connection issues")
    print("  4. Selenium WebDriver issues (check ChromeDriver installation)")
