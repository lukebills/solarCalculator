"""
Solar Data Module - Handles solar data retrieval and processing from NREL's PVWatts API

This module provides functionality to:
- Retrieve solar production data from PVWatts API
- Validate system parameters
- Process and save solar data
- Generate CSV files for analysis

Program Flow:
1. Load environment variables and API configuration
2. Get and validate user input for system parameters
3. Fetch solar data from PVWatts API
4. Process and save the API response
5. Generate and save CSV data for analysis
"""

import os
import requests
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import json
from datetime import datetime
import sys

# --- Step 1: Environment Setup ---
# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get API key from environment variables
API_KEY = os.getenv('PVWATTS_API_KEY')

# Verify API key is set
if not API_KEY:
    raise RuntimeError(f"PVWATTS_API_KEY not set (checked {env_path})")

# API Configuration
BASE_URL = 'https://developer.nrel.gov/api/pvwatts/v8.json'

# Location data for Perth, Australia
PERTH_LATITUDE = -32.03  # negative for southern hemisphere
PERTH_LONGITUDE = 115.98

def validate_parameters(params):
    """
    Validate the input parameters against PVWatts API requirements
    
    Args:
        params (dict): Dictionary containing system parameters
        
    Raises:
        ValueError: If any parameter is outside acceptable ranges
        
    Validation Rules:
    - System capacity: 0.05 to 500000 kW
    - Module type: 0 (Standard), 1 (Premium), or 2 (Thin film)
    - Losses: -5 to 99 percent
    - Array type: 0-4 (see documentation for options)
    - Tilt: 0 to 90 degrees
    - Azimuth: 0 to <360 degrees
    - DC to AC ratio: 0.5 to 2.0
    - Ground coverage ratio: 0.1 to 1.0
    - DC capacity factor: 0 to 100 percent
    """
    # System capacity validation (0.05 to 500000 kW)
    if not 0.05 <= params['system_capacity'] <= 500000:
        raise ValueError("System capacity must be between 0.05 and 500000 kW")
    
    # Module type validation (0, 1, or 2)
    if params['module_type'] not in [0, 1, 2]:
        raise ValueError("Module type must be 0 (Standard), 1 (Premium), or 2 (Thin film)")
    
    # Losses validation (-5 to 99 percent)
    if not -5 <= params['losses'] <= 99:
        raise ValueError("System losses must be between -5 and 99 percent")
    
    # Array type validation (0, 1, 2, 3, or 4)
    if params['array_type'] not in [0, 1, 2, 3, 4]:
        raise ValueError("Array type must be 0-4 (see documentation for options)")
    
    # Tilt validation (0 to 90 degrees)
    if not 0 <= params['tilt'] <= 90:
        raise ValueError("Tilt angle must be between 0 and 90 degrees")
    
    # Azimuth validation (0 to <360 degrees)
    if not 0 <= params['azimuth'] < 360:
        raise ValueError("Azimuth angle must be between 0 and 360 degrees")
    
    # DC to AC ratio validation (0.5 to 2.0)
    if not 0.5 <= params['dc_ac_ratio'] <= 2.0:
        raise ValueError("DC to AC ratio must be between 0.5 and 2.0")
    
    # Ground coverage ratio validation (0.1 to 1.0)
    if not 0.1 <= params['ground_coverage_ratio'] <= 1.0:
        raise ValueError("Ground coverage ratio must be between 0.1 and 1.0")
    
    # DC capacity factor validation (0 to 100 percent)
    if not 0 <= params['dc_capacity_factor'] <= 100:
        raise ValueError("DC capacity factor must be between 0 and 100 percent")

def get_user_input():
    """
    Get and validate solar system parameters from user input
    
    Returns:
        dict: Dictionary containing validated system parameters
        
    Process:
    1. Get system capacity with validation
    2. Set default module type to Standard (0)
    3. Get system losses with default breakdown
    4. Get array type with options
    5. Get tilt and azimuth angles
    6. Get DC to AC ratio with default
    7. Get ground coverage ratio with default
    8. Get DC capacity factor with default
    9. Compile and validate all parameters
    """
    print("\n=== Solar Panel System Parameters ===")
    
    # Get system capacity with validation
    while True:
        try:
            system_capacity = float(input("System size (kW): "))
            if not 0.05 <= system_capacity <= 500000:
                raise ValueError
            break
        except ValueError:
            print("Error: System size must be between 0.05 and 500000 kW.")
    
    # Hardcode module_type to 0 (Standard)
    module_type = 0
    
    # Default system losses (sum of all categories)
    default_losses = 15.0
    print("\nSystem Losses (default breakdown, total 15%):")
    print("  Soiling: 2%\n  Shading: 3%\n  Snow: 0%\n  Mismatch: 2%\n  Wiring: 2%\n  Connections: 0.5%\n  Light-Induced Degradation: 1.5%\n  Nameplate Rating: 1%\n  Age: 0%\n  Availability: 3%")
    losses_input = input(f"System losses (%, between -5 and 99) [default {default_losses}%]: ")
    losses = float(losses_input) if losses_input.strip() else default_losses
    
    # Get array type with options
    print("\nArray Type Options:")
    print("0: Fixed - Open Rack")
    print("1: Fixed - Roof Mounted")
    print("2: 1-Axis")
    print("3: 1-Axis Backtracking")
    print("4: 2-Axis")
    array_type = int(input("Select array type (0-4): "))
    
    # Get tilt and azimuth angles
    tilt = float(input("Panel tilt angle (degrees, 0 to 90): "))
    azimuth = float(input("Panel azimuth angle (degrees, 0 to 360): "))
    
    # Get DC to AC ratio with default
    dc_ac_ratio = float(input("DC to AC ratio (default 1.2): ") or "1.2")
    
    # Get ground coverage ratio with default
    ground_coverage_ratio = float(input("Ground coverage ratio (default 0.4): ") or "0.4")
    
    # Get DC capacity factor with default
    dc_capacity_factor = float(input("DC capacity factor (%, default 19.3): ") or "19.3")
    
    # Compile parameters
    params = {
        'system_capacity': system_capacity,
        'module_type': module_type,
        'losses': losses,
        'array_type': array_type,
        'tilt': tilt,
        'azimuth': azimuth,
        'dc_ac_ratio': dc_ac_ratio,
        'ground_coverage_ratio': ground_coverage_ratio,
        'dc_capacity_factor': dc_capacity_factor
    }
    
    # Validate all parameters
    validate_parameters(params)
    
    return params

def save_api_response(data, params):
    """
    Save the API response and parameters to a text file for debugging and review
    
    Args:
        data (dict): API response data
        params (dict): Parameters used in the request
        
    Process:
    1. Create output directory if it doesn't exist
    2. Generate filename with timestamp
    3. Prepare content with formatted sections
    4. Write to file
    """
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).resolve().parent / "api_responses"
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pvwatts_response_{timestamp}.txt"
    output_path = output_dir / filename
    
    # Prepare the content with formatted sections
    content = [
        "=== PVWatts API Response ===",
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n=== Request Parameters ===",
        json.dumps(params, indent=2),
        "\n=== API Response ===",
        json.dumps(data, indent=2)
    ]
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(content))
    
    print(f"\n✔ API response saved to: {output_path}")

def fetch_solar_data(params):
    """
    Fetch solar data from PVWatts v8 API
    
    Args:
        params (dict): Dictionary of system parameters
        
    Returns:
        dict: Dictionary containing the API response
        
    Raises:
        RuntimeError: If there are API errors or invalid response structure
        
    Process:
    1. Build request parameters
    2. Make API request
    3. Parse and validate response
    4. Save response for debugging
    """
    # Required parameters for PVWatts v8
    request_params = {
        'api_key': API_KEY,
        'format': 'json',
        'system_capacity': params['system_capacity'],
        'module_type': 0,  # Standard module type
        'losses': 14,      # Default system losses
        'array_type': 0,   # Fixed open rack
        'tilt': params['tilt'],
        'azimuth': params['azimuth'],
        'lat': PERTH_LATITUDE,
        'lon': PERTH_LONGITUDE,
        'timeframe': 'hourly'
    }
    
    # Build URL with parameters
    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"

    try:
        # Make API request
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        
        # Parse JSON response
        data = resp.json()
        
        # Save the API response for debugging
        save_api_response(data, request_params)
        
        return data
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")

def save_to_csv(data, output_path):
    """
    Save hourly solar data to CSV file with datetime and additional columns
    
    Args:
        data (dict): PVWatts API response data
        output_path (Path): Path to save the CSV file
        
    Raises:
        RuntimeError: If required data is missing or invalid
        
    Process:
    1. Extract outputs from API response
    2. Create datetime index for the year
    3. Define fields to extract
    4. Build data dictionary
    5. Create and save DataFrame
    """
    try:
        # Extract outputs from API response
        outputs = data.get("outputs", {})
        if not outputs or "ac" not in outputs:
            raise RuntimeError("No hourly 'ac' data found in PVWatts response outputs")
        
        # Create datetime index for the year
        n_hours = len(outputs["ac"])
        dt_index = pd.date_range(start="2024-01-01 00:00:00", periods=n_hours, freq="H")
        
        # Define fields to extract from API response
        hourly_fields = [
            "ac", "dc", "poa", "dn", "df", "tamb", "tcell", "wspd", "alb"
        ]
        
        # Build data dictionary for DataFrame
        data_dict = {
            "datetime": dt_index,
            "month": dt_index.month,
            "day": dt_index.day,
            "hour": dt_index.hour
        }
        
        # Add hourly data fields
        for field in hourly_fields:
            data_dict[field] = outputs.get(field, [None]*n_hours)
        
        # Create and save DataFrame
        df = pd.DataFrame(data_dict)
        df.to_csv(output_path, index=False)
        
    except Exception as e:
        raise RuntimeError(f"Error saving data to CSV: {str(e)}")

def main():
    """
    Main function to run the solar data retrieval process
    
    Process:
    1. Get system parameters from user
    2. Fetch data from PVWatts API
    3. Save the data
    4. Print summary statistics
    5. Handle any errors
    """
    try:
        # Get system parameters from user
        params = get_user_input()
        
        # Fetch data from PVWatts API
        data = fetch_solar_data(params)
        
        # Save the data
        results_dir = Path(__file__).resolve().parent / "solar_results"
        results_dir.mkdir(exist_ok=True)
        output_path = results_dir / "solar_pvwatts_data.csv"
        save_to_csv(data, output_path)
        
        # Print summary statistics
        print("\nSummary Statistics:")
        print(f"System Size: {params['system_capacity']} kW")
        print(f"Tilt Angle: {params['tilt']}°")
        print(f"Azimuth Angle: {params['azimuth']}°")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
