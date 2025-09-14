# Copenhagen to Antalya Flight Scraper - Setup Instructions

This document provides detailed instructions on how to set up and run the Copenhagen to Antalya flight scraper on your machine.

## Prerequisites

- Python 3.8 or higher
- Chrome web browser installed
- Git (to clone the repository)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd flights
```

### 2. Set Up a Virtual Environment

#### Using the provided setup script:

The repository includes a setup script that automates the virtual environment creation process:

```bash
# Make the script executable
chmod +x setup_venv.sh

# Run the setup script
./setup_venv.sh
```

The script will:
- Create a new virtual environment called `flights_venv`
- Install all required dependencies from `requirements.txt`
- Provide further instructions

#### Manual setup (alternative):

If you prefer to set up the environment manually:

```bash
# Create a virtual environment
python3 -m venv flights_venv

# Activate the virtual environment
# On macOS/Linux:
source flights_venv/bin/activate
# On Windows:
# flights_venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Run the Flight Scraper

With the virtual environment activated:

```bash
python copenhagen_antalya_scraper.py
```

## Output Files

The script will generate the following files:
- A PNG screenshot of flight results
- A CSV file containing direct flight prices
- Debug files (if any issues occur)

## Troubleshooting

- **ChromeDriver Issues**: If you encounter errors related to ChromeDriver, the script will attempt to download the appropriate version automatically. If this fails, download ChromeDriver manually from https://chromedriver.chromium.org/downloads and ensure it's in your PATH.

- **Permission Issues**: Make sure the setup script has execute permissions (`chmod +x setup_venv.sh`).

- **Consent Page Handling**: The script includes robust methods to handle Google's consent pages. If issues persist, check the generated debug files for more information.