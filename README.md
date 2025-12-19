# Tax Data Scraper - Multi-County Repository

Scrapers for extracting tax and property data from multiple county websites (La Crosse, Brown, Green Lake).

## Quick Start

```bash
# Setup
cd venv
pip install -r requirements.txt

# Run tests
python test_lacrosse_normalized.py      # La Crosse with normalization
python test_lacrosse.py                 # La Crosse basic
python test_brown_county.py             # Brown County
python test_website1.py                 # Green Lake County
```

## Files Overview

### Core Files
- **`scraper.py`** - Base scrapers (Green Lake, Brown County)
- **`lacrosse_scraper.py`** - La Crosse County scraper
- **`data_normalizer.py`** - Normalizes data into 5 database tables
- **`multi_county_scraper.py`** - Multi-county framework

### Test Scripts
- **`test_lacrosse_normalized.py`** - La Crosse with normalized output (recommended)
- **`test_lacrosse.py`** - La Crosse basic test
- **`test_brown_county.py`** - Brown County test
- **`test_website1.py`** - Green Lake County test

### Config Files
- **`brown_county_config.py`** - Brown County settings
- **`brown_county_test_helpers.py`** - Brown County test utilities

## Configuration

### La Crosse County
Edit parcel IDs in test script:
```python
parcel_ids = ["01-00023-010", "01-00257-000"]
```

### Brown County
Edit `brown_county_config.py`:
```python
TEST_PARCEL_NUMBERS = ["1-1360-1"]
SCRAPER_HEADLESS = True  # False to see browser
```

## Output Files

### Normalized (Recommended)
Creates 5 CSV files + 1 Excel file:
- `lacrosse_normalized_properties.csv`
- `lacrosse_normalized_tax_periods.csv`
- `lacrosse_normalized_installments.csv`
- `lacrosse_normalized_delinquent_taxes.csv`
- `lacrosse_normalized_penalties_interest.csv`
- `lacrosse_normalized_all_tables.xlsx`

### Raw Data
- CSV, Excel, and JSON files with raw scraped data

## Requirements

- Python 3.7+
- ChromeDriver (for Selenium)
- Packages: `requests`, `beautifulsoup4`, `selenium`, `pandas`, `lxml`, `openpyxl`

## Database Integration

Normalized CSV files are database-ready. See `DATABASE_SCHEMA.md` for SQL schema and import instructions.

## Troubleshooting

- **ChromeDriver**: Install via `brew install chromedriver` (macOS)
- **Selenium errors**: Set `headless=False` to see browser
- **Missing data**: Check raw JSON files for actual scraped data
