#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

def test_skyscanner_requests():
    """Test if Skyscanner shows CAPTCHA via requests"""
    print("🔍 Testing Skyscanner with requests...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    url = "https://www.skyscanner.com/transport/flights/cph/ayt/251017/251024/?adults=1"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status code: {response.status_code}")

        # Check for CAPTCHA indicators
        content = response.text.lower()
        captcha_indicators = [
            'captcha',
            'are you a person or a robot',
            'perimeterx',
            'px-captcha',
            'human verification',
            'bot detection',
            'access denied'
        ]

        found_indicators = [indicator for indicator in captcha_indicators if indicator in content]

        if found_indicators:
            print(f"❌ CAPTCHA detected! Found indicators: {found_indicators}")
            return False
        else:
            print("✅ No CAPTCHA detected in requests")
            return True

    except Exception as e:
        print(f"❌ Requests test failed: {e}")
        return False

def test_skyscanner_selenium():
    """Test if Skyscanner shows CAPTCHA via Selenium"""
    print("🔍 Testing Skyscanner with Selenium...")

    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = uc.Chrome(options=options, version_main=140)

        url = "https://www.skyscanner.com/transport/flights/cph/ayt/251017/251024/?adults=1"
        driver.get(url)

        time.sleep(5)

        page_source = driver.page_source.lower()

        # Check for CAPTCHA indicators
        captcha_indicators = [
            'captcha',
            'are you a person or a robot',
            'perimeterx',
            'px-captcha',
            'human verification',
            'bot detection',
            'access denied'
        ]

        found_indicators = [indicator for indicator in captcha_indicators if indicator in page_source]

        if found_indicators:
            print(f"❌ CAPTCHA detected! Found indicators: {found_indicators}")

            # Save debug HTML
            with open("debug_captcha_selenium.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Debug HTML saved to debug_captcha_selenium.html")
            return False
        else:
            print("✅ No CAPTCHA detected in Selenium")
            return True

    except Exception as e:
        print(f"❌ Selenium test failed: {e}")
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print("🧪 Testing Skyscanner CAPTCHA status...")
    print("=" * 50)

    requests_ok = test_skyscanner_requests()
    print()
    selenium_ok = test_skyscanner_selenium()

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Requests method: {'✅ OK' if requests_ok else '❌ CAPTCHA'}")
    print(f"Selenium method: {'✅ OK' if selenium_ok else '❌ CAPTCHA'}")

    if not requests_ok and not selenium_ok:
        print("\n⚠️  Both methods are blocked by CAPTCHA!")
        print("Need to implement enhanced anti-detection measures.")
    elif requests_ok or selenium_ok:
        print(f"\n✅ At least one method is working!")
