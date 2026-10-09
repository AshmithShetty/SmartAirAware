def get_violations(
    headcount: int,
    indoor_pm25: float,
    zone_temp_min_c: float,
    zone_temp_max_c: float,
    pm25_limit: float,
    comfort_min_c: float,
    comfort_max_c: float
) -> bool:
    """
    Returns True if the hour is occupied and either PM2.5 or comfort limits are breached.
    """
    if headcount <= 0:
        return False
        
    if indoor_pm25 > pm25_limit:
        return True
        
    # EnergyPlus parses max and mean. Since we don't have min exactly from parser right now,
    # we'll use mean for the lower bound check, or assume min <= mean.
    # The plan says "maximum zone temperature is above the comfort maximum or the minimum is below the comfort minimum".
    # For now, we will check if the mean drops below min_c, or max exceeds max_c.
    if zone_temp_max_c > comfort_max_c:
        return True
        
    if zone_temp_min_c < comfort_min_c:
        return True
        
    return False
