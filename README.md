# Flight Price Monitoring with Skyscanner

Automated flight price monitoring script that scrapes Skyscanner using HTTP requests with enhanced anti-detection and VPN rotation to compare prices from different countries.

## 🎯 Features

- **Skyscanner-only scraping** using HTTP requests with anti-detection
- **VPN rotation** through Germany using NordVPN
- **Session-based requests** with cookie persistence
- **Enhanced anti-detection** with realistic browser fingerprinting
- **CAPTCHA detection** and automatic URL fallback
- **Smart price validation** to avoid false positives
- **Debug mode** with HTML output for troubleshooting
- **CSV export** of all collected price data

## 📋 System Requirements

### Operating System
- Linux (Amazon Linux, RHEL, Ubuntu, etc.)
- macOS (for development)

### Software Dependencies
- **Python 3.8+** (tested with Python 3.12.7)
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

### 4. Setup NordVPN
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
- Germany (primary)

### Files Generated
- `flight_prices.csv` - Price data results
- `debug_skyscanner_requests_url_*.html` - Debug HTML for troubleshooting

## 🏃‍♂️ Usage

### Basic Usage
```bash
python3 fetch_flight_price.py
```

### Expected Output
```
🚀 Starting Skyscanner-only flight price monitoring agent...
🕷️  Skyscanner ONLY - with human-like behavior simulation
❌ NO simulation fallback - real data only
📊 Results will be saved to: flight_prices.csv
🐛 Debug mode: True

⚠️  Requirements: requests library installed

============================================================
🌍 Processing: Germany
🔗 Connecting to NordVPN: Germany
✅ Connected to Germany
🌐 Current IP: [German IP]
💰 Scraping Skyscanner with requests...
⏱️  Waiting 15.2 seconds before scraping...
🔍 Scraping Skyscanner with requests...
🔄 Trying enhanced Skyscanner requests...
🌐 Establishing session via homepage...
✅ Homepage loaded successfully
⏱️  Human-like delay: 4.2s
Response status: 200
💸 Germany: €245 (Skyscanner-Requests) (via Skyscanner Requests)
✅ Completed: Germany

🎉 All done! Results saved to flight_prices.csv
```

### Output Files
- **`flight_prices.csv`**: Contains columns: Country, IP Address, Price, Timestamp, Method
- **`debug_skyscanner_requests_url_*.html`**: Full HTML content captured for each URL attempt

## 🔧 Anti-Detection Features

### Enhanced Request Headers
- **Realistic Chrome 140 fingerprint** with proper Sec-CH-UA headers
- **macOS platform identification** for consistency
- **Complete HTTP header set** including Sec-Fetch attributes

### Session Management
- **Cookie persistence** across requests
- **Homepage session establishment** before search queries
- **Referer chain** for realistic navigation patterns

### CAPTCHA Handling
- **Real-time CAPTCHA detection** on all pages
- **Automatic URL fallback** when blocked
- **Multiple domain strategy** (.net, .com, .de)

### Price Validation
- **Smart price filtering** (€100-€1500 range)
- **False positive detection** excludes common fake prices
- **Realistic price prioritization** under €1000

## 🔧 Troubleshooting

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
Set `DEBUG_MODE = True` in the script to generate detailed HTML debug files for each URL attempt.

### Common Errors

**"CAPTCHA detected"**
- The script automatically tries multiple URLs when CAPTCHA is encountered
- Check debug HTML files to see what protection was triggered

**"VPN connection failed"**
- Ensure NordVPN is properly installed and logged in
- Check your NordVPN subscription status

**"No prices found"**
- Check `debug_skyscanner_requests_url_*.html` files for page content
- Skyscanner may have changed their page structure
- Price may be outside the validation range (€100-€1500)

**"High price (possible false positive)"**
- Script detected a price but flagged it as potentially incorrect
- Check debug HTML to verify if it's a real price

## 📊 Results Format

The CSV output contains:
```csv
Country,IP Address,Price,Timestamp,Method
Germany,1.2.3.4,€245 (Skyscanner-Requests),2025-09-13 16:30:00,Skyscanner Requests
```

## 🔒 Security & Ethics

- Uses enhanced anti-detection techniques to avoid blocking
- Respects website rate limits with human-like delays
- Rotates through different IP addresses via VPN
- Session-based requests mimic real browser behavior
- For personal use only - respect Skyscanner's terms of service

## 🛠️ Development

### Project Structure
```
flights/
├── fetch_flight_price.py  # Main requests-based scraper
├── test_captcha.py        # CAPTCHA detection test script
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore           # Git ignore patterns
├── flight_prices.csv   # Generated results
└── debug_*.html       # Generated debug files
```

### Dependencies
- `requests>=2.31.0` - HTTP requests and session management
- `beautifulsoup4>=4.12.0` - HTML parsing

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
