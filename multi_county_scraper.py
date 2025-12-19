"""
Multi-County Tax Scraper Framework

This module provides a framework for scraping tax data from multiple counties
and normalizing it into a consistent database-ready format.
"""

from typing import List, Dict, Optional
from data_normalizer import TaxDataNormalizer
from lacrosse_scraper import LaCrosseScraper
import pandas as pd
import json
from datetime import datetime


class MultiCountyScraper:
    """Framework for scraping multiple counties"""
    
    def __init__(self):
        self.scrapers = {
            'lacrosse': LaCrosseScraper,
            # Add other county scrapers here as they're implemented
            # 'brown': BrownCountyScraper,
            # 'greenlake': GreenLakeScraper,
        }
        self.normalizer = TaxDataNormalizer()
    
    def scrape_county(self, county_name: str, parcel_ids: List[str], **kwargs) -> Dict:
        """
        Scrape a specific county
        
        Args:
            county_name: Name of the county (e.g., 'lacrosse')
            parcel_ids: List of parcel IDs to scrape
            **kwargs: Additional arguments for the scraper
            
        Returns:
            Dictionary with normalized data tables
        """
        if county_name.lower() not in self.scrapers:
            raise ValueError(f"County '{county_name}' not supported. Available: {list(self.scrapers.keys())}")
        
        print(f"\n{'='*60}")
        print(f"Scraping {county_name.upper()} County")
        print(f"{'='*60}\n")
        
        # Initialize scraper
        scraper_class = self.scrapers[county_name.lower()]
        scraper = scraper_class()
        
        # Scrape
        results = scraper.scrape(parcel_ids, **kwargs)
        
        # Normalize
        normalized_data = self.normalizer.normalize_scraped_data(results)
        
        # Add county identifier to all tables
        for table_name, df in normalized_data.items():
            if not df.empty:
                df['county'] = county_name.lower()
        
        return normalized_data
    
    def scrape_multiple_counties(self, county_configs: List[Dict]) -> Dict[str, pd.DataFrame]:
        """
        Scrape multiple counties and combine results
        
        Args:
            county_configs: List of dicts with 'county', 'parcel_ids', and optional kwargs
            
        Returns:
            Combined normalized data tables
        """
        all_data = {
            'properties': [],
            'tax_periods': [],
            'installments': [],
            'delinquent_taxes': [],
            'penalties_interest': []
        }
        
        for config in county_configs:
            county_name = config['county']
            parcel_ids = config['parcel_ids']
            kwargs = config.get('kwargs', {})
            
            try:
                county_data = self.scrape_county(county_name, parcel_ids, **kwargs)
                
                # Combine data
                for table_name in all_data.keys():
                    if not county_data[table_name].empty:
                        all_data[table_name].append(county_data[table_name])
            
            except Exception as e:
                print(f"\n✗ Error scraping {county_name}: {e}")
                continue
        
        # Combine all DataFrames
        combined_data = {}
        for table_name, dfs in all_data.items():
            if dfs:
                combined_data[table_name] = pd.concat(dfs, ignore_index=True)
            else:
                # Create empty DataFrame with proper columns
                combined_data[table_name] = self.normalizer._create_properties_df() if table_name == 'properties' else pd.DataFrame()
        
        return combined_data
    
    def save_normalized_data(self, data: Dict[str, pd.DataFrame], output_dir: str = ".", prefix: str = "tax_data"):
        """
        Save normalized data to CSV files and Excel
        
        Args:
            data: Dictionary of DataFrames
            output_dir: Directory to save files
            prefix: Prefix for filenames
        """
        import os
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save individual CSV files
        for table_name, df in data.items():
            csv_path = os.path.join(output_dir, f"{prefix}_{table_name}.csv")
            df.to_csv(csv_path, index=False)
            print(f"✓ Saved {table_name} to {csv_path} ({len(df)} rows)")
        
        # Save combined Excel file
        excel_path = os.path.join(output_dir, f"{prefix}_all_tables.xlsx")
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for table_name, df in data.items():
                df.to_excel(writer, sheet_name=table_name, index=False)
        print(f"✓ Saved all tables to {excel_path}")
        
        return {
            'csv_files': [os.path.join(output_dir, f"{prefix}_{name}.csv") for name in data.keys()],
            'excel_file': excel_path
        }


def main():
    """Example usage"""
    scraper = MultiCountyScraper()
    
    # Example: Scrape La Crosse County
    lacrosse_parcels = [
        "01-00023-010",
        "01-00257-000",
    ]
    
    print("=" * 60)
    print("Multi-County Tax Scraper")
    print("=" * 60)
    
    # Single county
    data = scraper.scrape_county('lacrosse', lacrosse_parcels, tax_year="2025")
    scraper.save_normalized_data(data, prefix="lacrosse_tax_data")
    
    # Multiple counties (example)
    # county_configs = [
    #     {'county': 'lacrosse', 'parcel_ids': ['01-00023-010'], 'kwargs': {'tax_year': '2025'}},
    #     {'county': 'brown', 'parcel_ids': ['12345'], 'kwargs': {}},
    # ]
    # combined_data = scraper.scrape_multiple_counties(county_configs)
    # scraper.save_normalized_data(combined_data, prefix="multi_county_tax_data")


if __name__ == "__main__":
    main()
