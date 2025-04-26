"""
Data Conversion Utility - Converts half-hourly meter data to hourly format

This module processes electricity meter data by:
- Converting half-hourly readings to hourly totals
- Aggregating usage data
- Maintaining meter reading status
- Formatting output for consistency

Program Flow:
1. Read and parse input data
2. Convert datetime format
3. Aggregate half-hourly data to hourly
4. Format and save output
"""

import pandas as pd
import numpy as np

def convert_to_hourly(input_file='HalfHourlyMeterData.csv', output_file='HourlyMeterData.csv'):
    """
    Convert half-hourly meter data to hourly format
    
    Args:
        input_file (str): Path to input CSV file with half-hourly data
        output_file (str): Path to save the hourly data CSV
        
    Returns:
        pd.DataFrame: Processed hourly data
        
    Process:
    1. Read input data, skipping header rows
    2. Convert date and time to datetime
    3. Group data by hour
    4. Format and save output
    """
    # --- Step 1: Read Input Data ---
    # Read CSV file, skipping the first 5 rows which typically contain metadata
    df = pd.read_csv(input_file, skiprows=5)
    
    # --- Step 2: Convert Datetime Format ---
    # Combine Date and Time columns into a datetime object
    # dayfirst=True ensures correct parsing of dates in DD/MM/YYYY format
    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], dayfirst=True)
    
    # Create separate date and hour columns for grouping
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    
    # --- Step 3: Aggregate to Hourly Data ---
    # Group by date and hour, summing the usage values
    # For meter reading status, use 'Actual' if all readings in the hour are actual,
    # otherwise mark as 'Estimated'
    hourly_data = df.groupby(['date', 'hour']).agg({
        'Usage not yet billed': 'sum',  # Sum of unbilled usage for the hour
        'Usage already billed': 'sum',  # Sum of billed usage for the hour
        'Meter reading status': lambda x: 'Actual' if all(x == 'Actual') else 'Estimated'
    }).reset_index()
    
    # --- Step 4: Format Numbers ---
    # Round all usage values to 3 decimal places and format consistently
    hourly_data['Usage not yet billed'] = hourly_data['Usage not yet billed'].round(3).map('{:.3f}'.format)
    hourly_data['Usage already billed'] = hourly_data['Usage already billed'].round(3).map('{:.3f}'.format)
    
    # --- Step 5: Prepare Output Format ---
    # Convert date back to string format
    hourly_data['Date'] = hourly_data['date'].astype(str)
    
    # Format hour as HH:00 (e.g., "01:00", "13:00")
    hourly_data['Time'] = hourly_data['hour'].apply(lambda x: f"{x:02d}:00")
    
    # Select and order columns for output
    hourly_data = hourly_data[['Date', 'Time', 'Usage not yet billed', 'Usage already billed', 'Meter reading status']]
    
    # --- Step 6: Save Results ---
    # Save processed data to CSV file
    hourly_data.to_csv(output_file, index=False)
    print(f"Hourly data saved to {output_file}")
    
    return hourly_data

if __name__ == '__main__':
    # Run the conversion if script is executed directly
    convert_to_hourly() 