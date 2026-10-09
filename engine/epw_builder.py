import shutil
from datetime import datetime
import math

def get_doy(date_str):
    """Returns the non-leap day of year (1-365) for a given date string (YYYY-MM-DD)."""
    dt = datetime.fromisoformat(date_str.split("T")[0])
    # Map Feb 29 to Feb 28
    if dt.month == 2 and dt.day == 29:
        dt = dt.replace(day=28)
    
    # Calculate DOY treating the year as non-leap
    # A standard non-leap year is 2023
    dt_non_leap = datetime(2023, dt.month, dt.day)
    return dt_non_leap.timetuple().tm_yday

def build_epw(base_epw_path: str, out_epw_path: str, forecast: list):
    """
    Overwrites the base EPW with forecast data.
    forecast is a list of dicts: {"hour_utc": "...", "temp_c": ..., "dewpoint_c": ..., "rh_pct": ...}
    We need to overwrite the data for dates D and D+1 in local time.
    For simplicity, the forecast already contains 24 to 48 hours of data.
    """
    shutil.copy2(base_epw_path, out_epw_path)
    
    # Parse the forecast to a dictionary keyed by (month, day, hour)
    # EnergyPlus EPW uses local time, 1-24 hours.
    forecast_map = {}
    for row in forecast:
        # Assuming forecast time is local time for the building
        dt = datetime.fromisoformat(row["hour_utc"]) # Keep as is, pretending it's local
        if dt.month == 2 and dt.day == 29:
            dt = dt.replace(day=28)
        
        # EPW hours are 1-24. datetime hour is 0-23.
        epw_hour = dt.hour + 1
        forecast_map[(dt.month, dt.day, epw_hour)] = row

    # Now read and overwrite
    with open(base_epw_path, 'r') as f_in, open(out_epw_path, 'w') as f_out:
        for line in f_in:
            if not line.strip() or line.startswith(("LOCATION", "DESIGN CONDITIONS", "TYPICAL/EXTREME", "GROUND TEMPERATURES", "HOLIDAYS/DAYLIGHT", "COMMENTS", "DATA PERIODS")):
                f_out.write(line)
                continue
            
            parts = line.split(',')
            if len(parts) > 10:
                try:
                    month = int(parts[1])
                    day = int(parts[2])
                    hour = int(parts[3])
                    
                    if (month, day, hour) in forecast_map:
                        f_row = forecast_map[(month, day, hour)]
                        parts[6] = f"{f_row['temp_c']:.1f}"
                        parts[7] = f"{f_row['dewpoint_c']:.1f}"
                        parts[8] = f"{f_row['rh_pct']:.0f}"
                        line = ",".join(parts)
                except ValueError:
                    pass
            f_out.write(line)
