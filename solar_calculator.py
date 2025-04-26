"""
Solar Calculator - A tool for analyzing solar panel and battery system economics

This script calculates the financial viability of installing solar panels and optionally a battery system.
It uses real electricity usage data and solar production estimates to determine:
- Energy self-consumption
- Grid exports and imports
- Financial savings
- Payback period

Program Flow:
1. Generate solar production data using PVWatts API
2. Load and process electricity usage data
3. Calculate solar-only scenario (without battery)
4. Calculate battery scenario (if requested)
5. Perform financial analysis
6. Generate reports and visualizations
"""

import pandas as pd
import numpy as np
import subprocess
import os
from dotenv import load_dotenv
from pathlib import Path
import json

# --- Step 1: Initial Setup ---
# Load environment variables for API keys and configuration
load_dotenv()

# --- Step 2: Generate Solar Data ---
# Run Solar_data.py to get solar production estimates from PVWatts API
print("\nRunning Solar_data.py to generate solar PV data...")
subprocess.run(["python3", "Solar_data.py"])

# --- Step 3: Load and Prepare Data ---
# Set up directories and file paths
results_dir = Path("solar_results")
results_dir.mkdir(exist_ok=True)
solar_file = results_dir / "solar_pvwatts_data.csv"
meter_file = "Synergy Data/HourlyMeterData.csv"

# Verify required files exist
if not os.path.exists(solar_file):
    raise FileNotFoundError(f"{solar_file} not found. Please ensure Solar_data.py ran successfully.")
if not os.path.exists(meter_file):
    raise FileNotFoundError(f"{meter_file} not found. Please provide your hourly meter data CSV.")

# Load data files
solar_data = pd.read_csv(solar_file, parse_dates=["datetime"])
meter_data = pd.read_csv(meter_file)

# --- Step 4: Data Processing ---
# Convert meter data datetime and standardize column names
meter_data["datetime"] = pd.to_datetime(meter_data["Date"] + " " + meter_data["Time"], format="%Y-%m-%d %H:%M")
meter_data = meter_data.rename(columns={"Usage already billed": "usage_kwh"})

# Merge solar and meter data on datetime
combined = pd.merge(solar_data, meter_data, on="datetime", how="inner")

# --- Step 5: Solar-Only Scenario Calculations ---
# Convert AC power to kWh and extract hour for time-based calculations
combined["solar_kwh"] = combined["ac"] / 1000
combined["hour"] = combined["datetime"].dt.hour

# Calculate basic solar-only metrics:
# - Self-consumed: Minimum of solar production and usage
# - Exported: Excess solar after self-consumption
# - Imported: Grid power needed when solar is insufficient
combined["self_consumed_solar_only"] = np.minimum(combined["solar_kwh"], combined["usage_kwh"])
combined["exported_solar_only"] = np.maximum(combined["solar_kwh"] - combined["usage_kwh"], 0)
combined["imported_solar_only"] = np.maximum(combined["usage_kwh"] - combined["solar_kwh"], 0)

# --- Step 6: Battery Configuration ---
# Get battery configuration from user if desired
use_battery = input("\nWould you like to include a battery? (y/n): ").strip().lower() == 'y'
if use_battery:
    # Get battery specifications
    battery_capacity = float(input("Battery capacity (kWh): "))
    max_charge_rate = float(input("Max charge rate (kW): "))
    max_discharge_rate = float(input("Max discharge rate (kW): "))
    round_trip_eff = float(input("Round-trip efficiency (%, e.g. 90): ")) / 100.0
else:
    # Set battery parameters to zero if not used
    battery_capacity = 0
    max_charge_rate = 0
    max_discharge_rate = 0
    round_trip_eff = 1.0

# --- Step 7: Battery Scenario Calculations ---
# Initialize columns for battery tracking
n = len(combined)
combined["battery_soc"] = 0.0  # State of charge
combined["battery_charge"] = 0.0
combined["battery_discharge"] = 0.0
combined["self_consumed"] = 0.0
combined["exported"] = 0.0
combined["imported"] = 0.0

# Simulate battery operation hour by hour
soc = 0.0  # State of charge (kWh)
for i in range(n):
    # Get current hour's data
    usage = combined.at[i, "usage_kwh"]
    solar = combined.at[i, "solar_kwh"]
    hour = combined.at[i, "hour"]
    
    # Step 1: Use solar for immediate consumption
    self_consumed = min(solar, usage)
    remaining_solar = solar - self_consumed
    remaining_usage = usage - self_consumed
    battery_charge = 0.0
    battery_discharge = 0.0
    imported = 0.0
    exported = 0.0
    
    # Step 2: Charge battery with excess solar
    if use_battery and remaining_solar > 0:
        # Calculate possible charge based on battery capacity and charge rate
        charge_possible = min(max_charge_rate, battery_capacity - soc)
        charge_energy = min(remaining_solar, charge_possible)
        soc += charge_energy * round_trip_eff
        battery_charge = charge_energy
        remaining_solar -= charge_energy
    
    # Step 3: Export any remaining solar to grid
    if remaining_solar > 0:
        exported = remaining_solar
    
    # Step 4: Discharge battery if usage not met
    if use_battery and remaining_usage > 0:
        # Calculate possible discharge based on battery state and discharge rate
        discharge_possible = min(max_discharge_rate, soc)
        discharge_energy = min(remaining_usage, discharge_possible)
        soc -= discharge_energy
        battery_discharge = discharge_energy
        remaining_usage -= discharge_energy
    
    # Step 5: Import from grid if still needed
    if remaining_usage > 0:
        imported = remaining_usage
    
    # Step 6: Record all values
    combined.at[i, "battery_soc"] = soc
    combined.at[i, "battery_charge"] = battery_charge
    combined.at[i, "battery_discharge"] = battery_discharge
    combined.at[i, "self_consumed"] = self_consumed + battery_discharge
    combined.at[i, "exported"] = exported
    combined.at[i, "imported"] = imported

# --- Step 8: Financial Analysis ---
# Define electricity rates and peak hours
supply_charge_per_day = 1.1322  # $/day
energy_rate = 0.315823  # $/kWh
peak_start = 15  # 3pm
peak_end = 20    # 9pm

# Calculate peak/off-peak rates
combined["is_peak"] = combined["hour"].between(peak_start, peak_end, inclusive="both")
combined["feedin_rate"] = np.where(combined["is_peak"], 0.10, 0.02)

# Calculate total days and supply charge
total_days = combined["datetime"].dt.date.nunique()
supply_charge_total = supply_charge_per_day * total_days

# --- Step 9: Solar-Only Scenario Results ---
solar_only = {}
solar_only["total_self_consumed"] = combined["self_consumed_solar_only"].sum()
solar_only["total_exported"] = combined["exported_solar_only"].sum()
solar_only["total_imported"] = combined["imported_solar_only"].sum()
solar_only["total_usage"] = combined["usage_kwh"].sum()
solar_only["total_solar"] = combined["solar_kwh"].sum()
solar_only["export_earnings"] = (combined["exported_solar_only"] * combined["feedin_rate"]).sum()
solar_only["cost_without_solar"] = solar_only["total_usage"] * energy_rate + supply_charge_total
solar_only["cost_with_solar"] = solar_only["total_imported"] * energy_rate - solar_only["export_earnings"] + supply_charge_total
solar_only["total_savings"] = solar_only["cost_without_solar"] - solar_only["cost_with_solar"]

# --- Step 10: Battery Scenario Results ---
total_self_consumed = combined["self_consumed"].sum()
total_exported = combined["exported"].sum()
total_imported = combined["imported"].sum()
total_usage = combined["usage_kwh"].sum()
total_solar = combined["solar_kwh"].sum()
total_battery_charge = combined["battery_charge"].sum()
total_battery_discharge = combined["battery_discharge"].sum()
export_earnings = (combined["exported"] * combined["feedin_rate"]).sum()
cost_without_solar = total_usage * energy_rate + supply_charge_total
cost_with_solar = total_imported * energy_rate - export_earnings + supply_charge_total
total_savings = cost_without_solar - cost_with_solar

# Calculate payback period
system_cost = float(input("Total system cost ($, e.g. 8000): "))
payback_years = system_cost / total_savings if total_savings > 0 else float('inf')

# --- Step 11: Display Results ---
print("\n--- Solar Financial Analysis ---")
print(f"Total energy used: {total_usage:.2f} kWh")
print(f"Total solar produced: {total_solar:.2f} kWh")
print(f"Self-consumed solar (solar only): {solar_only['total_self_consumed']:.2f} kWh")
print(f"Self-consumed solar (including battery): {total_self_consumed:.2f} kWh")
print(f"Exported to grid: {total_exported:.2f} kWh")
print(f"Imported from grid: {total_imported:.2f} kWh")
if use_battery:
    print(f"Total battery charge: {total_battery_charge:.2f} kWh")
    print(f"Total battery discharge: {total_battery_discharge:.2f} kWh")
print(f"Annual supply charge: ${supply_charge_total:,.2f}")
print(f"Total earned from exported electricity: ${export_earnings:,.2f}")
print(f"Cost without solar: ${cost_without_solar:,.2f}")
print(f"Cost with solar: ${cost_with_solar:,.2f}")
print(f"Total savings per year: ${total_savings:,.2f}")
print(f"Estimated payback period: {payback_years:.1f} years")

# --- Step 12: Save Results ---
# Save detailed hourly data
output_file = results_dir / 'solar_analysis_results.csv'
combined.to_csv(output_file, index=False)

# Save summary data for report generation
summary_data = {
    "solar_only": solar_only,
    "battery": {
        "total_self_consumed": total_self_consumed,
        "total_exported": total_exported,
        "total_imported": total_imported,
        "total_usage": total_usage,
        "total_solar": total_solar,
        "total_battery_charge": total_battery_charge,
        "total_battery_discharge": total_battery_discharge,
        "export_earnings": export_earnings,
        "cost_without_solar": cost_without_solar,
        "cost_with_solar": cost_with_solar,
        "total_savings": total_savings,
        "payback_years": payback_years,
        "use_battery": use_battery
    },
    "supply_charge_total": supply_charge_total,
    "system_cost": system_cost
}
with open(results_dir / 'solar_summary.json', 'w') as f:
    json.dump(summary_data, f, indent=2)

print(f"\nAnalysis complete! Results saved to {output_file}")

# --- Step 13: Generate Report ---
generate_report = input("\nWould you like to generate a Word report? (y/n): ").strip().lower() == 'y'
if generate_report:
    print("Generating Word report...")
    subprocess.run(["python3", "generate_solar_report.py"])

def calculate_solar_production(solar_data, params):
    """
    Calculate solar production with the new factors
    
    Args:
        solar_data (dict): Dictionary containing solar radiation data by month
        params (dict): Dictionary containing system parameters
        
    Returns:
        dict: Monthly solar production in kWh
    """
    # Apply DC to AC ratio to adjust system capacity
    adjusted_capacity = params['system_capacity'] * params['dc_ac_ratio']
    
    # Apply ground coverage ratio to adjust effective capacity
    effective_capacity = adjusted_capacity * params['ground_coverage_ratio']
    
    # Apply DC capacity factor to adjust production
    capacity_factor = params['dc_capacity_factor'] / 100.0
    
    # Calculate monthly production
    monthly_production = {}
    for month, data in solar_data.items():
        # Get solar radiation (kWh/m²/day)
        solar_radiation = data['solar_radiation']
        
        # Calculate daily production (kWh)
        daily_production = effective_capacity * solar_radiation * capacity_factor
        
        # Calculate monthly production (kWh)
        days_in_month = data['days_in_month']
        monthly_production[month] = daily_production * days_in_month
    
    return monthly_production

def display_system_summary(params):
    """
    Display a summary table of the solar system configuration
    
    Args:
        params (dict): Dictionary containing system parameters
    """
    print("\n=== System Configuration Summary ===")
    print("┌───────────────────────────────┬──────────────┐")
    print("│ Parameter                     │ Value        │")
    print("├───────────────────────────────┼──────────────┤")
    print(f"│ System Size                  │ {params['system_capacity']:6.1f} kW    │")
    print(f"│ System Cost                  │ ${params['system_cost']:8,.2f}  │")
    print(f"│ Location                     │ {params['location']:14} │")
    
    if params['include_battery']:
        print("├───────────────────────────────┼──────────────┤")
        print(f"│ Battery Capacity             │ {params['battery_capacity']:6.1f} kWh  │")
        print("└───────────────────────────────┴──────────────┘")
        print(f"\nTotal System Cost (Solar + Battery): ${params['system_cost']:,.2f}")
    else:
        print("└───────────────────────────────┴──────────────┘")
        print(f"\nTotal System Cost: ${params['system_cost']:,.2f}")

def check_existing_files():
    """
    Check for existing output files and ask for confirmation before proceeding
    
    Returns:
        bool: True if user confirms to proceed, False otherwise
    """
    # List of files that will be overwritten
    files_to_check = [
        "solar_results/solar_analysis_results.csv",
        "solar_results/solar_summary.json",
        "solar_results/solar_pvwatts_data.csv",
        "reports/solar_analysis_report.docx",
        "reports/plot1.png",
        "reports/plot2.png",
        "reports/plot3.png"
    ]
    
    # Check which files exist
    existing_files = [f for f in files_to_check if os.path.exists(f)]
    
    if existing_files:
        print("\n⚠️ Warning: The following files will be overwritten:")
        for file in existing_files:
            print(f"  - {file}")
        
        response = input("\nDo you want to proceed? (y/n): ").lower()
        return response == 'y'
    
    return True

def main():
    """
    Main function to run the solar calculator
    """
    # Check for existing files and get confirmation
    if not check_existing_files():
        print("Operation cancelled by user.")
        return
    
    # Get user input for system configuration
    params = {
        'system_capacity': float(input("Enter system size (kW): ")),
        'system_cost': float(input("Enter system cost ($): ")),
        'location': input("Enter suburb: "),
        'tilt': float(input("Enter tilt angle (degrees): ")),
        'azimuth': float(input("Enter azimuth angle (degrees): ")),
        'dc_ac_ratio': float(input("Enter DC to AC ratio: ")),
        'ground_coverage_ratio': float(input("Enter ground coverage ratio: ")),
        'dc_capacity_factor': float(input("Enter DC capacity factor (%): ")),
        'include_battery': input("Include battery? (y/n): ").lower() == 'y'
    }
    
    if params['include_battery']:
        params.update({
            'battery_capacity': float(input("Enter battery capacity (kWh): ")),
            'max_charge_rate': float(input("Enter max charge rate (kW): ")),
            'max_discharge_rate': float(input("Enter max discharge rate (kW): ")),
            'round_trip_eff': float(input("Enter round trip efficiency (%): ")) / 100.0
        })
    
    # Display system configuration summary
    display_system_summary(params)
    
    # Get solar data using the same parameters
    solar_data = get_solar_data(params)
    
    # Calculate production with new factors
    monthly_production = calculate_solar_production(solar_data, params)
    
    # Print results
    print("\nMonthly Solar Production (kWh):")
    for month, production in monthly_production.items():
        print(f"{month}: {production:.2f}")

if __name__ == "__main__":
    main() 