"""
Web Scraper for Land Records Websites

This module contains scrapers for:
1. Website 1: Green Lake Transcendent Tech (API-based)
2. Brown County: ASP.NET WebForms-based scraper with Selenium integration
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Optional, Any
import time
import re
import xml.etree.ElementTree as ET
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains


class BaseScraper:
    """Base class for all scrapers with common functionality"""
    
    def __init__(self, base_url: str = ""):
        """
        Initialize the scraper with a session and default headers
        
        Args:
            base_url: Base URL for the website
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """
        Make a GET request
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments to pass to requests.get
            
        Returns:
            Response object
        """
        return self.session.get(url, **kwargs)
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """Save scraped data to CSV file"""
        if not data:
            print("No data to save")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """Save scraped data to Excel file"""
        if not data:
            print("No data to save")
            return
        
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Data saved to {filename}")


class Website1Scraper(BaseScraper):
    """Scraper for Green Lake Transcendent Tech Land Records"""
    
    def __init__(self, base_url: str = "https://greenlake.transcendenttech.com/LandRecords", 
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Website 1 scraper
        
        Args:
            base_url: Base URL for the website
            username: Optional username for login
            password: Optional password for login
        """
        super().__init__(base_url)
        self.username = username
        self.password = password
    
    def login(self):
        """Establish a session by accessing the search page to get cookies"""
        try:
            # Access the search page to get initial cookies
            search_url = f"{self.base_url}/PropertyListing/RealEstateTaxParcel#/Search"
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Error during login: {e}")
            return False
    
    def search_parcels(self, parcel_number: str) -> requests.Response:
        """
        Search for parcels using the RealEstateTaxParcelService API
        
        Args:
            parcel_number: Parcel number to search for
            
        Returns:
            Response object with search results
        """
        if not self.session.cookies:
            self.login()
        
        url = f"{self.base_url}/api/RealEstateTaxParcelService"
        params = {
            'municipality': '',
            'parcelNum': parcel_number,
            'streetNum': '',
            'streetName': '',
            'streetAddress': '',
            'UsplsNum': '',
            'townlocation': '',
            'locationtype': '',
            'firstName': '',
            'lastName': '',
            'sortBy': 'PAR_NUM_SRT',
            'numRecords': '20',
            'inactive': 'true',
            'deleted': 'false',
            'page': '1',
            'bankrupt': 'false',
            'StateAssessed': 'false',
            'privateParcels': 'false',
            'tags': '',
            'tagInd': '0'
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response
    
    def get_tax_bill(self, parcel_id: str) -> requests.Response:
        """
        Get tax bill details using the TaxBillService API
        
        Args:
            parcel_id: Parcel ID obtained from search results
        
        Returns:
            Response object with tax bill details
        """
        url = f"{self.base_url}/api/TaxBillService/{parcel_id}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response
    
    def scrape_parcel(self, parcel_number: str) -> Dict[str, Any]:
        """
        Scrape a single parcel by combining search and tax bill data
        
        Args:
            parcel_number: Parcel number to scrape
            
        Returns:
            Dictionary containing combined parcel and tax bill data
        """
        try:
            # Search for parcel
            search_response = self.search_parcels(parcel_number)
            
            # Check if response is empty
            if not search_response.text or not search_response.text.strip():
                return {'ParcelNumber': parcel_number, 'Error': 'Empty response from search API'}
            
            # Parse XML response (API returns XML, not JSON)
            try:
                root = ET.fromstring(search_response.text)
                # Convert XML to list of dictionaries
                search_data = []
                # Look for parcel items in the XML
                # The XML structure may vary, so we'll try to find common elements
                for item in root.findall('.//{http://schemas.datacontract.org/2004/07/LRS.Providers.ServiceViewModels.PropertyListing.RealEstateTaxParcel}RealEstateTaxParcelVm'):
                    parcel_dict = {}
                    for child in item:
                        # Remove namespace prefix from tag name
                        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        parcel_dict[tag_name] = child.text if child.text else ''
                    if parcel_dict:
                        search_data.append(parcel_dict)
                
                # If no structured data found, try parsing as simple XML
                if not search_data:
                    # Try alternative parsing - maybe the structure is different
                    # Parse all elements and create a flat structure
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                            if tag_name not in ['RealEstateTaxParcelResultsVm', 'RealEstateTaxParcelVm']:
                                if not search_data:
                                    search_data.append({})
                                search_data[0][tag_name] = elem.text.strip()
                
            except ET.ParseError as e:
                # Try JSON as fallback
                try:
                    search_data = search_response.json()
                except ValueError:
                    error_msg = f'Invalid XML/JSON response: {str(e)}'
                    response_preview = search_response.text[:200] if search_response.text else 'Empty'
                    print(f"DEBUG - Parcel {parcel_number}: Response preview: {response_preview}")
                    return {'ParcelNumber': parcel_number, 'Error': error_msg, 'ResponsePreview': response_preview}
            except Exception as e:
                error_msg = f'Error parsing response: {str(e)}'
                response_preview = search_response.text[:200] if search_response.text else 'Empty'
                print(f"DEBUG - Parcel {parcel_number}: Response preview: {response_preview}")
                return {'ParcelNumber': parcel_number, 'Error': error_msg, 'ResponsePreview': response_preview}
            
            if not search_data or len(search_data) == 0:
                return {'ParcelNumber': parcel_number, 'Error': 'No results found'}
            
            # Get the first result's ParcelId
            parcel_id = search_data[0].get('ParcelId')
            if not parcel_id:
                return {'ParcelNumber': parcel_number, 'Error': 'No ParcelId found'}
            
            # Get tax bill
            tax_response = self.get_tax_bill(str(parcel_id))
            
            # Check if tax response is empty
            if not tax_response.text or not tax_response.text.strip():
                return {
                    'ParcelNumber': parcel_number,
                    'SearchData': search_data,
                    'Error': 'Empty response from tax bill API'
                }
            
            # Parse XML response (API returns XML, not JSON)
            try:
                tax_root = ET.fromstring(tax_response.text)
                # Convert XML to dictionary
                tax_data = {}
                # Parse all elements in the tax bill XML
                for elem in tax_root.iter():
                    if elem.text and elem.text.strip():
                        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        # Skip root element names
                        if tag_name not in ['TaxBillVm', 'TaxBillResultsVm']:
                            tax_data[tag_name] = elem.text.strip()
            except ET.ParseError as e:
                # Try JSON as fallback
                try:
                    tax_data = tax_response.json()
                except ValueError:
                    error_msg = f'Invalid XML/JSON in tax bill response: {str(e)}'
                    tax_preview = tax_response.text[:200] if tax_response.text else 'Empty'
                    print(f"DEBUG - Parcel {parcel_number}: Tax response preview: {tax_preview}")
                    return {
                        'ParcelNumber': parcel_number,
                        'SearchData': search_data,
                        'Error': error_msg,
                        'TaxResponsePreview': tax_preview
                    }
            except Exception as e:
                error_msg = f'Error parsing tax bill response: {str(e)}'
                tax_preview = tax_response.text[:200] if tax_response.text else 'Empty'
                print(f"DEBUG - Parcel {parcel_number}: Tax response preview: {tax_preview}")
                return {
                    'ParcelNumber': parcel_number,
                    'SearchData': search_data,
                    'Error': error_msg,
                    'TaxResponsePreview': tax_preview
                }
            
            # Combine search and tax data
            result = {
                'ParcelNumber': parcel_number,
                'SearchData': search_data,
                'TaxBillData': tax_data
            }
            
            return result
            
        except requests.RequestException as e:
            return {'ParcelNumber': parcel_number, 'Error': str(e)}
        except Exception as e:
            return {'ParcelNumber': parcel_number, 'Error': f'Unexpected error: {str(e)}'}
            
    
    def scrape(self, parcel_numbers: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple parcels
        
        Args:
            parcel_numbers: List of parcel numbers to scrape
            
        Returns:
            List of dictionaries containing scraped data
        """
        results = []
        for parcel_number in parcel_numbers:
            print(f"Scraping parcel: {parcel_number}")
            result = self.scrape_parcel(parcel_number)
            results.append(result)
            time.sleep(1)  # Be respectful with rate limiting
        
        return results


def extract_aspnet_tokens(html: str) -> Dict[str, str]:
    """
    Extract ASP.NET WebForms tokens from HTML response
    
    Args:
        html: HTML content to parse
        
    Returns:
        Dictionary containing extracted tokens
    """
    tokens = {}
    
    def extract_hidden_field(field_name: str) -> Optional[str]:
        """Extract hidden field value by name using multiple patterns"""
        patterns = [
            re.compile(rf'<input[^>]*name=["\']{re.escape(field_name)}["\'][^>]*value=["\']([^"\']*)["\']', re.I),
            re.compile(rf'<input[^>]*value=["\']([^"\']*)["\'][^>]*name=["\']{re.escape(field_name)}["\']', re.I),
            re.compile(rf'id=["\']{re.escape(field_name)}["\'][^>]*value=["\']([^"\']*)["\']', re.I),
        ]
        
        for pattern in patterns:
            match = pattern.search(html)
            if match and match.group(1):
                return match.group(1)
        
        # Check if field exists but is empty
        empty_pattern = re.compile(rf'name=["\']{re.escape(field_name)}["\']', re.I)
        if empty_pattern.search(html):
            return ''
        
        return None
    
    # List of ASP.NET tokens to extract
    tokens_to_extract = [
        '__VIEWSTATE',
        '__VIEWSTATEGENERATOR',
        '__EVENTVALIDATION',
        '__VIEWSTATEENCRYPTED',
        '__PREVIOUSPAGE',
        '__EVENTARGUMENT',
        '__EVENTTARGET',
        '__LASTFOCUS',
        '__SCROLLPOSITIONX',
        '__SCROLLPOSITIONY'
    ]
    
    for token_name in tokens_to_extract:
        value = extract_hidden_field(token_name)
        if value is not None:
            tokens[token_name] = value
    
    # Also extract toolkit hidden field if present
    toolkit_field = extract_hidden_field('ctl00_cphMainApp_ToolkitScriptManager1_HiddenField')
    if toolkit_field is not None:
        tokens['ctl00_cphMainApp_ToolkitScriptManager1_HiddenField'] = toolkit_field
    
    return tokens


class BrownCountyScraper(BaseScraper):
    """Scraper for Brown County Land Records (ASP.NET WebForms)"""
    
    def __init__(self, base_url: str = "https://prod-landrecords.browncountywi.gov",
                 headless: bool = True, selenium_timeout: int = 30):
        """
        Initialize Brown County scraper
        
        Args:
            base_url: Base URL for the website
            headless: Run browser in headless mode
            selenium_timeout: Timeout for Selenium operations in seconds
        """
        super().__init__(base_url)
        self.headless = headless
        self.selenium_timeout = selenium_timeout
        self.driver = None
        self.tokens = {}
        
        # Update headers for ASP.NET compatibility
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
        })
        self.session.headers.update(self.headers)
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver and sync cookies from requests session"""
        if self.driver is None:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Sync cookies from requests session to Selenium
            self._sync_cookies_to_selenium()
    
    def _sync_cookies_to_selenium(self):
        """Sync cookies from requests session to Selenium WebDriver"""
        if self.driver and self.session.cookies:
            # Navigate to base URL first to set domain
            self.driver.get(self.base_url)
            # Add all cookies from requests session
            for cookie in self.session.cookies:
                try:
                    self.driver.add_cookie({
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain or '.browncountywi.gov',
                        'path': cookie.path or '/',
                        'secure': cookie.secure
                    })
                except Exception as e:
                    print(f"Warning: Could not add cookie {cookie.name}: {e}")
    
    def _sync_cookies_from_selenium(self):
        """Sync cookies from Selenium WebDriver to requests session"""
        if self.driver:
            for cookie in self.driver.get_cookies():
                self.session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
    
    def _close_selenium(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_cookie(self) -> Dict[str, str]:
        """
        Step 1: Get initial cookies and extract ASP.NET tokens
        
        Returns:
            Dictionary containing extracted tokens
        """
        try:
            url = f"{self.base_url}/Search.aspx"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract tokens from HTML
            self.tokens = extract_aspnet_tokens(response.text)
            
            if not self.tokens.get('__VIEWSTATE'):
                print("WARNING: __VIEWSTATE was not extracted!")
            if not self.tokens.get('__EVENTVALIDATION'):
                print("WARNING: __EVENTVALIDATION was not extracted!")
            
            print(f"Extracted {len(self.tokens)} tokens from getcookie")
            return self.tokens
            
        except requests.RequestException as e:
            print(f"Error in get_cookie: {e}")
            return {}
    
    def accept_terms(self) -> Dict[str, str]:
        """
        Step 2: Accept terms and conditions, extract new tokens, and click button via Selenium
        
        Returns:
            Dictionary containing extracted tokens after accepting terms
        """
        try:
            # Prepare form data for POST request
            form_data = {
                'ctl00_cphMainApp_ToolkitScriptManager1_HiddenField': self.tokens.get('ctl00_cphMainApp_ToolkitScriptManager1_HiddenField', ''),
                '__LASTFOCUS': self.tokens.get('__LASTFOCUS', ''),
                '__EVENTTARGET': self.tokens.get('__EVENTTARGET', ''),
                '__EVENTARGUMENT': self.tokens.get('__EVENTARGUMENT', ''),
                '__VIEWSTATE': self.tokens.get('__VIEWSTATE', ''),
                '__VIEWSTATEGENERATOR': self.tokens.get('__VIEWSTATEGENERATOR', ''),
                '__SCROLLPOSITIONX': '0',
                '__SCROLLPOSITIONY': '0',
                '__VIEWSTATEENCRYPTED': self.tokens.get('__VIEWSTATEENCRYPTED', ''),
                '__EVENTVALIDATION': self.tokens.get('__EVENTVALIDATION', ''),
                'ctl00$cphMainApp$pageWidth': '1890',
                'ctl00$cphMainApp$pageHeight': '1034',
                'ctl00$cphMainApp$ParcelSearchCriteria1$PropertyType': 'optRealEstate',
                'ctl00$cphMainApp$ParcelSearchCriteria1$mtxtParcelNumber': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtLastName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtFirstName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlOwnerStatus': 'ALLBUTFORMER',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtHouseNumber': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlPrefixDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtStreetName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlStreetType': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlSuffixDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlMunicipality': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$cbCurrentProperties': 'on',
                'ctl00$cphMainApp$ParcelSearchCriteria1$cbHistoricalProperties': 'on',
                'ctl00$cphMainApp$btnEntryPageAccept': 'I Accept'
            }
            
            # POST request to accept terms
            url = f"{self.base_url}/"
            response = self.session.post(url, data=form_data, timeout=30)
            response.raise_for_status()
            
            # Extract new tokens
            new_tokens = extract_aspnet_tokens(response.text)
            self.tokens.update(new_tokens)
            
            # Use Selenium to click the "I Accept" button
            self._init_selenium()
            self.driver.get(url)
            # Sync cookies after navigation
            self._sync_cookies_from_selenium()
            
            # Wait for and click the accept button
            try:
                accept_button = WebDriverWait(self.driver, self.selenium_timeout).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_cphMainApp_btnEntryPageAccept"))
                )
                accept_button.click()
                
                # Wait for page to load
                time.sleep(2)
                
                # Extract tokens from the new page
                page_source = self.driver.page_source
                final_tokens = extract_aspnet_tokens(page_source)
                self.tokens.update(final_tokens)
                
                print("Successfully accepted terms and extracted new tokens")
                return self.tokens
                
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Error clicking accept button: {e}")
                # Still return tokens from POST response
                return self.tokens
                
        except requests.RequestException as e:
            print(f"Error in accept_terms: {e}")
            return self.tokens
    
    def search_property(self, parcel_number: str) -> Dict[str, str]:
        """
        Step 3: Search for property by parcel number
        
        Args:
            parcel_number: Parcel number to search for
            
        Returns:
            Dictionary containing extracted tokens after search
        """
        try:
            # Prepare form data for POST request
            form_data = {
                'ctl00$cphMainApp$ToolkitScriptManager1': 'ctl00$cphMainApp$upSearch|ctl00$cphMainApp$ButtonParcelSearch',
                'ctl00_cphMainApp_ToolkitScriptManager1_HiddenField': self.tokens.get('ctl00_cphMainApp_ToolkitScriptManager1_HiddenField', ''),
                '__LASTFOCUS': self.tokens.get('__LASTFOCUS', ''),
                '__EVENTTARGET': 'cphMainApp$ButtonParcelSearch',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': self.tokens.get('__VIEWSTATE', ''),
                '__VIEWSTATEGENERATOR': self.tokens.get('__VIEWSTATEGENERATOR', ''),
                '__SCROLLPOSITIONX': '0',
                '__SCROLLPOSITIONY': '0',
                '__VIEWSTATEENCRYPTED': self.tokens.get('__VIEWSTATEENCRYPTED', ''),
                '__EVENTVALIDATION': self.tokens.get('__EVENTVALIDATION', ''),
                'ctl00$cphMainApp$pageWidth': '1149',
                'ctl00$cphMainApp$pageHeight': '1034',
                'ctl00$cphMainApp$ParcelSearchCriteria1$PropertyType': 'optRealEstate',
                'ctl00$cphMainApp$ParcelSearchCriteria1$mtxtParcelNumber': parcel_number,
                'ctl00$cphMainApp$ParcelSearchCriteria1$mtxtAltParcelNumber': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtLastName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtFirstName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlOwnerStatus': 'ALLBUTFORMER',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtHouseNumber': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlPrefixDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$txtStreetName': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlStreetType': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlSuffixDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$DropDownListPlatType': 'All',
                'ctl00$cphMainApp$ParcelSearchCriteria1$DropDownListPlatDesc': 'All',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlSection': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlTownship': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlTownshipDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlRange': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlRangeDir': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddl40Quarter': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddl160Quarter': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$ddlMunicipality': '',
                'ctl00$cphMainApp$ParcelSearchCriteria1$cbCurrentProperties': 'on',
                'ctl00$cphMainApp$ParcelSearchCriteria1$cbHistoricalProperties': 'on',
                'ctl00$cphMainApp$ButtonParcelSearch': 'Search For Properties'
            }
            
            # Set headers for AJAX request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-MicrosoftAjax': 'Delta=true',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.base_url}/',
                'Origin': self.base_url
            }
            
            # POST request to search
            url = f"{self.base_url}/Search.aspx"
            response = self.session.post(url, data=form_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract new tokens
            new_tokens = extract_aspnet_tokens(response.text)
            self.tokens.update(new_tokens)
            
            # Use Selenium to fill form and click search button
            if self.driver:
                try:
                    # Navigate to search page if not already there
                    if 'Search.aspx' not in self.driver.current_url:
                        self.driver.get(url)
                        time.sleep(2)
                        # Sync cookies after navigation
                        self._sync_cookies_from_selenium()
                    
                    # Fill in parcel number
                    parcel_input = WebDriverWait(self.driver, self.selenium_timeout).until(
                        EC.presence_of_element_located((By.ID, "mtxtParcelNumber"))
                    )
                    parcel_input.clear()
                    parcel_input.send_keys(parcel_number)
                    
                    # Click search button
                    search_button = WebDriverWait(self.driver, self.selenium_timeout).until(
                        EC.element_to_be_clickable((By.ID, "ButtonParcelSearch"))
                    )
                    search_button.click()
                    
                    # Wait for results to load
                    time.sleep(3)
                    
                    # Extract tokens from the new page
                    page_source = self.driver.page_source
                    final_tokens = extract_aspnet_tokens(page_source)
                    self.tokens.update(final_tokens)
                    
                    print(f"Successfully searched for parcel {parcel_number}")
                    
                except (TimeoutException, NoSuchElementException) as e:
                    print(f"Error in Selenium search interaction: {e}")
            
            return self.tokens
            
        except requests.RequestException as e:
            print(f"Error in search_property: {e}")
            return self.tokens
    
    def get_tax_info(self) -> Dict[str, Any]:
        """
        Step 4: Click taxes button and get tax information
        
        Returns:
            Dictionary containing tax information
        """
        try:
            if not self.driver:
                self._init_selenium()
                self.driver.get(f"{self.base_url}/Search.aspx")
                time.sleep(2)
                # Sync cookies after navigation
                self._sync_cookies_from_selenium()
            
            # Click taxes button using Selenium
            try:
                # Wait for the element to be present
                taxes_link = WebDriverWait(self.driver, self.selenium_timeout).until(
                    EC.presence_of_element_located((By.ID, "LinkButtonTaxes"))
                )
                
                # Scroll element into view to avoid click interception
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", taxes_link)
                time.sleep(0.5)  # Wait for scroll to complete
                
                # Try regular click first
                try:
                    taxes_link.click()
                except Exception:
                    # If regular click fails, try JavaScript click
                    self.driver.execute_script("arguments[0].click();", taxes_link)
                
                # Wait for page to update
                time.sleep(3)  # Increased wait time for page to load
                
                # Extract new tokens from updated page
                page_source = self.driver.page_source
                new_tokens = extract_aspnet_tokens(page_source)
                self.tokens.update(new_tokens)
                
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Error clicking taxes button: {e}")
                # Try alternative: use JavaScript to trigger the postback directly
                try:
                    print("Attempting JavaScript postback as fallback...")
                    self.driver.execute_script(
                        "WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions("
                        "'ctl00$cphMainApp$SearchDetailsParcel$LinkButtonTaxes', "
                        "'', true, '', '', false, true));"
                    )
                    time.sleep(3)
                    page_source = self.driver.page_source
                    new_tokens = extract_aspnet_tokens(page_source)
                    self.tokens.update(new_tokens)
                except Exception as js_error:
                    print(f"JavaScript fallback also failed: {js_error}")
                    return {'Error': f'Could not click taxes button: {e}'}
            
            # Prepare form data for POST request
            form_data = {
                'ctl00_cphMainApp_ToolkitScriptManager1_HiddenField': self.tokens.get('ctl00_cphMainApp_ToolkitScriptManager1_HiddenField', ''),
                '__EVENTTARGET': 'ctl00$cphMainApp$SearchDetailsParcel$LinkButtonTaxes',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': self.tokens.get('__LASTFOCUS', ''),
                '__VIEWSTATE': self.tokens.get('__VIEWSTATE', ''),
                '__VIEWSTATEGENERATOR': self.tokens.get('__VIEWSTATEGENERATOR', ''),
                '__SCROLLPOSITIONX': '0',
                '__SCROLLPOSITIONY': '170',
                '__VIEWSTATEENCRYPTED': self.tokens.get('__VIEWSTATEENCRYPTED', ''),
                '__EVENTVALIDATION': self.tokens.get('__EVENTVALIDATION', ''),
                'ctl00$cphMainApp$ParcelSearchCriteria1$PropertyType': 'optRealEstate',
                '__ASYNCPOST': 'true'
            }
            
            # Set headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f'{self.base_url}/Search.aspx',
                'Origin': self.base_url
            }
            
            # POST request to get tax info
            url = f"{self.base_url}/Search.aspx"
            response = self.session.post(url, data=form_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Also get the page source from Selenium after clicking (more reliable)
            selenium_html = None
            if self.driver:
                time.sleep(2)  # Wait for page to fully load
                selenium_html = self.driver.page_source
            
            # Parse tax information from both sources
            tax_data = self._parse_tax_html(response.text, selenium_html)
            
            print("Successfully retrieved tax information")
            return tax_data
            
        except requests.RequestException as e:
            print(f"Error in get_tax_info: {e}")
            return {'Error': str(e)}
    
    def _parse_aspnet_ajax_response(self, response_text: str) -> str:
        """
        Parse ASP.NET AJAX update panel response format
        Format: "1|#||4|81358|updatePanel|ctl00_cphMainApp_upSearch|<html content>"
        
        Args:
            response_text: Raw ASP.NET AJAX response
            
        Returns:
            Extracted HTML content
        """
        # ASP.NET AJAX responses start with pipe-separated metadata
        if '|updatePanel|' in response_text:
            parts = response_text.split('|updatePanel|', 1)
            if len(parts) > 1:
                # Extract HTML content after the updatePanel marker
                html_content = parts[1].split('|', 1)[-1] if '|' in parts[1] else parts[1]
                return html_content
        return response_text
    
    def _parse_tax_html(self, response_html: str, selenium_html: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse tax information from HTML response
        
        Args:
            response_html: HTML from POST response
            selenium_html: Optional HTML from Selenium page source
            
        Returns:
            Dictionary containing parsed tax data
        """
        tax_data = {
            'raw_html': response_html,
            'parsed_data': {}
        }
        
        # Prefer Selenium HTML if available (more complete)
        html_to_parse = selenium_html if selenium_html else response_html
        
        # Parse ASP.NET AJAX response format if needed
        if html_to_parse and '|updatePanel|' in html_to_parse:
            html_to_parse = self._parse_aspnet_ajax_response(html_to_parse)
        
        if not html_to_parse:
            return tax_data
        
        soup = BeautifulSoup(html_to_parse, 'html.parser')
        
        # Look for tax-related content
        # Common patterns: tables, divs with tax info, specific IDs/classes
        
        # 1. Find all tables (tax data is often in tables)
        tables = soup.find_all('table')
        tax_data['tables_found'] = len(tables)
        
        # 2. Extract data from tables
        tax_tables_data = []
        for i, table in enumerate(tables):
            table_data = self._extract_table_data(table)
            if table_data:
                tax_tables_data.append({
                    'table_index': i,
                    'data': table_data,
                    'headers': table_data.get('headers', []),
                    'rows': table_data.get('rows', [])
                })
        tax_data['parsed_data']['tables'] = tax_tables_data
        
        # 3. Look for specific tax-related elements by ID or class
        tax_elements = {}
        
        # Common tax-related IDs/classes to search for
        tax_selectors = [
            ('id', ['tax', 'Tax', 'TAX', 'bill', 'Bill', 'BILL']),
            ('class', ['tax', 'Tax', 'TAX', 'bill', 'Bill', 'BILL', 'amount', 'Amount', 'due', 'Due'])
        ]
        
        for selector_type, keywords in tax_selectors:
            for keyword in keywords:
                if selector_type == 'id':
                    elements = soup.find_all(id=re.compile(keyword, re.I))
                else:
                    elements = soup.find_all(class_=re.compile(keyword, re.I))
                
                for elem in elements:
                    elem_id = elem.get('id', '')
                    elem_class = ' '.join(elem.get('class', []))
                    key = f"{elem_id}_{elem_class}" if elem_id else elem_class
                    if key:
                        tax_elements[key] = {
                            'tag': elem.name,
                            'text': elem.get_text(strip=True),
                            'html': str(elem)[:500]  # First 500 chars
                        }
        
        tax_data['parsed_data']['tax_elements'] = tax_elements
        
        # 4. Extract all text content and look for patterns
        all_text = soup.get_text()
        
        # Look for common tax-related patterns
        patterns = {
            'amounts': re.findall(r'\$[\d,]+\.?\d*', all_text),
            'years': re.findall(r'\b(19|20)\d{2}\b', all_text),
            'parcel_numbers': re.findall(r'\d+[-.]?\d+[-.]?\d+', all_text),
        }
        tax_data['parsed_data']['patterns'] = patterns
        
        # 5. Look for specific divs or sections that might contain tax info
        # Common containers: divs with specific IDs, sections, etc.
        tax_containers = []
        containers = soup.find_all(['div', 'section'], id=re.compile(r'(tax|bill|payment|assessment)', re.I))
        for container in containers:
            container_data = {
                'id': container.get('id', ''),
                'class': ' '.join(container.get('class', [])),
                'text': container.get_text(strip=True)[:500],
                'children_count': len(container.find_all())
            }
            tax_containers.append(container_data)
        tax_data['parsed_data']['containers'] = tax_containers
        
        # 6. Extract form fields (tax forms often have input fields)
        form_inputs = []
        inputs = soup.find_all(['input', 'select', 'textarea'])
        for inp in inputs:
            inp_type = inp.get('type', '')
            inp_name = inp.get('name', '')
            inp_id = inp.get('id', '')
            inp_value = inp.get('value', '')
            
            # Look for tax-related inputs
            if any(keyword in (inp_name + inp_id).lower() for keyword in ['tax', 'bill', 'amount', 'due', 'assessment']):
                form_inputs.append({
                    'type': inp_type,
                    'name': inp_name,
                    'id': inp_id,
                    'value': inp_value,
                    'label': self._find_input_label(soup, inp)
                })
        tax_data['parsed_data']['form_inputs'] = form_inputs
        
        # 7. Extract Installments and Tax History specifically
        installments, tax_history = self._extract_installments_and_history(soup, tax_tables_data)
        tax_data['parsed_data']['installments'] = installments
        tax_data['parsed_data']['tax_history'] = tax_history
        
        return tax_data
    
    def _extract_installments_and_history(self, soup: BeautifulSoup, tables_data: List[Dict]) -> tuple:
        """
        Extract installments and tax history from parsed tables
        
        Args:
            soup: BeautifulSoup object
            tables_data: List of parsed table data
            
        Returns:
            Tuple of (installments_list, tax_history_list)
        """
        installments = []
        tax_history = []
        
        # Look through tables for installments and tax history
        for table_info in tables_data:
            headers = table_info.get('headers', [])
            rows = table_info.get('rows', [])
            
            # Check for Installments table (headers: ['Due Date', 'Amount'])
            if len(headers) >= 2 and 'Due Date' in headers and 'Amount' in headers:
                due_date_idx = headers.index('Due Date')
                amount_idx = headers.index('Amount')
                
                for row in rows:
                    if len(row) > max(due_date_idx, amount_idx):
                        installment = {
                            'due_date': row[due_date_idx].strip() if due_date_idx < len(row) else '',
                            'amount': row[amount_idx].strip() if amount_idx < len(row) else ''
                        }
                        # Only add if we have valid data
                        if installment['due_date'] and installment['amount']:
                            installments.append(installment)
            
            # Check for Tax History table (headers include 'Year', 'Amount', 'Interest Paid', etc.)
            if len(headers) >= 7 and 'Year' in headers and 'Amount' in headers:
                # Look for tax history indicators
                if any(col in headers for col in ['Interest Paid', 'Penalties Paid', 'Paid', 'Last Paid', 'Amount Due', 'Status']):
                    year_idx = headers.index('Year')
                    amount_idx = headers.index('Amount')
                    
                    # Find indices for other columns if they exist
                    interest_paid_idx = headers.index('Interest Paid') if 'Interest Paid' in headers else None
                    penalties_paid_idx = headers.index('Penalties Paid') if 'Penalties Paid' in headers else None
                    paid_idx = headers.index('Paid') if 'Paid' in headers else None
                    last_paid_idx = headers.index('Last Paid') if 'Last Paid' in headers else None
                    amount_due_idx = headers.index('Amount Due') if 'Amount Due' in headers else None
                    status_idx = headers.index('Status') if 'Status' in headers else None
                    
                    for row in rows:
                        if len(row) > year_idx:
                            # Skip header-like rows (check if first cell is a year)
                            year_value = row[year_idx].strip() if year_idx < len(row) else ''
                            if year_value and year_value.isdigit() and len(year_value) == 4:
                                history_entry = {
                                    'year': year_value,
                                    'amount': row[amount_idx].strip() if amount_idx and amount_idx < len(row) else '',
                                    'interest_paid': row[interest_paid_idx].strip() if interest_paid_idx is not None and interest_paid_idx < len(row) else '',
                                    'penalties_paid': row[penalties_paid_idx].strip() if penalties_paid_idx is not None and penalties_paid_idx < len(row) else '',
                                    'paid': row[paid_idx].strip() if paid_idx is not None and paid_idx < len(row) else '',
                                    'last_paid': row[last_paid_idx].strip() if last_paid_idx is not None and last_paid_idx < len(row) else '',
                                    'amount_due': row[amount_due_idx].strip() if amount_due_idx is not None and amount_due_idx < len(row) else '',
                                    'status': row[status_idx].strip() if status_idx is not None and status_idx < len(row) else ''
                                }
                                tax_history.append(history_entry)
        
        return installments, tax_history
    
    def _extract_table_data(self, table) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from an HTML table
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            Dictionary with headers and rows, or None if table is empty
        """
        headers = []
        rows = []
        
        # Find header row (th elements)
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Find all data rows
        data_rows = table.find_all('tr')[1:] if headers else table.find_all('tr')
        
        for row in data_rows:
            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if cells:
                rows.append(cells)
        
        if not rows and not headers:
            return None
        
        return {
            'headers': headers,
            'rows': rows,
            'row_count': len(rows)
        }
    
    def _find_input_label(self, soup, input_elem) -> str:
        """
        Find the label associated with an input element
        
        Args:
            soup: BeautifulSoup object
            input_elem: Input element
            
        Returns:
            Label text or empty string
        """
        # Try to find label by 'for' attribute matching input id
        inp_id = input_elem.get('id', '')
        if inp_id:
            label = soup.find('label', {'for': inp_id})
            if label:
                return label.get_text(strip=True)
        
        # Try to find parent label
        parent = input_elem.find_parent('label')
        if parent:
            return parent.get_text(strip=True)
        
        # Try to find preceding label
        prev = input_elem.find_previous('label')
        if prev:
            return prev.get_text(strip=True)
        
        return ''
    
    def _extract_property_details(self, soup: BeautifulSoup, tables_data: List[Dict]) -> Dict[str, Any]:
        """
        Extract property details from parsed tables
        
        Args:
            soup: BeautifulSoup object
            tables_data: List of parsed table data
            
        Returns:
            Dictionary containing property details
        """
        property_details = {}
        
        # Look for property information table (usually first table with property info)
        for table_info in tables_data:
            headers = table_info.get('headers', [])
            rows = table_info.get('rows', [])
            
            # Check for property info table (headers like 'Tax Year', 'Parcel Number', 'Property Address', etc.)
            if len(headers) >= 3 and any(col in headers for col in ['Parcel Number', 'Property Address', 'Municipality', 'Owner']):
                if rows and len(rows) > 0:
                    row = rows[0]  # Get first row
                    
                    # Map headers to values
                    for i, header in enumerate(headers):
                        if i < len(row):
                            value = row[i].strip()
                            if value:
                                # Normalize header names
                                header_lower = header.lower()
                                if 'parcel' in header_lower and 'number' in header_lower:
                                    property_details['parcel_number'] = value
                                elif 'property' in header_lower and 'address' in header_lower:
                                    property_details['property_address'] = value
                                elif 'billing' in header_lower and 'address' in header_lower:
                                    property_details['billing_address'] = value
                                elif 'municipality' in header_lower:
                                    property_details['municipality'] = value
                                elif 'owner' in header_lower:
                                    property_details['owner'] = value
                                elif 'tax' in header_lower and 'year' in header_lower:
                                    property_details['tax_year'] = value
                                elif 'prop' in header_lower and 'type' in header_lower:
                                    property_details['property_type'] = value
        
        # Also try to extract from specific elements
        bill_number_elem = soup.find(id='lblBillNumber')
        if bill_number_elem:
            property_details['bill_number'] = bill_number_elem.get_text(strip=True)
        
        net_mill_rate_elem = soup.find(id='lblNetMillRate')
        if net_mill_rate_elem:
            property_details['net_mill_rate'] = net_mill_rate_elem.get_text(strip=True)
        
        return property_details
    
    def scrape_parcel(self, parcel_number: str) -> Dict[str, Any]:
        """
        Complete flow to scrape a single parcel
        
        Args:
            parcel_number: Parcel number to scrape
            
        Returns:
            Dictionary containing all scraped data (clean format)
        """
        try:
            result = {'ParcelNumber': parcel_number}
            
            # Step 1: Get cookie and extract tokens
            print(f"Step 1: Getting cookies for parcel {parcel_number}...")
            tokens = self.get_cookie()
            if not tokens:
                return {'ParcelNumber': parcel_number, 'Error': 'Failed to get initial cookies'}
            
            # Step 2: Accept terms
            print(f"Step 2: Accepting terms for parcel {parcel_number}...")
            tokens = self.accept_terms()
            
            # Step 3: Search property
            print(f"Step 3: Searching for parcel {parcel_number}...")
            tokens = self.search_property(parcel_number)
            
            # Step 4: Get tax info
            print(f"Step 4: Getting tax information for parcel {parcel_number}...")
            tax_data = self.get_tax_info()
            
            # Extract only essential data
            if 'Error' not in tax_data:
                parsed_data = tax_data.get('parsed_data', {})
                
                # Get property details
                if self.driver:
                    try:
                        page_source = self.driver.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        # Parse ASP.NET AJAX if needed
                        if '|updatePanel|' in page_source:
                            page_source = self._parse_aspnet_ajax_response(page_source)
                            soup = BeautifulSoup(page_source, 'html.parser')
                        
                        tables = soup.find_all('table')
                        tables_data = []
                        for table in tables:
                            table_data = self._extract_table_data(table)
                            if table_data:
                                tables_data.append(table_data)
                        
                        property_details = self._extract_property_details(soup, tables_data)
                        result['PropertyDetails'] = property_details
                    except Exception as e:
                        print(f"Warning: Could not extract property details: {e}")
                
                # Extract only installments and tax history
                result['Installments'] = parsed_data.get('installments', [])
                result['TaxHistory'] = parsed_data.get('tax_history', [])
            else:
                result['Error'] = tax_data.get('Error')
            
            return result
            
        except Exception as e:
            return {'ParcelNumber': parcel_number, 'Error': f'Unexpected error: {str(e)}'}
    
    def scrape(self, parcel_numbers: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple parcels
        
        Args:
            parcel_numbers: List of parcel numbers to scrape
            
        Returns:
            List of dictionaries containing scraped data
        """
        results = []
        try:
            for parcel_number in parcel_numbers:
                print(f"\n{'='*60}")
                print(f"Scraping parcel: {parcel_number}")
                print(f"{'='*60}")
                result = self.scrape_parcel(parcel_number)
                results.append(result)
                time.sleep(2)  # Be respectful with rate limiting
        finally:
            # Always close Selenium driver
            self._close_selenium()
        
        return results
    
    def __del__(self):
        """Cleanup: close Selenium driver"""
        self._close_selenium()

