import subprocess
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import random
import logging
import re
import json
from typing import Optional, Union
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COUNTRIES = ["Germany"]
RESULTS_FILE = "flight_prices.csv"
DEBUG_MODE = True

# VPN control
def connect_vpn(country):
    print(f"🔗 Connecting to NordVPN: {country}")
    result = subprocess.run(["nordvpn", "connect", country], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Connected to {country}")
    else:
        print(f"❌ Failed to connect to {country}: {result.stderr}")
    time.sleep(20)

def disconnect_vpn():
    print("🔌 Disconnecting VPN...")
    subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
    time.sleep(10)

def get_current_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        return response.json().get("ip", "Unknown")
    except:
        return "Unknown"

def save_debug_html(content, filename):
    if DEBUG_MODE:
        with open(f"debug_{filename}.html", "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        logger.info(f"Debug HTML saved to debug_{filename}.html")

def scrape_pegasus_selenium():
    """Scrape Pegasus Airlines using improved Selenium approach based on RapidSeedbox template"""
    driver = None
    try:
        print("🔄 Starting improved Pegasus Airlines Selenium scraper...")

        # Create driver with enhanced options
        driver = make_pegasus_driver(headless=True)

        # Build Pegasus URL
        pegasus_url = build_pegasus_url(
            origin="CPH",
            destination="AYT",
            departure_date="2025-10-17",
            return_date="2025-10-24"
        )

        print(f"🔍 Loading Pegasus URL: {pegasus_url}")
        driver.get(pegasus_url)

        # Wait for flight results to load
        print("⏳ Waiting for flight results...")
        try:
            WebDriverWait(driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".flight-result")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='flight']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".fare-option")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='price']")),
                    EC.invisibility_of_element_located((By.ID, "loading"))
                )
            )
            print("✅ Flight results loaded")
        except TimeoutException:
            print("⚠️  Timeout waiting for results, checking page anyway...")

        # Wait a bit more for dynamic content
        time.sleep(5)

        # Save debug HTML
        save_debug_html(driver.page_source, "pegasus_selenium_improved")

        # Extract flight details
        flights = extract_pegasus_flights(driver)

        if flights:
            # Return the first/cheapest flight price
            cheapest = min(flights, key=lambda x: x.get('price_numeric', float('inf')))
            price = cheapest.get('price', 'No price found')
            return price, f"Pegasus Selenium Improved ({len(flights)} flights found)"

        return "No flights found with improved Selenium", "Selenium improved - no results"

    except Exception as e:
        logger.error(f"Improved Pegasus Selenium scraping failed: {e}")
        return "Improved Selenium error", f"Error: {str(e)}"
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def make_pegasus_driver(headless: bool = True) -> webdriver.Chrome:
    """Create optimized Chrome driver for Pegasus Airlines"""
    opts = Options()

    if headless:
        opts.add_argument("--headless=new")  # Modern headless mode

    # Essential arguments for stability
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    # Anti-detection measures
    opts.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    # Performance optimizations
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-images")
    # opts.add_argument("--disable-javascript")  # Removed - JS needed for price loading

    # Use webdriver-manager for automatic ChromeDriver management
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    except:
        # Fallback to system ChromeDriver
        driver = webdriver.Chrome(options=opts)

    # Hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def build_pegasus_url(origin: str, destination: str, departure_date: str, return_date: str) -> str:
    """Build Pegasus Airlines search URL"""
    base = "https://web.flypgs.com/booking"
    params = {
        "language": "en",
        "adultCount": 1,
        "arrivalPort": destination,
        "departurePort": origin,
        "currency": "EUR",
        "dateOption": 1,
        "departureDate": departure_date,
        "returnDate": return_date,
        "ili": f"{origin}-{destination}",
        "iln": "home page-Booking"
    }

    from urllib.parse import urlencode
    return f"{base}?{urlencode(params)}"


def get_text_safe(parent, css: str) -> Optional[str]:
    """Safely get text from CSS selector"""
    try:
        element = parent.find_element(By.CSS_SELECTOR, css)
        return element.text.strip() if element.text else None
    except:
        return None


def extract_pegasus_flights(driver) -> list[dict]:
    """Extract flight details from Pegasus Airlines results page"""
    flights = []

    # Multiple selectors to find flight cards
    flight_selectors = [
        ".flight-result",
        "[data-testid*='flight']",
        ".fare-option",
        ".flight-option",
        ".booking-option",
        "[class*='flight-card']",
        "[class*='FlightCard']"
    ]

    cards = []
    for selector in flight_selectors:
        try:
            found_cards = driver.find_elements(By.CSS_SELECTOR, selector)
            if found_cards:
                cards = found_cards
                print(f"✅ Found {len(cards)} flight cards with selector: {selector}")
                break
        except:
            continue

    if not cards:
        print("❌ No flight cards found, trying alternative extraction...")
        # Try to find any elements with price information
        price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '€') or contains(text(), '₺')]")
        for element in price_elements:
            try:
                text = element.text.strip()
                price = extract_price_from_text(text)
                if price:
                    flights.append({
                        "airline": "Pegasus Airlines",
                        "price": price,
                        "price_numeric": float(price.replace('€', '').replace(',', '.')),
                        "departure_time": None,
                        "arrival_time": None,
                        "duration": None,
                        "stops": None,
                        "scraped_at": int(time.time())
                    })
            except:
                continue
        return flights

    # Extract details from each flight card
    for i, card in enumerate(cards):
        try:
            # Try multiple price selectors
            price_selectors = [
                ".price", "[data-testid*='price']", "[class*='price']", "[class*='Price']",
                ".fare", "[class*='fare']", ".amount", "[class*='amount']",
                ".total", "[class*='total']", ".currency"
            ]

            price = None
            for price_sel in price_selectors:
                price_text = get_text_safe(card, price_sel)
                if price_text:
                    price = extract_price_from_text(price_text)
                    if price:
                        break

            # If no price in selectors, check all text in card
            if not price:
                card_text = card.text
                price = extract_price_from_text(card_text)

            # Extract other details
            airline = get_text_safe(card, ".airline") or get_text_safe(card, "[class*='airline']") or "Pegasus Airlines"
            departure = get_text_safe(card, ".departure") or get_text_safe(card, "[class*='departure']")
            arrival = get_text_safe(card, ".arrival") or get_text_safe(card, "[class*='arrival']")
            duration = get_text_safe(card, ".duration") or get_text_safe(card, "[class*='duration']")
            stops = get_text_safe(card, ".stops") or get_text_safe(card, "[class*='stops']")

            if price:
                try:
                    price_numeric = float(price.replace('€', '').replace('₺', '').replace(',', '.'))
                except:
                    price_numeric = float('inf')

                flights.append({
                    "airline": airline,
                    "price": price,
                    "price_numeric": price_numeric,
                    "departure_time": departure,
                    "arrival_time": arrival,
                    "duration": duration,
                    "stops": stops,
                    "scraped_at": int(time.time())
                })
                print(f"✅ Extracted flight {i+1}: {airline} - {price}")

        except Exception as e:
            print(f"❌ Error extracting flight {i+1}: {e}")
            continue

    return flights


def extract_price_from_text(text):
    """Extract and validate price from text"""
    if not text:
        return None

    # Multiple price patterns
    patterns = [
        r'€\s*(\d{2,4}(?:[.,]\d{2})?)',
        r'(\d{2,4}(?:[.,]\d{2})?)\s*€',
        r'EUR\s*(\d{2,4}(?:[.,]\d{2})?)',
        r'(\d{2,4}(?:[.,]\d{2})?)\s*EUR'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price_str = match.replace(',', '.')
                price_num = float(price_str)
                # Validate realistic price range and exclude common false positives
                if 100 <= price_num <= 1500 and price_num not in [1000, 2000]:
                    return f"€{price_num}"
            except ValueError:
                continue

    return None


def fetch_flight_price_pegasus_only(country):
    """Fetch flight prices from Pegasus Airlines only"""
    try:
        print(f"\n🇹🇷 Fetching Pegasus Airlines prices via {country}...")

        # Connect to VPN
        connect_vpn(country)

        # Get current IP
        current_ip = get_current_ip()
        print(f"🌐 Current IP: {current_ip}")

        # Scrape Pegasus
        price, source = scrape_pegasus_selenium()

        # Disconnect VPN
        disconnect_vpn()

        return {
            'Country': country,
            'IP': current_ip,
            'Price': price,
            'Source': source,
            'Timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        logger.error(f"Pegasus fetching failed for {country}: {e}")
        disconnect_vpn()  # Ensure VPN is disconnected
        return {
            'Country': country,
            'IP': 'Unknown',
            'Price': f'Error: {str(e)}',
            'Source': 'Pegasus Error',
            'Timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }


# Main agent loop
def run_agent():
    print("🚀 Starting Pegasus Airlines-only flight price monitoring agent...")
    print("🕷️  Pegasus Airlines ONLY - with human-like behavior simulation")
    print("❌ NO simulation fallback - real data only")
    print(f"📊 Results will be saved to: {RESULTS_FILE}")
    print(f"🐛 Debug mode: {DEBUG_MODE}")
    print("\n⚠️  Requirements: requests library installed")

    with open(RESULTS_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Country", "IP Address", "Price", "Timestamp", "Method"])

        for country in COUNTRIES:
            print(f"\n{'='*60}")
            print(f"🌍 Processing: {country}")

            result = fetch_flight_price_pegasus_only(country)

            writer.writerow([result['Country'], result['IP'], result['Price'], result['Timestamp'], result['Source']])
            file.flush()

            print(f"✅ Completed: {country}")

    print(f"\n🎉 All done! Results saved to {RESULTS_FILE}")
    print("\n📋 Check debug_skyscanner_requests.html for troubleshooting")


if __name__ == "__main__":
    run_agent()
