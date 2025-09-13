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

def create_selenium_driver(headless=True):
    """Create Selenium WebDriver with enhanced anti-detection for PerimeterX bypass"""
    try:
        print("🤖 Creating undetected Chrome driver with enhanced PerimeterX bypass...")

        # Advanced Chrome options for maximum stealth
        options = uc.ChromeOptions()

        # Essential stealth options
        if headless:
            options.add_argument("--headless=new")

        # Enhanced anti-detection arguments
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")

        # Remove automation indicators
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")

        # Realistic browser fingerprint
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Memory and performance optimizations
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")

        # Network and security for bypass
        options.add_argument("--disable-web-security")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")

        # Additional PerimeterX bypass options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)

        # Prefs to disable automation detection
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.plugins": 1,
            "profile.content_settings.plugin_whitelist.adobe-flash-player": 1,
            "profile.content_settings.exceptions.plugins.*,*.per_resource.adobe-flash-player": 1,
            "PluginsAllowedForUrls": ["https://www.skyscanner.com", "https://www.skyscanner.net", "https://www.skyscanner.de"]
        }
        options.add_experimental_option("prefs", prefs)

        # Create driver with specific version for stability
        driver = uc.Chrome(options=options, version_main=120, driver_executable_path=None)

        # Enhanced stealth techniques for PerimeterX bypass
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // Mock chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // Mock permissions
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' }),
                    }),
                });

                // Override automation detection
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => 1,
                });

                // Mock connection
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        rtt: 50,
                        downlink: 10
                    }),
                });

                // Remove automation flags
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

                // Mock screen properties
                Object.defineProperty(screen, 'availWidth', {
                    get: () => 1920,
                });
                Object.defineProperty(screen, 'availHeight', {
                    get: () => 1080,
                });

                // Mock timezone
                Date.prototype.getTimezoneOffset = function() {
                    return -60; // CET timezone
                };
            '''
        })

        # Additional CDP commands for stealth
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "acceptLanguage": "en-US,en;q=0.9",
            "platform": "MacIntel"
        })

        # Set realistic viewport
        driver.set_window_size(1920, 1080)
        driver.set_window_position(0, 0)

        logger.info("✅ Enhanced undetected Chrome driver created successfully")
        return driver

    except Exception as e:
        logger.error(f"❌ Failed to create Chrome driver: {e}")
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
        driver = create_selenium_driver(headless=False)
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

def scrape_skyscanner_requests():
    """Fallback method for Skyscanner using requests when Selenium fails"""
    try:
        print("🔄 Trying Skyscanner requests fallback...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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

        # Fallback to requests if Selenium fails
        print("🔄 Fallback to Skyscanner requests...")
        price, method = scrape_skyscanner_requests()
        if price and method and "error" not in price.lower() and "failed" not in method.lower():
            if any(currency in price for currency in ['€', '$', '£']):
                logger.info(f"SUCCESS with Skyscanner requests: {price}")
                return price, method
            else:
                logger.info(f"Skyscanner requests returned: {price} (no currency found)")
        else:
            logger.info(f"Skyscanner requests returned: {price} via {method}")

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
