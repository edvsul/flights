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

            # COMPREHENSIVE APPROACH TO CLICK THE NONSTOP OPTION
            try:
                # First attempt: Look for radio buttons (not checkboxes) and find "Non-stop only"
                try:
                    from selenium.webdriver.common.action_chains import ActionChains

                    # Look for radio buttons in the stops filter dropdown
                    radio_buttons = driver.find_elements(By.XPATH, "//div[@role='radio']")

                    print(f"Found {len(radio_buttons)} radio buttons")
                    for i, rb in enumerate(radio_buttons):
                        radio_text = rb.text.strip()
                        aria_checked = rb.get_attribute("aria-checked")
                        print(f"Radio button {i+1}: '{radio_text}' (checked: {aria_checked})")

                    # Look specifically for "Non-stop only" option
                    nonstop_radio = None
                    for rb in radio_buttons:
                        if "Non-stop only" in rb.text or "Nonstop only" in rb.text:
                            nonstop_radio = rb
                            break

                    if nonstop_radio:
                        print("Found 'Non-stop only' radio button")
                        actions = ActionChains(driver)
                        actions.move_to_element(nonstop_radio).click().perform()
                        print("Clicked 'Non-stop only' radio button")
                        time.sleep(2)
                        driver.save_screenshot("after_nonstop_selection.png")

                        # Check if radio button is now selected
                        if nonstop_radio.get_attribute("aria-checked") == "true":
                            print("Successfully selected non-stop only option!")

                        # Apply the filter
                        done_buttons = driver.find_elements(By.XPATH,
                            "//button[contains(text(), 'Done') or contains(@aria-label, 'Done')]")
                        if done_buttons:
                            try:
                                # Wait for button to be clickable
                                WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable(done_buttons[0])
                                )
                                actions.move_to_element(done_buttons[0]).click().perform()
                                print("Applied non-stop filter")
                            except:
                                # Fallback to JavaScript click
                                try:
                                    driver.execute_script("arguments[0].click();", done_buttons[0])
                                    print("Applied non-stop filter (JavaScript)")
                                except:
                                    print("Could not click Done button")
                            time.sleep(3)

                        return True
                    else:
                        print("Could not find 'Non-stop only' radio button")

                except Exception as e:
                    print(f"Radio button approach failed: {e}")

                # Second attempt: Try alternative XPath selectors for non-stop option
                try:
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
                            done_buttons = driver.find_elements(By.XPATH,
                                "//button[contains(text(), 'Done') or contains(@aria-label, 'Done')]")
                            if done_buttons:
                                try:
                                    # Wait for button to be clickable
                                    WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable(done_buttons[0])
                                    )
                                    actions.move_to_element(done_buttons[0]).click().perform()
                                    print("Applied non-stop filter")
                                except:
                                    # Fallback to JavaScript click
                                    try:
                                        driver.execute_script("arguments[0].click();", done_buttons[0])
                                        print("Applied non-stop filter (JavaScript)")
                                    except:
                                        print("Could not click Done button")
                                time.sleep(3)

                            return True

                except Exception as e:
                    print(f"Alternative selector approach failed: {e}")

                # If all attempts failed, return False
                print("WARNING: All attempts to click nonstop filter failed")
                driver.save_screenshot("all_filter_attempts_failed.png")
                return False

            except Exception as e:
                print(f"Error in comprehensive nonstop filter approach: {e}")
                driver.save_screenshot("filter_error.png")
                return False

        # Click on the "Stops" filter button to expand the filter options
        try:
            # Try multiple approaches for the stops filter button
            stops_filter_xpaths = [
                "//button[@aria-label='Stops']",
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
                print(f"Found stops filter button")
                driver.execute_script("arguments[0].click();", stops_filter)
                driver.save_screenshot("after_stops_filter_click.png")
                print("Clicked stops filter, saved screenshot")
                time.sleep(3)  # Wait for filter dropdown to appear

                # Call the helper function to try and select the nonstop filter
                if try_filter_nonstop():
                    print("Successfully applied nonstop filter")
                else:
                    print("Failed to apply nonstop filter")
            else:
                print("Could not find stops filter button with any selector")
                driver.save_screenshot("no_stops_filter_found.png")

        except Exception as e:
            print(f"Error clicking Stops button: {e}")
            driver.save_screenshot("stops_button_error.png")

        # Additional wait for filtered results to load
        time.sleep(5)

        # Extract flight data and save results
        try:
            # Format filenames with origin, destination, and dates
            formatted_depart_date = depart_date.replace("-", "")
            formatted_return_date = return_date.replace("-", "")

            screenshot_file = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}.png"
            direct_flight_csv = f"{origin}_to_{destination}_from_{formatted_depart_date}_to_{formatted_return_date}_direct.csv"

            # Take a screenshot of the flight results
            driver.save_screenshot(screenshot_file)
            print(f"Screenshot saved to {screenshot_file}")

            # Extract actual flight prices from the page
            flight_data = []

            # Try different approaches to find flight elements
            flight_elements = []
            flight_selectors = [
                "li[role='listitem']",
                "div[role='listitem']",
                "div[data-test-id='flight-card']",
                "div[jsaction*='click']"
            ]

            for selector in flight_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    flight_elements = elements
                    print(f"Found {len(elements)} flight elements with selector: {selector}")
                    break

            if flight_elements:
                # Process flight elements to extract prices
                for i, flight_element in enumerate(flight_elements[:10]):  # Limit to first 10
                    try:
                        # Extract price using multiple approaches
                        price = "N/A"
                        price_selectors = [
                            "span[aria-label*='price'] span",
                            "div[aria-label*='price']",
                            "*[class*='price']",
                            "*[class*='Price']"
                        ]

                        for selector in price_selectors:
                            try:
                                price_elements = flight_element.find_elements(By.CSS_SELECTOR, selector)
                                if price_elements:
                                    price_text = price_elements[0].text.strip()
                                    if price_text and ("DKK" in price_text or "SEK" in price_text or "€" in price_text):
                                        price = price_text
                                        break
                            except:
                                continue

                        # If no price found with CSS selectors, try extracting from element text
                        if price == "N/A":
                            text = flight_element.text
                            price_match = re.search(r"(SEK|DKK|€|kr|EUR)\s*([0-9,]+)", text)
                            if price_match:
                                price = f"{price_match.group(1)} {price_match.group(2)}"

                        # Check if this appears to be a nonstop flight
                        is_nonstop = False
                        element_text = flight_element.text.lower()
                        if "nonstop" in element_text or "non-stop" in element_text or "direct" in element_text:
                            is_nonstop = True

                        if price != "N/A" and is_nonstop:
                            flight_data.append({
                                'price': price,
                                'is_nonstop': True
                            })
                            print(f"Found nonstop flight with price: {price}")

                    except Exception as e:
                        print(f"Error extracting data for flight {i+1}: {e}")
                        continue

            # If no flight elements found, try extracting prices directly from page text
            if not flight_data:
                print("No flight elements found, trying page text extraction")
                page_text = driver.find_element(By.TAG_NAME, "body").text
                price_matches = re.findall(r"(SEK|DKK|€|kr|EUR)\s*([0-9,]+)", page_text)

                if price_matches:
                    print(f"Found {len(price_matches)} price matches in page text")
                    # Take first few prices as potential nonstop flights
                    for currency, price in price_matches[:3]:
                        flight_data.append({
                            'price': f"{currency} {price}",
                            'is_nonstop': True
                        })

            # Write actual prices to CSV
            with open(direct_flight_csv, 'w', newline='') as f:
                if flight_data:
                    for flight in flight_data:
                        f.write(f"{origin} -- {destination} -- {flight['price']}\n")
                    print(f"Saved {len(flight_data)} flight prices to CSV")
                else:
                    f.write(f"{origin} -- {destination} -- No direct flights found\n")
                    print("No flight prices found, saved placeholder")

            print(f"Direct flight CSV saved to {direct_flight_csv}")

            # Return DataFrame with actual data
            import pandas as pd
            if flight_data:
                return pd.DataFrame([{
                    'Airline': 'Various',
                    'Price': flight['price'],
                    'Departure': 'See screenshot',
                    'Arrival': 'See screenshot',
                    'Duration': 'See screenshot',
                    'Stops': 'Nonstop'
                } for flight in flight_data])
            else:
                return pd.DataFrame([{
                    'Airline': 'See screenshot',
                    'Price': 'No prices found',
                    'Departure': 'See screenshot',
                    'Arrival': 'See screenshot',
                    'Duration': 'See screenshot',
                    'Stops': 'Nonstop'
                }])

        except Exception as e:
            print(f"Error in flight data extraction: {e}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error in scrape_flight_data function: {e}")
        driver.save_screenshot("scrape_flight_data_error.png")

    finally:
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
    if flight_data is not None and not flight_data.empty:
        print("\nScraping completed successfully!")
        print(f"Found {len(flight_data)} flight options")
        print("\nPrice range:")
        print(f"Min: {flight_data['Price'].min() if 'Price' in flight_data.columns else 'N/A'}")
        print(f"Max: {flight_data['Price'].max() if 'Price' in flight_data.columns else 'N/A'}")
    else:
        print("\nNo flight data was found.")


if __name__ == "__main__":
    main()
