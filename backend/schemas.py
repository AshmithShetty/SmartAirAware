from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class SettingsSchema(BaseModel):
    comfort_min_c: float = Field(..., description="Minimum indoor comfort temperature in C")
    comfort_max_c: float = Field(..., description="Maximum indoor comfort temperature in C")
    pm25_limit: float = Field(..., gt=0, description="Indoor PM2.5 threshold limit in ug/m3")
    peak_start_h: int = Field(..., ge=0, le=23, description="Start hour of peak electricity pricing")
    peak_end_h: int = Field(..., ge=1, le=24, description="End hour of peak electricity pricing")
    filter_eff: Optional[float] = Field(0.8, ge=0.0, le=1.0)
    infiltration_ach: Optional[float] = Field(0.3, ge=0.0)
    penetration: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    deposition_per_h: Optional[float] = Field(0.5, ge=0.0)
    person_source_ugps: Optional[float] = Field(0.0, ge=0.0)
    lambda_peak: Optional[float] = Field(1.0, ge=0.0)
    gamma_switch: Optional[float] = Field(0.5, ge=0.0)
    violation_penalty: Optional[float] = Field(1000.0, ge=0.0)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.comfort_min_c >= self.comfort_max_c:
            raise ValueError("comfort_min_c must be strictly less than comfort_max_c")
        if self.peak_start_h >= self.peak_end_h:
            raise ValueError("peak_start_h must be strictly less than peak_end_h")
        return self

class OccupancyItemSchema(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    headcount: int = Field(..., ge=0)

class OccupancyUpdateSchema(BaseModel):
    max_capacity: Optional[int] = Field(None, gt=0)
    occupancy: List[OccupancyItemSchema]

    @model_validator(mode="after")
    def validate_occupancy_list(self):
        if len(self.occupancy) != 24:
            raise ValueError("Occupancy profile must contain exactly 24 hourly entries (0-23)")
        
        hours = [item.hour for item in self.occupancy]
        if sorted(hours) != list(range(24)):
            raise ValueError("Occupancy profile must have unique hours covering 0 through 23")

        if self.max_capacity is not None:
            for item in self.occupancy:
                if item.headcount > self.max_capacity:
                    raise ValueError(
                        f"Headcount {item.headcount} at hour {item.hour} exceeds max_capacity {self.max_capacity}"
                    )
        return self

class OccupancyResponseSchema(BaseModel):
    max_capacity: int
    occupancy: List[OccupancyItemSchema]

class ScheduleRowSchema(BaseModel):
    datetime: str
    mode_label: str
    cooling_setpoint_c: float
    outdoor_air_lps: float
    action: str
    headcount: int
    outdoor_temp_c: float
    outdoor_pm25: float
    expected_zone_temp_c: float
    expected_indoor_pm25: float
    expected_kw: float
    locked: bool = False

class KPISchema(BaseModel):
    baseline_kwh: float
    optimized_kwh: float
    baseline_peak_kw: float
    optimized_peak_kw: float
    comfort_hours_met: int
    occupied_hours: int
    iaq_violations: int
    flexible_kw: float

class ScheduleLatestResponse(BaseModel):
    run_id: str
    run_time: str
    forecast_age_min: float
    stale_forecast: bool
    summary: Dict[str, Any]
    schedule: List[ScheduleRowSchema]

class ForecastRowSchema(BaseModel):
    hour_utc: str
    temp_c: float
    rh_pct: float
    dewpoint_c: float
    pm25: float
    us_aqi: Optional[int] = None

class RunSchema(BaseModel):
    id: str
    started_utc: str
    ended_utc: Optional[str] = None
    status: str
    window_start_utc: Optional[str] = None
    stale_forecast: bool
    error_text: Optional[str] = None

class ActionResponse(BaseModel):
    message: str
    run_id: Optional[str] = None
    status: Optional[str] = None
