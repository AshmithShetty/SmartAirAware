import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config_modes import MODES

def _run_energyplus(mode_name, mode_dir, epw_path, timeout_s):
    """Runs EnergyPlus in a specific directory."""
    energyplus_dir = os.getenv("ENERGYPLUS_DIR")
    if not energyplus_dir:
        raise ValueError("ENERGYPLUS_DIR not set in .env")
        
    energyplus_exe = os.path.join(energyplus_dir, "energyplus")
    if os.name == 'nt':
        energyplus_exe += ".exe"
        
    idf_path = os.path.join(mode_dir, "building.idf")
    
    cmd = [
        energyplus_exe,
        "-w", epw_path,
        "-d", mode_dir,
        idf_path
    ]
    
    try:
        # Check if the process can run successfully within the timeout
        res = subprocess.run(cmd, cwd=mode_dir, capture_output=True, text=True, timeout=timeout_s)
        
        # Check for fatal errors in eplusout.err
        err_path = os.path.join(mode_dir, "eplusout.err")
        if os.path.exists(err_path):
            with open(err_path, 'r') as f:
                err_content = f.read()
                if "**  Fatal  **" in err_content:
                    raise RuntimeError(f"EnergyPlus fatal error in {mode_name}:\n{err_content}")
                    
        return mode_name, True, None
    except subprocess.TimeoutExpired:
        return mode_name, False, "Timeout"
    except Exception as e:
        return mode_name, False, str(e)


def run_all_modes(run_folder: str, epw_path: str):
    """
    Executes EnergyPlus for all modes concurrently using ThreadPoolExecutor.
    """
    timeout_s = int(os.getenv("SIM_TIMEOUT_S", 300))
    results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_run_energyplus, mode_name, os.path.join(run_folder, mode_name), epw_path, timeout_s): mode_name
            for mode_name in MODES.keys()
        }
        
        for future in as_completed(futures):
            mode_name = futures[future]
            try:
                m_name, success, err = future.result()
                if not success:
                    raise RuntimeError(f"Simulation failed for {m_name}: {err}")
                results[m_name] = True
            except Exception as e:
                raise RuntimeError(f"Simulation failed for {mode_name}: {e}")
                
    return results
