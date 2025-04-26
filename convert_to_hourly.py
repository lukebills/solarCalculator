import pandas as pd
import numpy as np

def convert_to_hourly(input_file='HalfHourlyMeterData.csv', output_file='HourlyMeterData.csv'):
    # Read the CSV file, skipping the header rows
    df = pd.read_csv(input_file, skiprows=5)
    
    # Convert Date and Time columns to datetime with dayfirst=True
    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], dayfirst=True)
    
    # Create date and hour columns for grouping
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    
    # Group by date and hour, summing the usage
    hourly_data = df.groupby(['date', 'hour']).agg({
        'Usage not yet billed': 'sum',
        'Usage already billed': 'sum',
        'Meter reading status': lambda x: 'Actual' if all(x == 'Actual') else 'Estimated'
    }).reset_index()
    
    # Format numbers to always show 3 decimal places
    hourly_data['Usage not yet billed'] = hourly_data['Usage not yet billed'].round(3).map('{:.3f}'.format)
    hourly_data['Usage already billed'] = hourly_data['Usage already billed'].round(3).map('{:.3f}'.format)
    
    # Format the output
    hourly_data['Date'] = hourly_data['date'].astype(str)
    hourly_data['Time'] = hourly_data['hour'].apply(lambda x: f"{x:02d}:00")
    hourly_data = hourly_data[['Date', 'Time', 'Usage not yet billed', 'Usage already billed', 'Meter reading status']]
    
    # Save to CSV
    hourly_data.to_csv(output_file, index=False)
    print(f"Hourly data saved to {output_file}")
    
    return hourly_data

if __name__ == '__main__':
    convert_to_hourly() 