import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os

class GoogleFlightsScraper:
    def __init__(self, headless=True):
        self.driver = None
        self.setup_driver(headless)

    def setup_driver(self, headless):
        """Setup Chrome driver with optimized options"""
        chrome_options = Options()

        # Force headless mode for server environments
        chrome_options.add_argument("--headless=new")

        # Essential options for stability and server environments
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # Fix user data directory conflicts
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")

        # Additional server environment fixes
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")

        # Anti-detection measures
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Performance optimizations
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-default-apps")

        # Memory and process optimizations
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")

        try:
            # First, try to remove old chromedriver from PATH if it exists
            old_driver_path = "/usr/bin/chromedriver"
            if os.path.exists(old_driver_path):
                print(f"⚠️ Found old ChromeDriver at {old_driver_path}")
                print("💡 Consider removing it: sudo rm /usr/bin/chromedriver")

            # Use webdriver-manager to get compatible ChromeDriver
            print("🔄 Installing compatible ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ ChromeDriver installed successfully")

        except Exception as e:
            print(f"❌ ChromeDriver installation failed: {e}")
            print("🔄 Trying fallback method...")

            # Fallback: try system ChromeDriver with additional options
            try:
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--allow-running-insecure-content")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Using system ChromeDriver")
            except Exception as e2:
                print(f"❌ System ChromeDriver also failed: {e2}")
                raise Exception("Could not initialize ChromeDriver. Please ensure Chrome and compatible ChromeDriver are installed.")

        # Hide webdriver property
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except:
            pass

        # Set timeouts
        self.driver.implicitly_wait(10)
        self.driver.set_page_load_timeout(60)

    def search_flights(self, origin="CPH", destination="AYT", departure_date=None, return_date=None):
        """Search for flights on Google Flights"""
        try:
            # Default dates if not provided
            if not departure_date:
                departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            if not return_date:
                return_date = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")

            print(f"🔍 Searching flights from {origin} to {destination}")
            print(f"📅 Departure: {departure_date}, Return: {return_date}")

            # Build Google Flights URL with proper format
            base_url = "https://www.google.com/travel/flights"
            # Use the correct Google Flights URL structure
            url = f"{base_url}?tfs=CBwQAhooEgoyMDI1LTEwLTE3agcIARIDQ1BIcgcIARIDQVlUGgoyMDI1LTEwLTI0&hl=en&curr=EUR"

            print(f"🌐 Loading: {url}")
            self.driver.get(url)

            # Wait for page to load
            time.sleep(8)

            # Save debug HTML to see what we're getting
            self.save_debug_html("google_flights_initial")

            # Handle cookie consent if present
            try:
                cookie_selectors = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'I agree')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[contains(text(), 'Accept all')]",
                    "//*[@id='L2AGLb']",  # Google's "Accept all" button
                    "//div[contains(text(), 'Accept')]//parent::button"
                ]

                for selector in cookie_selectors:
                    try:
                        cookie_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        cookie_button.click()
                        time.sleep(2)
                        print("✅ Cookie consent accepted")
                        break
                    except TimeoutException:
                        continue

            except Exception as e:
                print(f"ℹ️ No cookie consent found or error: {e}")

            # Wait for flight results to load with more comprehensive selectors
            print("⏳ Waiting for flight results...")
            try:
                WebDriverWait(self.driver, 45).until(
                    EC.any_of(
                        # Updated Google Flights selectors
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='flight']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".pIav2d")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[jsname]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".yR1fYc")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listitem']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".JMc5Xc")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='flight']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='price']")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '€') or contains(text(), '$') or contains(text(), 'kr')]")),
                        # Look for any elements that might contain flight info
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='button']"))
                    )
                )
                print("✅ Flight results loaded")
            except TimeoutException:
                print("⚠️ Timeout waiting for results")

            # Additional wait for dynamic content
            time.sleep(15)

            # Save debug HTML after waiting
            self.save_debug_html("google_flights_after_wait")

            # Check current URL to see if we were redirected
            current_url = self.driver.current_url
            print(f"📍 Current URL: {current_url}")

            # Check page title
            page_title = self.driver.title
            print(f"📄 Page title: {page_title}")

            # Extract flight data
            flights = self.extract_flight_data()

            return flights

        except Exception as e:
            print(f"❌ Error searching flights: {e}")
            # Save debug HTML on error
            self.save_debug_html("google_flights_error")
            return []

    def save_debug_html(self, filename):
        """Save page source for debugging"""
        try:
            with open(f"debug_{filename}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"🐛 Debug HTML saved: debug_{filename}.html")
        except Exception as e:
            print(f"⚠️ Could not save debug HTML: {e}")

    def extract_flight_data(self):
        """Extract flight information from the page"""
        flights = []

        try:
            # Multiple selectors to try for flight results
            flight_selectors = [
                "[data-testid='flight-offer']",
                ".pIav2d",
                "[jsname='IWWDBc']",
                ".yR1fYc",
                "[role='listitem']",
                ".JMc5Xc"
            ]

            flight_elements = []
            for selector in flight_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    flight_elements = elements
                    print(f"✅ Found {len(elements)} flights using selector: {selector}")
                    break

            if not flight_elements:
                print("⚠️ No flight elements found, trying XPath selectors...")
                xpath_selectors = [
                    "//*[contains(@class, 'flight')]",
                    "//*[contains(@data-testid, 'flight')]",
                    "//*[contains(text(), '$') or contains(text(), '€') or contains(text(), '£')]"
                ]

                for xpath in xpath_selectors:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        flight_elements = elements
                        print(f"✅ Found {len(elements)} elements using XPath: {xpath}")
                        break

            # Extract data from found elements
            for i, element in enumerate(flight_elements[:10]):  # Limit to first 10 results
                try:
                    flight_data = {}

                    # Try to extract price
                    price_selectors = [
                        ".YMlIz",
                        "[data-testid='price']",
                        ".U3gSDe",
                        ".qLTi0d"
                    ]

                    price = "Not found"
                    for price_sel in price_selectors:
                        try:
                            price_elem = element.find_element(By.CSS_SELECTOR, price_sel)
                            price = price_elem.text.strip()
                            if price and any(char in price for char in ['$', '€', '£', 'kr']):
                                break
                        except:
                            continue

                    # If no price found in element, try to find any price text
                    if price == "Not found":
                        element_text = element.text
                        import re
                        price_match = re.search(r'[€$£]\s*[\d,]+|[\d,]+\s*[€$£kr]', element_text)
                        if price_match:
                            price = price_match.group()

                    # Try to extract airline
                    airline_selectors = [
                        ".sSHqwe",
                        "[data-testid='airline']",
                        ".h1fkLb"
                    ]

                    airline = "Unknown"
                    for airline_sel in airline_selectors:
                        try:
                            airline_elem = element.find_element(By.CSS_SELECTOR, airline_sel)
                            airline = airline_elem.text.strip()
                            if airline:
                                break
                        except:
                            continue

                    # Try to extract duration
                    duration_selectors = [
                        ".gvkrdb",
                        "[data-testid='duration']",
                        ".AdWm1c"
                    ]

                    duration = "Unknown"
                    for duration_sel in duration_selectors:
                        try:
                            duration_elem = element.find_element(By.CSS_SELECTOR, duration_sel)
                            duration = duration_elem.text.strip()
                            if duration and ('h' in duration or 'min' in duration):
                                break
                        except:
                            continue

                    flight_data = {
                        'price': price,
                        'airline': airline,
                        'duration': duration,
                        'element_text': element.text[:200] + "..." if len(element.text) > 200 else element.text
                    }

                    flights.append(flight_data)
                    print(f"Flight {i+1}: {price} - {airline} - {duration}")

                except Exception as e:
                    print(f"⚠️ Error extracting flight {i+1}: {e}")
                    continue

            print(f"✅ Extracted {len(flights)} flights")
            return flights

        except Exception as e:
            print(f"❌ Error extracting flight data: {e}")
            return []

    def get_cheapest_flight(self, flights):
        """Find the cheapest flight from the results"""
        if not flights:
            return None

        cheapest = None
        min_price = float('inf')

        for flight in flights:
            price_text = flight.get('price', '')
            # Extract numeric price
            import re
            price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
            if price_match:
                try:
                    price_num = float(price_match.group().replace(',', ''))
                    if price_num < min_price:
                        min_price = price_num
                        cheapest = flight
                except:
                    continue

        return cheapest

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def main():
    """Main function to run the Google Flights scraper"""
    scraper = GoogleFlightsScraper(headless=False)  # Set to True for headless mode

    try:
        # Search flights from CPH (Copenhagen) to AYT (Antalya)
        flights = scraper.search_flights(
            origin="CPH",
            destination="AYT",
            departure_date="2025-10-17",  # Adjust dates as needed
            return_date="2025-10-24"
        )

        if flights:
            print(f"\n🔍 Found {len(flights)} flights:")
            for i, flight in enumerate(flights, 1):
                print(f"{i}. {flight['price']} - {flight['airline']} - {flight['duration']}")

            # Get cheapest flight
            cheapest = scraper.get_cheapest_flight(flights)
            if cheapest:
                print(f"\n💰 Cheapest flight: {cheapest['price']} - {cheapest['airline']}")

            # Save to CSV
            df = pd.DataFrame(flights)
            df.to_csv('google_flights_results.csv', index=False)
            print(f"\n💾 Results saved to google_flights_results.csv")

        else:
            print("❌ No flights found")

    except Exception as e:
        print(f"❌ Error in main: {e}")

    finally:
        scraper.close()

if __name__ == "__main__":
    main()
