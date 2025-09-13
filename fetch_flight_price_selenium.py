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

def scrape_pegasus_airlines():
    """Scrape Pegasus Airlines direct booking page for CPH-AYT flights"""
    try:
        print("🔄 Trying Pegasus Airlines direct booking...")
        session = requests.Session()

        # Enhanced headers for Pegasus website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
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

        # Step 1: Visit Pegasus homepage to establish session
        print("🏠 Establishing session with Pegasus Airlines...")
        homepage_response = session.get("https://web.flypgs.com/", timeout=15)
        if homepage_response.status_code != 200:
            return "Pegasus homepage access failed", "Session establishment error"

        # Step 2: Access the direct booking URL
        pegasus_url = "https://web.flypgs.com/booking?AFFILIATEID=XSS00&returnDate=2025-10-24&arrivalPort=AYT&adultCount=1&dateOption=1&language=EN&childCount=0&departurePort=CPH&currency=EUR&departureDate=2025-10-17&infantCount=0&skyscanner_redirectid=E8cT5f9OTQCKksEVF5ULsQ"

        print("🔍 Accessing Pegasus booking page...")
        time.sleep(random.uniform(2, 4))  # Human-like delay

        response = session.get(pegasus_url, timeout=30)
        print(f"Pegasus response status: {response.status_code}")

        if response.status_code == 200:
            # Save debug HTML
            save_debug_html(response.text, "pegasus_booking")

            # Check for common blocking indicators
            content_lower = response.text.lower()
            blocking_indicators = ['captcha', 'access denied', 'blocked', 'security check', 'human verification']

            if any(indicator in content_lower for indicator in blocking_indicators):
                print("❌ Pegasus page blocked or requires verification!")
                return "Pegasus page blocked", "Access denied"

            # Extract prices using multiple strategies
            price = extract_pegasus_prices(response.text)
            if price:
                return price, "Pegasus Airlines Direct"

            # Try API endpoint discovery for Pegasus
            api_price = try_pegasus_api_endpoints(session, response.text)
            if api_price:
                return api_price, "Pegasus API"

        elif response.status_code == 302 or response.status_code == 301:
            print("🔄 Pegasus redirected, following redirect...")
            # Follow redirect manually to maintain session
            redirect_url = response.headers.get('Location')
            if redirect_url:
                redirect_response = session.get(redirect_url, timeout=30)
                if redirect_response.status_code == 200:
                    save_debug_html(redirect_response.text, "pegasus_redirect")
                    price = extract_pegasus_prices(redirect_response.text)
                    if price:
                        return price, "Pegasus Airlines Redirect"

        return "No Pegasus prices found", "Pegasus scraping failed"

    except Exception as e:
        logger.error(f"Pegasus Airlines scraping failed: {e}")
        return "Pegasus scraping error", f"Error: {str(e)}"


def extract_pegasus_prices(html_content):
    """Extract prices from Pegasus Airlines booking page"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Strategy 1: Look for Pegasus-specific price elements
        pegasus_price_selectors = [
            # Common airline booking price selectors
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="Price"]',
            '[class*="fare"]',
            '[class*="Fare"]',
            '[class*="amount"]',
            '[class*="Amount"]',
            '[class*="total"]',
            '[class*="Total"]',
            # Pegasus-specific selectors (common patterns)
            '.flight-price',
            '.fare-price',
            '.booking-price',
            '.total-price',
            '[data-price]',
            '[data-fare]',
            '.currency',
            # Turkish airline specific
            '.ucret',
            '.fiyat',
            '.tutar'
        ]

        for selector in pegasus_price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    # Check text content
                    text = element.get_text(strip=True)
                    price = extract_price_from_text(text)
                    if price:
                        print(f"✅ Found Pegasus price in element: {price}")
                        return price

                    # Check attributes
                    for attr in ['data-price', 'data-fare', 'data-amount', 'title', 'aria-label', 'value']:
                        attr_value = element.get(attr, '')
                        if attr_value:
                            price = extract_price_from_text(attr_value)
                            if price:
                                print(f"✅ Found Pegasus price in attribute {attr}: {price}")
                                return price
            except Exception:
                continue

        # Strategy 2: Look for JSON data in script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and len(script.string) > 50:
                script_content = script.string

                # Look for flight/booking data structures
                json_patterns = [
                    r'flightData["\']?\s*[:=]\s*({.+?})',
                    r'bookingData["\']?\s*[:=]\s*({.+?})',
                    r'fareData["\']?\s*[:=]\s*({.+?})',
                    r'priceData["\']?\s*[:=]\s*({.+?})',
                    r'"flights":\s*(\[.+?\])',
                    r'"fares":\s*(\[.+?\])',
                    r'"prices":\s*(\[.+?\])',
                    r'window\.initialData\s*=\s*({.+?});',
                    r'window\.flightResults\s*=\s*({.+?});'
                ]

                for pattern in json_patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL)
                    for match in matches:
                        try:
                            json_data = json.loads(match)
                            price = extract_price_from_api_response(json_data)
                            if price:
                                print(f"✅ Found Pegasus price in JSON: {price}")
                                return price
                        except json.JSONDecodeError:
                            continue

        # Strategy 3: Search for EUR price patterns in entire HTML
        eur_patterns = [
            r'€\s*(\d{2,4}(?:[.,]\d{2})?)',
            r'EUR\s*(\d{2,4}(?:[.,]\d{2})?)',
            r'(\d{2,4}(?:[.,]\d{2})?)\s*€',
            r'(\d{2,4}(?:[.,]\d{2})?)\s*EUR',
            # Turkish Lira patterns (in case EUR not available)
            r'₺\s*(\d{3,5}(?:[.,]\d{2})?)',
            r'TL\s*(\d{3,5}(?:[.,]\d{2})?)',
            r'(\d{3,5}(?:[.,]\d{2})?)\s*₺',
            r'(\d{3,5}(?:[.,]\d{2})?)\s*TL'
        ]

        for pattern in eur_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.replace(',', '.')
                    price_num = float(price_str)

                    # Different validation for EUR vs TL
                    if '€' in pattern or 'EUR' in pattern:
                        if 100 <= price_num <= 1500:
                            print(f"✅ Found EUR price pattern: €{price_num}")
                            return f"€{price_num}"
                    else:  # Turkish Lira
                        if 3000 <= price_num <= 45000:  # Approximate TL range
                            # Convert TL to EUR (approximate rate 1 EUR = 30 TL)
                            eur_price = price_num / 30
                            if 100 <= eur_price <= 1500:
                                print(f"✅ Found TL price pattern: ₺{price_num} (~€{eur_price:.0f})")
                                return f"€{eur_price:.0f}"
                except ValueError:
                    continue

        return None

    except Exception as e:
        print(f"Error extracting Pegasus prices: {e}")
        return None


def try_pegasus_api_endpoints(session, html_content):
    """Try to find and call Pegasus API endpoints"""
    try:
        # Look for API endpoints in the HTML/JavaScript
        api_patterns = [
            r'["\']([^"\']*api[^"\']*flight[^"\']*)["\']',
            r'["\']([^"\']*flight[^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*booking[^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*search[^"\']*flight[^"\']*)["\']',
            r'url["\']?\s*:\s*["\']([^"\']*api[^"\']*)["\']',
            r'endpoint["\']?\s*:\s*["\']([^"\']*)["\']'
        ]

        potential_endpoints = []
        for pattern in api_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            potential_endpoints.extend(matches)

        # Common Pegasus API endpoint patterns
        base_endpoints = [
            "/api/flight/search",
            "/api/booking/search",
            "/api/flights/availability",
            "/booking/api/search",
            "/flight/api/search"
        ]

        # Try potential endpoints
        for endpoint in set(potential_endpoints + base_endpoints):
            if not endpoint.startswith('http'):
                endpoint = f"https://web.flypgs.com{endpoint}"

            try:
                print(f"🔍 Trying Pegasus API: {endpoint}")

                # Prepare API request
                api_headers = session.headers.copy()
                api_headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': 'https://web.flypgs.com/booking'
                })

                # Try both GET and POST
                for method in ['GET', 'POST']:
                    try:
                        if method == 'GET':
                            api_response = session.get(endpoint, headers=api_headers, timeout=15)
                        else:
                            # Basic flight search payload
                            payload = {
                                "departurePort": "CPH",
                                "arrivalPort": "AYT",
                                "departureDate": "2025-10-17",
                                "returnDate": "2025-10-24",
                                "adultCount": 1,
                                "childCount": 0,
                                "infantCount": 0,
                                "currency": "EUR"
                            }
                            api_response = session.post(endpoint, json=payload, headers=api_headers, timeout=15)

                        if api_response.status_code == 200:
                            try:
                                api_data = api_response.json()
                                price = extract_price_from_api_response(api_data)
                                if price:
                                    print(f"✅ Found price via Pegasus API: {price}")
                                    return price
                            except json.JSONDecodeError:
                                continue

                    except Exception:
                        continue

            except Exception:
                continue

        return None

    except Exception as e:
        print(f"Error trying Pegasus API endpoints: {e}")
        return None


def extract_price_from_api_response(api_data):
    """Extract price from API JSON response"""
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
        price, source = scrape_pegasus_airlines()

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
