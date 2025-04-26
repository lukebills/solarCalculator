"""
Test Runner for Solar Calculator

This script runs a test case for the solar calculator with predefined inputs.
It simulates user input for a 6.6 kW solar system installation.

Test Case Parameters:
- System size: 6.6 kW
- System cost: [To be provided]
- Tilt angle: [To be provided]
- Azimuth angle: [To be provided]
- Battery configuration: [To be provided]
"""

import sys
from io import StringIO
from solar_calculator import main
import subprocess
import os

def run_test():
    """
    Run the solar calculator test with predefined inputs
    
    Process:
    1. Set up test inputs
    2. Redirect stdin to test inputs
    3. Run solar calculator
    4. Restore original stdin
    """
    # Save the original stdin
    original_stdin = sys.stdin
    
    # Create test inputs for solar calculator
    # Format: system_size, system_cost, tilt, azimuth, battery_choice, battery_capacity, 
    #         max_charge_rate, max_discharge_rate, round_trip_eff
    test_inputs = StringIO(
        "6.6\n" +  # System size (kW)
        "4936\n" +  # System cost ($)
        "31\n" +    # Tilt angle (degrees)
        "6\n" +     # Azimuth angle (degrees)
        "n\n" +     # Include battery? (y/n)
        "1.2\n" +   # DC to AC ratio
        "0.4\n" +   # Ground coverage ratio
        "19.3\n"    # DC capacity factor
    )
    
    # Redirect stdin to our test inputs
    sys.stdin = test_inputs
    
    try:
        # Run the main function with our test inputs
        main()
    finally:
        # Restore the original stdin
        sys.stdin = original_stdin

def setup_test_environment():
    """
    Set up the test environment by:
    1. Creating necessary directories
    2. Ensuring required files exist
    3. Running data conversion if needed
    """
    # Create required directories
    os.makedirs("solar_results", exist_ok=True)
    os.makedirs("Synergy Data", exist_ok=True)
    
    # Check if hourly data exists, if not run conversion
    if not os.path.exists("Synergy Data/HourlyMeterData.csv"):
        print("Converting half-hourly data to hourly format...")
        from convert_to_hourly import convert_to_hourly
        convert_to_hourly()

if __name__ == "__main__":
    print("\n=== Solar Calculator Test Run ===")
    print("System Configuration:")
    print("- System size: 6.6 kW")
    print("- System cost: $4,936")
    print("- Tilt angle: 31°")
    print("- Azimuth angle: 6°")
    print("- DC to AC ratio: 1.2")
    print("- Ground coverage ratio: 0.4")
    print("- DC capacity factor: 19.3%")
    print("- Battery: Not included")
    print("\nSetting up test environment...")
    
    # Set up test environment
    setup_test_environment()
    
    print("\nStarting simulation...\n")
    run_test()
    
    print("\nTest completed. Check solar_results directory for output files.") 