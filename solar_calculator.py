import pandas as pd
import numpy as np
import subprocess
import os
from dotenv import load_dotenv
from pathlib import Path
import json

# Load environment variables from .env file
load_dotenv()

# --- Step 1: Run Solar_data.py to generate solar_pvwatts_data.csv ---
print("\nRunning Solar_data.py to generate solar PV data...")
subprocess.run(["python3", "Solar_data.py"])  # Assumes Solar_data.py is in the same directory

# --- Step 2: Read the generated solar_pvwatts_data.csv and HourlyMeterData.csv ---
results_dir = Path("solar_results")
results_dir.mkdir(exist_ok=True)
solar_file = results_dir / "solar_pvwatts_data.csv"
meter_file = "Synergy Data/HourlyMeterData.csv"

if not os.path.exists(solar_file):
    raise FileNotFoundError(f"{solar_file} not found. Please ensure Solar_data.py ran successfully.")
if not os.path.exists(meter_file):
    raise FileNotFoundError(f"{meter_file} not found. Please provide your hourly meter data CSV.")

solar_data = pd.read_csv(solar_file, parse_dates=["datetime"])
meter_data = pd.read_csv(meter_file)

# --- Step 3: Prepare and merge data on datetime ---
meter_data["datetime"] = pd.to_datetime(meter_data["Date"] + " " + meter_data["Time"], format="%Y-%m-%d %H:%M")
meter_data = meter_data.rename(columns={"Usage already billed": "usage_kwh"})
combined = pd.merge(solar_data, meter_data, on="datetime", how="inner")

# --- Step 4: Calculate solar-only scenario (no battery) ---
combined["solar_kwh"] = combined["ac"] / 1000
combined["hour"] = combined["datetime"].dt.hour  # Ensure hour column exists

# Solar-only scenario
combined["self_consumed_solar_only"] = np.minimum(combined["solar_kwh"], combined["usage_kwh"])
combined["exported_solar_only"] = np.maximum(combined["solar_kwh"] - combined["usage_kwh"], 0)
combined["imported_solar_only"] = np.maximum(combined["usage_kwh"] - combined["solar_kwh"], 0)

# --- Step 5: Battery option and full scenario ---
use_battery = input("\nWould you like to include a battery? (y/n): ").strip().lower() == 'y'
if use_battery:
    battery_capacity = float(input("Battery capacity (kWh): "))
    max_charge_rate = float(input("Max charge rate (kW): "))
    max_discharge_rate = float(input("Max discharge rate (kW): "))
    round_trip_eff = float(input("Round-trip efficiency (%, e.g. 90): ")) / 100.0
else:
    battery_capacity = 0
    max_charge_rate = 0
    max_discharge_rate = 0
    round_trip_eff = 1.0

# Initialize battery tracking columns
n = len(combined)
combined["battery_soc"] = 0.0
combined["battery_charge"] = 0.0
combined["battery_discharge"] = 0.0
combined["self_consumed"] = 0.0
combined["exported"] = 0.0
combined["imported"] = 0.0

soc = 0.0  # State of charge (kWh)
for i in range(n):
    usage = combined.at[i, "usage_kwh"]
    solar = combined.at[i, "solar_kwh"]
    hour = combined.at[i, "hour"]
    # 1. Use solar for self-consumption
    self_consumed = min(solar, usage)
    remaining_solar = solar - self_consumed
    remaining_usage = usage - self_consumed
    battery_charge = 0.0
    battery_discharge = 0.0
    imported = 0.0
    exported = 0.0
    # 2. Charge battery with excess solar
    if use_battery and remaining_solar > 0:
        charge_possible = min(max_charge_rate, battery_capacity - soc)
        # Account for charging efficiency (only store what can be used after losses)
        charge_energy = min(remaining_solar, charge_possible)
        soc += charge_energy * round_trip_eff
        battery_charge = charge_energy
        remaining_solar -= charge_energy
    # 3. Export any remaining solar
    if remaining_solar > 0:
        exported = remaining_solar
    # 4. If usage not met, discharge battery
    if use_battery and remaining_usage > 0:
        discharge_possible = min(max_discharge_rate, soc)
        discharge_energy = min(remaining_usage, discharge_possible)
        soc -= discharge_energy
        battery_discharge = discharge_energy
        remaining_usage -= discharge_energy
    # 5. If still not met, import from grid
    if remaining_usage > 0:
        imported = remaining_usage
    # 6. Track values
    combined.at[i, "battery_soc"] = soc
    combined.at[i, "battery_charge"] = battery_charge
    combined.at[i, "battery_discharge"] = battery_discharge
    combined.at[i, "self_consumed"] = self_consumed + battery_discharge
    combined.at[i, "exported"] = exported
    combined.at[i, "imported"] = imported

# --- Step 6: Apply rates and calculate costs for both scenarios ---
supply_charge_per_day = 1.1322  # $/day
energy_rate = 0.315823  # $/kWh
peak_start = 15  # 3pm
peak_end = 20    # 9pm
combined["is_peak"] = combined["hour"].between(peak_start, peak_end, inclusive="both")
combined["feedin_rate"] = np.where(combined["is_peak"], 0.10, 0.02)

total_days = combined["datetime"].dt.date.nunique()
supply_charge_total = supply_charge_per_day * total_days

# Solar-only scenario
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

# Battery scenario
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

system_cost = float(input("Total system cost ($, e.g. 8000): "))
payback_years = system_cost / total_savings if total_savings > 0 else float('inf')

# --- Step 7: Print and save summary ---
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

# Save detailed results
output_file = results_dir / 'solar_analysis_results.csv'
combined.to_csv(output_file, index=False)

# Save summary data for report
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

# --- Optionally generate Word report ---
generate_report = input("\nWould you like to generate a Word report? (y/n): ").strip().lower() == 'y'
if generate_report:
    print("Generating Word report...")
    subprocess.run(["python3", "generate_solar_report.py"])

def calculate_solar_production(solar_data, params):
    """
    Calculate solar production with the new factors
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

def main():
    # Get user input
    params = get_user_input()
    
    # Get solar data
    solar_data = get_solar_data(params)
    
    # Calculate production with new factors
    monthly_production = calculate_solar_production(solar_data, params)
    
    # Print results
    print("\nMonthly Solar Production (kWh):")
    for month, production in monthly_production.items():
        print(f"{month}: {production:.2f}")
    
    # Generate report
    print("\nGenerating Word report...")
    subprocess.run(["python3", "generate_solar_report.py"])

if __name__ == "__main__":
    main() 