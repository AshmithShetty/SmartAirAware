def compute_indoor_pm25(
    c_out: float,
    headcount: int,
    oa_multiplier: float,
    oa_per_person_m3s: float,
    oa_per_area_m3s: float,
    floor_area_m2: float,
    volume_m3: float,
    filter_eff: float,
    infiltration_ach: float,
    penetration: float,
    deposition_per_h: float,
    person_source_ugps: float = 0.0
) -> float:
    """
    Computes steady-state indoor PM2.5 (ug/m3).
    Q values are in m3/s.
    """
    q_oa = oa_multiplier * (oa_per_person_m3s * headcount + oa_per_area_m3s * floor_area_m2)
    q_inf = (infiltration_ach * volume_m3) / 3600.0
    q_dep = (deposition_per_h * volume_m3) / 3600.0
    
    numerator = c_out * (q_oa * (1.0 - filter_eff) + penetration * q_inf) + person_source_ugps * headcount
    denominator = q_oa + q_inf + q_dep
    
    if denominator == 0:
        return c_out
        
    return numerator / denominator
