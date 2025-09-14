# Copenhagen to Antalya Flight Scraper

This script scrapes flight information from Google Flights for a specific route and dates:
- Origin: Copenhagen
- Destination: Antalya
- Departure Date: October 17, 2025
- Return Date: October 24, 2025

## Setup Instructions

### 1. Initialize the Virtual Environment

Run the provided setup script to create a virtual environment and install required packages:

```bash
# Make script executable if not already
chmod +x setup_venv.sh

# Run setup script
./setup_venv.sh
```

This script will:
- Create a new virtual environment named `flights_venv`
- Install all required packages from `requirements.txt`

### 2. Activate the Virtual Environment

```bash
# On macOS/Linux:
source flights_venv/bin/activate

# On Windows:
source flights_venv/Scripts/activate
```

## Running the Scraper

Once your environment is set up and activated, run the scraper:

```bash
python copenhagen_antalya_scraper.py
```

## Output Files

The script generates the following output files:

1. **Screenshot of flight results**:
   - `Copenhagen_Antalya_2025-10-17_2025-10-24.png`

2. **CSV file with flight details**:
   - `Copenhagen_Antalya_2025-10-17_2025-10-24.csv`
   - Contains airline, price, departure/arrival times, duration, and stop information

3. **Price visualization chart**:
   - `Copenhagen_Antalya_2025-10-17_2025-10-24_prices.png`
   - Bar chart showing prices of different flight options

## Troubleshooting

If you encounter any issues:

1. **Consent Page Handling**: The script attempts to handle Google's consent page automatically. If it fails, it will save the HTML to `debug_consent_page.html` for debugging.

2. **Page Loading Errors**: If the flight results don't load properly, the script will save the page source to `debug_google_flights_after_wait.html` for debugging.

3. **General Errors**: For any other errors, a screenshot will be saved with the format `error_YYYYMMDD_HHMMSS.png`.

## Requirements

The script uses the following packages:
- selenium
- webdriver-manager
- pandas
- matplotlib
- pillow