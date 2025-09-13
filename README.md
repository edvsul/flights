# Flight Price Monitoring with Skyscanner

Automated flight price monitoring script that scrapes Skyscanner using Selenium WebDriver with VPN rotation to compare prices from different countries.

## 🎯 Features

- **Skyscanner-only scraping** using Selenium for JavaScript rendering
- **VPN rotation** through Germany and India using NordVPN
- **Automatic ChromeDriver management** with WebDriver Manager
- **Stealth browsing** with anti-detection measures
- **Debug mode** with HTML output for troubleshooting
- **CSV export** of all collected price data

## 📋 System Requirements

### Operating System
- Linux (Amazon Linux, RHEL, Ubuntu, etc.)
- macOS (for development)

### Software Dependencies
- **Python 3.8+** (tested with Python 3.12.7)
- **Google Chrome** or **Chromium** browser
- **NordVPN** CLI client
- **Git** (for version control)

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd flights
```

### 2. Python Environment Setup
```bash
# Using pyenv (recommended)
pyenv shell 3.12.7

# Or using system Python
python3 --version  # Ensure 3.8+
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Chrome Browser

#### Option A: Google Chrome (Recommended)
```bash
# Add Google Chrome repository
sudo tee /etc/yum.repos.d/google-chrome.repo <<EOF
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

# Install Chrome
sudo dnf install -y google-chrome-stable
```

#### Option B: Chromium (Alternative)
```bash
# Enable EPEL repository
sudo dnf install -y epel-release

# Install Chromium
sudo dnf install -y chromium chromium-headless
```

### 5. Setup NordVPN
```bash
# Install NordVPN (follow official instructions)
# https://nordvpn.com/download/linux/

# Login to NordVPN
nordvpn login

# Test connection
nordvpn connect Germany
nordvpn status
nordvpn disconnect
```

## ⚙️ Configuration

### Target Route
Currently configured for: **Copenhagen (CPH) → Antalya (AYT)**
- Departure: October 17, 2025
- Return: October 24, 2025
- Passengers: 1 adult

### VPN Countries
- Germany
- India

### Files Generated
- `flight_prices.csv` - Price data results
- `debug_skyscanner_selenium.html` - Debug HTML for troubleshooting

## 🏃‍♂️ Usage

### Basic Usage
```bash
python3 fetch_flight_price_selenium.py
```

### Expected Output
```
🚀 Starting Skyscanner-only flight price monitoring agent...
🤖 Using Selenium for JavaScript rendering
🕷️  Skyscanner ONLY - no other sites
❌ NO simulation fallback - real data only
📊 Results will be saved to: flight_prices.csv

============================================================
🌍 Processing: Germany
🔗 Connecting to NordVPN: Germany
✅ Connected to Germany
🌐 Current IP: [German IP]
💰 Scraping Skyscanner with Selenium...
🔍 Loading Skyscanner with Selenium...
⏳ Waiting for JavaScript to load content...
Price elements detected on page
💸 Germany: €245 (Skyscanner-Selenium) (via Skyscanner Selenium)
✅ Completed: Germany

============================================================
🌍 Processing: India
[... continues for India ...]

🎉 All done! Results saved to flight_prices.csv
```

### Output Files
- **`flight_prices.csv`**: Contains columns: Country, IP Address, Price, Timestamp, Method
- **`debug_skyscanner_selenium.html`**: Full HTML content captured by Selenium

## 🔧 Troubleshooting

### ChromeDriver Issues
The script uses WebDriver Manager to automatically handle ChromeDriver versions. If you encounter issues:

```bash
# Verify Chrome installation
google-chrome --version

# Test Selenium
python3 -c "from selenium import webdriver; print('Selenium ready!')"
```

### VPN Connection Issues
```bash
# Check NordVPN status
nordvpn status

# Test manual connection
nordvpn connect Germany
curl https://api.ipify.org
nordvpn disconnect
```

### Debug Mode
Set `DEBUG_MODE = True` in the script to generate detailed HTML debug files.

### Common Errors

**"Chrome version mismatch"**
- Solution: WebDriver Manager automatically handles this

**"VPN connection failed"**
- Ensure NordVPN is properly installed and logged in
- Check your NordVPN subscription status

**"No prices found"**
- Check `debug_skyscanner_selenium.html` for page content
- Skyscanner may have changed their page structure

## 📊 Results Format

The CSV output contains:
```csv
Country,IP Address,Price,Timestamp,Method
Germany,1.2.3.4,€245 (Skyscanner-Selenium),2025-09-13 16:30:00,Skyscanner Selenium
India,5.6.7.8,€198 (Skyscanner-Selenium),2025-09-13 16:35:00,Skyscanner Selenium
```

## 🔒 Security & Ethics

- Uses stealth browsing techniques to avoid detection
- Respects website rate limits with random delays
- Rotates through different IP addresses via VPN
- For personal use only - respect Skyscanner's terms of service

## 🛠️ Development

### Project Structure
```
flights/
├── fetch_flight_price_selenium.py  # Main Selenium-based scraper
├── fetch_flight_price.py          # Legacy requests-based scraper
├── requirements.txt               # Python dependencies
├── README.md                     # This file
├── .gitignore                   # Git ignore patterns
├── flight_prices.csv           # Generated results
└── debug_*.html               # Generated debug files
```

### Dependencies
- `beautifulsoup4>=4.12.0` - HTML parsing
- `selenium>=4.15.0` - Browser automation
- `requests>=2.31.0` - HTTP requests (for IP checking)
- `webdriver-manager>=4.0.0` - Automatic ChromeDriver management

## 📝 License

This project is for educational and personal use only. Please respect the terms of service of the websites being scraped.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**⚠️ Disclaimer**: This tool is for personal use only. Always respect website terms of service and rate limits. Use responsibly.
