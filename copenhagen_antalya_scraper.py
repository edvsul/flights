#!/usr/bin/env python3
import os
import time
import re
import random
import shutil
import uuid
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import tempfile
from selenium.webdriver.common.keys import Keys
import subprocess
from datetime import datetime


def setup_driver():
    """Set up and return a configured Chrome WebDriver with clean session."""
    chrome_options = Options()

    # Essential options for headless operation
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")

    # Create unique temporary directory in current working directory
    unique_id = str(uuid.uuid4())[:8]
    timestamp = str(int(time.time()))
    temp_dir_name = f"chrome_session_{timestamp}_{unique_id}"
    temp_dir = os.path.join(os.getcwd(), "temp_chrome_sessions", temp_dir_name)
    os.makedirs(temp_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    # Ensure completely clean session - no cache, cookies, or stored data
    chrome_options.add_argument("--incognito")  # Private browsing mode
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-domain-reliability")

    # Clear any existing data
    chrome_options.add_argument("--aggressive-cache-discard")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")

    # User agent - randomize slightly for each session
    chrome_versions = ["120.0.0.0", "119.0.0.0", "121.0.0.0"]
    chrome_version = random.choice(chrome_versions)
    chrome_options.add_argument(f"--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36")

    # Exclude automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Additional prefs for clean session
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "geolocation": 2,
        },
        "profile.managed_default_content_settings": {
            "images": 1
        },
        "profile.default_content_settings": {
            "popups": 0
        }
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Create WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Remove webdriver property and other automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array")
    driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise")
    driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol")

    print(f"Created clean browser session with temp directory: {temp_dir}")

    # Store temp_dir in driver for cleanup later
    driver.temp_dir = temp_dir
    return driver


def handle_consent_page(driver):
    """Handle Google's consent page if it appears."""
    try:
        # Wait for consent dialog
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@role, 'dialog')] | //form[contains(@action, 'consent')] | //div[@id='consent-bump'] | //div[contains(@class, 'consent')]"))
        )

        # Try multiple approaches to find consent buttons
        consent_approaches = [
            "//button[contains(text(), 'Accept all') or contains(text(), 'I agree') or contains(text(), 'Agree') or contains(text(), 'Accept')]|//div[contains(text(), 'Accept all') and @role='button']|//span[contains(text(), 'Accept all') and @role='button']",
            "//form[contains(@action, 'consent')]//button|//form[contains(@action, 'consent')]//input[@type='submit']",
            "//button[contains(@class, 'primary')]|//button[contains(@class, 'accept')]|//button[contains(@class, 'agree')]",
            "//div[@role='dialog']//button[1]|//div[contains(@class, 'dialog')]//button[1]",
            "//div[@role='button' and (contains(., 'Accept') or contains(., 'Agree'))]|//span[@role='button' and (contains(., 'Accept') or contains(., 'Agree'))]",
            "//button"
        ]

        for xpath in consent_approaches:
            try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for button in buttons:
                    if button.is_displayed():
                        print(f"Found potential consent button: {button.text or 'unnamed button'}")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)

                        # Check if dialog disappeared
                        try:
                            dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                            if not dialogs or not any(d.is_displayed() for d in dialogs):
                                print("Successfully handled consent page!")
                                return True
                        except:
                            pass
            except Exception:
                continue

        # Try iframe handling
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    for xpath in consent_approaches:
                        buttons = driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            if button.is_displayed():
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)
                                driver.switch_to.default_content()
                                return True
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
                    continue

        print("Warning: Could not automatically handle consent page")
        return False

    except TimeoutException:
        return True

    return False


def apply_nonstop_filter(driver):
    """Apply nonstop filter to flight results."""
    try:
        # Find stops filter button
        stops_selectors = [
            "//button[@aria-label='Stops']",
            "//div[contains(@aria-label, 'Stops')][@role='button']",
            "//button[contains(@aria-label, 'Stops') or contains(text(), 'Stops')]",
            "//div[text()='Stops']/parent::div[@role='button']",
            "//div[contains(text(), 'Stops')]/ancestor::div[@role='button'][1]"
        ]

        stops_filter = None
        for xpath in stops_selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    stops_filter = elements[0]
                    print(f"Found stops filter with selector: {xpath}")
                    break
            except:
                continue

        if not stops_filter:
            print("Could not find stops filter button")
            return False

        # Click stops filter
        driver.execute_script("arguments[0].click();", stops_filter)
        time.sleep(3)

        # Find and click nonstop option
        nonstop_selectors = [
            "//div[contains(text(), 'Non-stop only')]",
            "//div[contains(text(), 'Nonstop only')]",
            "//span[contains(text(), 'Non-stop only')]",
            "//span[contains(text(), 'Nonstop only')]",
            "//label[contains(text(), 'Non-stop only')]",
            "//label[contains(text(), 'Nonstop only')]"
        ]

        for selector in nonstop_selectors:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"Found non-stop element with selector: {selector}")
                actions = ActionChains(driver)
                actions.move_to_element(elements[0]).click().perform()
                print("Clicked non-stop option")
                time.sleep(2)

                # Apply the filter
                done_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Done') or contains(@aria-label, 'Done')]")
                if done_buttons:
                    try:
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(done_buttons[0]))
                        actions.move_to_element(done_buttons[0]).click().perform()
                        print("Applied non-stop filter")
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", done_buttons[0])
                            print("Applied non-stop filter (JavaScript)")
                        except:
                            print("Could not click Done button")
                    time.sleep(3)
                return True

        print("Could not find nonstop option")
        return False

    except Exception as e:
        print(f"Error applying nonstop filter: {e}")
        return False


def select_eur_currency(driver):
    """Select EUR currency on Google Flights."""
    try:
        print("Attempting to select EUR currency...")
        time.sleep(5)

        # Check if EUR is already selected
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "€" in page_text:
            print("EUR currency appears to already be selected")
            return True

        # Find currency button
        currency_selectors = [
            "//button[@aria-label='Currency']",
            "//div[contains(@aria-label, 'Currency')][@role='button']",
            "//button[contains(text(), 'Currency')]"
        ]

        currency_button = None
        for selector in currency_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and elements[0].is_displayed():
                    currency_button = elements[0]
                    break
            except:
                continue

        if not currency_button:
            print("Could not find currency selector button")
            return False

        # Click currency button
        driver.execute_script("arguments[0].click();", currency_button)
        time.sleep(3)

        # Find and select EUR option
        eur_selectors = [
            "//div[contains(text(), 'EUR')]",
            "//span[contains(text(), 'EUR')]",
            "//li[contains(text(), 'EUR')]"
        ]

        for selector in eur_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and elements[0].is_displayed():
                    driver.execute_script("arguments[0].click();", elements[0])
                    time.sleep(3)
                    break
            except:
                continue

        # Click confirmation button if present
        confirmation_selectors = [
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Done')]"
        ]

        for selector in confirmation_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and elements[0].is_displayed():
                    driver.execute_script("arguments[0].click();", elements[0])
                    time.sleep(3)
                    break
            except:
                continue

        time.sleep(5)
        return True

    except Exception as e:
        print(f"Error selecting EUR currency: {e}")
        return False


def extract_flight_prices(driver):
    """Extract flight prices from the page."""
    flight_data = []

    # Find flight elements
    flight_elements = driver.find_elements(By.CSS_SELECTOR, "div[jsaction*='click']")

    if flight_elements:
        visible_flights = 0
        for flight_element in flight_elements:
            try:
                if not flight_element.is_displayed():
                    continue

                # Skip small elements
                element_size = flight_element.size
                if element_size['height'] < 50 or element_size['width'] < 200:
                    continue

                visible_flights += 1
                if visible_flights > 10:
                    break

                # Extract price from element text
                text = flight_element.text
                print(f"Checking flight element {visible_flights}: {text[:100]}...")

                # Look for EUR prices
                eur_price_patterns = [
                    r"€\s*([0-9,]+)",           # €1,951
                    r"EUR\s*([0-9,]+)",         # EUR 1951
                    r"([0-9,]+)\s*€",           # 1951 €
                    r"([0-9,]+)\s*EUR"          # 1951 EUR
                ]

                for pattern in eur_price_patterns:
                    eur_price_match = re.search(pattern, text)
                    if eur_price_match:
                        price_value = int(eur_price_match.group(1).replace(",", ""))
                        if 100 <= price_value <= 10000:
                            price = f"€{eur_price_match.group(1)}"
                            flight_data.append({'price': price, 'is_nonstop': True})
                            print(f"Found EUR flight with price: {price}")
                            break

                # If no EUR found, try basic fallback currencies
                if not any(re.search(pattern, text) for pattern in eur_price_patterns):
                    # Basic fallback patterns for common currencies
                    fallback_patterns = [
                        (r"\$\s*([0-9,]+)", "USD", 50, 5000),
                        (r"£\s*([0-9,]+)", "GBP", 50, 4000),
                        (r"(DKK)\s*([0-9,]+)", "DKK", 400, 35000),
                        (r"(AFN)\s*([0-9,]+)", "AFN", 5000, 500000),
                        (r"([0-9,]+)\s*kr", "kr", 500, 50000)
                    ]

                    for pattern, currency_code, min_val, max_val in fallback_patterns:
                        price_match = re.search(pattern, text, re.IGNORECASE)
                        if price_match:
                            price_value_str = price_match.group(1) if len(price_match.groups()) == 1 else price_match.group(2)
                            try:
                                price_value = int(price_value_str.replace(",", ""))
                                if min_val <= price_value <= max_val:
                                    price = f"{currency_code} {price_value_str}"
                                    flight_data.append({'price': price, 'is_nonstop': True})
                                    print(f"Found {currency_code} flight with price: {price}")
                                    break
                            except ValueError:
                                continue

            except Exception as e:
                print(f"Error processing flight element: {e}")
                continue

        print(f"Processed {visible_flights} visible flight elements")

    # Fallback: extract from page text if no flight elements found
    if not flight_data:
        print("No flight elements found, trying page text extraction")
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Try to find EUR prices in page text
        eur_price_patterns = [
            r"€\s*([0-9,]+)",
            r"EUR\s*([0-9,]+)",
            r"([0-9,]+)\s*€",
            r"([0-9,]+)\s*EUR"
        ]

        all_eur_matches = []
        for pattern in eur_price_patterns:
            matches = re.findall(pattern, page_text)
            all_eur_matches.extend(matches)

        if all_eur_matches:
            valid_prices = []
            seen_prices = set()

            for price in all_eur_matches:
                try:
                    price_value = int(price.replace(",", ""))
                    if 100 <= price_value <= 10000 and price_value not in seen_prices:
                        valid_prices.append(f"€{price}")
                        seen_prices.add(price_value)
                        if len(valid_prices) >= 3:
                            break
                except:
                    continue

            for price in valid_prices:
                flight_data.append({'price': price, 'is_nonstop': True})
                print(f"Extracted EUR price from page text: {price}")

        # Basic fallback to other currencies if no EUR found
        if not flight_data:
            fallback_patterns = [
                (r"\$\s*([0-9,]+)", "USD", 50, 5000),
                (r"(DKK)\s*([0-9,]+)", "DKK", 400, 35000),
                (r"(AFN)\s*([0-9,]+)", "AFN", 5000, 500000),
                (r"([0-9,]+)\s*kr", "kr", 500, 50000)
            ]

            for pattern, currency_code, min_val, max_val in fallback_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    for match in matches[:2]:  # Only take first 2 matches
                        try:
                            price_value_str = match[1] if isinstance(match, tuple) and len(match) > 1 else match
                            price_value = int(price_value_str.replace(",", ""))
                            if min_val <= price_value <= max_val:
                                price = f"{currency_code} {price_value_str}"
                                flight_data.append({'price': price, 'is_nonstop': True})
                                print(f"Extracted {currency_code} price: {price}")
                        except (ValueError, IndexError):
                            continue
                    if flight_data:  # Stop after finding prices in one currency
                        break

    print(f"Total flight data extracted: {len(flight_data)} flights")
    return flight_data


def get_nordvpn_countries():
    """Get list of available NordVPN countries."""
    try:
        print("Getting available NordVPN countries...")
        result = subprocess.run(['nordvpn', 'countries'], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Parse the output to extract country names
            countries_text = result.stdout.strip()
            print(f"NordVPN countries output: {countries_text[:200]}...")

            # Split by lines and extract country names
            # NordVPN typically outputs countries separated by commas or in a list format
            countries = []

            # Try different parsing approaches
            if ',' in countries_text:
                # Comma-separated format
                countries = [country.strip() for country in countries_text.split(',') if country.strip()]
            else:
                # Line-separated format
                lines = countries_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-') and not line.startswith('Available'):
                        # Split by whitespace and take country names
                        parts = line.split()
                        for part in parts:
                            if len(part) > 2 and part.isalpha():
                                countries.append(part)

            # Remove duplicates and filter valid country names
            unique_countries = []
            seen = set()
            for country in countries:
                country_clean = country.strip().replace(',', '').replace('.', '')
                if (len(country_clean) > 2 and
                    country_clean.isalpha() and
                    country_clean.lower() not in seen and
                    country_clean.lower() not in ['available', 'countries', 'nordvpn']):
                    unique_countries.append(country_clean)
                    seen.add(country_clean.lower())

            print(f"Found {len(unique_countries)} available countries: {unique_countries[:10]}...")
            return unique_countries

        else:
            print(f"Error getting NordVPN countries: {result.stderr}")
            return []

    except subprocess.TimeoutExpired:
        print("Timeout getting NordVPN countries")
        return []
    except Exception as e:
        print(f"Error getting NordVPN countries: {e}")
        return []


def connect_to_nordvpn_country(country):
    """Connect to a specific NordVPN country."""
    try:
        print(f"Connecting to NordVPN country: {country}")
        result = subprocess.run(['nordvpn', 'connect', country], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(f"Successfully connected to {country}")
            print(f"Connection output: {result.stdout.strip()}")

            # Wait a bit for connection to stabilize
            time.sleep(10)

            # Verify connection
            status_result = subprocess.run(['nordvpn', 'status'], capture_output=True, text=True, timeout=30)
            if status_result.returncode == 0:
                print(f"Connection status: {status_result.stdout.strip()}")

            return True
        else:
            print(f"Failed to connect to {country}: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"Timeout connecting to {country}")
        return False
    except Exception as e:
        print(f"Error connecting to {country}: {e}")
        return False


def disconnect_nordvpn():
    """Disconnect from NordVPN."""
    try:
        print("Disconnecting from NordVPN...")
        result = subprocess.run(['nordvpn', 'disconnect'], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("Successfully disconnected from NordVPN")
            print(f"Disconnect output: {result.stdout.strip()}")
            time.sleep(5)  # Wait for disconnection to complete
            return True
        else:
            print(f"Error disconnecting from NordVPN: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("Timeout disconnecting from NordVPN")
        return False
    except Exception as e:
        print(f"Error disconnecting from NordVPN: {e}")
        return False


def scrape_flight_data(origin, destination, depart_date, return_date, country=None):
    """Scrape flight data from Google Flights."""
    driver = setup_driver()

    try:
        # Use the working EUR URL approach
        base_url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{depart_date}%20through%20{return_date}"
        url = f"{base_url}&curr=EUR"

        print(f"Trying URL approach 1: {url}")
        driver.get(url)
        time.sleep(5)

        # Quick check if EUR symbols appear
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "€" in page_text:
            print(f"SUCCESS: EUR symbols found with URL approach 1")
        else:
            print(f"No EUR symbols found with URL approach 1")

        # Handle consent page
        if not handle_consent_page(driver):
            print("Could not handle consent page, but continuing anyway...")

        # Wait for main content
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")))
            print("Main content loaded")
        except TimeoutException:
            print("Timeout waiting for main content to load")

        time.sleep(10)  # Wait for flight results

        # Apply nonstop filter
        apply_nonstop_filter(driver)
        time.sleep(10)  # Wait for filtered results

        # Select EUR currency
        select_eur_currency(driver)
        time.sleep(10)  # Wait for currency change to take effect

        # Take screenshot and extract prices
        formatted_depart_date = depart_date.replace("-", "")
        formatted_return_date = return_date.replace("-", "")
        country_suffix = f"_{country}" if country else ""

        # Ensure screenshots directory exists
        os.makedirs("screenshots", exist_ok=True)
        screenshot_file = f"screenshots/{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}{country_suffix}.png"

        print(f"Screenshot file: {screenshot_file}")

        driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved to {screenshot_file}")

        flight_data = extract_flight_prices(driver)

        # Flight data extracted, will be saved to CSV by main function

        # Return DataFrame with country information
        if flight_data:
            return pd.DataFrame([{
                'Country': country,
                'Airline': 'Various',
                'Price': flight['price'],
                'Departure': 'See screenshot',
                'Arrival': 'See screenshot',
                'Duration': 'See screenshot',
                'Stops': 'Nonstop'
            } for flight in flight_data])
        else:
            return pd.DataFrame([{
                'Country': country,
                'Airline': 'See screenshot',
                'Price': 'No prices found',
                'Departure': 'See screenshot',
                'Arrival': 'See screenshot',
                'Duration': 'See screenshot',
                'Stops': 'Nonstop'
            }])

    except Exception as e:
        print(f"Error in scrape_flight_data function: {e}")
        return pd.DataFrame()

    finally:
        # Proper cleanup with temp directory removal
        temp_dir = getattr(driver, 'temp_dir', None)
        try:
            driver.quit()
        except:
            pass

        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up temp directory {temp_dir}: {e}")


def cleanup_old_temp_dirs():
    """Clean up any leftover Chrome temp directories from previous runs."""
    try:
        temp_base = os.path.join(os.getcwd(), "temp_chrome_sessions")
        if os.path.exists(temp_base):
            for item in os.listdir(temp_base):
                if item.startswith("chrome_session_"):
                    temp_path = os.path.join(temp_base, item)
                    if os.path.isdir(temp_path):
                        try:
                            shutil.rmtree(temp_path, ignore_errors=True)
                            print(f"Cleaned up leftover temp directory: {temp_path}")
                        except:
                            pass
            # Remove the temp_chrome_sessions directory if it's empty
            try:
                if not os.listdir(temp_base):
                    os.rmdir(temp_base)
                    print("Removed empty temp_chrome_sessions directory")
            except:
                pass
    except Exception as e:
        print(f"Warning: Could not clean up old temp directories: {e}")


def main():
    # Clean up any leftover temp directories first
    cleanup_old_temp_dirs()

    # Define flight search parameters
    origin = "Copenhagen"
    destination = "Antalya"
    depart_date = "2025-10-17"
    return_date = "2025-10-24"

    print(f"Scraping flights from {origin} to {destination} on {depart_date} through {return_date}...")

    # Get available NordVPN countries
    countries = get_nordvpn_countries()
    if not countries:
        print("ERROR: No NordVPN countries available. NordVPN is required for this script.")
        print("Please ensure NordVPN is installed and you are logged in.")
        return
    else:
        print(f"Found {len(countries)} NordVPN countries to test: {countries}")

    all_flight_data = []
    successful_countries = []
    failed_countries = []

    # Disconnect from any existing VPN connection
    disconnect_nordvpn()

    for i, country in enumerate(countries, 1):
        print(f"\n{'='*60}")
        print(f"Processing country {i}/{len(countries)}: {country}")
        print(f"{'='*60}")

        # Connect to VPN (required)
        print(f"Connecting to {country}...")
        if not connect_to_nordvpn_country(country):
            print(f"Failed to connect to {country}, skipping...")
            failed_countries.append(country)
            continue
        print(f"Successfully connected to {country}, proceeding with scraping...")

        try:
            # Scrape flight data for this country with clean browser
            print(f"Creating clean browser session for {country}...")
            flight_data = scrape_flight_data(origin, destination, depart_date, return_date, country)

            if flight_data is not None and not flight_data.empty:
                all_flight_data.append(flight_data)
                successful_countries.append(country)
                print(f"Successfully scraped data for {country}: {len(flight_data)} flights found")

                # Save individual country CSV file
                os.makedirs("prices", exist_ok=True)
                country_suffix = f"_{country}"
                individual_csv = f"prices/{origin}_to_{destination}_direct{country_suffix}.csv"
                flight_data.to_csv(individual_csv, index=False)
                print(f"Individual country data saved to {individual_csv}")
            else:
                print(f"No flight data found for {country}")
                failed_countries.append(country)

        except Exception as e:
            print(f"Error scraping data for {country}: {e}")
            failed_countries.append(country)

        # Add a small delay between countries for stability
        if i < len(countries):
            time.sleep(3)  # Brief pause between countries

    # Final VPN disconnect
    disconnect_nordvpn()

    # Combine all data and create consolidated report
    if all_flight_data:
        combined_data = pd.concat(all_flight_data, ignore_index=True)

        # Save consolidated CSV
        os.makedirs("prices", exist_ok=True)
        consolidated_csv = f"prices/{origin}_to_{destination}_consolidated_prices.csv"
        combined_data.to_csv(consolidated_csv, index=False)
        print(f"\nConsolidated data saved to {consolidated_csv}")

        # Print summary by country
        print("\n" + "="*80)
        print("FLIGHT PRICE SUMMARY BY COUNTRY")
        print("="*80)

        for country_name in combined_data['Country'].unique():
            country_data = combined_data[combined_data['Country'] == country_name]
            prices = country_data['Price'].tolist()
            valid_prices = [p for p in prices if p != 'No prices found']

            print(f"\n{country_name}:")
            print(f"  Flights found: {len(country_data)}")
            if valid_prices:
                print(f"  Prices: {', '.join(valid_prices)}")
            else:
                print(f"  Prices: No valid prices found")

        print(f"\n\nSUMMARY:")
        print(f"Successful countries: {len(successful_countries)} - {successful_countries}")
        print(f"Failed countries: {len(failed_countries)} - {failed_countries}")
        print(f"Total flights found: {len(combined_data)}")

    else:
        print("\nNo flight data was collected from any country.")
        print(f"Failed countries: {failed_countries}")


if __name__ == "__main__":
    main()
