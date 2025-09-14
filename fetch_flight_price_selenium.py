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

class GoogleFlightsScraper:
    def __init__(self, headless=True):
        self.driver = None
        self.setup_driver(headless)

    def setup_driver(self, headless):
        """Setup Chrome driver with optimized options"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless")

        # Essential options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Anti-detection measures
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Performance optimizations
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            self.driver = webdriver.Chrome(options=chrome_options)

        # Hide webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Set timeouts
        self.driver.implicitly_wait(10)
        self.driver.set_page_load_timeout(30)

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

            # Build Google Flights URL
            base_url = "https://www.google.com/travel/flights"
            url = f"{base_url}?q=Flights%20to%20{destination}%20from%20{origin}%20on%20{departure_date}%20through%20{return_date}"

            print(f"🌐 Loading: {url}")
            self.driver.get(url)

            # Wait for page to load
            time.sleep(5)

            # Handle cookie consent if present
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(text(), 'OK')]"))
                )
                cookie_button.click()
                time.sleep(2)
                print("✅ Cookie consent accepted")
            except TimeoutException:
                print("ℹ️ No cookie consent found")

            # Wait for flight results to load
            print("⏳ Waiting for flight results...")
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='flight-offer']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".pIav2d")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[jsname='IWWDBc']")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'flight') or contains(@data-testid, 'flight')]"))
                    )
                )
                print("✅ Flight results loaded")
            except TimeoutException:
                print("⚠️ Timeout waiting for results")

            # Additional wait for dynamic content
            time.sleep(10)

            # Extract flight data
            flights = self.extract_flight_data()

            return flights

        except Exception as e:
            print(f"❌ Error searching flights: {e}")
            return []

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
            print(f"\n� Found {len(flights)} flights:")
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
