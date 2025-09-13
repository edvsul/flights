import subprocess
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import random
from urllib.parse import urlencode
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COUNTRIES = ["Germany", "India"]
RESULTS_FILE = "flight_prices.csv"
DEBUG_MODE = True  # Set to True for detailed debugging

# VPN control
def connect_vpn(country):
    print(f"🔗 Connecting to NordVPN: {country}")
    result = subprocess.run(["nordvpn", "connect", country], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Connected to {country}")
    else:
        print(f"❌ Failed to connect to {country}: {result.stderr}")
    time.sleep(15)  # Longer wait for connection to stabilize

def disconnect_vpn():
    print("🔌 Disconnecting VPN...")
    subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
    time.sleep(8)

def get_current_ip():
    """Get current IP to verify VPN connection"""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        return response.json().get("ip", "Unknown")
    except:
        return "Unknown"

def get_random_user_agent():
    """Return a random realistic user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0'
    ]
    return random.choice(user_agents)

def create_session():
    """Create a requests session with enhanced headers and settings"""
    session = requests.Session()

    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"'
    }

    session.headers.update(headers)

    # Add some realistic session behavior
    session.cookies.set('currency', 'EUR')
    session.cookies.set('locale', 'en-US')

    return session

def save_debug_html(content, filename):
    """Save HTML content for debugging"""
    if DEBUG_MODE:
        with open(f"debug_{filename}.html", "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        logger.info(f"Debug HTML saved to debug_{filename}.html")

def scrape_kayak_improved():
    """Improved Kayak scraping with better anti-detection"""
    try:
        session = create_session()

        # First, visit the main page to get cookies
        print("🔍 Visiting Kayak homepage first...")
        session.get("https://www.kayak.com", timeout=20)
        time.sleep(random.uniform(3, 6))

        # Now try the search
        search_url = "https://www.kayak.com/flights/CPH-AYT/2025-10-17/2025-10-24?sort=bestflight_a&adults=1"

        print("🔍 Scraping Kayak with improved method...")
        response = session.get(search_url, timeout=30)

        if response.status_code == 200:
            save_debug_html(response.text, "kayak_improved")
            soup = BeautifulSoup(response.content, 'html.parser')

            # More comprehensive price selectors
            price_selectors = [
                '[data-testid="price-text"]',
                '.f8F1-price-text',
                '.price-text',
                '[class*="price"]',
                '[data-testid*="price"]',
                '.Flights-Results-FlightPriceSection',
                '.resultWrapper .price'
            ]

            for selector in price_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    for element in elements[:5]:
                        text = element.get_text(strip=True)
                        logger.info(f"Element text: {text}")
                        if any(currency in text for currency in ['€', '$', '£']) and any(char.isdigit() for char in text):
                            return f"{text} (Kayak)", "Kayak Improved"

            # Check if we're being blocked
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logger.warning("Kayak appears to be blocking requests")
                return "Blocked by Kayak", "Kayak Blocked"

        return None, None

    except Exception as e:
        logger.error(f"Kayak improved error: {e}")
        return None, None

def scrape_skyscanner():
    """Scrape Skyscanner with enhanced anti-detection"""
    try:
        session = create_session()

        # Visit homepage first
        print("🔍 Visiting Skyscanner homepage first...")
        session.get("https://www.skyscanner.net", timeout=20)
        time.sleep(random.uniform(3, 6))

        # Skyscanner search URL
        url = "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR"

        print("🔍 Scraping Skyscanner...")
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            save_debug_html(response.text, "skyscanner")
            soup = BeautifulSoup(response.content, 'html.parser')

            # Skyscanner price selectors
            price_selectors = [
                '[data-testid="listing-price-detailed"]',
                '[data-testid="price"]',
                '.BpkText_bpk-text__price',
                '[class*="Price"]',
                '[class*="price"]',
                '.fqs-price',
                '[data-testid*="price"]'
            ]

            for selector in price_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    for element in elements[:5]:
                        text = element.get_text(strip=True)
                        logger.info(f"Element text: {text}")
                        if any(currency in text for currency in ['€', '$', '£']) and any(char.isdigit() for char in text):
                            return f"{text} (Skyscanner)", "Skyscanner"

            # Check if blocked
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logger.warning("Skyscanner appears to be blocking requests")
                return "Blocked by Skyscanner", "Skyscanner Blocked"

        return None, None

    except Exception as e:
        logger.error(f"Skyscanner error: {e}")
        return None, None

def scrape_kiwi():
    """Scrape Kiwi.com with enhanced anti-detection"""
    try:
        session = create_session()

        # Visit homepage first
        print("🔍 Visiting Kiwi.com homepage first...")
        session.get("https://www.kiwi.com", timeout=20)
        time.sleep(random.uniform(3, 6))

        # Kiwi.com search URL
        url = "https://www.kiwi.com/en/search/results/copenhagen-denmark/antalya-turkey/2025-10-17/2025-10-24?sortBy=price&adults=1&currency=EUR"

        print("🔍 Scraping Kiwi.com...")
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            save_debug_html(response.text, "kiwi")
            soup = BeautifulSoup(response.content, 'html.parser')

            # Kiwi.com price selectors
            price_selectors = [
                '[data-test="ResultCardPrice"]',
                '[data-test*="price"]',
                '.ResultCardPrice',
                '[class*="Price"]',
                '[class*="price"]',
                '.price',
                '[data-testid*="price"]'
            ]

            for selector in price_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    for element in elements[:5]:
                        text = element.get_text(strip=True)
                        logger.info(f"Element text: {text}")
                        if any(currency in text for currency in ['€', '$', '£']) and any(char.isdigit() for char in text):
                            return f"{text} (Kiwi)", "Kiwi.com"

            # Check if blocked
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logger.warning("Kiwi.com appears to be blocking requests")
                return "Blocked by Kiwi.com", "Kiwi Blocked"

        return None, None

    except Exception as e:
        logger.error(f"Kiwi.com error: {e}")
        return None, None

def fetch_flight_price_improved(country):
    """Flight price fetching with only real scraping - no simulation"""

    # Add longer random delay
    delay = random.uniform(8, 15)
    print(f"⏱️  Waiting {delay:.1f} seconds before scraping...")
    time.sleep(delay)

    strategies = [
        ("Kayak", scrape_kayak_improved),
        ("Skyscanner", scrape_skyscanner),
        ("Kiwi.com", scrape_kiwi)
    ]

    for strategy_name, strategy_func in strategies:
        try:
            print(f"🔍 Trying {strategy_name}...")
            price, method = strategy_func()
            if price and method and "failed" not in price.lower() and "blocked" not in price.lower():
                logger.info(f"Success with {strategy_name}: {price}")
                return price, method
            else:
                logger.info(f"{strategy_name} didn't return valid price")
        except Exception as e:
            logger.error(f"{strategy_name} failed: {e}")
            continue

    # No fallback - return failure if all scraping methods fail
    logger.error("All scraping methods failed - no price data available")
    return "No price data available", "All scraping failed"

# Main agent loop
def run_agent():
    print("🚀 Starting flight price monitoring agent...")
    print("🕷️  Using ONLY real scraping from Kayak, Skyscanner, and Kiwi.com")
    print("❌ NO simulation fallback - real data only")
    print(f"📊 Results will be saved to: {RESULTS_FILE}")
    print(f"🐛 Debug mode: {DEBUG_MODE}")

    with open(RESULTS_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Country", "IP Address", "Price", "Timestamp", "Method"])

        for country in COUNTRIES:
            print(f"\n{'='*50}")
            print(f"🌍 Processing: {country}")

            # Connect to VPN
            connect_vpn(country)

            # Verify connection
            current_ip = get_current_ip()
            print(f"🌐 Current IP: {current_ip}")

            # Fetch price using only real scraping methods
            print("💰 Scraping flight prices from real sites only...")
            price, method = fetch_flight_price_improved(country)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"💸 {country}: {price} (via {method})")

            # Save results
            writer.writerow([country, current_ip, price, timestamp, method])
            file.flush()  # Ensure data is written immediately

            # Disconnect VPN
            disconnect_vpn()

            print(f"✅ Completed: {country}")

    print(f"\n🎉 All done! Results saved to {RESULTS_FILE}")
    print("\n📋 This script uses ONLY real scraping - no simulated data")
    print("   Check debug_*.html files for troubleshooting if scraping fails")

if __name__ == "__main__":
    run_agent()
