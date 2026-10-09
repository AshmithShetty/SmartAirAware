import os
import shutil
from eppy.modeleditor import IDF
from .config_modes import MODES, SCHEDULES, MAX_CAPACITY

def _build_hourly_schedule(idf, schedule_name, hourly_values):
    """
    Overwrites a Schedule:Compact object to use explicit hourly values for AllDays.
    hourly_values is a list of 24 values corresponding to hour 1 to 24.
    """
    schedules = idf.idfobjects['SCHEDULE:COMPACT']
    sched = next((s for s in schedules if s.Name.lower() == schedule_name.lower()), None)
    
    if not sched:
        print(f"Warning: Schedule {schedule_name} not found.")
        return
    
    # Clear existing fields after field 2
    # field 1: Name, field 2: Schedule Type Limits Name
    # We will build: Through: 12/31, For: AllDays, Until: 01:00, val1, Until: 02:00, val2...
    
    # Eppy way to clear and set fields:
    # A Schedule:Compact has variable number of fields.
    # We can just reset obj.obj to the first 3 elements (Type, Name, Type Limits)
    base_obj = sched.obj[:3]
    base_obj[2] = '' # Clear the Schedule Type Limits Name so values > 1 are permitted
    new_fields = ['Through: 12/31', 'For: AllDays']
    for i, val in enumerate(hourly_values):
        new_fields.append(f'Until: {i+1:02d}:00')
        new_fields.append(val)
        
    sched.obj = base_obj + new_fields


def build_mode_idfs(base_idf_path: str, run_folder: str, headcount_profile: list, window_start_date_str: str):
    """
    Reads base_idf_path, sets up RunPeriod for D through D+1,
    and writes out 4 IDF files into run_folder/<mode>/building.idf.
    headcount_profile: list of 24 ints (for window)
    window_start_date_str: 'YYYY-MM-DD'
    """
    from datetime import datetime, timedelta
    
    dt = datetime.fromisoformat(window_start_date_str)
    dt_next = dt + timedelta(days=1)
    
    iddfile = os.getenv("ENERGYPLUS_IDD")
    if not IDF.getiddname():
        IDF.setiddname(iddfile)
        
    idf = IDF(base_idf_path)
    
    # Set RunPeriod
    run_periods = idf.idfobjects['RUNPERIOD']
    if run_periods:
        rp = run_periods[0]
        rp.Begin_Month = dt.month
        rp.Begin_Day_of_Month = dt.day
        rp.End_Month = dt_next.month
        rp.End_Day_of_Month = dt_next.day
    else:
        idf.newidfobject('RUNPERIOD',
            Begin_Month=dt.month, Begin_Day_of_Month=dt.day,
            End_Month=dt_next.month, End_Day_of_Month=dt_next.day)

    # Enable Weather File Simulation
    sim_control = idf.idfobjects['SIMULATIONCONTROL']
    if sim_control:
        sim_control[0].Run_Simulation_for_Weather_File_Run_Periods = 'Yes'
    else:
        idf.newidfobject('SIMULATIONCONTROL', Run_Simulation_for_Weather_File_Run_Periods='Yes')

    # Set occupancy schedule (applies to all modes)
    # The headcount_profile is for 24 hours of the window (D).
    # We apply it to D and D+1 (For: AllDays covers all days in the run).
    occ_fractions = [h / MAX_CAPACITY for h in headcount_profile]
    _build_hourly_schedule(idf, SCHEDULES['occupancy'], occ_fractions)
    
    # For each mode, create a folder and an IDF
    for mode_name, mode_config in MODES.items():
        mode_dir = os.path.join(run_folder, mode_name)
        os.makedirs(mode_dir, exist_ok=True)
        
        # Set Cooling Setpoint schedule
        _build_hourly_schedule(idf, SCHEDULES['cooling_setpoint'], [mode_config['cooling_setpoint_c']] * 24)
        
        # Set Outdoor Air schedule
        _build_hourly_schedule(idf, SCHEDULES['outdoor_air'], [mode_config['oa_multiplier']] * 24)
        
        out_idf = os.path.join(mode_dir, "building.idf")
        idf.saveas(out_idf)

