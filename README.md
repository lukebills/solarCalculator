# Solar Calculator

A comprehensive tool for analyzing the financial viability of solar panel and battery systems. This calculator uses real electricity usage data and solar production estimates to determine energy self-consumption, grid exports/imports, financial savings, and payback periods.

## Features

- **Solar Production Analysis**: Calculate potential solar energy production based on location and system parameters
- **Battery Simulation**: Model battery behavior including charging, discharging, and efficiency losses
- **Financial Analysis**: 
  - Calculate energy savings
  - Estimate payback period
  - Compare scenarios with and without battery storage
- **Report Generation**: Generate detailed Word reports with analysis results and visualizations

## Prerequisites

- Python 3.8 or higher
- Required Python packages (see `requirements.txt`)
- NREL PVWatts API key (for solar data)
- Electricity usage data in CSV format

## Installation

1. Clone the repository:
```bash
git clone https://github.com/lukebills/solarCalculator.git
cd solarCalculator
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your PVWatts API key:
```
PVWATTS_API_KEY=your_api_key_here
```

## Usage

1. Place your electricity usage data in the `Synergy Data` folder as `HourlyMeterData.csv`

2. Run the solar calculator:
```bash
python solar_calculator.py
```

3. Follow the prompts to:
   - Enter system parameters
   - Choose whether to include battery storage
   - Input battery specifications (if applicable)
   - Specify system cost

4. Review the generated analysis and optionally create a Word report

## Output

The calculator generates:
- Detailed CSV files with hourly analysis
- JSON summary files
- Optional Word reports with visualizations
- Console output with key metrics

## Project Structure

- `solar_calculator.py`: Main analysis script
- `Solar_data.py`: Handles solar data retrieval from PVWatts API
- `generate_solar_report.py`: Creates Word reports with analysis results
- `convert_to_hourly.py`: Utility for data format conversion
- `requirements.txt`: Python package dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NREL PVWatts API for solar production data
- Synergy for electricity usage data format 