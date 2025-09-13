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

# Undetected Chrome driver for advanced bot detection bypass
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COUNTRIES = ["Germany", "India"]
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

def create_selenium_driver():
    """Create an undetected Selenium Chrome driver with stealth options"""
    try:
        # Use undetected-chromedriver with advanced stealth
        options = uc.ChromeOptions()

        # Basic stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Advanced anti-detection
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")

        # Performance options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--memory-pressure-off")

        # Window size (important for detection)
        options.add_argument("--window-size=1920,1080")

        # Run in headless mode
        options.add_argument("--headless=new")  # Use new headless mode

        # Create undetected Chrome driver
        driver = uc.Chrome(
            options=options,
            version_main=None,  # Auto-detect Chrome version
            driver_executable_path=None,  # Auto-download driver
            browser_executable_path=None,  # Use system Chrome
            user_data_dir=None,  # Use temp profile
            suppress_welcome=True,
            use_subprocess=True,
            debug=False
        )

        # Additional stealth measures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("window.chrome = { runtime: {} }")

        # Set realistic viewport
        driver.set_window_size(1920, 1080)

        return driver

    except Exception as e:
        logger.error(f"Failed to create undetected Chrome driver: {e}")
        return None

def save_debug_html(content, filename):
    if DEBUG_MODE:
        with open(f"debug_{filename}.html", "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        logger.info(f"Debug HTML saved to debug_{filename}.html")

def scrape_skyscanner_selenium():
    """Scrape Skyscanner using Selenium for JavaScript rendering"""
    driver = None
    try:
        driver = create_selenium_driver()
        if not driver:
            return "Driver creation failed", "Selenium Error"

        print("🔍 Loading Skyscanner with Selenium...")

        # Navigate to search URL
        search_url = "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR"
        driver.get(search_url)

        # Wait for page to load
        print("⏳ Waiting for JavaScript to load content...")
        time.sleep(15)  # Give time for JS to render

        # Wait for price elements to appear
        try:
            # Wait for any price-related element
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='price'], [class*='price'], .price")))
            logger.info("Price elements detected on page")
        except TimeoutException:
            logger.warning("Timeout waiting for price elements")

        # Additional wait for dynamic content
        time.sleep(10)

        # Get page source after JavaScript execution
        page_source = driver.page_source
        save_debug_html(page_source, "skyscanner_selenium")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Comprehensive price selectors
        price_selectors = [
            '[data-testid="listing-price-detailed"]',
            '[data-testid="price"]',
            '[data-testid*="price"]',
            '.BpkText_bpk-text__price',
            '[class*="Price"]',
            '[class*="price"]',
            '.fqs-price',
            '[aria-label*="price"]',
            '[title*="price"]'
        ]

        for selector in price_selectors:
            elements = soup.select(selector)
            logger.info(f"Skyscanner Selenium: Found {len(elements)} elements for '{selector}'")

            for element in elements[:10]:
                text = element.get_text(strip=True)
                if text:
                    logger.info(f"Element text: {text}")
                    # Look for price patterns
                    price_match = re.search(r'[€$£]\s*\d{2,4}', text)
                    if price_match:
                        price = price_match.group()
                        logger.info(f"Skyscanner Selenium: Found price {price}")
                        return f"{price} (Skyscanner-Selenium)", "Skyscanner Selenium"

        # Fallback: search entire page text
        all_text = soup.get_text()
        prices = re.findall(r'[€$£]\s*\d{2,4}', all_text)
        if prices:
            valid_prices = [p for p in prices if 100 <= int(re.search(r'\d+', p).group()) <= 2000]
            if valid_prices:
                price = valid_prices[0]
                logger.info(f"Skyscanner Selenium: Found price via regex: {price}")
                return f"{price} (Skyscanner-Selenium-regex)", "Skyscanner Selenium"

        logger.warning("Skyscanner Selenium: No prices found")
        return "No prices found", "Skyscanner Selenium No Prices"

    except Exception as e:
        logger.error(f"Skyscanner Selenium error: {e}")
        return f"Error: {str(e)}", "Skyscanner Selenium Error"
    finally:
        if driver:
            driver.quit()

def fetch_flight_price_skyscanner_only(country):
    """Fetch flight prices from Skyscanner only using Selenium"""

    delay = random.uniform(10, 20)
    print(f"⏱️  Waiting {delay:.1f} seconds before scraping...")
    time.sleep(delay)

    try:
        print(f"🔍 Scraping Skyscanner with Selenium...")
        price, method = scrape_skyscanner_selenium()

        if price and method and "error" not in price.lower() and "failed" not in method.lower():
            if any(currency in price for currency in ['€', '$', '£']):
                logger.info(f"SUCCESS with Skyscanner: {price}")
                return price, method
            else:
                logger.info(f"Skyscanner returned: {price} (no currency found)")
        else:
            logger.info(f"Skyscanner returned: {price} via {method}")

    except Exception as e:
        logger.error(f"Skyscanner failed: {e}")

    logger.error("Skyscanner scraping failed")
    return "Skyscanner scraping failed", "No data available"

# Main agent loop
def run_agent():
    print("🚀 Starting Skyscanner-only flight price monitoring agent...")
    print("🤖 Using UNDETECTED Chrome for advanced bot bypass")
    print("🕷️  Skyscanner ONLY - with human-like behavior simulation")
    print("❌ NO simulation fallback - real data only")
    print(f"📊 Results will be saved to: {RESULTS_FILE}")
    print(f"🐛 Debug mode: {DEBUG_MODE}")
    print("\n⚠️  Requirements: Chrome browser and undetected-chromedriver installed")

    with open(RESULTS_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Country", "IP Address", "Price", "Timestamp", "Method"])

        for country in COUNTRIES:
            print(f"\n{'='*60}")
            print(f"🌍 Processing: {country}")

            # Connect to VPN
            connect_vpn(country)

            # Verify connection
            current_ip = get_current_ip()
            print(f"🌐 Current IP: {current_ip}")

            # Fetch price using Skyscanner only
            print("💰 Scraping Skyscanner with undetected Chrome...")
            price, method = fetch_flight_price_skyscanner_only(country)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"💸 {country}: {price} (via {method})")

            # Save results
            writer.writerow([country, current_ip, price, timestamp, method])
            file.flush()

            # Disconnect VPN
            disconnect_vpn()

            print(f"✅ Completed: {country}")

    print(f"\n🎉 All done! Results saved to {RESULTS_FILE}")
    print("\n📋 Check debug_skyscanner_selenium.html for troubleshooting")

if __name__ == "__main__":
    run_agent()
