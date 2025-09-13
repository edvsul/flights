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
    """Enhanced method for Skyscanner using requests with anti-detection"""
    try:
        print("🔄 Trying enhanced Skyscanner requests...")

        # Create session for cookie persistence
        session = requests.Session()

        # Enhanced headers with more realistic fingerprint
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="140", "Google Chrome";v="140"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"macOS"'
        }

        session.headers.update(headers)

        # First, visit homepage to establish session
        print("🌐 Establishing session via homepage...")
        try:
            homepage_response = session.get("https://www.skyscanner.net", timeout=15)

            # Check for CAPTCHA on homepage
            if homepage_response.status_code == 200:
                content_lower = homepage_response.text.lower()
                captcha_indicators = ['captcha', 'are you a person or a robot', 'perimeterx', 'px-captcha', 'human verification', 'access denied']

                if any(indicator in content_lower for indicator in captcha_indicators):
                    print("❌ CAPTCHA detected on homepage via requests!")
                    save_debug_html(homepage_response.text, "captcha_homepage_requests")
                    return "CAPTCHA detected on homepage", "Requests CAPTCHA"

                print("✅ Homepage loaded successfully")
            else:
                print(f"⚠️  Homepage returned status: {homepage_response.status_code}")

        except Exception as e:
            logger.warning(f"Homepage visit failed: {e}")

        # Human-like delay
        time.sleep(random.uniform(2, 5))

        # Try multiple Skyscanner URLs with different strategies
        urls = [
            "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR",
            "https://www.skyscanner.com/transport/flights/cph/ayt/251017/251024/?adults=1&cabinclass=economy&rtn=1",
            "https://www.skyscanner.de/transport/fluge/cph/ayt/?adults=1&cabinclass=economy",
            "https://www.skyscanner.net/transport/flights/cph/ayt/?adults=1&currency=EUR"
        ]

        for i, url in enumerate(urls):
            try:
                logger.info(f"Trying Skyscanner requests with URL {i+1}/{len(urls)}: {url}")

                # Add referer for more realistic requests
                if i > 0:
                    session.headers.update({'Referer': urls[i-1]})

                # Random delay between requests
                if i > 0:
                    delay = random.uniform(3, 8)
                    print(f"⏱️  Human-like delay: {delay:.1f}s")
                    time.sleep(delay)

                response = session.get(url, timeout=30)
                print(f"Response status: {response.status_code}")

                if response.status_code == 200:
                    # Check for CAPTCHA first
                    content_lower = response.text.lower()
                    captcha_indicators = ['captcha', 'are you a person or a robot', 'perimeterx', 'px-captcha', 'human verification', 'access denied']

                    if any(indicator in content_lower for indicator in captcha_indicators):
                        print(f"❌ CAPTCHA detected on URL {i+1}!")
                        save_debug_html(response.text, f"captcha_url_{i+1}_requests")
                        continue  # Try next URL

                    save_debug_html(response.text, f"skyscanner_requests_url_{i+1}")

                    # Parse HTML with BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Enhanced JSON data extraction from script tags
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if script.string and len(script.string) > 100:  # Only check substantial scripts
                            script_content = script.string.lower()
                            if any(keyword in script_content for keyword in ['price', 'eur', 'amount', 'cost']):
                                # Multiple JSON price extraction patterns
                                json_patterns = [
                                    r'"price"[^}]*?(\d{2,4})',
                                    r'"EUR"[^}]*?(\d{2,4})',
                                    r'"currency":"EUR"[^}]*?"amount":(\d{2,4})',
                                    r'"amount":(\d{2,4})[^}]*?"currency":"EUR"',
                                    r'"value":(\d{2,4})[^}]*?"currency":"EUR"',
                                    r'"totalPrice":(\d{2,4})',
                                    r'"basePrice":(\d{2,4})'
                                ]

                                for pattern in json_patterns:
                                    json_prices = re.findall(pattern, script.string)
                                    if json_prices:
                                        for price_str in json_prices:
                                            try:
                                                price_num = int(price_str)
                                                # More restrictive price range to avoid false positives
                                                if 100 <= price_num <= 1500:  # Realistic flight price range
                                                    price = f"€{price_num}"
                                                    logger.info(f"Skyscanner requests found price in JSON: {price}")
                                                    return f"{price} (Skyscanner-Requests-JSON)", "Skyscanner Requests JSON"
                                            except ValueError:
                                                continue

                    # Enhanced HTML text price patterns with better validation
                    price_patterns = [
                        r'€\s*(\d{2,4})',
                        r'EUR\s*(\d{2,4})',
                        r'(\d{2,4})\s*€',
                        r'(\d{2,4})\s*EUR',
                        # German specific patterns
                        r'ab\s*€\s*(\d{2,4})',
                        r'von\s*€\s*(\d{2,4})',
                        # English patterns
                        r'from\s*€\s*(\d{2,4})',
                        r'starting\s*at\s*€\s*(\d{2,4})',
                    ]

                    found_prices = []
                    for pattern in price_patterns:
                        matches = re.findall(pattern, response.text, re.IGNORECASE)
                        if matches:
                            for match in matches:
                                try:
                                    price_num = int(match)
                                    # More restrictive validation - avoid common false positives
                                    if 100 <= price_num <= 1500 and price_num not in [2000, 1000]:  # Exclude common false positives
                                        found_prices.append(price_num)
                                except ValueError:
                                    continue

                    if found_prices:
                        # Remove duplicates, sort, and take the lowest reasonable price
                        unique_prices = sorted(list(set(found_prices)))
                        # Filter out prices that are too high or common false positives
                        realistic_prices = [p for p in unique_prices if p < 1000]

                        if realistic_prices:
                            price = f"€{realistic_prices[0]}"
                            logger.info(f"Skyscanner requests found realistic price: {price}")
                            return f"{price} (Skyscanner-Requests)", "Skyscanner Requests"
                        elif unique_prices:
                            # If no realistic prices, take the lowest available but flag it
                            price = f"€{unique_prices[0]}"
                            logger.warning(f"Skyscanner requests found high price (possible false positive): {price}")
                            return f"{price} (Skyscanner-Requests-HighPrice)", "Skyscanner Requests High"

                elif response.status_code == 403:
                    print(f"❌ Access denied (403) for URL {i+1}")
                    save_debug_html(response.text, f"access_denied_url_{i+1}")
                    continue
                elif response.status_code == 429:
                    print(f"❌ Rate limited (429) for URL {i+1}")
                    # Longer delay for rate limiting
                    time.sleep(random.uniform(10, 20))
                    continue
                else:
                    logger.info(f"Skyscanner requests: Unexpected status {response.status_code} for {url}")

            except requests.exceptions.Timeout:
                logger.error(f"Skyscanner requests timeout for {url}")
                continue
            except Exception as e:
                logger.error(f"Skyscanner requests error for {url}: {e}")
                continue

        logger.warning("Skyscanner requests: No prices found in any URL")
        return "No prices found", "Skyscanner Requests No Prices"

    except Exception as e:
        logger.error(f"Skyscanner requests error: {e}")
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
