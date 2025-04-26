import os
import requests
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import json
from datetime import datetime

# ─── Load .env from the absolute path ─────────────────────────────────────────────
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('PVWATTS_API_KEY')

if not API_KEY:
    raise RuntimeError(f"PVWATTS_API_KEY not set (checked {env_path})")

# ─── Configuration ───────────────────────────────────────────────────────────────
BASE_URL = 'https://developer.nrel.gov/api/pvwatts/v8.json'

# Location data for Perth, Australia
PERTH_LATITUDE = -32.03  # negative for southern hemisphere
PERTH_LONGITUDE = 115.98

def validate_parameters(params):
    """
    Validate the input parameters against PVWatts requirements
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
    Get system parameters from user input
    """
    print("\n=== Solar Panel System Parameters ===")
    
    # Get system capacity
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
    
    # Get array type
    print("\nArray Type Options:")
    print("0: Fixed - Open Rack")
    print("1: Fixed - Roof Mounted")
    print("2: 1-Axis")
    print("3: 1-Axis Backtracking")
    print("4: 2-Axis")
    array_type = int(input("Select array type (0-4): "))
    
    # Get tilt and azimuth
    tilt = float(input("Panel tilt angle (degrees, 0 to 90): "))
    azimuth = float(input("Panel azimuth angle (degrees, 0 to 360): "))
    
    # Get DC to AC ratio
    dc_ac_ratio = float(input("DC to AC ratio (default 1.2): ") or "1.2")
    
    # Get ground coverage ratio
    ground_coverage_ratio = float(input("Ground coverage ratio (default 0.4): ") or "0.4")
    
    # Get DC capacity factor
    dc_capacity_factor = float(input("DC capacity factor (%, default 19.3): ") or "19.3")
    
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
    
    # Validate parameters
    validate_parameters(params)
    
    return params

def save_api_response(data, params):
    """
    Save the API response and parameters to a text file for review
    
    Parameters:
    - data: API response data
    - params: Parameters used in the request
    """
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).resolve().parent / "api_responses"
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pvwatts_response_{timestamp}.txt"
    output_path = output_dir / filename
    
    # Prepare the content
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
    
    Parameters:
    - params: Dictionary of parameters
    
    Returns:
    - Dictionary containing the API response
    """
    # Required parameters for PVWatts v8
    request_params = {
        'api_key': API_KEY,
        'format': 'json',
        'system_capacity': params['system_capacity'],
        'module_type': params['module_type'],
        'losses': params['losses'],
        'array_type': params['array_type'],
        'tilt': params['tilt'],
        'azimuth': params['azimuth'],
        'lat': PERTH_LATITUDE,
        'lon': PERTH_LONGITUDE,
        'timeframe': 'hourly'
    }
    
    # Build URL with parameters
    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        
        data = resp.json()
        
        # Save the API response to a file
        save_api_response(data, request_params)
        
        # Check for API errors
        if "errors" in data and data["errors"]:
            raise RuntimeError(f"PVWatts API errors: {data['errors']}")
            
        # Check if we have the expected data structure
        if "outputs" not in data:
            raise RuntimeError("No 'outputs' field in API response")
            
        if "ac" not in data["outputs"]:
            raise RuntimeError("No 'ac' data in API response outputs")
            
        return data
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error fetching PVWatts data: {str(e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error parsing API response: {str(e)}")

def save_to_csv(data, output_path):
    """
    Save hourly data to CSV file, generating datetime, month, day, and hour columns.
    
    Parameters:
    - data: PVWatts API response data
    - output_path: Path to save the CSV file
    """
    try:
        # Extract outputs (hourly arrays are directly in outputs)
        outputs = data.get("outputs", {})
        if not outputs or "ac" not in outputs:
            raise RuntimeError("No hourly 'ac' data found in PVWatts response outputs")
        
        n_hours = len(outputs["ac"])
        dt_index = pd.date_range(start="2024-01-01 00:00:00", periods=n_hours, freq="H")
        
        # List of possible hourly fields
        hourly_fields = [
            "ac", "dc", "poa", "dn", "df", "tamb", "tcell", "wspd", "alb"
        ]
        # Build the data dictionary for DataFrame
        data_dict = {
            "datetime": dt_index,
            "month": dt_index.month,
            "day": dt_index.day,
            "hour": dt_index.hour
        }
        for field in hourly_fields:
            data_dict[field] = outputs.get(field, [None]*n_hours)
        
        df = pd.DataFrame(data_dict)
        df.to_csv(output_path, index=False)
    except KeyError as e:
        raise RuntimeError(f"Missing required data field: {str(e)}")

def main():
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
        print(f"Annual AC Energy: {data['outputs']['ac_annual']:.2f} kWh")
        print(f"Annual Solar Radiation: {data['outputs']['solrad_annual']:.2f} kWh/m²/day")
        print(f"Capacity Factor: {data['outputs']['capacity_factor']:.2f}%")
        
        # Print monthly statistics
        print("\nMonthly AC Energy Production (kWh):")
        for i, monthly_ac in enumerate(data['outputs']['ac_monthly'], 1):
            print(f"Month {i}: {monthly_ac:.2f}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nDebug information:")
        print(f"Parameters used: {params}")
        raise

if __name__ == '__main__':
    main()
