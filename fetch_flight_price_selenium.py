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
    try:
        print("🔄 Trying enhanced Skyscanner requests with API discovery...")
        session = requests.Session()

        # Enhanced headers with more realistic browser fingerprinting
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="140", "Google Chrome";v="140", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        session.headers.update(headers)

        # Step 1: Establish session via homepage
        print("🏠 Establishing session via homepage...")
        homepage_response = session.get("https://www.skyscanner.net", timeout=15)
        if homepage_response.status_code != 200:
            return "Homepage access failed", "Session establishment error"

        # Check for CAPTCHA on homepage
        if any(indicator in homepage_response.text.lower() for indicator in ['captcha', 'perimeterx', 'px-captcha']):
            print("❌ CAPTCHA detected on homepage!")
            return "CAPTCHA detected", "Homepage blocked"

        # Step 2: Try API endpoints first (most reliable)
        api_endpoints = [
            # Modern Skyscanner API endpoints
            "https://www.skyscanner.net/g/conductor/v1/fps3/search/?adults=1&cabinClass=economy&currency=EUR&locale=en-US&locationSchema=sky&market=US&destinationEntityId=95673612&originEntityId=95673519&outboundDate=2025-10-17&inboundDate=2025-10-24",
            "https://www.skyscanner.net/api/v1/flights/browse/browsequotes/v1.0/US/EUR/en-US/CPH-sky/AYT-sky/2025-10-17/2025-10-24?adults=1&children=0&infants=0&cabinclass=Economy",
            "https://www.skyscanner.de/g/chiron/api/v1/prices/search?adults=1&cabinClass=economy&currency=EUR&locale=de-DE&market=DE&destinationEntityId=95673612&originEntityId=95673519&outboundDate=2025-10-17&inboundDate=2025-10-24",
        ]

        for i, api_url in enumerate(api_endpoints):
            try:
                print(f"🔍 Trying API endpoint {i+1}/{len(api_endpoints)}")

                # Update headers for API calls
                api_headers = session.headers.copy()
                api_headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': 'https://www.skyscanner.net/',
                    'X-Requested-With': 'XMLHttpRequest'
                })

                api_response = session.get(api_url, headers=api_headers, timeout=30)
                print(f"API response status: {api_response.status_code}")

                if api_response.status_code == 200:
                    try:
                        api_data = api_response.json()
                        print(f"✅ Got JSON response from API endpoint {i+1}")

                        # Extract prices from API response
                        price = extract_price_from_api_response(api_data)
                        if price:
                            return price, f"API endpoint {i+1}"

                    except json.JSONDecodeError:
                        print(f"❌ API endpoint {i+1} returned non-JSON data")
                        continue

            except Exception as e:
                print(f"❌ API endpoint {i+1} failed: {e}")
                continue

        # Step 3: Enhanced web scraping with multiple strategies
        time.sleep(random.uniform(2, 5))

        # Try multiple Skyscanner URLs with different strategies
        urls = [
            "https://www.skyscanner.net/transport/flights/cph/ayt/251017/251024/?adults=1&currency=EUR",
            "https://www.skyscanner.com/transport/flights/cph/ayt/251017/251024/?adults=1&cabinclass=economy&rtn=1",
            "https://www.skyscanner.de/transport/fluge/cph/ayt/251017/251024/?adults=1&cabinclass=economy&rtn=1",
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

                    # Enhanced price extraction strategies
                    price = extract_price_from_html_enhanced(response.text)
                    if price:
                        return price, f"Enhanced HTML extraction URL {i+1}"

            except Exception as e:
                logger.error(f"URL {i+1} failed: {e}")
                continue

        return "No prices found with enhanced methods", "All strategies failed"

    except Exception as e:
        logger.error(f"Enhanced Skyscanner requests failed: {e}")
        return "Enhanced scraping failed", f"Error: {str(e)}"


def extract_price_from_api_response(api_data):
    """Extract price from Skyscanner API JSON response"""
    try:
        # Common API response structures
        price_paths = [
            # Modern API structure
            ['Quotes', 0, 'MinPrice'],
            ['quotes', 0, 'price'],
            ['results', 0, 'pricing_options', 0, 'price', 'amount'],
            ['itineraries', 0, 'pricing_options', 0, 'price', 'amount'],
            # Legacy API structure
            ['Quotes', 0, 'Price'],
            ['quotes', 0, 'Price'],
            # Direct price fields
            ['price'],
            ['minPrice'],
            ['totalPrice'],
            ['amount']
        ]

        def get_nested_value(data, path):
            """Safely get nested dictionary value"""
            current = data
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
                    current = current[key]
                else:
                    return None
            return current

        # Try each path
        for path in price_paths:
            price_value = get_nested_value(api_data, path)
            if price_value is not None:
                # Validate price
                if isinstance(price_value, (int, float)) and 100 <= price_value <= 1500:
                    return f"€{price_value}"
                elif isinstance(price_value, str):
                    # Extract numeric value from string
                    import re
                    price_match = re.search(r'(\d+(?:\.\d{2})?)', str(price_value))
                    if price_match:
                        price_num = float(price_match.group(1))
                        if 100 <= price_num <= 1500:
                            return f"€{price_num}"

        # Search for any price-like values in the entire response
        price_regex = re.compile(r'["\']?(?:price|amount|cost)["\']?\s*:\s*["\']?(\d+(?:\.\d{2})?)["\']?', re.IGNORECASE)
        api_str = str(api_data)
        matches = price_regex.findall(api_str)

        for match in matches:
            try:
                price_num = float(match)
                if 100 <= price_num <= 1500:
                    return f"€{price_num}"
            except ValueError:
                continue

        return None

    except Exception as e:
        print(f"Error extracting price from API response: {e}")
        return None


def extract_price_from_html_enhanced(html_content):
    """Enhanced price extraction from HTML with multiple strategies"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Strategy 1: Look for embedded JSON data in script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and len(script.string) > 100:
                script_content = script.string

                # Look for window.__INITIAL_STATE__ or similar
                json_patterns = [
                    r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                    r'window\.__internal\s*=\s*({.+?});',
                    r'window\[\"__internal\"\]\s*=\s*({.+?});',
                    r'__NEXT_DATA__["\']?\s*:\s*({.+?})',
                    r'REDUX_STATE["\']?\s*:\s*({.+?})',
                    r'"searchResults":\s*({.+?})',
                    r'"itineraries":\s*(\[.+?\])',
                    r'"quotes":\s*(\[.+?\])'
                ]

                for pattern in json_patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL)
                    for match in matches:
                        try:
                            json_data = json.loads(match)
                            price = extract_price_from_api_response(json_data)
                            if price:
                                return price
                        except json.JSONDecodeError:
                            continue

        # Strategy 2: Look for price patterns in HTML attributes and text
        price_selectors = [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="Price"]',
            '[class*="amount"]',
            '[class*="cost"]',
            '.BpkText_bpk-text__*[title*="€"]',
            '[aria-label*="€"]',
            '[title*="€"]'
        ]

        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    # Check text content
                    text = element.get_text(strip=True)
                    price = extract_price_from_text(text)
                    if price:
                        return price

                    # Check attributes
                    for attr in ['title', 'aria-label', 'data-price', 'value']:
                        attr_value = element.get(attr, '')
                        if attr_value:
                            price = extract_price_from_text(attr_value)
                            if price:
                                return price
            except Exception:
                continue

        # Strategy 3: Search entire HTML for price patterns
        price_regex = re.compile(r'€\s*(\d{2,4}(?:[.,]\d{2})?)', re.IGNORECASE)
        matches = price_regex.findall(html_content)

        for match in matches:
            try:
                # Handle both comma and dot as decimal separator
                price_str = match.replace(',', '.')
                price_num = float(price_str)
                if 100 <= price_num <= 1500:
                    return f"€{price_num}"
            except ValueError:
                continue

        return None

    except Exception as e:
        print(f"Error in enhanced HTML price extraction: {e}")
        return None


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
