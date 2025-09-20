#!/usr/bin/env python3
import os
import time
import re
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


def setup_driver():
    """Set up and return a configured Chrome WebDriver."""
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

    # Add unique user data directory
    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    # Additional stability options
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")

    # User agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Exclude automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Create WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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

        # Wait for page to load
        time.sleep(3)

        # Multiple selectors for currency button/dropdown
        currency_selectors = [
            "//button[@aria-label='Currency']",
            "//div[contains(@aria-label, 'Currency')][@role='button']",
            "//button[contains(text(), 'Currency') or contains(@aria-label, 'currency')]",
            "//div[contains(text(), 'Currency')]/parent::div[@role='button']",
            "//button[contains(@data-value, 'currency')]",
            "//div[@role='button'][contains(., 'DKK') or contains(., 'SEK') or contains(., 'USD') or contains(., 'EUR')]",
            "//button[contains(., 'DKK') or contains(., 'SEK') or contains(., 'USD') or contains(., 'EUR')]"
        ]

        currency_button = None
        for selector in currency_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed():
                            currency_button = element
                            print(f"Found currency selector with: {selector}")
                            break
                    if currency_button:
                        break
            except:
                continue

        if not currency_button:
            print("Could not find currency selector button")
            return False

        # Click currency button
        driver.execute_script("arguments[0].click();", currency_button)
        time.sleep(2)

        # Look for EUR option in dropdown/menu
        eur_selectors = [
            "//div[contains(text(), 'EUR') and contains(text(), '€')]",
            "//span[contains(text(), 'EUR') and contains(text(), '€')]",
            "//li[contains(text(), 'EUR') or contains(text(), '€')]",
            "//div[@role='option'][contains(text(), 'EUR') or contains(text(), '€')]",
            "//button[contains(text(), 'EUR') and contains(text(), '€')]",
            "//div[contains(text(), 'Euro') or contains(text(), 'EUR')]",
            "//span[text()='EUR']",
            "//div[text()='EUR']"
        ]

        eur_selected = False
        for selector in eur_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed():
                            print(f"Found EUR option with selector: {selector}")
                            driver.execute_script("arguments[0].click();", element)
                            print("Selected EUR currency")
                            time.sleep(2)
                            eur_selected = True
                            break
                    if eur_selected:
                        break
            except:
                continue

        if not eur_selected:
            print("Could not find EUR option in currency menu")
            # Try to close any open menus by clicking elsewhere
            try:
                driver.find_element(By.TAG_NAME, "body").click()
            except:
                pass
            return False

        # Wait specifically for currency dialog to be visible
        try:
            print("Waiting for currency selection dialog...")
            WebDriverWait(driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Select your currency')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'Select your currency')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@role, 'dialog')]//button[contains(text(), 'OK')]"))
                )
            )
            print("Currency dialog detected")
            time.sleep(2)  # Allow dialog to fully render
        except TimeoutException:
            print("Currency dialog not detected, proceeding with button search...")

        # Look for and click OK/Done/Apply button to confirm currency selection
        confirmation_selectors = [
            # Most specific - Google Flights currency dialog OK button
            "//div[contains(text(), 'Select your currency')]/ancestor::div[contains(@role, 'dialog')]//button[contains(text(), 'OK')]",
            "//div[contains(text(), 'Select your currency')]/following::button[contains(text(), 'OK')]",
            "//div[contains(@aria-label, 'Select your currency')]//button[contains(text(), 'OK')]",

            # Currency dialog variations
            "//div[contains(@role, 'dialog')]//button[contains(text(), 'OK')]",
            "//div[contains(@class, 'dialog')]//button[contains(text(), 'OK')]",
            "//div[contains(@aria-label, 'currency') or contains(@aria-label, 'Currency')]//button[contains(text(), 'OK')]",

            # Modal/overlay specific
            "//div[contains(@class, 'modal')]//button[contains(text(), 'OK')]",
            "//div[contains(@class, 'overlay')]//button[contains(text(), 'OK')]",

            # Generic OK button searches
            "//button[text()='OK']",
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Done')]",
            "//button[contains(text(), 'Apply')]",

            # Aria-label and role based
            "//button[contains(@aria-label, 'OK') or contains(@aria-label, 'Done') or contains(@aria-label, 'Apply')]",
            "//div[@role='button'][contains(text(), 'OK') or contains(text(), 'Done') or contains(text(), 'Apply')]",
            "//span[@role='button'][contains(text(), 'OK') or contains(text(), 'Done') or contains(text(), 'Apply')]",

            # CSS class based
            "//button[contains(@class, 'primary') or contains(@class, 'confirm') or contains(@class, 'ok')]",
            "//button[contains(@type, 'submit')]",

            # Last resort - any button in dialog/modal
            "//div[contains(@role, 'dialog')]//button",
            "//div[contains(@class, 'dialog')]//button",
            "//div[contains(@class, 'modal')]//button"
        ]

        confirmation_clicked = False
        for selector in confirmation_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text.strip()

                            # Validate that this is actually an OK/confirmation button
                            valid_confirmation_texts = ['OK', 'Done', 'Apply', 'Confirm', 'Save']
                            is_valid_button = any(valid_text.lower() in element_text.lower() for valid_text in valid_confirmation_texts)

                            # Skip buttons with just numbers or single characters
                            if len(element_text) <= 2 and element_text.isdigit():
                                print(f"Skipping numeric button: '{element_text}'")
                                continue

                            # Skip if text doesn't contain valid confirmation words
                            if element_text and not is_valid_button:
                                print(f"Skipping non-confirmation button: '{element_text}'")
                                continue

                            print(f"Found valid confirmation button with selector: {selector}")
                            print(f"Button text: '{element_text}' (enabled: {element.is_enabled()})")

                            # Try both regular click and JavaScript click
                            try:
                                element.click()
                                print("Clicked confirmation button with regular click")
                            except:
                                driver.execute_script("arguments[0].click();", element)
                                print("Clicked confirmation button with JavaScript click")

                            time.sleep(3)

                            # Verify the dialog is closed after clicking
                            try:
                                dialog_still_open = driver.find_elements(By.XPATH, "//div[contains(text(), 'Select your currency')]")
                                if not dialog_still_open or not any(d.is_displayed() for d in dialog_still_open):
                                    print("Currency dialog closed successfully!")
                                    confirmation_clicked = True
                                    break
                                else:
                                    print("Dialog still open, trying next selector...")
                            except:
                                # Assume success if we can't check
                                confirmation_clicked = True
                                break

                    if confirmation_clicked:
                        break
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue

        if not confirmation_clicked:
            print("Could not find confirmation button, trying alternative approaches...")

            # Try to find any button with "OK" anywhere in the page
            try:
                print("Scanning all buttons on page for valid confirmation text...")
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(all_buttons)} total buttons on page")

                for i, button in enumerate(all_buttons):
                    if button.is_displayed() and button.is_enabled():
                        button_text = button.text.strip()
                        print(f"Button {i+1}: '{button_text}' (displayed: {button.is_displayed()}, enabled: {button.is_enabled()})")

                        # Look specifically for OK button
                        if button_text.upper() == 'OK':
                            print(f"Found exact OK button: '{button_text}'")
                            try:
                                # Scroll to button to ensure it's clickable
                                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(1)

                                # Try clicking
                                button.click()
                                print("Successfully clicked OK button with regular click")
                                time.sleep(3)

                                # Verify dialog closed
                                dialog_still_open = driver.find_elements(By.XPATH, "//div[contains(text(), 'Select your currency')]")
                                if not dialog_still_open or not any(d.is_displayed() for d in dialog_still_open):
                                    print("Currency dialog closed successfully after OK click!")
                                    confirmation_clicked = True
                                    break
                                else:
                                    print("Dialog still open after OK click, trying JavaScript click...")
                                    driver.execute_script("arguments[0].click();", button)
                                    time.sleep(3)

                                    # Check again
                                    dialog_still_open = driver.find_elements(By.XPATH, "//div[contains(text(), 'Select your currency')]")
                                    if not dialog_still_open or not any(d.is_displayed() for d in dialog_still_open):
                                        print("Currency dialog closed successfully after JavaScript OK click!")
                                        confirmation_clicked = True
                                        break

                            except Exception as e:
                                print(f"Error clicking OK button: {e}")
                                continue

                        # Also try buttons with "Done", "Apply", etc.
                        elif button_text.upper() in ['DONE', 'APPLY', 'CONFIRM', 'SAVE']:
                            print(f"Found potential confirmation button: '{button_text}'")
                            try:
                                driver.execute_script("arguments[0].click();", button)
                                print(f"Clicked {button_text} button")
                                time.sleep(3)
                                confirmation_clicked = True
                                break
                            except Exception as e:
                                print(f"Error clicking {button_text} button: {e}")
                                continue

            except Exception as e:
                print(f"Error searching all buttons: {e}")

        if not confirmation_clicked:
            print("Could not find confirmation button, currency may still be applied")
            # Try pressing Enter key as fallback
            try:
                print("Trying Enter key as fallback confirmation")
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
                time.sleep(2)
                print("Trying Escape key to close any dialogs")
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(2)
            except Exception as e:
                print(f"Error with keyboard fallback: {e}")

        # Wait for currency change to take effect
        time.sleep(5)  # Increased wait time for currency change
        print("EUR currency selection completed")
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
                if visible_flights > 15:  # Increased to catch more flights
                    break

                # Extract price from element text - prioritize EUR
                text = flight_element.text
                print(f"Checking flight element {visible_flights}: {text[:100]}...")  # Debug output

                # First try to find EUR prices specifically - improved patterns
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
                        if 100 <= price_value <= 50000:
                            price = f"€{eur_price_match.group(1)}"

                            # Check if nonstop (more lenient since filter was applied)
                            element_text = text.lower()
                            is_nonstop = ("nonstop" in element_text or "non-stop" in element_text or
                                        "direct" in element_text or len(flight_data) == 0)  # Assume first flights are nonstop after filter

                            flight_data.append({'price': price, 'is_nonstop': True})
                            print(f"Found EUR flight with price: {price}")
                            break  # Found EUR price, don't check other patterns

                # If no EUR found, try fallback currencies
                if not any(eur_price_match for pattern in eur_price_patterns if re.search(pattern, text)):
                    price_match = re.search(r"(SEK|DKK|kr)\s*([0-9,]+)", text)
                    if price_match:
                        price_value = int(price_match.group(2).replace(",", ""))
                        if 1000 <= price_value <= 50000:
                            price = f"{price_match.group(1)} {price_match.group(2)}"
                            flight_data.append({'price': price, 'is_nonstop': True})
                            print(f"Found fallback currency flight with price: {price}")

            except Exception as e:
                print(f"Error processing flight element: {e}")
                continue

        print(f"Processed {visible_flights} visible flight elements")

    # Enhanced fallback: extract from page text if no flight elements found
    if not flight_data:
        print("No flight elements found, trying page text extraction")
        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"Page text sample: {page_text[:500]}...")  # Debug output

        # First try to find EUR prices in page text - improved patterns
        eur_price_patterns = [
            r"€\s*([0-9,]+)",           # €1,951
            r"EUR\s*([0-9,]+)",         # EUR 1951
            r"([0-9,]+)\s*€",           # 1951 €
            r"([0-9,]+)\s*EUR"          # 1951 EUR
        ]

        all_eur_matches = []
        for pattern in eur_price_patterns:
            matches = re.findall(pattern, page_text)
            all_eur_matches.extend(matches)

        if all_eur_matches:
            print(f"Found {len(all_eur_matches)} EUR price matches in page text")
            valid_prices = []
            seen_prices = set()

            for price in all_eur_matches:
                try:
                    price_value = int(price.replace(",", ""))
                    if 100 <= price_value <= 10000 and price_value not in seen_prices:
                        valid_prices.append(f"€{price}")
                        seen_prices.add(price_value)
                        if len(valid_prices) >= 5:  # Get more prices
                            break
                except:
                    continue

            for price in valid_prices:
                flight_data.append({'price': price, 'is_nonstop': True})
                print(f"Extracted EUR price from page text: {price}")

        # Fallback to other currencies if no EUR found
        if not flight_data:
            price_matches = re.findall(r"(DKK|SEK|kr)\s*([0-9,]+)", page_text)
            if price_matches:
                print(f"Found {len(price_matches)} non-EUR price matches")
                valid_prices = []
                seen_prices = set()

                for currency, price in price_matches:
                    try:
                        price_value = int(price.replace(",", ""))
                        if 2000 <= price_value <= 10000 and price_value not in seen_prices:
                            valid_prices.append(f"{currency} {price}")
                            seen_prices.add(price_value)
                            if len(valid_prices) >= 3:
                                break
                    except:
                        continue

                for price in valid_prices:
                    flight_data.append({'price': price, 'is_nonstop': True})
                    print(f"Extracted fallback price: {price}")

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
            return unique_countries[:10]  # Limit to first 10 countries for testing

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
        # Navigate to Google Flights
        url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{depart_date}%20through%20{return_date}"
        driver.get(url)
        time.sleep(5)

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
        screenshot_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}{country_suffix}.png"

        driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved to {screenshot_file}")

        flight_data = extract_flight_prices(driver)

        # Save to CSV with country information
        country_suffix = f"_{country}" if country else ""
        direct_flight_csv = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_direct{country_suffix}.csv"
        
        with open(direct_flight_csv, 'w', newline='') as f:
            if flight_data:
                for flight in flight_data:
                    f.write(f"{origin} -- {destination} -- {flight['price']} -- {country or 'Unknown'}\n")
                print(f"Saved {len(flight_data)} flight prices to CSV for {country or 'Unknown'}")
            else:
                f.write(f"{origin} -- {destination} -- No direct flights found -- {country or 'Unknown'}\n")

        print(f"Direct flight CSV saved to {direct_flight_csv}")

        # Return DataFrame with country information
        if flight_data:
            return pd.DataFrame([{
                'Country': country or 'Unknown',
                'Airline': 'Various',
                'Price': flight['price'],
                'Departure': 'See screenshot',
                'Arrival': 'See screenshot',
                'Duration': 'See screenshot',
                'Stops': 'Nonstop'
            } for flight in flight_data])
        else:
            return pd.DataFrame([{
                'Country': country or 'Unknown',
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
        driver.quit()


def main():
    # Define flight search parameters
    origin = "Copenhagen"
    destination = "Antalya"
    depart_date = "2025-10-17"
    return_date = "2025-10-24"

    print(f"Scraping flights from {origin} to {destination} on {depart_date} through {return_date}...")

    # Get available NordVPN countries
    countries = get_nordvpn_countries()
    if not countries:
        print("No NordVPN countries available, running without VPN...")
        countries = [None]  # Run once without VPN
    else:
        print(f"Found {len(countries)} NordVPN countries to test: {countries}")

    all_flight_data = []
    successful_countries = []
    failed_countries = []

    # Disconnect from any existing VPN connection
    disconnect_nordvpn()

    for i, country in enumerate(countries, 1):
        print(f"\n{'='*60}")
        print(f"Processing country {i}/{len(countries)}: {country or 'No VPN'}")
        print(f"{'='*60}")

        # Connect to VPN if country is specified
        if country:
            print(f"Connecting to {country}...")
            if not connect_to_nordvpn_country(country):
                print(f"Failed to connect to {country}, skipping...")
                failed_countries.append(country)
                continue
            print(f"Successfully connected to {country}, proceeding with scraping...")

        try:
            # Scrape flight data for this country
            flight_data = scrape_flight_data(origin, destination, depart_date, return_date, country)

            if flight_data is not None and not flight_data.empty:
                all_flight_data.append(flight_data)
                successful_countries.append(country or 'No VPN')
                print(f"Successfully scraped data for {country or 'No VPN'}: {len(flight_data)} flights found")
            else:
                print(f"No flight data found for {country or 'No VPN'}")
                failed_countries.append(country or 'No VPN')

        except Exception as e:
            print(f"Error scraping data for {country or 'No VPN'}: {e}")
            failed_countries.append(country or 'No VPN')

        # Add a small delay between countries for stability
        if i < len(countries):
            time.sleep(3)  # Brief pause between countries

    # Final VPN disconnect
    if countries and countries[0] is not None:
        disconnect_nordvpn()

    # Combine all data and create consolidated report
    if all_flight_data:
        combined_data = pd.concat(all_flight_data, ignore_index=True)
        
        # Save consolidated CSV
        consolidated_csv = f"{origin}_to_{destination}_consolidated_prices.csv"
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
