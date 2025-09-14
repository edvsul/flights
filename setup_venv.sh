#!/bin/bash

# Setup script for the flight scraper virtual environment

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Echo with color function
echo_color() {
    echo -e "${1}${2}${NC}"
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo_color $RED "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Print welcome message
echo_color $GREEN "=== Setting up virtual environment for Flight Scraper ==="

# Create virtual environment if it doesn't exist
VENV_NAME="flights_venv"
if [ ! -d "$VENV_NAME" ]; then
    echo_color $YELLOW "Creating new virtual environment: $VENV_NAME"
    python3 -m venv $VENV_NAME
    if [ $? -ne 0 ]; then
        echo_color $RED "Failed to create virtual environment. Please check your Python installation."
        exit 1
    fi
else
    echo_color $YELLOW "Virtual environment already exists: $VENV_NAME"
fi

# Activate virtual environment and install packages
echo_color $YELLOW "Installing required packages..."

# Different activation paths for different OS
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # macOS or Linux
    source "$VENV_NAME/bin/activate"
    if [ $? -ne 0 ]; then
        echo_color $RED "Failed to activate virtual environment."
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    source "$VENV_NAME/Scripts/activate"
    if [ $? -ne 0 ]; then
        echo_color $RED "Failed to activate virtual environment."
        exit 1
    fi
else
    echo_color $RED "Unknown operating system. Please activate the virtual environment manually."
    exit 1
fi

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo_color $RED "Failed to install required packages."
    exit 1
fi

# Print success message
echo_color $GREEN "=== Setup completed successfully! ==="
echo_color $GREEN "To activate the virtual environment, run:"
echo_color $YELLOW "source $VENV_NAME/bin/activate  # On macOS/Linux"
echo_color $YELLOW "source $VENV_NAME/Scripts/activate  # On Windows"
echo_color $GREEN "To run the scraper:"
echo_color $YELLOW "python copenhagen_antalya_scraper.py"
echo_color $GREEN "=== Happy scraping! ==="