"""
La Crosse County Scraper

This scraper handles:
1. Getting cookies from login page
2. Guest login via Selenium
3. Property search via API and Selenium form interaction
4. Tax information retrieval
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Optional, Any
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import json


class LaCrosseScraper:
    """Scraper for La Crosse County Land Records"""
    
    def __init__(self, base_url: str = "https://pp-lacrosse-co-wi-fb.app.landnav.com"):
        """
        Initialize La Crosse scraper
        
        Args:
            base_url: Base URL for the website
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.cookies = {}
        self.driver = None
        
        # Set default headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
    
    def get_cookies(self) -> Dict[str, str]:
        """
        Step 1: Get cookies from the login page (lacrosse get cookie)
        
        Returns:
            Dictionary of cookies
        """
        print("Step 1: Getting cookies from login page...")
        try:
            url = f"{self.base_url}/login"
            response = self.session.get(url)
            response.raise_for_status()
            
            # Extract cookies from session (requests handles Set-Cookie automatically)
            cookies_dict = {}
            cookie_strings = []
            
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
                cookie_strings.append(f"{cookie.name}={cookie.value}")
            
            # Also check Set-Cookie header if present (may contain additional info)
            set_cookie_header = response.headers.get('Set-Cookie')
            if set_cookie_header:
                # Handle multiple Set-Cookie headers (they might be comma-separated or in a list)
                # In requests, multiple Set-Cookie headers are usually handled automatically
                # But we can parse the header string if needed
                if isinstance(set_cookie_header, str):
                    # Split by comma if multiple cookies (though requests usually handles this)
                    cookie_parts = set_cookie_header.split(',')
                    for cookie_part in cookie_parts:
                        # Extract cookie name=value part (before the first semicolon)
                        cookie_value = cookie_part.split(';')[0].strip()
                        if '=' in cookie_value:
                            name, value = cookie_value.split('=', 1)
                            if name not in cookies_dict:  # Don't overwrite existing
                                cookies_dict[name] = value
                                cookie_strings.append(f"{name}={value}")
            
            self.cookies = cookies_dict
            cookie_header = '; '.join(cookie_strings) if cookie_strings else ''
            
            print(f"✓ Cookies retrieved: {len(cookies_dict)} cookie(s)")
            if cookie_header:
                print(f"  Cookie header: {cookie_header[:100]}..." if len(cookie_header) > 100 else f"  Cookie header: {cookie_header}")
            else:
                print("  No cookies found in response")
            
            return cookies_dict
            
        except Exception as e:
            print(f"✗ Error getting cookies: {e}")
            raise
    
    def setup_selenium(self, headless: bool = False):
        """
        Setup Selenium WebDriver
        
        Args:
            headless: Run browser in headless mode
        """
        if self.driver is None:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add cookies to browser
            if self.cookies:
                # We'll add cookies after navigating to the domain
                pass
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.maximize_window()
            print("✓ Selenium WebDriver initialized")
    
    def guest_login_selenium(self):
        """
        Step 2: Perform guest login using Selenium to click the submit button
        
        Returns:
            True if successful, False otherwise
        """
        print("\nStep 2: Performing guest login via Selenium...")
        
        if self.driver is None:
            self.setup_selenium()
        
        try:
            # Navigate to login page first to set cookies
            login_url = f"{self.base_url}/login"
            self.driver.get(login_url)
            time.sleep(2)
            
            # Add cookies to the browser
            for name, value in self.cookies.items():
                try:
                    self.driver.add_cookie({'name': name, 'value': value})
                except Exception as e:
                    print(f"  Warning: Could not add cookie {name}: {e}")
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(2)
            
            # Find and click the "Accept and Sign In" button
            # The button has text "Accept and Sign In" and type="submit"
            try:
                # Try multiple selectors
                button_selectors = [
                    "//button[@type='submit' and contains(text(), 'Accept and Sign In')]",
                    "//button[contains(@class, 'btn-primary') and contains(text(), 'Accept and Sign In')]",
                    "//form[@id='GuestLoginForm']//button[@type='submit']",
                    "button.btn-primary[type='submit']"
                ]
                
                button = None
                for selector in button_selectors:
                    try:
                        if selector.startswith("//") or selector.startswith("//"):
                            button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        break
                    except TimeoutException:
                        continue
                
                if button is None:
                    raise NoSuchElementException("Could not find guest login button")
                
                # Scroll into view and click
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                button.click()
                
                print("✓ Guest login button clicked")
                
                # Wait for navigation/redirect after login
                time.sleep(3)
                
                # Check if we're redirected (should be on search page or similar)
                current_url = self.driver.current_url
                print(f"✓ Current URL after login: {current_url}")
                
                # Update session cookies from browser
                browser_cookies = self.driver.get_cookies()
                for cookie in browser_cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                    self.cookies[cookie['name']] = cookie['value']
                
                return True
                
            except Exception as e:
                print(f"✗ Error clicking guest login button: {e}")
                # Take screenshot for debugging
                try:
                    self.driver.save_screenshot("guest_login_error.png")
                    print("  Screenshot saved to guest_login_error.png")
                except:
                    pass
                raise
                
        except Exception as e:
            print(f"✗ Error in guest login: {e}")
            raise
    
    def search_property_api(self, parcel_id: str, tax_year: Optional[str] = None) -> Dict:
        """
        Step 3a: Search for property using the POST API call
        
        Args:
            parcel_id: Parcel ID to search for (e.g., "01-00023-010")
            tax_year: Optional tax year filter
            
        Returns:
            Search results as dictionary
        """
        print(f"\nStep 3a: Searching for property via API (Parcel ID: {parcel_id})...")
        
        url = f"{self.base_url}/Search/RealEstate/Search/Search"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/Search/RealEstate/Search',
        }
        
        # Prepare form data
        form_data = {
            'IsAdvancedSearch': 'true',
            'TaxYearSearchType': '0',
            'MinTaxYear': '',
            'MaxTaxYear': '2025',
            'MunicipalityCode': '',
            'LastName': '',
            'FirstName': '',
            'MiddleName': '',
            'OwnerStatus': '3',
            'AddressSearchType': '0',
            'HouseNumber': '',
            'HouseNumberSuffix': '',
            'PrefixDirection': '',
            'StreetName': '',
            'StreetType': '',
            'SuffixDirection': '',
            'UnitType': '',
            'UnitNumber': '',
            'UserDefinedIdSearchType': '0',
            'MinUserDefinedId': parcel_id,
            'MaxUserDefinedId': '',
            'PropertyNumberListInput': '',
            'UserDefinedId2SearchType': '0',
            'MinUserDefinedId2': '',
            'MaxUserDefinedId2': '',
            'AltPropertyNumberListInput': '',
            'PlatCode': '',
            'PlatDescription': '',
            'Block': '',
            'LotTypeName': '',
            'Lot': '',
            'Section': '',
            'Township': '',
            'TownshipDirection': '0',
            'Range': '',
            'RangeDirection': '1',
            'Quarter40': '',
            'Quarter160': '',
            'GovernmentLot': '',
            'pagination[page]': '1',
            'pagination[perpage]': '100',
            'query': '',
        }
        
        try:
            response = self.session.post(url, data=form_data, headers=headers)
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                data = response.json()
                print(f"✓ API search successful")
                return data
            except:
                # If not JSON, return HTML
                print(f"✓ API search successful (HTML response)")
                return {'html': response.text, 'status_code': response.status_code}
                
        except Exception as e:
            print(f"✗ Error in API search: {e}")
            raise
    
    def search_property_selenium(self, parcel_id: str):
        """
        Step 3b: Fill the search form and click submit using Selenium
        
        Args:
            parcel_id: Parcel ID to search for
        """
        print(f"\nStep 3b: Filling search form via Selenium (Parcel ID: {parcel_id})...")
        
        if self.driver is None:
            raise Exception("Selenium driver not initialized. Call guest_login_selenium first.")
        
        try:
            # Navigate to search page
            search_url = f"{self.base_url}/Search/RealEstate/Search"
            self.driver.get(search_url)
            
            # Wait for page to be ready
            WebDriverWait(self.driver, 15).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # Additional wait for dynamic content
            
            # Try to close any modals or overlays that might be blocking
            try:
                # Look for common modal close buttons
                modal_selectors = [
                    "button[data-dismiss='modal']",
                    ".modal-close",
                    ".close",
                    "[aria-label='Close']"
                ]
                for selector in modal_selectors:
                    try:
                        close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if close_btn.is_displayed():
                            close_btn.click()
                            time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            # Find the MinUserDefinedId input field
            try:
                # Wait for page to be fully loaded and JavaScript to be ready
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Additional wait for dynamic content
                
                # Try multiple selectors to find the input field (in order of specificity)
                parcel_input = None
                selectors = [
                    (By.CSS_SELECTOR, "input[name='MinUserDefinedId'][data-mask-type='ParcelNumber']"),
                    (By.CSS_SELECTOR, "input.form-control[name='MinUserDefinedId']"),
                    (By.NAME, "MinUserDefinedId"),
                    (By.CSS_SELECTOR, "input[name='MinUserDefinedId']"),
                    (By.CSS_SELECTOR, "input[data-mask-type='ParcelNumber']"),
                    (By.XPATH, "//input[@name='MinUserDefinedId' and @data-mask-type='ParcelNumber']"),
                    (By.XPATH, "//input[@name='MinUserDefinedId']"),
                    (By.XPATH, "//input[@data-mask-type='ParcelNumber']"),
                ]
                
                for by, selector in selectors:
                    try:
                        parcel_input = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((by, selector))
                        )
                        # Check if it's actually visible and enabled
                        if parcel_input.is_displayed() and parcel_input.is_enabled():
                            print(f"  Found input field using selector: {selector}")
                            break
                        else:
                            parcel_input = None
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if parcel_input is None:
                    # Take a screenshot for debugging
                    try:
                        self.driver.save_screenshot("input_not_found.png")
                        print("  Screenshot saved to input_not_found.png")
                    except:
                        pass
                    raise NoSuchElementException("Could not find MinUserDefinedId input field")
                
                # Wait for element to be interactable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(parcel_input)
                )
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parcel_input)
                time.sleep(0.5)
                
                # Try multiple methods to fill the input
                try:
                    # Method 1: Click, clear, and send keys
                    parcel_input.click()
                    time.sleep(0.3)
                    parcel_input.clear()
                    time.sleep(0.2)
                    parcel_input.send_keys(parcel_id)
                    time.sleep(0.5)
                    # Trigger blur event to handle the onblur handler
                    parcel_input.send_keys(Keys.TAB)
                    print(f"✓ Filled parcel ID: {parcel_id} (normal method)")
                except Exception as e1:
                    print(f"  Warning: Normal input failed, trying JavaScript: {e1}")
                    try:
                        # Method 2: JavaScript to set value and trigger all events
                        self.driver.execute_script("""
                            var input = arguments[0];
                            var value = arguments[1];
                            input.value = value;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            input.dispatchEvent(new Event('blur', { bubbles: true }));
                            // Trigger the onblur handler if it exists
                            if (input.onblur) {
                                input.onblur();
                            }
                        """, parcel_input, parcel_id)
                        time.sleep(0.5)
                        print(f"✓ Filled parcel ID: {parcel_id} (JavaScript method)")
                    except Exception as e2:
                        print(f"  Warning: JavaScript method also failed: {e2}")
                        # Method 3: Try setting value attribute directly
                        try:
                            self.driver.execute_script("arguments[0].setAttribute('value', arguments[1]);", parcel_input, parcel_id)
                            self.driver.execute_script("arguments[0].value = arguments[1];", parcel_input, parcel_id)
                            time.sleep(0.5)
                            print(f"✓ Filled parcel ID: {parcel_id} (attribute method)")
                        except Exception as e3:
                            print(f"  Warning: All methods failed: {e3}")
                            raise
                
                time.sleep(1)
                
                # Find and click the Search button
                search_button_selectors = [
                    "button#SearchButton",
                    "button.btn-primary[type='submit']",
                    "//button[@id='SearchButton']",
                    "//button[contains(@class, 'btn-primary') and @type='submit']"
                ]
                
                search_button = None
                for selector in search_button_selectors:
                    try:
                        if selector.startswith("//"):
                            search_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            search_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        break
                    except TimeoutException:
                        continue
                
                if search_button is None:
                    raise NoSuchElementException("Could not find Search button")
                
                # Scroll into view and click
                self.driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                time.sleep(0.5)
                search_button.click()
                
                print("✓ Search button clicked")
                
                # Wait for search results to load
                time.sleep(3)
                
                # Check if any rows are present and get the first row
                row_element = None
                property_id = None
                
                try:
                    # Wait for table rows to appear
                    rows = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.kt-datatable__row"))
                    )
                    if rows and len(rows) > 0:
                        # Get the first row
                        row_element = rows[0]
                        # Extract property ID from row id (e.g., "row_1638665")
                        row_id = row_element.get_attribute("id")
                        if row_id and row_id.startswith("row_"):
                            property_id = row_id.replace("row_", "")
                        print(f"✓ Found {len(rows)} search result row(s), Property ID: {property_id}")
                except TimeoutException:
                    print("  No search result rows found")
                
                # Update cookies from browser
                browser_cookies = self.driver.get_cookies()
                for cookie in browser_cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                    self.cookies[cookie['name']] = cookie['value']
                
                return {
                    'row_element': row_element,
                    'property_id': property_id
                }
                
            except Exception as e:
                print(f"✗ Error in Selenium search: {e}")
                # Take screenshot for debugging
                try:
                    self.driver.save_screenshot("search_error.png")
                    print("  Screenshot saved to search_error.png")
                except:
                    pass
                raise
                
        except Exception as e:
            print(f"✗ Error in search form interaction: {e}")
            raise
    
    def find_row_by_property_id(self, property_id: str):
        """
        Find the search result row by Property ID, even if form wasn't filled
        
        Args:
            property_id: Property ID to search for
            
        Returns:
            Dictionary with row_element and property_id, or None if not found
        """
        print(f"\nTrying to find row by Property ID: {property_id}...")
        
        if self.driver is None:
            return None
        
        try:
            # Navigate to search page if not already there
            current_url = self.driver.current_url
            if 'Search/RealEstate/Search' not in current_url:
                search_url = f"{self.base_url}/Search/RealEstate/Search"
                self.driver.get(search_url)
                time.sleep(2)
            
            # Wait for any existing results to load
            time.sleep(2)
            
            # Try to find row by ID attribute
            try:
                row_id = f"row_{property_id}"
                row_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, row_id))
                )
                print(f"✓ Found row by ID: {row_id}")
                return {
                    'row_element': row_element,
                    'property_id': property_id
                }
            except TimeoutException:
                # Try finding by CSS selector
                try:
                    row_element = self.driver.find_element(By.CSS_SELECTOR, f"tr[id='row_{property_id}']")
                    print(f"✓ Found row by CSS selector")
                    return {
                        'row_element': row_element,
                        'property_id': property_id
                    }
                except NoSuchElementException:
                    print(f"  Could not find row with ID row_{property_id}")
                    return None
                    
        except Exception as e:
            print(f"  Error finding row: {e}")
            return None
    
    def navigate_directly_to_taxes(self, property_id: str) -> bool:
        """
        Navigate directly to the Taxes page for a property (fallback if row click fails)
        
        Args:
            property_id: Property ID
            
        Returns:
            True if successful
        """
        print(f"\nNavigating directly to Taxes page (Property ID: {property_id})...")
        
        try:
            # Navigate directly to taxes page
            taxes_url = f"{self.base_url}/Search/RealEstate/Taxes?propertyId={property_id}"
            self.driver.get(taxes_url)
            
            # Wait for page to load
            time.sleep(3)
            
            print("✓ Navigated directly to Taxes page")
            return True
            
        except Exception as e:
            print(f"✗ Error navigating to taxes page: {e}")
            raise
    
    def click_row_and_navigate_to_taxes(self, row_element, property_id: str) -> bool:
        """
        Click on the search result row and navigate to Taxes tab
        
        Args:
            row_element: Selenium WebElement for the row
            property_id: Property ID extracted from row
            
        Returns:
            True if successful
        """
        print(f"\nClicking on search result row (Property ID: {property_id})...")
        
        try:
            # Scroll row into view and click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row_element)
            time.sleep(0.5)
            
            # Click on the row
            row_element.click()
            print("✓ Row clicked")
            
            # Wait for page to load after row click
            time.sleep(2)
            
            # Find and click the Taxes tab
            taxes_tab_selectors = [
                "a[data-tab='Taxes']",
                "a.nav-link[href*='Taxes']",
                "//a[@data-tab='Taxes']",
                "//li[@class='nav-item']//a[contains(@href, 'Taxes')]"
            ]
            
            taxes_tab = None
            for selector in taxes_tab_selectors:
                try:
                    if selector.startswith("//"):
                        taxes_tab = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        taxes_tab = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except TimeoutException:
                    continue
            
            if taxes_tab is None:
                raise NoSuchElementException("Could not find Taxes tab")
            
            # Scroll into view and click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", taxes_tab)
            time.sleep(0.5)
            taxes_tab.click()
            print("✓ Taxes tab clicked")
            
            # Wait for taxes page to load
            time.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"✗ Error clicking row/navigating to taxes: {e}")
            raise
    
    def extract_installments_and_unpaid_taxes(self) -> Dict:
        """
        Extract installments and unpaid taxes from the current taxes page
        
        Returns:
            Dictionary containing installments and unpaid taxes information
        """
        tax_info = {
            'installments': [],
            'unpaid_taxes': [],
            'html': self.driver.page_source
        }
        
        try:
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all tables on the page
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                headers = []
                
                # Get table headers
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                # Process each data row
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    row_data = {}
                    
                    for i, cell in enumerate(cells):
                        header = headers[i] if i < len(headers) else f'column_{i}'
                        cell_text = cell.get_text(strip=True)
                        row_data[header] = cell_text
                    
                    if row_data:
                        # Check if this row contains installment or unpaid tax information
                        # Look for common patterns
                        row_text = ' '.join(row_data.values()).lower()
                        
                        # Check for installment indicators
                        if any(keyword in row_text for keyword in ['installment', 'due date', 'payment']):
                            tax_info['installments'].append(row_data)
                        
                        # Check for unpaid tax indicators
                        if any(keyword in row_text for keyword in ['unpaid', 'delinquent', 'outstanding', 'balance']):
                            tax_info['unpaid_taxes'].append(row_data)
                        
                        # If no specific keywords, add to both for review
                        if not any(keyword in row_text for keyword in ['installment', 'unpaid', 'delinquent', 'outstanding', 'balance', 'due date', 'payment']):
                            # Try to identify by structure - if it has amount columns, it might be tax data
                            if any('amount' in str(k).lower() or 'total' in str(k).lower() or '$' in str(v) for k, v in row_data.items()):
                                tax_info['installments'].append(row_data)
            
            print(f"✓ Extracted {len(tax_info['installments'])} installment(s) and {len(tax_info['unpaid_taxes'])} unpaid tax record(s)")
            
        except Exception as e:
            print(f"  Warning: Error extracting tax info: {e}")
        
        return tax_info
    
    def get_tax_info(self, property_id: str) -> Dict:
        """
        Step 4: Get tax information for a property (POST request as requested)
        
        Note: Postman collection shows GET, but implementing as POST per user request
        
        Args:
            property_id: Property ID (e.g., "1638665")
            
        Returns:
            Tax information as dictionary
        """
        print(f"\nStep 4: Retrieving tax information (Property ID: {property_id})...")
        
        url = f"{self.base_url}/Search/RealEstate/Taxes"
        # Using POST with propertyId in query params or body
        params = {'propertyId': property_id}
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'{self.base_url}/Search/RealEstate/General?propertyId={property_id}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        # POST with propertyId in body
        data = {'propertyId': property_id}
        
        try:
            # Try POST first (as requested), fallback to GET if needed
            response = self.session.post(url, params=params, data=data, headers=headers)
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract tax information including installments and unpaid taxes
            tax_data = {
                'property_id': property_id,
                'html': response.text,
                'status_code': response.status_code,
                'installments': [],
                'unpaid_taxes': []
            }
            
            # Extract installments and unpaid taxes from HTML
            try:
                # Find all tables on the page
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    headers = []
                    
                    # Get table headers
                    header_row = table.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                    
                    # Process each data row
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        row_data = {}
                        
                        for i, cell in enumerate(cells):
                            header = headers[i] if i < len(headers) else f'column_{i}'
                            cell_text = cell.get_text(strip=True)
                            row_data[header] = cell_text
                        
                        if row_data:
                            # Check if this row contains installment or unpaid tax information
                            row_text = ' '.join(row_data.values()).lower()
                            
                            # Check for installment indicators
                            if any(keyword in row_text for keyword in ['installment', 'due date', 'payment', 'install']):
                                tax_data['installments'].append(row_data)
                            
                            # Check for unpaid tax indicators
                            if any(keyword in row_text for keyword in ['unpaid', 'delinquent', 'outstanding', 'balance', 'owed']):
                                tax_data['unpaid_taxes'].append(row_data)
                            
                            # If no specific keywords but has amount data, add to installments
                            if not any(keyword in row_text for keyword in ['installment', 'unpaid', 'delinquent', 'outstanding', 'balance', 'due date', 'payment', 'owed']):
                                if any('amount' in str(k).lower() or 'total' in str(k).lower() or '$' in str(v) for k, v in row_data.items()):
                                    tax_data['installments'].append(row_data)
            except Exception as e:
                print(f"  Warning: Error extracting structured tax data: {e}")
            
            print(f"✓ Tax information retrieved: {len(tax_data['installments'])} installment(s), {len(tax_data['unpaid_taxes'])} unpaid tax record(s)")
            return tax_data
            
        except Exception as e:
            print(f"✗ Error retrieving tax information: {e}")
            raise
    
    def scrape(self, parcel_ids: List[str], tax_year: Optional[str] = None) -> List[Dict]:
        """
        Complete scraping workflow for one or more parcel IDs
        
        Args:
            parcel_ids: List of parcel IDs to scrape
            tax_year: Optional tax year filter
            
        Returns:
            List of results dictionaries
        """
        results = []
        
        try:
            # Step 1: Get cookies
            self.get_cookies()
            
            # Step 2: Guest login via Selenium
            self.guest_login_selenium()
            
            # Step 3: Search for each parcel
            for parcel_id in parcel_ids:
                print(f"\n{'='*60}")
                print(f"Processing Parcel ID: {parcel_id}")
                print(f"{'='*60}")
                
                result = {
                    'parcel_id': parcel_id,
                    'search_data': None,
                    'tax_data': None,
                    'error': None
                }
                
                try:
                    # 3a: API search
                    search_data = self.search_property_api(parcel_id, tax_year)
                    result['search_data'] = search_data
                    
                    # Extract property ID from search results if available
                    property_id = None
                    if isinstance(search_data, dict):
                        # Try to extract property ID from search results
                        if 'data' in search_data and len(search_data.get('data', [])) > 0:
                            results_data = search_data['data']
                            
                            # Handle both list and dict cases
                            if isinstance(results_data, dict):
                                # Convert dict to list of values
                                results_list = list(results_data.values())
                                print(f"  Found {len(results_list)} search result(s) (from dict)")
                            elif isinstance(results_data, list):
                                results_list = results_data
                                print(f"  Found {len(results_list)} search result(s) (from list)")
                            else:
                                print(f"  Warning: Unexpected data type: {type(results_data)}")
                                results_list = []
                            
                            # Debug: Check structure of first item if available
                            if results_list:
                                first_item = results_list[0] if isinstance(results_list, list) else None
                                if first_item is not None:
                                    print(f"  First result type: {type(first_item)}")
                                    if isinstance(first_item, dict):
                                        print(f"  First result keys: {list(first_item.keys())[:10]}")
                                    elif isinstance(first_item, (str, int)):
                                        print(f"  First result value: {str(first_item)[:100]}")
                            
                            # Ensure results_list is iterable
                            if not isinstance(results_list, (list, tuple)):
                                print(f"  Warning: results_list is not a list/tuple, type: {type(results_list)}")
                                results_list = []
                            
                            # Try to find the result that matches our parcel_id
                            matching_result = None
                            if results_list:
                                for res in results_list:
                                    # Only process if res is a dictionary
                                    if not isinstance(res, dict):
                                        continue
                                    
                                    # Check if this result matches our parcel_id
                                    user_defined_id = res.get('UserDefinedId') or res.get('userDefinedId') or res.get('ParcelNumber') or res.get('parcelNumber')
                                    if user_defined_id and str(user_defined_id).strip() == str(parcel_id).strip():
                                        matching_result = res
                                        print(f"  Found matching result for parcel {parcel_id}")
                                        break
                            
                            # Use matching result if found, otherwise find first dict result
                            target_result = None
                            if matching_result:
                                target_result = matching_result
                            elif results_list:
                                # Find first dictionary in results
                                for res in results_list:
                                    if isinstance(res, dict):
                                        target_result = res
                                        print(f"  Using first dictionary result (no exact match found)")
                                        break
                            
                            if target_result and isinstance(target_result, dict):
                                # Check both PropertyId and propertyId, handle 0 as valid ID
                                property_id = target_result.get('PropertyId')
                                if property_id is None:
                                    property_id = target_result.get('propertyId')
                                if property_id is None:
                                    # Try other possible field names
                                    property_id = target_result.get('PropertyID') or target_result.get('Id') or target_result.get('id')
                                if property_id is not None:
                                    property_id = str(property_id)  # Convert to string
                                    print(f"  Extracted Property ID from API: {property_id}")
                                else:
                                    print(f"  Warning: Could not extract Property ID from search results. Keys: {list(target_result.keys())[:10]}")
                            else:
                                print(f"  Warning: No dictionary results found in search data. First item type: {type(results_list[0]) if results_list else 'N/A'}")
                    else:
                        print(f"  Warning: Search data is not a dict, type: {type(search_data)}")
                    
                    # 3b: Selenium form interaction and row click
                    selenium_result = None
                    try:
                        selenium_result = self.search_property_selenium(parcel_id)
                        # Ensure it's a dict
                        if not isinstance(selenium_result, dict):
                            print(f"  Warning: Selenium result is not a dict, type: {type(selenium_result)}")
                            selenium_result = {'row_element': None, 'property_id': None}
                    except Exception as selenium_error:
                        print(f"  Warning: Selenium form interaction failed: {selenium_error}")
                        selenium_result = {'row_element': None, 'property_id': None}
                    
                    # Use property_id from Selenium row if available (more reliable)
                    if selenium_result and isinstance(selenium_result, dict):
                        row_property_id = selenium_result.get('property_id')
                        if row_property_id is not None:
                            property_id = str(row_property_id)  # Convert to string
                            print(f"  Using Property ID from Selenium row: {property_id}")
                    
                    # Step 4: Click row, navigate to taxes, and extract tax info
                    row_element = None
                    if selenium_result and isinstance(selenium_result, dict):
                        row_element = selenium_result.get('row_element')
                    
                    # If no row found from form filling, try to find it by Property ID
                    if property_id is not None and row_element is None:
                        print("  Attempting to find row by Property ID...")
                        row_result = self.find_row_by_property_id(property_id)
                        if row_result:
                            row_element = row_result.get('row_element')
                    
                    # If we have property_id, proceed with tax extraction
                    if property_id is not None:
                        page_tax_info = None
                        
                        # Try to use row element if available
                        if row_element:
                            try:
                                # Click row and navigate to taxes tab
                                self.click_row_and_navigate_to_taxes(row_element, property_id)
                                
                                # Extract installments and unpaid taxes from the page
                                page_tax_info = self.extract_installments_and_unpaid_taxes()
                                
                            except Exception as row_error:
                                print(f"  Warning: Error clicking row: {row_error}")
                                # Try direct navigation as fallback
                                try:
                                    self.navigate_directly_to_taxes(property_id)
                                    page_tax_info = self.extract_installments_and_unpaid_taxes()
                                except Exception as nav_error:
                                    print(f"  Warning: Direct navigation also failed: {nav_error}")
                        else:
                            # No row found, try direct navigation
                            print("  No row element found, trying direct navigation...")
                            try:
                                self.navigate_directly_to_taxes(property_id)
                                page_tax_info = self.extract_installments_and_unpaid_taxes()
                            except Exception as nav_error:
                                print(f"  Warning: Direct navigation failed: {nav_error}")
                        
                        # Always make the API call for tax info
                        try:
                            api_tax_info = self.get_tax_info(property_id)
                            
                            # Combine both sources if page extraction succeeded
                            if page_tax_info:
                                result['tax_data'] = {
                                    'property_id': property_id,
                                    'page_extracted': page_tax_info,
                                    'api_extracted': api_tax_info,
                                    'installments': page_tax_info.get('installments', []) + api_tax_info.get('installments', []),
                                    'unpaid_taxes': page_tax_info.get('unpaid_taxes', []) + api_tax_info.get('unpaid_taxes', [])
                                }
                            else:
                                # API-only
                                result['tax_data'] = api_tax_info
                                
                        except Exception as api_error:
                            print(f"  Warning: API tax retrieval failed: {api_error}")
                            # Use page data if available
                            if page_tax_info:
                                result['tax_data'] = {
                                    'property_id': property_id,
                                    'page_extracted': page_tax_info
                                }
                    else:
                        print("  Warning: Could not extract property ID from search results")
                    
                except Exception as e:
                    error_msg = str(e) if e else f"Unknown error: {type(e).__name__}"
                    result['error'] = error_msg
                    print(f"✗ Error processing parcel {parcel_id}: {error_msg}")
                    import traceback
                    print(f"  Traceback: {traceback.format_exc()}")
                
                results.append(result)
                time.sleep(1)  # Small delay between requests
            
            return results
            
        except Exception as e:
            print(f"✗ Fatal error in scraping workflow: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("\n✓ Selenium driver closed")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """Save scraped data to CSV file"""
        if not data:
            print("No data to save")
            return
        
        # Flatten nested dictionaries for CSV
        flattened_data = []
        for item in data:
            flat_item = {'parcel_id': item.get('parcel_id')}
            
            # Add search data fields
            if item.get('search_data'):
                if isinstance(item['search_data'], dict):
                    for key, value in item['search_data'].items():
                        if isinstance(value, (str, int, float, bool)):
                            flat_item[f'search_{key}'] = value
                        else:
                            flat_item[f'search_{key}'] = str(value)
            
            # Add tax data fields (including installments and unpaid taxes)
            if item.get('tax_data'):
                if isinstance(item['tax_data'], dict):
                    # Handle installments
                    if 'installments' in item['tax_data']:
                        installments = item['tax_data']['installments']
                        if isinstance(installments, list):
                            flat_item['installments_count'] = len(installments)
                            for i, installment in enumerate(installments, 1):
                                if isinstance(installment, dict):
                                    for key, value in installment.items():
                                        flat_item[f'installment_{i}_{key}'] = str(value) if value else ''
                    
                    # Handle unpaid taxes
                    if 'unpaid_taxes' in item['tax_data']:
                        unpaid_taxes = item['tax_data']['unpaid_taxes']
                        if isinstance(unpaid_taxes, list):
                            flat_item['unpaid_taxes_count'] = len(unpaid_taxes)
                            for i, unpaid in enumerate(unpaid_taxes, 1):
                                if isinstance(unpaid, dict):
                                    for key, value in unpaid.items():
                                        flat_item[f'unpaid_tax_{i}_{key}'] = str(value) if value else ''
                    
                    # Add other tax data fields
                    for key, value in item['tax_data'].items():
                        if key not in ['installments', 'unpaid_taxes']:
                            if isinstance(value, (str, int, float, bool)):
                                flat_item[f'tax_{key}'] = value
                            elif not isinstance(value, (list, dict)):
                                flat_item[f'tax_{key}'] = str(value)
            
            # Add error if present
            if item.get('error'):
                flat_item['error'] = item['error']
            
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False)
        print(f"✓ Data saved to {filename}")
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """Save scraped data to Excel file"""
        if not data:
            print("No data to save")
            return
        
        # Flatten nested dictionaries for Excel
        flattened_data = []
        for item in data:
            flat_item = {'parcel_id': item.get('parcel_id')}
            
            # Add search data fields
            if item.get('search_data'):
                if isinstance(item['search_data'], dict):
                    for key, value in item['search_data'].items():
                        if isinstance(value, (str, int, float, bool)):
                            flat_item[f'search_{key}'] = value
                        else:
                            flat_item[f'search_{key}'] = str(value)
            
            # Add tax data fields (including installments and unpaid taxes)
            if item.get('tax_data'):
                if isinstance(item['tax_data'], dict):
                    # Handle installments
                    if 'installments' in item['tax_data']:
                        installments = item['tax_data']['installments']
                        if isinstance(installments, list):
                            flat_item['installments_count'] = len(installments)
                            for i, installment in enumerate(installments, 1):
                                if isinstance(installment, dict):
                                    for key, value in installment.items():
                                        flat_item[f'installment_{i}_{key}'] = str(value) if value else ''
                    
                    # Handle unpaid taxes
                    if 'unpaid_taxes' in item['tax_data']:
                        unpaid_taxes = item['tax_data']['unpaid_taxes']
                        if isinstance(unpaid_taxes, list):
                            flat_item['unpaid_taxes_count'] = len(unpaid_taxes)
                            for i, unpaid in enumerate(unpaid_taxes, 1):
                                if isinstance(unpaid, dict):
                                    for key, value in unpaid.items():
                                        flat_item[f'unpaid_tax_{i}_{key}'] = str(value) if value else ''
                    
                    # Add other tax data fields
                    for key, value in item['tax_data'].items():
                        if key not in ['installments', 'unpaid_taxes']:
                            if isinstance(value, (str, int, float, bool)):
                                flat_item[f'tax_{key}'] = value
                            elif not isinstance(value, (list, dict)):
                                flat_item[f'tax_{key}'] = str(value)
            
            # Add error if present
            if item.get('error'):
                flat_item['error'] = item['error']
            
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✓ Data saved to {filename}")
