import subprocess
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import random
from urllib.parse import urlencode

COUNTRIES = ["Germany", "India", "Mexico", "Turkey", "Thailand"]
RESULTS_FILE = "flight_prices.csv"

# VPN control
def connect_vpn(country):
    print(f"🔗 Connecting to NordVPN: {country}")
    result = subprocess.run(["nordvpn", "connect", country], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Connected to {country}")
    else:
        print(f"❌ Failed to connect to {country}: {result.stderr}")
    time.sleep(10)  # Wait for connection to stabilize

def disconnect_vpn():
    print("🔌 Disconnecting VPN...")
    subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)
    time.sleep(5)

def get_current_ip():
    """Get current IP to verify VPN connection"""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        return response.json().get("ip", "Unknown")
    except:
        return "Unknown"

def get_random_user_agent():
    """Return a random user agent to avoid detection"""
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

def create_session():
    """Create a requests session with proper headers"""
    session = requests.Session()

    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

    session.headers.update(headers)
    return session

def scrape_kayak_prices():
    """Scrape flight prices from Kayak"""
    try:
        session = create_session()

        # Kayak search URL for CPH to AYT
        params = {
            'origin': 'CPH',
            'destination': 'AYT',
            'depart': '2025-10-17',
            'return': '2025-10-24',
            'adults': '1',
            'currency': 'EUR'
        }

        url = f"https://www.kayak.com/flights/CPH-AYT/2025-10-17/2025-10-24?sort=bestflight_a&adults=1"

        print("� Scraping Kayak for flight prices...")
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for price elements (Kayak uses various selectors)
            price_selectors = [
                '[data-testid="price-text"]',
                '.price-text',
                '.f8F1-price-text',
                '[class*="price"]',
                '[data-testid*="price"]'
            ]

            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    for element in price_elements[:3]:  # Check first 3 matches
                        price_text = element.get_text(strip=True)
                        if '€' in price_text or '$' in price_text:
                            return f"{price_text} (Kayak)", "Kayak Scraping"

            # Fallback: look for any element containing price-like text
            all_text = soup.get_text()
            import re
            prices = re.findall(r'€\s*\d{2,4}', all_text)
            if prices:
                return f"{prices[0]} (Kayak)", "Kayak Scraping"

        return "No prices found on Kayak", "Kayak Scraping"

    except Exception as e:
        print(f"❌ Kayak scraping error: {e}")
        return "Kayak scraping failed", "Kayak Scraping Error"

def scrape_momondo_prices():
    """Scrape flight prices from Momondo"""
    try:
        session = create_session()

        # Momondo search URL
        url = "https://www.momondo.com/flight-search/CPH-AYT/2025-10-17/2025-10-24?sort=bestflight_a&adults=1"

        print("🔍 Scraping Momondo for flight prices...")
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for price elements
            price_selectors = [
                '[data-testid="price_column"]',
                '.price',
                '[class*="price"]',
                '.f8F1-price-text'
            ]

            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    for element in price_elements[:3]:
                        price_text = element.get_text(strip=True)
                        if '€' in price_text or '$' in price_text:
                            return f"{price_text} (Momondo)", "Momondo Scraping"

            # Fallback: regex search
            all_text = soup.get_text()
            import re
            prices = re.findall(r'€\s*\d{2,4}', all_text)
            if prices:
                return f"{prices[0]} (Momondo)", "Momondo Scraping"

        return "No prices found on Momondo", "Momondo Scraping"

    except Exception as e:
        print(f"❌ Momondo scraping error: {e}")
        return "Momondo scraping failed", "Momondo Scraping Error"

def scrape_skyscanner_prices():
    """Scrape flight prices from Skyscanner"""
    try:
        session = create_session()

        # Skyscanner search URL
        url = "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR"

        print("🔍 Scraping Skyscanner for flight prices...")
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Skyscanner price selectors
            price_selectors = [
                '[data-testid="listing-price-detailed"]',
                '[data-testid="price"]',
                '.BpkText_bpk-text__price',
                '[class*="Price"]',
                '[class*="price"]',
                '.fqs-price'
            ]

            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    for element in price_elements[:3]:
                        price_text = element.get_text(strip=True)
                        if '€' in price_text or '$' in price_text or '£' in price_text:
                            return f"{price_text} (Skyscanner)", "Skyscanner Scraping"

            # Fallback: regex search for prices
            all_text = soup.get_text()
            import re
            prices = re.findall(r'[€$£]\s*\d{2,4}', all_text)
            if prices:
                return f"{prices[0]} (Skyscanner)", "Skyscanner Scraping"

        return "No prices found on Skyscanner", "Skyscanner Scraping"

    except Exception as e:
        print(f"❌ Skyscanner scraping error: {e}")
        return "Skyscanner scraping failed", "Skyscanner Scraping Error"

def fetch_price_simulation(country):
    """Simulate flight prices for testing purposes"""
    import random

    # Simulate scraping delay
    time.sleep(random.uniform(2, 5))

    # Generate realistic price based on country
    base_prices = {
        "Germany": (300, 500),
        "India": (250, 400),
        "Mexico": (400, 600),
        "Turkey": (200, 350),
        "Thailand": (350, 550)
    }

    price_range = base_prices.get(country, (300, 500))
    price = random.randint(price_range[0], price_range[1])

    return f"€{price} (simulated)", "Simulation"

def fetch_flight_price(country):
    """Try multiple scraping sources in order of preference"""

    # Add random delay to avoid being detected as bot
    time.sleep(random.uniform(3, 8))

    # Try Kayak first (usually most reliable)
    try:
        price, method = scrape_kayak_prices()
        if "failed" not in price.lower() and "no prices" not in price.lower():
            return price, method
    except:
        pass

    # Try Momondo second
    try:
        price, method = scrape_momondo_prices()
        if "failed" not in price.lower() and "no prices" not in price.lower():
            return price, method
    except:
        pass

    # Try Skyscanner third
    try:
        price, method = scrape_skyscanner_prices()
        if "failed" not in price.lower() and "no prices" not in price.lower():
            return price, method
    except:
        pass

    # Fallback to simulation
    price, method = fetch_price_simulation(country)
    return price, method

# Main agent loop
def run_agent():
    print("🚀 Starting flight price monitoring agent...")
    print("🕷️  Using web scraping approach (Beautiful Soup)")
    print(f"📊 Results will be saved to: {RESULTS_FILE}")

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

            # Fetch price using web scraping
            print("💰 Scraping flight prices from booking sites...")
            price, method = fetch_flight_price(country)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"💸 {country}: {price} (via {method})")

            # Save results
            writer.writerow([country, current_ip, price, timestamp, method])
            file.flush()  # Ensure data is written immediately

            # Disconnect VPN
            disconnect_vpn()

            print(f"✅ Completed: {country}")

    print(f"\n🎉 All done! Results saved to {RESULTS_FILE}")
    print("\n📋 This script uses web scraping with Beautiful Soup")
    print("   No API keys needed - scrapes directly from booking sites!")

if __name__ == "__main__":
    run_agent()
