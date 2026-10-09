import os
import shutil
from .config_modes import MODES, SCHEDULES
from .idf_builder import _build_hourly_schedule, build_mode_idfs
from .runner import _run_energyplus
from .parser import parse_sql

def run_verify(
    schedule: list,
    base_idf_path: str,
    run_folder: str,
    epw_path: str,
    headcount: list,
    window_start_date_str: str,
    timeout_s: int = 300,
    start_hour: int = 0
):
    """
    Builds and runs a single IDF with the exact schedule applied hour-by-hour.
    Returns the parsed results.
    """
    verify_dir = os.path.join(run_folder, "verify")
    os.makedirs(verify_dir, exist_ok=True)
    
    from eppy.modeleditor import IDF
    from datetime import datetime, timedelta
    
    dt = datetime.fromisoformat(window_start_date_str)
    dt_next = dt + timedelta(days=1)
    
    idf = IDF(base_idf_path)
    
    run_periods = idf.idfobjects['RUNPERIOD']
    if run_periods:
        rp = run_periods[0]
        rp.Begin_Month = dt.month
        rp.Begin_Day_of_Month = dt.day
        rp.End_Month = dt_next.month
        rp.End_Day_of_Month = dt_next.day
        
    sim_control = idf.idfobjects['SIMULATIONCONTROL']
    if sim_control:
        sim_control[0].Run_Simulation_for_Weather_File_Run_Periods = 'Yes'

    # Occupancy
    from .config_modes import MAX_CAPACITY
    occ_fractions = [h / MAX_CAPACITY for h in headcount]
    _build_hourly_schedule(idf, SCHEDULES['occupancy'], occ_fractions)
    
    # Modes
    cooling_vals = [MODES[m]['cooling_setpoint_c'] for m in schedule]
    oa_vals = [MODES[m]['oa_multiplier'] for m in schedule]
    
    _build_hourly_schedule(idf, SCHEDULES['cooling_setpoint'], cooling_vals)
    _build_hourly_schedule(idf, SCHEDULES['outdoor_air'], oa_vals)
    
    out_idf = os.path.join(verify_dir, "building.idf")
    idf.saveas(out_idf)
    
    # Run
    _, success, err = _run_energyplus("verify", verify_dir, epw_path, timeout_s)
    if not success:
        raise RuntimeError(f"Verify run failed: {err}")
        
    # Parse
    sql_path = os.path.join(verify_dir, "eplusout.sql")
    return parse_sql(sql_path, window_start_date_str, start_hour=start_hour)

def verify_loop(
    schedule: list,
    mode_table: dict,
    headcount: list,
    local_hours: list,
    last_mode: str,
    last_h0_mode: str,
    settings: dict,
    base_idf_path: str,
    run_folder: str,
    epw_path: str,
    window_start_date_str: str,
    optimize_fn,
    start_hour: int = 0
):
    """
    Runs verify up to 3 times (2 re-solves).
    If an occupied hour breaches comfort unexpectedly, mark that hour and the previous one Maintain-only.
    """
    max_loops = 3
    current_schedule = schedule.copy()
    
    for loop in range(max_loops):
        print(f"Verify loop {loop+1}/{max_loops}...")
        parsed_results = run_verify(
            current_schedule, base_idf_path, run_folder, epw_path, headcount, window_start_date_str,
            start_hour=start_hour
        )
        
        # Check comfort violations
        unexpected_breach = False
        
        for h, row in enumerate(parsed_results):
            if headcount[h] > 0:
                breached = row['zone_temp_max_c'] > settings['comfort_max_c'] or row['zone_temp_min_c'] < settings['comfort_min_c']
                
                # Check if the optimizer predicted a violation
                predicted_viol = mode_table[current_schedule[h]][h]['violation']
                
                if breached and not predicted_viol:
                    print(f"Unexpected comfort breach at hour {h} (mode {current_schedule[h]}). Temp: {row['zone_temp_min_c']} to {row['zone_temp_max_c']}")
                    unexpected_breach = True
                    
                    # Mark this hour and the previous one Maintain-only
                    # We do this by artificially increasing the violation penalty of all other modes to infinity
                    # But since we pass mode_table to optimizer, we can just modify mode_table for these hours!
                    for m in mode_table.keys():
                        if m != 'Maintain':
                            mode_table[m][h]['violation'] = 1000 # huge penalty
                            if h > 0:
                                mode_table[m][h-1]['violation'] = 1000
                                
        if not unexpected_breach or loop == max_loops - 1:
            return current_schedule, parsed_results
            
        # Re-solve
        current_schedule = optimize_fn(
            mode_table, headcount, local_hours, last_mode, last_h0_mode,
            settings['lambda_peak'], settings['gamma_switch'], settings['violation_penalty'],
            settings['peak_start_h'], settings['peak_end_h']
        )
        
    return current_schedule, parsed_results
