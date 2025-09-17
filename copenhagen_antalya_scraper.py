#!/usr/bin/env python3
import os
import time
import re
import pandas as pd
import subprocess
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


def connect_to_vpn(country):
    """Connect to NordVPN server in specified country."""
    try:
        print(f"Connecting to NordVPN server in {country}...")

        # Disconnect any existing connection
        subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
        time.sleep(2)

        # Connect to specified country
        result = subprocess.run(["nordvpn", "connect", country], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Successfully connected to {country}")
            time.sleep(5)  # Wait for connection to stabilize
            return True
        else:
            print(f"Failed to connect to {country}: {result.stderr}")
            return False

    except Exception as e:
        print(f"Error connecting to VPN: {e}")
        return False


def disconnect_vpn():
    """Disconnect from NordVPN."""
    try:
        print("Disconnecting from VPN...")
        subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
        time.sleep(2)
        print("Disconnected from VPN")
    except Exception as e:
        print(f"Error disconnecting from VPN: {e}")


def get_current_ip():
    """Get current IP address to verify VPN connection."""
    try:
        result = subprocess.run(["curl", "-s", "https://ipinfo.io/ip"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return "Unknown"
    except:
        return "Unknown"


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
                price_match = re.search(r"(SEK|DKK|€|kr|EUR)\s*([0-9,]+)", text)
                if price_match:
                    price_value = int(price_match.group(2).replace(",", ""))
                    if 1000 <= price_value <= 50000:
                        price = f"{price_match.group(1)} {price_match.group(2)}"

                        # Check if nonstop
                        element_text = text.lower()
                        if "nonstop" in element_text or "non-stop" in element_text or "direct" in element_text:
                            flight_data.append({'price': price, 'is_nonstop': True})
                            print(f"Found nonstop flight with price: {price}")

            except Exception:
                continue

        print(f"Processed {visible_flights} visible flight elements")

    # Fallback: extract from page text if no flight elements found
    if not flight_data:
        print("No flight elements found, trying page text extraction")
        page_text = driver.find_element(By.TAG_NAME, "body").text
        price_matches = re.findall(r"(DKK|SEK|€)\s*([0-9,]+)", page_text)

        if price_matches:
            print(f"Found {len(price_matches)} price matches")
            valid_prices = []
            seen_prices = set()

            for currency, price in price_matches:
                try:
                    price_value = int(price.replace(",", ""))
                    if 2000 <= price_value <= 10000 and price_value not in seen_prices:
                        valid_prices.append(f"{currency} {price}")
                        seen_prices.add(price_value)
                        if len(valid_prices) >= 2:
                            break
                except:
                    continue

            for price in valid_prices:
                flight_data.append({'price': price, 'is_nonstop': True})
                print(f"Extracted price: {price}")

    return flight_data


def scrape_flight_data_for_country(origin, destination, depart_date, return_date, country):
    """Scrape flight data from Google Flights for a specific country."""
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

        # Take screenshot
        formatted_depart_date = depart_date.replace("-", "")
        formatted_return_date = return_date.replace("-", "")
        screenshot_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_{country.replace(' ', '_')}.png"

        driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved to {screenshot_file}")

        flight_data = extract_flight_prices(driver)
        return flight_data

    except Exception as e:
        print(f"Error in scrape_flight_data_for_country function: {e}")
        return []

    finally:
        driver.quit()


def main():
    # Define flight search parameters
    origin = "Copenhagen"
    destination = "Antalya"
    depart_date = "2025-10-17"
    return_date = "2025-10-24"

    # List of countries to test
    countries = [
        "Bosnia and Herzegovina",
        "Croatia",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "Estonia"
    ]

    # CSV file for all results
    formatted_depart_date = depart_date.replace("-", "")
    formatted_return_date = return_date.replace("-", "")
    csv_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_all_countries.csv"

    print(f"Starting multi-country flight price comparison...")
    print(f"Route: {origin} to {destination}")
    print(f"Dates: {depart_date} to {return_date}")
    print(f"Countries: {', '.join(countries)}")

    all_results = []

    for country in countries:
        print(f"\n{'='*50}")
        print(f"Processing {country}")
        print(f"{'='*50}")

        # Connect to VPN
        if connect_to_vpn(country):
            current_ip = get_current_ip()
            print(f"Current IP: {current_ip}")

            # Scrape flight data
            flight_data = scrape_flight_data_for_country(origin, destination, depart_date, return_date, country)

            # Add country info to each flight
            for flight in flight_data:
                flight['country'] = country
                flight['ip'] = current_ip
                all_results.append(flight)

            print(f"Found {len(flight_data)} flights for {country}")
        else:
            print(f"Failed to connect to VPN for {country}, skipping...")

        # Small delay between countries
        time.sleep(5)

    # Disconnect VPN
    disconnect_vpn()

    # Save all results to CSV
    if all_results:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            f.write("Origin,Destination,Price,Country,IP\n")
            for result in all_results:
                f.write(f"{origin},{destination},{result['price']},{result['country']},{result['ip']}\n")

        print(f"\n{'='*50}")
        print(f"SUMMARY")
        print(f"{'='*50}")
        print(f"Total flights found: {len(all_results)}")
        print(f"Results saved to: {csv_file}")

        # Print summary by country
        country_summary = {}
        for result in all_results:
            country = result['country']
            if country not in country_summary:
                country_summary[country] = []
            country_summary[country].append(result['price'])

        for country, prices in country_summary.items():
            print(f"{country}: {len(prices)} flights - {', '.join(prices)}")

    else:
        print("No flight data collected from any country")


if __name__ == "__main__":
    main()
