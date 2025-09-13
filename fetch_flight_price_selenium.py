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

def scrape_skyscanner_requests():
    """Fallback method for Skyscanner using requests when Selenium fails"""
    try:
        print("🔄 Trying Skyscanner requests fallback...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Try multiple Skyscanner URLs
        urls = [
            "https://www.skyscanner.com/transport/flights/cph/ayt/251017/251024/?adults=1&cabinclass=economy&rtn=1",
            "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR",
            "https://www.skyscanner.com/transport/flights/cph/ayt/?adults=1&cabinclass=economy",
            "https://www.skyscanner.de/transport/fluge/cph/ayt/?adults=1&cabinclass=economy"
        ]

        for url in urls:
            try:
                logger.info(f"Trying Skyscanner requests with URL: {url}")
                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    save_debug_html(response.text, "skyscanner_requests")

                    # Parse HTML with BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Look for JSON data in script tags (common in modern SPAs)
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if script.string and ('price' in script.string.lower() or 'eur' in script.string.lower()):
                            # Extract prices from JSON data
                            json_prices = re.findall(r'"price"[^}]*?(\d{2,4})', script.string)
                            eur_prices = re.findall(r'"EUR"[^}]*?(\d{2,4})', script.string)
                            currency_prices = re.findall(r'"currency":"EUR"[^}]*?"amount":(\d{2,4})', script.string)

                            all_found_prices = json_prices + eur_prices + currency_prices
                            if all_found_prices:
                                for price_str in all_found_prices:
                                    price_num = int(price_str)
                                    if 50 <= price_num <= 2000:
                                        price = f"€{price_num}"
                                        logger.info(f"Skyscanner requests found price in JSON: {price}")
                                        return f"{price} (Skyscanner-Requests-JSON)", "Skyscanner Requests JSON"

                    # Look for price patterns in the HTML text
                    price_patterns = [
                        r'€\s*(\d{2,4})',
                        r'EUR\s*(\d{2,4})',
                        r'(\d{2,4})\s*€',
                        r'(\d{2,4})\s*EUR',
                        r'"price":\s*"?€?(\d{2,4})',
                        r'"amount":\s*"?(\d{2,4})"?',
                        r'price.*?(\d{2,4})',
                        # German specific patterns
                        r'ab\s*€\s*(\d{2,4})',
                        r'€(\d{2,4})',
                        r'(\d{2,4})€',
                    ]

                    for pattern in price_patterns:
                        matches = re.findall(pattern, response.text, re.IGNORECASE)
                        if matches:
                            valid_prices = []
                            for match in matches:
                                try:
                                    price_num = int(match)
                                    if 50 <= price_num <= 2000:
                                        valid_prices.append(f"€{price_num}")
                                except ValueError:
                                    continue

                            if valid_prices:
                                price = valid_prices[0]
                                logger.info(f"Skyscanner requests found price: {price}")
                                return f"{price} (Skyscanner-Requests)", "Skyscanner Requests"

                logger.info(f"Skyscanner requests: No prices found in {url} (status: {response.status_code})")

            except Exception as e:
                logger.error(f"Skyscanner requests error for {url}: {e}")
                continue

        logger.warning("Skyscanner requests: No prices found in any URL")
        return "No prices found", "Skyscanner Requests No Prices"

    except Exception as e:
        logger.error(f"Skyscanner requests fallback error: {e}")
        return f"Error: {str(e)}", "Skyscanner Requests Error"

def fetch_flight_price_skyscanner_only(country):
    """Fetch flight prices from Skyscanner only using requests"""

    delay = random.uniform(10, 20)
    print(f"⏱️  Waiting {delay:.1f} seconds before scraping...")
    time.sleep(delay)

    try:
        print(f"🔍 Scraping Skyscanner with requests...")
        price, method = scrape_skyscanner_requests()

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
    print("🕷️  Skyscanner ONLY - with human-like behavior simulation")
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

            # Connect to VPN
            connect_vpn(country)

            # Verify connection
            current_ip = get_current_ip()
            print(f"🌐 Current IP: {current_ip}")

            # Fetch price using Skyscanner only
            print("💰 Scraping Skyscanner with requests...")
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
    print("\n📋 Check debug_skyscanner_requests.html for troubleshooting")

if __name__ == "__main__":
    run_agent()
