"""
Configuration for simulation modes, schedule names, and default settings.
"""

MODES = {
    "Ventilate": {
        "cooling_setpoint_c": 24.0,
        "oa_multiplier": 1.5,
    },
    "Maintain": {
        "cooling_setpoint_c": 24.5,
        "oa_multiplier": 1.0,
    },
    "Reduce HVAC": {
        "cooling_setpoint_c": 26.5,
        "oa_multiplier": 0.6,
    },
    "Shift Load": {
        "cooling_setpoint_c": 23.0,
        "oa_multiplier": 0.8,
    },
}

SCHEDULES = {
    "cooling_setpoint": "CLGSETP_SCH",
    "outdoor_air": "MinOA_MotorizedDamper_Sched",
    "occupancy": "BLDG_OCC_SCH",
}

DEFAULT_SETTINGS = {
    "comfort_min_c": 23.0,
    "comfort_max_c": 27.0,
    "pm25_limit": 35.0,  # ug/m3
    "peak_start_h": 14,
    "peak_end_h": 18,
    "filter_eff": 0.8,
    "infiltration_ach": 0.3,
    "penetration": 1.0,
    "deposition_per_h": 0.5,
    "person_source_ugps": 0.0,
    "lambda_peak": 1.0,
    "gamma_switch": 0.5,
    "violation_penalty": 1000.0,
}

# Building specific default (max capacity)
MAX_CAPACITY = 268
