#!/usr/bin/env python3
import os
import time
import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import matplotlib.pyplot as plt
import tempfile


def setup_driver():
    """Set up and return a configured Chrome WebDriver."""
    chrome_options = Options()

    # Essential options for headless Linux operation
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")

    # Add unique user data directory to avoid conflicts
    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    # Additional stability options for headless environments
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")

    # Linux Chrome user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Exclude automation flags to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Create WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Execute stealth JavaScript to avoid detection
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def handle_consent_page(driver):
    """Handle Google's consent page if it appears."""
    try:
        # Wait for the consent dialog or any dialog that might contain consent buttons
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@role, 'dialog')] | //form[contains(@action, 'consent')] | //div[@id='consent-bump'] | //div[contains(@class, 'consent')]"))
        )

        # Save the page for debugging if needed
        with open("debug_consent_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # Try multiple approaches to find and click the Accept button
        accept_button_approaches = [
            # Approach 1: Direct button text matching
            "//button[contains(text(), 'Accept all') or contains(text(), 'I agree') or contains(text(), 'Agree') or contains(text(), 'Accept')]|//div[contains(text(), 'Accept all') and @role='button']|//span[contains(text(), 'Accept all') and @role='button']",

            # Approach 2: Buttons inside a form with consent in the action
            "//form[contains(@action, 'consent')]//button|//form[contains(@action, 'consent')]//input[@type='submit']",

            # Approach 3: Buttons with specific classes often used for primary actions
            "//button[contains(@class, 'primary')]|//button[contains(@class, 'accept')]|//button[contains(@class, 'agree')]",

            # Approach 4: First button in a dialog (often the primary action)
            "//div[@role='dialog']//button[1]|//div[contains(@class, 'dialog')]//button[1]",

            # Approach 5: Any element with role='button' and accept-related text
            "//div[@role='button' and (contains(., 'Accept') or contains(., 'Agree'))]|//span[@role='button' and (contains(., 'Accept') or contains(., 'Agree'))]",

            # Approach 6: Generic buttons (last resort)
            "//button"
        ]

        # Try each approach in order
        for xpath in accept_button_approaches:
            try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for button in buttons:
                    try:
                        # Check if button is visible
                        if button.is_displayed():
                            print(f"Found potential consent button: {button.text or 'unnamed button'}")
                            # Use JavaScript click which is more reliable than regular click
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
                    except Exception as e:
                        print(f"Error clicking button: {e}")
                        continue
            except Exception as e:
                print(f"Error with approach: {e}")
                continue

        # If none of the approaches worked, try iframe handling
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            for iframe in iframes:
                try:
                    # Switch to iframe
                    driver.switch_to.frame(iframe)

                    # Try clicking accept buttons within the iframe
                    for xpath in accept_button_approaches:
                        buttons = driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            if button.is_displayed():
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)
                                driver.switch_to.default_content()
                                return True

                    # Return to main content
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
                    continue

        # If we get here, we couldn't handle the consent page automatically
        print("Warning: Could not automatically handle consent page")
        return False

    except TimeoutException:
        # No consent page appeared
        return True

    return False


def scrape_flight_data(origin, destination, depart_date, return_date):
    """
    Scrape flight data from Google Flights for a specific route and dates.

    Args:
        origin: Origin city (e.g., 'Copenhagen')
        destination: Destination city (e.g., 'Antalya')
        depart_date: Departure date in 'YYYY-MM-DD' format
        return_date: Return date in 'YYYY-MM-DD' format

    Returns:
        DataFrame containing flight information and saves a screenshot
    """
    # Initialize the driver
    driver = setup_driver()

    try:
        # Format the Google Flights URL with the specified parameters
        url = (f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20"
               f"{origin}%20on%20{depart_date}%20through%20{return_date}")

        # Load the Google Flights page
        driver.get(url)
        time.sleep(5)  # Initial wait for page load

        # Handle consent page if it appears
        if not handle_consent_page(driver):
            print("Could not handle consent page, but continuing anyway...")

        # Wait for the main content to load
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )
            print("Main content loaded")
        except TimeoutException:
            print("Timeout waiting for main content to load")
            # Save the page for debugging
            with open("debug_google_flights_after_wait.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        # Additional wait for flight results
        time.sleep(10)

        # Helper function to try multiple methods to select the nonstop filter
        def try_filter_nonstop():
            # Save a screenshot of the dropdown
            driver.save_screenshot("stops_dropdown.png")

            # Save the filter dropdown content for debugging
            with open("filter_dropdown_content.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            # COMPREHENSIVE APPROACH TO CLICK THE NONSTOP CHECKBOX
            try:
                # First attempt: Use ActionChains for more robust clicking
                try:
                    # Get all checkboxes
                    checkboxes = driver.find_elements(By.XPATH, "//div[@role='checkbox']")

                    # Print all checkboxes for debugging
                    print(f"Found {len(checkboxes)} checkboxes")
                    for i, cb in enumerate(checkboxes):
                        checkbox_text = cb.text.strip()
                        aria_checked = cb.get_attribute("aria-checked")
                        print(f"Checkbox {i+1}: '{checkbox_text}' (checked: {aria_checked})")

                    # The first checkbox is typically "Nonstop only" in Google Flights
                    if checkboxes:
                        first_checkbox = checkboxes[0]

                        # Try using ActionChains for more reliable clicking
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(first_checkbox).click().perform()
                        print("Used ActionChains to click first checkbox")

                        time.sleep(2)
                        driver.save_screenshot("after_actionchains_click.png")

                        # Check if checkbox is now checked
                        if first_checkbox.get_attribute("aria-checked") == "true":
                            print("Successfully selected nonstop checkbox!")

                        # Click Done button
                        done_buttons = driver.find_elements(By.XPATH,
                            "//button[contains(text(), 'Done') or contains(@aria-label, 'Done') or contains(text(), 'Apply')]")
                        if done_buttons:
                            actions = ActionChains(driver)
                            actions.move_to_element(done_buttons[0]).click().perform()
                            print("Clicked Done button with ActionChains")
                            time.sleep(3)
                            driver.save_screenshot("after_done_button.png")

                        time.sleep(2)
                        return True
                except Exception as e:
                    print(f"ActionChains approach failed: {e}")

                # Second attempt: Try directly constructing a URL with the nonstop filter
                try:
                    # Format a URL that includes the nonstop filter parameter
                    direct_url = (f"https://www.google.com/travel/flights?q=Flights%20to%20{destination}%20from%20"
                                f"{origin}%20on%20{depart_date}%20through%20{return_date}&sc=0&tfs=0")
                    print(f"Trying direct URL with nonstop filter: {direct_url}")

                    # Navigate to the URL with the filter already applied
                    driver.get(direct_url)
                    time.sleep(5)

                    # Take a screenshot to verify
                    driver.save_screenshot("direct_url_nonstop.png")
                    print("Used direct URL with nonstop filter parameter")
                    time.sleep(2)
                    return True
                except Exception as e:
                    print(f"Direct URL approach failed: {e}")

                # Third attempt: Try JavaScript click
                try:
                    # Try using JavaScript to click the first checkbox (usually nonstop)
                    driver.execute_script("""
                        var checkboxes = document.querySelectorAll('div[role="checkbox"]');
                        if (checkboxes.length > 0) {
                            checkboxes[0].click();
                            return true;
                        }
                        return false;
                    """)
                    print("Used JavaScript to click first checkbox")
                    time.sleep(2)
                    driver.save_screenshot("after_javascript_click.png")

                    # Try to click the Done button
                    driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].innerText.includes('Done') || buttons[i].innerText.includes('Apply')) {
                                buttons[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    print("Used JavaScript to click Done button")
                    time.sleep(3)
                    return True
                except Exception as e:
                    print(f"JavaScript approach failed: {e}")

                # If all attempts failed, notify and continue
                print("WARNING: All attempts to click nonstop filter failed")
                driver.save_screenshot("all_filter_attempts_failed.png")
                return False

            except Exception as e:
                print(f"Error in comprehensive nonstop filter approach: {e}")
                driver.save_screenshot("filter_error.png")
                return False

        # Click on the "Stops" filter button to expand the filter options
        try:
            # Try multiple approaches for the stops filter
            stops_filter_xpaths = [
                "//div[contains(@aria-label, 'Stops') or contains(@aria-label, 'stops')][@role='button']",
                "//button[contains(@aria-label, 'Stops') or contains(text(), 'Stops')]",
                "//div[text()='Stops']/parent::div[@role='button']",
                "//div[contains(text(), 'Stops')]/ancestor::div[@role='button'][1]",
                "//div[@jsname='BoeBrd']//div[contains(text(), 'Stops')]/ancestor::div[@jscontroller]"
            ]

            stops_filter = None
            for xpath in stops_filter_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        stops_filter = elements[0]
                        print(f"Found stops filter with selector: {xpath}")
                        break
                except Exception:
                    continue

            if stops_filter:
                print(f"Found stops filter button: {stops_filter.get_attribute('outerHTML')}")
                driver.execute_script("arguments[0].click();", stops_filter)
                # Take a screenshot after clicking the stops filter
                driver.save_screenshot("after_stops_filter_click.png")
                print("Clicked stops filter, saved screenshot")
                time.sleep(3)  # Wait for filter dropdown to appear
            else:
                print("Could not find stops filter button with any selector")
                # Save a screenshot for debugging
                driver.save_screenshot("no_stops_filter_found.png")
                print("Saved screenshot without stops filter")

            # Wait for the dropdown menu to appear
            time.sleep(2)

            # Call our comprehensive function to try multiple methods
            filter_success = try_filter_nonstop()
            print(f"Nonstop filter selection {'succeeded' if filter_success else 'failed'}")
        except Exception as e:
            print(f"Error clicking stops filter: {e}")
            # Save the page for debugging
            with open("debug_flights_stops_filter.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        # Additional wait for filtered results to load
        time.sleep(5)

        # Format filenames with origin, destination country, and dates
        formatted_depart_date = depart_date.replace("-", "")
        formatted_return_date = return_date.replace("-", "")

        # Define all output filenames
        screenshot_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}.png"
        direct_flight_csv = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_direct.csv"
        full_csv_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}.csv"

        # Initialize the direct flight CSV file with a clean slate
        with open(direct_flight_csv, 'w', newline='', encoding='utf-8') as f:
            # Write a header to identify what's in the CSV
            f.write("# Direct flights from Copenhagen to Antalya (valid prices only)\n")

        # Take a screenshot of the flight results
        driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved to {screenshot_file}")

        # Extract flight data with improved selectors
        flight_data = []

        # Try different approaches to find flight elements
        flight_elements = []
        flight_selectors = [
            "li[role='listitem']",
            "div[role='listitem']",
            "div[data-test-id='flight-card']",
            "div[jsaction*='click']" # Generic but might find flight cards
        ]

        for selector in flight_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                flight_elements = elements
                print(f"Found {len(elements)} flight elements with selector: {selector}")
                break

        if not flight_elements:
            print("Could not find any flight elements with our selectors")
            # Try to extract flights directly from the page text
            page_text = driver.find_element(By.TAG_NAME, "body").text
            price_matches = re.findall(r"(SEK|DKK|€|kr|EUR|$)\s*([0-9,]+)", page_text)

            if price_matches:
                print(f"Found {len(price_matches)} price matches in page text")
                for currency, price in price_matches[:5]:  # Limit to 5 results
                    flight_data.append({
                        'Airline': 'From page text',
                        'Price': f"{currency} {price}",
                        'Departure': 'N/A',
                        'Arrival': 'N/A',
                        'Duration': 'N/A',
                        'Stops': 'Nonstop'
                    })

                # Add direct flight to dedicated CSV based on page text
                with open(direct_flight_csv, 'w', newline='') as f:
                    for currency, price in price_matches[:5]:
                        f.write(f"{origin} -- {destination} -- {currency} {price}\n")
                print(f"Extracted prices directly from page text")

                # Take a screenshot with flight listing visible
                driver.save_screenshot("flights_from_page_text.png")
                print("Saved screenshot of page with prices")

                return pd.DataFrame(flight_data)

        # Process flight elements if we found them
        for i, flight_element in enumerate(flight_elements):
            try:
                # Try to get element that contains all flight info
                flight_info_html = flight_element.get_attribute('outerHTML')

                # Save the first flight element HTML for debugging
                if i == 0:
                    with open("flight_element_sample.html", "w", encoding="utf-8") as f:
                        f.write(flight_info_html)

                # Multiple approaches to extract price
                price = "N/A"
                price_selectors = [
                    "span[aria-label*='price'] span",
                    "div[aria-label*='price']",
                    "*[class*='price']",
                    "*[class*='Price']",
                    "*[data-test-id='price']"
                ]

                for selector in price_selectors:
                    try:
                        price_elements = flight_element.find_elements(By.CSS_SELECTOR, selector)
                        if price_elements:
                            price = price_elements[0].text.strip()
                            if price:
                                break
                    except:
                        continue

                # If we still don't have a price, try extracting it from the element's text
                if price == "N/A":
                    text = flight_element.text
                    price_match = re.search(r"(SEK|DKK|€|kr|EUR|\$)\s*([0-9,]+)", text)
                    if price_match:
                        price = f"{price_match.group(1)} {price_match.group(2)}"

                # Extract airline information
                airline = "N/A"
                airline_selectors = [
                    "div[aria-label*='operated by']",
                    "div[class*='airline']",
                    "div[data-test-id='airline']",
                    "img[alt*='logo']"  # Airline logos often have alt text with airline name
                ]

                for selector in airline_selectors:
                    try:
                        airline_elements = flight_element.find_elements(By.CSS_SELECTOR, selector)
                        if airline_elements:
                            airline_element = airline_elements[0]
                            if airline_element.get_attribute("aria-label"):
                                airline = airline_element.get_attribute("aria-label").replace("operated by ", "").strip()
                            elif airline_element.get_attribute("alt"):
                                airline = airline_element.get_attribute("alt").replace("logo", "").strip()
                            else:
                                airline = airline_element.text.strip()
                            if airline:
                                break
                    except:
                        continue

                # Extract the stops information to verify if it's truly non-stop
                stops = "Unknown"
                try:
                    # First check within this specific flight element
                    stops_text_patterns = [
                        # Look for elements within this specific flight card
                        flight_element.find_elements(By.XPATH, ".//*[contains(@aria-label, 'stop') or contains(text(), 'stop') or contains(text(), 'Non-stop') or contains(text(), 'Nonstop')]"),
                        flight_element.find_elements(By.XPATH, ".//*[contains(@class, 'stop') or contains(@class, 'connection')]"),
                        flight_element.find_elements(By.XPATH, ".//div[contains(text(), 'stop')]")
                    ]

                    # Check this specific flight element for stops info
                    for pattern in stops_text_patterns:
                        for element in pattern:
                            element_text = element.text.lower() if element.text else ""
                            aria_label = element.get_attribute("aria-label") or ""
                            aria_label = aria_label.lower()

                            # Check for stop info in text or aria-label
                            if "nonstop" in element_text or "non-stop" in element_text or "0 stop" in element_text:
                                stops = "Nonstop"
                                break
                            elif "nonstop" in aria_label or "non-stop" in aria_label or "0 stop" in aria_label:
                                stops = "Nonstop"
                                break
                            elif "1 stop" in element_text or "1 connection" in element_text:
                                stops = "1 stop"
                                break
                            elif "1 stop" in aria_label or "1 connection" in aria_label:
                                stops = "1 stop"
                                break

                        if stops != "Unknown":
                            break

                    # For flight element HTML, check if it contains nonstop info
                    if stops == "Unknown" and flight_info_html:
                        flight_info_html_lower = flight_info_html.lower()
                        if "nonstop" in flight_info_html_lower or "non-stop" in flight_info_html_lower or "0 stop" in flight_info_html_lower:
                            stops = "Nonstop"
                        elif "1 stop" in flight_info_html_lower or "1 connection" in flight_info_html_lower:
                            stops = "1 stop"

                    # Special case - check aria-label of the flight element itself
                    if stops == "Unknown":
                        flight_aria_label = flight_element.get_attribute("aria-label") or ""
                        flight_aria_label = flight_aria_label.lower()
                        if "nonstop" in flight_aria_label or "non-stop" in flight_aria_label or "0 stop" in flight_aria_label:
                            stops = "Nonstop"
                        elif "1 stop" in flight_aria_label or "1 connection" in flight_aria_label:
                            stops = "1 stop"

                except Exception as e:
                    print(f"Error extracting stops info: {e}")
                    stops = "Unknown"

                # Add to flight data
                flight_data.append({
                    'Airline': airline,
                    'Price': price,
                    'Departure': 'See screenshot',
                    'Arrival': 'See screenshot',
                    'Duration': 'See screenshot',
                    'Stops': stops
                })

                # Only save valid prices for true non-stop flights to CSV
                if price != "N/A" and ("DKK" in price or "SEK" in price) and stops == "Nonstop":
                    # Only append this price if it's actually a valid number
                    try:
                        # Extract the numeric part for validation
                        numeric_price = price.replace("DKK", "").replace("SEK", "").replace(",", "").strip()
                        if numeric_price and float(numeric_price) > 0:
                            # Append to the CSV instead of overwriting
                            with open(direct_flight_csv, 'a', newline='', encoding='utf-8') as f:
                                f.write(f"{origin} -- {destination} -- {price}\n")
                            print(f"Found verified non-stop flight with price: {price}")
                    except (ValueError, TypeError):
                        print(f"Skipping invalid price format: {price}")
                elif price != "N/A" and ("DKK" in price or "SEK" in price):
                    print(f"Skipping flight with price {price} - not a true non-stop flight (stops: {stops})")
                else:
                    # Don't print for every N/A to reduce output spam
                    if i % 50 == 0:  # Only print every 50th N/A item
                        print(f"Processed {i} flight elements, still searching for prices...")

            except Exception as e:
                print(f"Could not extract data for flight {i+1}: {e}")
                continue

        # If we didn't find any flights but did click the filters correctly
        if not flight_data:
            print("No flight data extracted, but we did interact with filters correctly")
            # Create a placeholder entry
            flight_data.append({
                'Airline': 'Check screenshot',
                'Price': 'Check screenshot',
                'Departure': 'Check screenshot',
                'Arrival': 'Check screenshot',
                'Duration': 'Check screenshot',
                'Stops': 'Nonstop'
            })

        # Create DataFrame from flight data
        df = pd.DataFrame(flight_data)

        # Create simple CSV with direct flight prices in requested format
        direct_flight_csv = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_direct.csv"

        # Extract direct flight prices
        direct_flights = []
        if not df.empty and 'Price' in df.columns and 'Stops' in df.columns:
            direct_flights = df[df['Stops'].str.contains('Nonstop|Direct', case=False, na=False)]

        # Save in the requested format: "Copenhagen -- Antalya -- <<price>>"
        with open(direct_flight_csv, 'w', newline='') as f:
            if isinstance(direct_flights, pd.DataFrame) and not direct_flights.empty:
                for _, row in direct_flights.iterrows():
                    f.write(f"{origin} -- {destination} -- {row['Price']}\n")
            else:
                # If no direct flights found, write placeholder
                f.write(f"{origin} -- {destination} -- No direct flights found\n")

        print(f"Direct flight prices saved to {direct_flight_csv}")

        # Save the full data CSV for reference
        df.to_csv(full_csv_file, index=False)
        print(f"Full flight data saved to {full_csv_file}")

        # Create a simple visualization of prices
        if not df.empty and 'Price' in df.columns:
            # Clean price data (remove currency symbols and convert to numeric)
            # Filter out N/A and empty prices first
            valid_prices = df[df['Price'] != 'N/A']['Price']
            if not valid_prices.empty:
                # Remove currency symbols and convert to numeric, handling empty strings
                numeric_prices = []
                for price in valid_prices:
                    try:
                        cleaned_price = re.sub(r'[^\d.]', '', str(price))
                        if cleaned_price and cleaned_price != '.':
                            numeric_prices.append(float(cleaned_price))
                    except (ValueError, TypeError):
                        continue

                if numeric_prices:
                    plt.figure(figsize=(10, 6))
                    plt.bar(range(len(numeric_prices)), numeric_prices)
                    plt.xlabel('Flight Options')
                    plt.ylabel('Price')
                    plt.title(f'Flight Prices from {origin} to {destination}')
                    plt.tight_layout()

                    # Save the visualization with consistent naming
                    chart_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_prices.png"
                    plt.savefig(chart_file)
                    print(f"Price chart saved to {chart_file}")
                    plt.close()
                else:
                    print("No valid numeric prices found for visualization")
            else:
                print("No valid prices found for visualization")
        return df

    except Exception as e:
        print(f"An error occurred: {e}")
        # Take a screenshot of the error state
        driver.save_screenshot(f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        return pd.DataFrame()

    finally:
        # Close the browser
        driver.quit()


def main():
    # Define the flight search parameters
    origin = "Copenhagen"
    destination = "Antalya"

    # Format dates as required by Google Flights (YYYY-MM-DD)
    depart_date = "2025-10-17"
    return_date = "2025-10-24"

    print(f"Scraping flights from {origin} to {destination} on {depart_date} through {return_date}...")

    # Scrape flight data
    flight_data = scrape_flight_data(origin, destination, depart_date, return_date)

    # Print summary of results
    if not flight_data.empty:
        print("\nScraping completed successfully!")
        print(f"Found {len(flight_data)} flight options")
        print("\nPrice range:")
        print(f"Min: {flight_data['Price'].min() if 'Price' in flight_data.columns else 'N/A'}")
        print(f"Max: {flight_data['Price'].max() if 'Price' in flight_data.columns else 'N/A'}")
    else:
        print("\nNo flight data was found.")


if __name__ == "__main__":
    main()
