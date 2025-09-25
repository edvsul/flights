# Copenhagen to Antalya Flight Price Scraper

A comprehensive flight price monitoring tool that scrapes Google Flights for Copenhagen (CPH) to Antalya (AYT) flights using NordVPN to compare prices from different geographic locations.

## 🎯 What This Script Does

This script automatically:
- **Connects to multiple NordVPN countries** to simulate browsing from different locations
- **Scrapes Google Flights** for direct/nonstop flights from Copenhagen to Antalya
- **Forces EUR currency** for consistent price comparison across all locations
- **Captures screenshots** of flight results from each country
- **Extracts flight prices** and saves them to CSV files
- **Generates consolidated reports** comparing prices across all tested countries

### Target Flight Details
- **Route**: Copenhagen (CPH) → Antalya (AYT)
- **Dates**: October 17-24, 2025 (7-day trip)
- **Filter**: Direct/nonstop flights only
- **Currency**: EUR (forced via URL parameter)

## 🔧 Prerequisites

### Required Software
- **Python 3.8+**
- **Chrome browser**
- **NordVPN subscription and CLI** (mandatory - no fallback option)
- **Git** (for cloning)

### NordVPN Setup
This script **requires** NordVPN to be installed and configured:

1. Install NordVPN CLI
2. Log in to your NordVPN account: `nordvpn login`
3. Verify connection: `nordvpn countries`

**⚠️ Important**: The script will exit with an error if NordVPN is not available.

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd flights

# Make setup script executable and run it
chmod +x setup_venv.sh
./setup_venv.sh

# Activate virtual environment
source flights_venv/bin/activate
```

### 2. Run the Scraper
```bash
python copenhagen_antalya_scraper.py
```

## 📊 Output Files

The script generates organized output files:

### Screenshots
```
screenshots/
├── Copenhagen_to_Antalya_from_20251017_to_20251024_Afghanistan.png
├── Copenhagen_to_Antalya_from_20251017_to_20251024_Germany.png
└── Copenhagen_to_Antalya_from_20251017_to_20251024_Australia.png
```

### Price Data
```
prices/
├── Copenhagen_to_Antalya_direct_Afghanistan.csv
├── Copenhagen_to_Antalya_direct_Germany.csv
├── Copenhagen_to_Antalya_direct_Australia.csv
└── Copenhagen_to_Antalya_consolidated_prices.csv  # Combined results
```

### CSV Structure
Each CSV contains:
- **Country**: VPN location used
- **Airline**: Flight carrier
- **Price**: Flight price (preferably in EUR)
- **Departure/Arrival**: Times (see screenshot for details)
- **Duration**: Flight duration (see screenshot)
- **Stops**: Always "Nonstop" (filtered)

## 🌍 How VPN Integration Works

1. **Country Discovery**: Script queries `nordvpn countries` to get available locations
2. **Sequential Connection**: Connects to each country one by one
3. **Clean Browser Sessions**: Creates fresh Chrome instance for each country
4. **Price Extraction**: Scrapes flight data with location-specific pricing
5. **Automatic Cleanup**: Disconnects VPN and cleans temporary files

## 💰 Price Extraction Logic

### Primary: EUR Currency
- Forces EUR via URL parameter: `&curr=EUR`
- Looks for prices in format: `€1,234`, `EUR 1234`, `1234 €`
- Price range validation: €100 - €10,000

### Fallback Currencies
If EUR not found, tries:
- **USD**: $50 - $5,000
- **GBP**: £50 - £4,000  
- **DKK**: 400 - 35,000 DKK
- **AFN**: 5,000 - 500,000 AFN (Afghanistan)
- **kr**: 500 - 50,000 kr (Nordic countries)

## 🛠️ Technical Features

### Browser Automation
- **Headless Chrome** with stealth options
- **Consent page handling** for GDPR compliance
- **Nonstop filter application** via DOM manipulation
- **Currency selection** with confirmation button clicking

### Session Management
- **Unique temp directories** for each country session
- **Complete session isolation** to prevent cross-contamination
- **Automatic cleanup** of temporary Chrome data

### Error Handling
- **Robust VPN connection** with retry logic
- **Screenshot capture** on errors for debugging
- **Graceful failure** - continues with next country if one fails
- **Comprehensive logging** of all operations

## 📋 Dependencies

```
selenium>=4.0.0
webdriver-manager>=3.8.0
pandas>=1.5.0
```

Install via: `pip install -r requirements.txt`

## 🔍 Troubleshooting

### Common Issues

**NordVPN Not Available**
```
ERROR: No NordVPN countries available. NordVPN is required for this script.
Please ensure NordVPN is installed and you are logged in.
```
**Solution**: Install NordVPN CLI and login with `nordvpn login`

**Chrome Driver Issues**
- Script auto-downloads ChromeDriver via webdriver-manager
- Ensure Chrome browser is installed and up-to-date

**No Prices Found**
- Check screenshots in `screenshots/` folder for visual debugging
- Verify Google Flights is accessible from your location
- Some countries may have different Google Flights interfaces

### Debug Files
- **Screenshots**: Visual confirmation of what the script sees
- **Temp directories**: Cleaned automatically but preserved on errors
- **Console output**: Detailed logging of each step

## 🎛️ Customization

### Modify Countries
Edit the `get_nordvpn_countries()` function to filter specific countries:
```python
return unique_countries[:5]  # Test only first 5 countries
```

### Change Route/Dates
Update the `main()` function:
```python
origin = "Copenhagen"        # Change departure city
destination = "Antalya"      # Change destination
depart_date = "2025-10-17"   # Change departure date
return_date = "2025-10-24"   # Change return date
```

### Adjust Price Ranges
Modify validation ranges in `extract_flight_prices()` function.

## 📈 Use Cases

- **Price comparison** across different geographic markets
- **Travel deal hunting** by leveraging regional pricing differences  
- **Market research** for flight pricing strategies
- **Automated monitoring** of specific route pricing trends

## ⚖️ Legal & Ethical Considerations

- **Respect robots.txt** and website terms of service
- **Rate limiting** built-in with delays between requests
- **Personal use** - not for commercial scraping at scale
- **VPN usage** complies with NordVPN terms of service

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with multiple VPN locations
5. Submit a pull request

---

**Note**: This script is designed for personal travel research and price comparison. Always verify prices on official airline websites before booking.
