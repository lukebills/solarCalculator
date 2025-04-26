"""
Initialization script for Solar Calculator

This script sets up the required directory structure and provides instructions
for downloading Synergy data.
"""

import os
import sys

def create_directories():
    """Create required directories for the solar calculator."""
    directories = [
        "solar_results",
        "Synergy Data",
        "reports"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def print_instructions():
    """Print instructions for downloading Synergy data."""
    print("\n=== Synergy Data Download Instructions ===")
    print("1. Log in to your Synergy account")
    print("2. Navigate to 'My Usage' or 'Energy Usage'")
    print("3. Select the date range for your analysis (recommended: 12 months)")
    print("4. Download the data in CSV format")
    print("5. Save the file as 'HourlyMeterData.csv' in the 'Synergy Data' folder")
    print("\nNote: Make sure the data includes:")
    print("  - Date and time")
    print("  - Energy consumption in kWh")
    print("  - Any other relevant meter readings")

def main():
    """Main initialization function."""
    print("=== Solar Calculator Initialization ===")
    print("\nSetting up directory structure...")
    create_directories()
    print_instructions()
    
    print("\nInitialization complete!")
    print("\nNext steps:")
    print("1. Download your Synergy data as instructed above")
    print("2. Run the solar calculator:")
    print("   python solar_calculator.py")
    print("\nFor more information, see the README.md file.")

if __name__ == "__main__":
    main() 