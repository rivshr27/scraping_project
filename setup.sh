#!/bin/bash

# Product Review Scraper Setup Script
# This script sets up the Python virtual environment and installs dependencies

echo "🚀 Setting up Product Review Scraper..."
echo "======================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🧪 Running basic functionality tests..."
python test_basic_functionality.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "To use the scraper:"
    echo "1. Activate the virtual environment: source venv/bin/activate"
    echo "2. Run the scraper: python review_scraper.py --help"
    echo ""
    echo "Example usage:"
    echo 'python review_scraper.py --company "Slack" --start-date "2023-01-01" --end-date "2023-12-31" --source "g2"'
else
    echo "❌ Setup tests failed. Please check the error messages above."
    exit 1
fi
