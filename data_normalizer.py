"""
Data Normalizer for La Crosse County Tax Data

This module normalizes scraped tax data into a consistent, database-ready format.
Creates separate tables for properties, tax periods, installments, and delinquent taxes.
"""

import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime
import re


class TaxDataNormalizer:
    """Normalizes tax data into structured, database-ready format"""
    
    def __init__(self):
        self.properties = []
        self.tax_periods = []
        self.installments = []
        self.delinquent_taxes = []
        self.penalties_interest = []
    
    def normalize_scraped_data(self, scraped_results: List[Dict]) -> Dict[str, pd.DataFrame]:
        """
        Normalize scraped data into separate tables
        
        Args:
            scraped_results: List of scraped result dictionaries
            
        Returns:
            Dictionary of DataFrames, one for each table
        """
        for result in scraped_results:
            parcel_id = result.get('parcel_id')
            search_data = result.get('search_data', {})
            tax_data = result.get('tax_data', {})
            
            # Extract property information
            property_info = self._extract_property_info(parcel_id, search_data, tax_data)
            if property_info:
                self.properties.append(property_info)
            
            # Extract tax periods and installments
            if tax_data:
                periods_data = self._extract_tax_periods(parcel_id, property_info, tax_data)
                self.tax_periods.extend(periods_data)
                
                installments_data = self._extract_installments(parcel_id, property_info, tax_data)
                self.installments.extend(installments_data)
                
                delinquent_data = self._extract_delinquent_taxes(parcel_id, property_info, tax_data)
                self.delinquent_taxes.extend(delinquent_data)
                
                penalties_data = self._extract_penalties_interest(parcel_id, property_info, tax_data)
                self.penalties_interest.extend(penalties_data)
        
        # Create DataFrames
        return {
            'properties': self._create_properties_df(),
            'tax_periods': self._create_tax_periods_df(),
            'installments': self._create_installments_df(),
            'delinquent_taxes': self._create_delinquent_taxes_df(),
            'penalties_interest': self._create_penalties_interest_df()
        }
    
    def _extract_property_info(self, parcel_id: str, search_data: Dict, tax_data: Dict) -> Optional[Dict]:
        """Extract property information"""
        property_info = {
            'parcel_id': parcel_id,
            'property_id': None,
            'owner_name': None,
            'municipality': None,
            'address': None,
            'extraction_date': datetime.now().isoformat(),
            'source': 'lacrosse_county'
        }
        
        # Extract from search_data
        if isinstance(search_data, dict) and 'data' in search_data:
            results_list = search_data.get('data', [])
            if isinstance(results_list, dict):
                results_list = list(results_list.values())
            
            for res in results_list:
                if isinstance(res, dict):
                    user_defined_id = res.get('UserDefinedId') or res.get('userDefinedId')
                    if user_defined_id and str(user_defined_id).strip() == str(parcel_id).strip():
                        property_info['property_id'] = str(res.get('PropertyId') or res.get('propertyId') or '')
                        property_info['owner_name'] = self._extract_owner_name(res)
                        property_info['municipality'] = res.get('MunicipalityDescription') or res.get('municipalityDescription') or ''
                        property_info['address'] = self._extract_address(res)
                        break
        
        # Extract property_id from tax_data if not found
        if not property_info['property_id'] and isinstance(tax_data, dict):
            property_info['property_id'] = str(tax_data.get('property_id') or '')
        
        return property_info if property_info.get('property_id') or property_info.get('owner_name') else None
    
    def _extract_owner_name(self, data: Dict) -> str:
        """Extract owner name from various possible fields"""
        name_fields = [
            'ConcatenatedName', 'concatenatedName', 'OwnerName', 'ownerName',
            'FirstName', 'LastName', 'FullName', 'fullName'
        ]
        
        for field in name_fields:
            if field in data and data[field]:
                return str(data[field]).strip()
        
        # Try combining first and last name
        first_name = data.get('FirstName') or data.get('firstName') or ''
        last_name = data.get('LastName') or data.get('lastName') or ''
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()
        
        return ''
    
    def _extract_address(self, data: Dict) -> str:
        """Extract property address"""
        address_parts = []
        
        house_number = data.get('PropertyAddress_HouseNumber') or data.get('houseNumber') or ''
        street_name = data.get('PropertyAddress_StreetName') or data.get('streetName') or ''
        street_type = data.get('PropertyAddress_StreetType') or data.get('streetType') or ''
        suffix_dir = data.get('PropertyAddress_SuffixDirection') or data.get('suffixDirection') or ''
        unit_type = data.get('PropertyAddress_UnitType') or data.get('unitType') or ''
        unit_number = data.get('PropertyAddress_UnitNumber') or data.get('unitNumber') or ''
        
        if house_number:
            address_parts.append(str(house_number))
        if street_name:
            address_parts.append(str(street_name))
        if street_type:
            address_parts.append(str(street_type))
        if suffix_dir:
            address_parts.append(str(suffix_dir))
        if unit_type and unit_number:
            address_parts.append(f"{unit_type} {unit_number}")
        elif unit_number:
            address_parts.append(f"Unit {unit_number}")
        
        return ', '.join(address_parts) if address_parts else ''
    
    def _extract_tax_periods(self, parcel_id: str, property_info: Optional[Dict], tax_data: Dict) -> List[Dict]:
        """Extract tax period information"""
        periods = []
        
        # Extract from tax_data structure
        if isinstance(tax_data, dict):
            # Check if tax_data has year-based structure
            for key, year_data in tax_data.items():
                if key.isdigit() or key == 'current':
                    year = key if key.isdigit() else self._extract_year_from_data(year_data)
                    if year:
                        period = {
                            'parcel_id': parcel_id,
                            'property_id': property_info.get('property_id') if property_info else None,
                            'tax_year': year,
                            'total_tax_amount': self._extract_amount(year_data, ['total', 'amount', 'totalTax', 'total_tax']),
                            'status': self._determine_status(year_data),
                            'extraction_date': datetime.now().isoformat()
                        }
                        periods.append(period)
        
        return periods
    
    def _extract_installments(self, parcel_id: str, property_info: Optional[Dict], tax_data: Dict) -> List[Dict]:
        """Extract installment information"""
        installments = []
        
        if isinstance(tax_data, dict):
            # First, check if tax_data has year-based structure
            # Process each year's data separately
            for key, year_data in tax_data.items():
                if key.isdigit() or key == 'current':
                    tax_year = key if key.isdigit() else None
                    
                    # Extract installments from this year's data
                    year_installments = []
                    if isinstance(year_data, dict):
                        year_installments = year_data.get('installments', [])
                        # Also check nested structures
                        if 'page_extracted' in year_data:
                            year_installments.extend(year_data['page_extracted'].get('installments', []))
                        if 'api_extracted' in year_data:
                            year_installments.extend(year_data['api_extracted'].get('installments', []))
                    
                    installment_num = 1
                    for inst in year_installments:
                        if isinstance(inst, dict):
                            # Use tax_year from parent if not in inst
                            inst_year = self._extract_year_from_data(inst) or tax_year
                            
                            installment = {
                                'parcel_id': parcel_id,
                                'property_id': property_info.get('property_id') if property_info else None,
                                'installment_number': installment_num,
                                'installment_type': self._determine_installment_type(inst, installment_num),
                                'amount': self._extract_amount(inst, ['amount', 'total', 'installmentAmount', 'due']),
                                'due_date': self._extract_date(inst, ['dueDate', 'due_date', 'date', 'due']),
                                'paid_date': self._extract_date(inst, ['paidDate', 'paid_date', 'paid']),
                                'status': self._determine_installment_status(inst),
                                'tax_year': inst_year,
                                'extraction_date': datetime.now().isoformat()
                            }
                            installments.append(installment)
                            installment_num += 1
            
            # Also extract from top-level installments list (if not year-structured)
            installments_list = tax_data.get('installments', [])
            
            # Also check page_extracted and api_extracted
            if 'page_extracted' in tax_data:
                installments_list.extend(tax_data['page_extracted'].get('installments', []))
            if 'api_extracted' in tax_data:
                installments_list.extend(tax_data['api_extracted'].get('installments', []))
            
            # Only process if we haven't already processed them in year-based structure
            if not any(key.isdigit() for key in tax_data.keys() if isinstance(key, str)):
                installment_num = 1
                for inst in installments_list:
                    if isinstance(inst, dict):
                        installment = {
                            'parcel_id': parcel_id,
                            'property_id': property_info.get('property_id') if property_info else None,
                            'installment_number': installment_num,
                            'installment_type': self._determine_installment_type(inst, installment_num),
                            'amount': self._extract_amount(inst, ['amount', 'total', 'installmentAmount', 'due']),
                            'due_date': self._extract_date(inst, ['dueDate', 'due_date', 'date', 'due']),
                            'paid_date': self._extract_date(inst, ['paidDate', 'paid_date', 'paid']),
                            'status': self._determine_installment_status(inst),
                            'tax_year': self._extract_year_from_data(inst),
                            'extraction_date': datetime.now().isoformat()
                        }
                        installments.append(installment)
                        installment_num += 1
            
            # Also extract from tax_tables if available
            if 'page_extracted' in tax_data:
                page_data = tax_data['page_extracted']
                if 'tax_tables' in page_data:
                    for table in page_data['tax_tables']:
                        table_installments = self._parse_table_for_installments(table, parcel_id, property_info, tax_data)
                        installments.extend(table_installments)
        
        return installments
    
    def _extract_delinquent_taxes(self, parcel_id: str, property_info: Optional[Dict], tax_data: Dict) -> List[Dict]:
        """Extract delinquent tax information - only when there's an actual unpaid amount"""
        delinquent = []
        
        if isinstance(tax_data, dict):
            # Extract from unpaid_taxes list
            unpaid_list = tax_data.get('unpaid_taxes', [])
            
            # Also check page_extracted and api_extracted
            if 'page_extracted' in tax_data:
                unpaid_list.extend(tax_data['page_extracted'].get('unpaid_taxes', []))
            if 'api_extracted' in tax_data:
                unpaid_list.extend(tax_data['api_extracted'].get('unpaid_taxes', []))
            
            for unpaid in unpaid_list:
                if isinstance(unpaid, dict):
                    delinquent_amount = self._extract_amount(unpaid, ['amount', 'balance', 'delinquent', 'unpaid', 'owed', 'remaining', 'outstanding'])
                    
                    # Only add if there's an actual delinquent amount > 0
                    if delinquent_amount and delinquent_amount > 0:
                        # Try to extract tax year from multiple sources
                        tax_year = self._extract_year_from_data(unpaid)
                        if not tax_year:
                            # Try to get from parent tax_data structure
                            tax_year = self._extract_year_from_tax_data_context(unpaid, tax_data)
                        
                        delinquent_record = {
                            'parcel_id': parcel_id,
                            'property_id': property_info.get('property_id') if property_info else None,
                            'tax_year': tax_year,
                            'delinquent_amount': delinquent_amount,
                            'status': 'delinquent',
                            'installments_delinquent': self._extract_delinquent_installments(unpaid),
                            'extraction_date': datetime.now().isoformat()
                        }
                        delinquent.append(delinquent_record)
            
            # Also check installments for unpaid/delinquent status
            installments_list = tax_data.get('installments', [])
            if 'page_extracted' in tax_data:
                installments_list.extend(tax_data['page_extracted'].get('installments', []))
            if 'api_extracted' in tax_data:
                installments_list.extend(tax_data['api_extracted'].get('installments', []))
            
            # Group installments by tax year and check for unpaid amounts
            installments_by_year = {}
            for inst in installments_list:
                if isinstance(inst, dict):
                    year = self._extract_year_from_data(inst)
                    status = self._determine_installment_status(inst)
                    amount = self._extract_amount(inst, ['amount', 'balance', 'unpaid', 'owed', 'remaining'])
                    
                    if year and status in ['delinquent', 'unpaid'] and amount and amount > 0:
                        if year not in installments_by_year:
                            installments_by_year[year] = {
                                'total_delinquent': 0.0,
                                'installments': []
                            }
                        installments_by_year[year]['total_delinquent'] += amount
                        installments_by_year[year]['installments'].append(inst)
            
            # Create delinquent records from installments
            for year, year_data in installments_by_year.items():
                if year_data['total_delinquent'] > 0:
                    # Check if we already have a record for this year
                    existing = any(d.get('tax_year') == year for d in delinquent)
                    if not existing:
                        delinquent_record = {
                            'parcel_id': parcel_id,
                            'property_id': property_info.get('property_id') if property_info else None,
                            'tax_year': year,
                            'delinquent_amount': year_data['total_delinquent'],
                            'status': 'delinquent',
                            'installments_delinquent': ', '.join([str(i.get('installment_number', '')) for i in year_data['installments']]),
                            'extraction_date': datetime.now().isoformat()
                        }
                        delinquent.append(delinquent_record)
        
        return delinquent
    
    def _extract_year_from_tax_data_context(self, data: Dict, tax_data: Dict) -> Optional[str]:
        """Extract tax year from parent tax_data structure"""
        # Check if data is within a year-keyed structure
        for key, year_data in tax_data.items():
            if key.isdigit():
                # Check if this data dict is within this year's data
                if isinstance(year_data, dict):
                    # Check if data is in year_data's lists
                    for list_key in ['unpaid_taxes', 'installments', 'tax_tables']:
                        if list_key in year_data:
                            items = year_data[list_key] if isinstance(year_data[list_key], list) else []
                            if data in items or any(data == item for item in items if isinstance(item, dict)):
                                return key
        return None
    
    def _extract_penalties_interest(self, parcel_id: str, property_info: Optional[Dict], tax_data: Dict) -> List[Dict]:
        """Extract penalties and interest information"""
        penalties = []
        
        if isinstance(tax_data, dict):
            # Look for penalties and interest in various places
            penalty_amount = self._extract_amount(tax_data, ['penalty', 'penalties', 'penaltyAmount'])
            interest_amount = self._extract_amount(tax_data, ['interest', 'interestAmount'])
            
            if penalty_amount or interest_amount:
                penalty_record = {
                    'parcel_id': parcel_id,
                    'property_id': property_info.get('property_id') if property_info else None,
                    'tax_year': self._extract_year_from_data(tax_data),
                    'penalty_amount': penalty_amount or 0.0,
                    'interest_amount': interest_amount or 0.0,
                    'total_penalties_interest': (penalty_amount or 0.0) + (interest_amount or 0.0),
                    'extraction_date': datetime.now().isoformat()
                }
                penalties.append(penalty_record)
        
        return penalties
    
    def _extract_amount(self, data: Dict, possible_keys: List[str]) -> Optional[float]:
        """Extract monetary amount from data"""
        for key in possible_keys:
            value = data.get(key)
            if value is not None:
                # Try to convert to float
                try:
                    # Remove currency symbols and commas
                    if isinstance(value, str):
                        cleaned = re.sub(r'[^\d.-]', '', value)
                        if cleaned:
                            return float(cleaned)
                    elif isinstance(value, (int, float)):
                        return float(value)
                except (ValueError, TypeError):
                    continue
        
        # Try to find amount in string values
        for key, value in data.items():
            if isinstance(value, str) and ('$' in value or any(char.isdigit() for char in value)):
                try:
                    cleaned = re.sub(r'[^\d.-]', '', value)
                    if cleaned and '.' in cleaned:
                        return float(cleaned)
                except:
                    continue
        
        return None
    
    def _extract_date(self, data: Dict, possible_keys: List[str]) -> Optional[str]:
        """Extract date from data"""
        for key in possible_keys:
            value = data.get(key)
            if value:
                try:
                    # Try to parse as date
                    if isinstance(value, str):
                        # Try common date formats
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                            try:
                                dt = datetime.strptime(value, fmt)
                                return dt.isoformat()
                            except:
                                continue
                    return str(value)
                except:
                    continue
        return None
    
    def _extract_year_from_data(self, data: Dict) -> Optional[str]:
        """Extract tax year from data"""
        if not isinstance(data, dict):
            return None
            
        # Check common year field names
        year_fields = ['year', 'taxYear', 'tax_year', 'Year', 'TAX_YEAR', 'TaxYear', 'tax-year']
        for field in year_fields:
            if field in data and data[field]:
                year_value = str(data[field]).strip()
                # Validate it looks like a year (4 digits, reasonable range)
                if year_value.isdigit() and len(year_value) == 4:
                    year_int = int(year_value)
                    if 1900 <= year_int <= 2100:
                        return year_value
        
        # Check for year in string values (e.g., "2025 Tax Year")
        for key, value in data.items():
            if isinstance(value, str):
                # Look for 4-digit year pattern
                year_match = re.search(r'\b(19|20)\d{2}\b', value)
                if year_match:
                    year = year_match.group(0)
                    if 1900 <= int(year) <= 2100:
                        return year
        
        return None
    
    def _determine_status(self, data: Dict) -> str:
        """Determine tax status"""
        status_lower = str(data.get('status', '')).lower()
        if 'delinquent' in status_lower or 'unpaid' in status_lower:
            return 'delinquent'
        elif 'paid' in status_lower:
            return 'paid'
        return 'current'
    
    def _determine_installment_type(self, data: Dict, installment_num: int) -> str:
        """Determine installment type (1st half, 2nd half, etc.)"""
        type_str = str(data.get('type', '')).lower()
        if 'first' in type_str or '1st' in type_str or installment_num == 1:
            return '1st_half'
        elif 'second' in type_str or '2nd' in type_str or installment_num == 2:
            return '2nd_half'
        return f'installment_{installment_num}'
    
    def _determine_installment_status(self, data: Dict) -> str:
        """Determine installment status"""
        status_lower = str(data.get('status', '')).lower()
        if 'paid' in status_lower:
            return 'paid'
        elif 'delinquent' in status_lower or 'unpaid' in status_lower:
            return 'delinquent'
        return 'pending'
    
    def _extract_delinquent_installments(self, data: Dict) -> str:
        """Extract which installments are delinquent"""
        inst_fields = ['installments', 'installment', 'delinquent_installments']
        for field in inst_fields:
            if field in data:
                return str(data[field])
        return ''
    
    def _parse_table_for_installments(self, table: List[List[str]], parcel_id: str, property_info: Optional[Dict], tax_data: Optional[Dict] = None) -> List[Dict]:
        """Parse HTML table data for installment information"""
        installments = []
        
        if not table or len(table) < 2:
            return installments
        
        # First row is usually headers
        headers = [h.lower() for h in table[0]]
        
        # Find column indices
        amount_idx = None
        date_idx = None
        type_idx = None
        year_idx = None
        status_idx = None
        
        for i, header in enumerate(headers):
            if 'amount' in header or 'total' in header or '$' in header:
                amount_idx = i
            if 'date' in header or 'due' in header:
                date_idx = i
            if 'type' in header or 'installment' in header:
                type_idx = i
            if 'year' in header:
                year_idx = i
            if 'status' in header or 'paid' in header or 'delinquent' in header:
                status_idx = i
        
        # Parse data rows
        for row_idx, row in enumerate(table[1:], 1):
            if len(row) > 0:
                # Extract tax year from row or context
                tax_year = None
                if year_idx and year_idx < len(row):
                    tax_year = row[year_idx].strip() if row[year_idx] else None
                    # Validate year format
                    if tax_year and (not tax_year.isdigit() or len(tax_year) != 4):
                        tax_year = None
                
                # If no year in row, try to extract from tax_data context
                if not tax_year and tax_data:
                    tax_year = self._extract_year_from_tax_data_context({'table_row': row}, tax_data)
                
                # Determine status
                status = 'pending'
                if status_idx and status_idx < len(row):
                    status_str = str(row[status_idx]).lower()
                    if 'paid' in status_str:
                        status = 'paid'
                    elif 'delinquent' in status_str or 'unpaid' in status_str:
                        status = 'delinquent'
                
                # Extract amount
                amount = self._parse_amount_from_string(row[amount_idx] if amount_idx and amount_idx < len(row) else '')
                
                installment = {
                    'parcel_id': parcel_id,
                    'property_id': property_info.get('property_id') if property_info else None,
                    'installment_number': row_idx,
                    'installment_type': row[type_idx] if type_idx and type_idx < len(row) else f'installment_{row_idx}',
                    'amount': amount,
                    'due_date': self._parse_date_from_string(row[date_idx] if date_idx and date_idx < len(row) else ''),
                    'paid_date': None,
                    'status': status,
                    'tax_year': tax_year,
                    'extraction_date': datetime.now().isoformat()
                }
                installments.append(installment)
        
        return installments
    
    def _parse_amount_from_string(self, value: str) -> Optional[float]:
        """Parse amount from string"""
        if not value:
            return None
        try:
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            if cleaned:
                return float(cleaned)
        except:
            pass
        return None
    
    def _parse_date_from_string(self, value: str) -> Optional[str]:
        """Parse date from string"""
        if not value:
            return None
        # Try to parse common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(str(value).strip(), fmt)
                return dt.isoformat()
            except:
                continue
        return str(value) if value else None
    
    def _create_properties_df(self) -> pd.DataFrame:
        """Create properties DataFrame"""
        if not self.properties:
            return pd.DataFrame(columns=[
                'parcel_id', 'property_id', 'owner_name', 'municipality', 
                'address', 'extraction_date', 'source'
            ])
        return pd.DataFrame(self.properties)
    
    def _create_tax_periods_df(self) -> pd.DataFrame:
        """Create tax periods DataFrame"""
        if not self.tax_periods:
            return pd.DataFrame(columns=[
                'parcel_id', 'property_id', 'tax_year', 'total_tax_amount',
                'status', 'extraction_date'
            ])
        return pd.DataFrame(self.tax_periods)
    
    def _create_installments_df(self) -> pd.DataFrame:
        """Create installments DataFrame"""
        if not self.installments:
            return pd.DataFrame(columns=[
                'parcel_id', 'property_id', 'installment_number', 'installment_type',
                'amount', 'due_date', 'paid_date', 'status', 'tax_year', 'extraction_date'
            ])
        return pd.DataFrame(self.installments)
    
    def _create_delinquent_taxes_df(self) -> pd.DataFrame:
        """Create delinquent taxes DataFrame"""
        if not self.delinquent_taxes:
            return pd.DataFrame(columns=[
                'parcel_id', 'property_id', 'tax_year', 'delinquent_amount',
                'status', 'installments_delinquent', 'extraction_date'
            ])
        return pd.DataFrame(self.delinquent_taxes)
    
    def _create_penalties_interest_df(self) -> pd.DataFrame:
        """Create penalties and interest DataFrame"""
        if not self.penalties_interest:
            return pd.DataFrame(columns=[
                'parcel_id', 'property_id', 'tax_year', 'penalty_amount',
                'interest_amount', 'total_penalties_interest', 'extraction_date'
            ])
        return pd.DataFrame(self.penalties_interest)
    
    def save_to_csv_files(self, dataframes: Dict[str, pd.DataFrame], base_filename: str):
        """Save all DataFrames to separate CSV files"""
        for table_name, df in dataframes.items():
            filename = f"{base_filename}_{table_name}.csv"
            df.to_csv(filename, index=False)
            print(f"✓ Saved {table_name} to {filename} ({len(df)} rows)")
    
    def save_to_excel_sheets(self, dataframes: Dict[str, pd.DataFrame], filename: str):
        """Save all DataFrames to separate sheets in an Excel file"""
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for table_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=table_name, index=False)
        print(f"✓ Saved all tables to {filename}")
