from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.orm import relationship
from .session import Base

class Building(Base):
    __tablename__ = "building"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    idf_path = Column(String(255), nullable=False)
    epw_path = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    floor_area_m2 = Column(Float, nullable=False)
    volume_m3 = Column(Float, nullable=False)
    max_capacity = Column(Integer, nullable=False)

class OccupancyHourly(Base):
    __tablename__ = "occupancy_hourly"

    hour = Column(Integer, primary_key=True)
    headcount = Column(Integer, nullable=False)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    comfort_min_c = Column(Float, nullable=False, default=23.0)
    comfort_max_c = Column(Float, nullable=False, default=27.0)
    pm25_limit = Column(Float, nullable=False, default=35.0)
    peak_start_h = Column(Integer, nullable=False, default=14)
    peak_end_h = Column(Integer, nullable=False, default=18)
    filter_eff = Column(Float, nullable=False, default=0.8)
    infiltration_ach = Column(Float, nullable=False, default=0.3)
    penetration = Column(Float, nullable=False, default=1.0)
    deposition_per_h = Column(Float, nullable=False, default=0.5)
    person_source_ugps = Column(Float, nullable=False, default=0.0)
    lambda_peak = Column(Float, nullable=False, default=1.0)
    gamma_switch = Column(Float, nullable=False, default=0.5)
    violation_penalty = Column(Float, nullable=False, default=1000.0)

class Run(Base):
    __tablename__ = "runs"

    id = Column(String(64), primary_key=True, index=True)
    started_utc = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_utc = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    window_start_utc = Column(DateTime, nullable=True)
    stale_forecast = Column(Boolean, nullable=False, default=False)
    error_text = Column(Text, nullable=True)

    forecasts = relationship("Forecast", back_populates="run", cascade="all, delete-orphan")
    mode_tables = relationship("ModeTable", back_populates="run", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="run", cascade="all, delete-orphan")
    kpi = relationship("KPI", back_populates="run", cascade="all, delete-orphan", uselist=False)

class Forecast(Base):
    __tablename__ = "forecast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    hour_utc = Column(DateTime, nullable=False)
    temp_c = Column(Float, nullable=False)
    rh_pct = Column(Float, nullable=False)
    dewpoint_c = Column(Float, nullable=False)
    pm25 = Column(Float, nullable=False)
    us_aqi = Column(Integer, nullable=True)

    run = relationship("Run", back_populates="forecasts")

class ModeTable(Base):
    __tablename__ = "mode_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(50), nullable=False)
    hour_utc = Column(DateTime, nullable=False)
    kwh = Column(Float, nullable=False)
    kw = Column(Float, nullable=False)
    zone_temp_max_c = Column(Float, nullable=False)
    zone_temp_mean_c = Column(Float, nullable=False)
    indoor_pm25 = Column(Float, nullable=False)

    run = relationship("Run", back_populates="mode_tables")

class Schedule(Base):
    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    hour_utc = Column(DateTime, nullable=False)
    mode = Column(String(50), nullable=False)
    cooling_setpoint_c = Column(Float, nullable=False)
    outdoor_air_lps = Column(Float, nullable=False)
    action = Column(String(50), nullable=False)
    headcount = Column(Integer, nullable=False)
    expected_zone_temp_c = Column(Float, nullable=False)
    expected_indoor_pm25 = Column(Float, nullable=False)
    expected_kw = Column(Float, nullable=False)
    locked = Column(Boolean, nullable=False, default=False)

    run = relationship("Run", back_populates="schedules")

class KPI(Base):
    __tablename__ = "kpi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    baseline_kwh = Column(Float, nullable=False)
    optimized_kwh = Column(Float, nullable=False)
    baseline_peak_kw = Column(Float, nullable=False)
    optimized_peak_kw = Column(Float, nullable=False)
    comfort_hours_met = Column(Integer, nullable=False)
    occupied_hours = Column(Integer, nullable=False)
    iaq_violations = Column(Integer, nullable=False)
    flexible_kw = Column(Float, nullable=False)

    run = relationship("Run", back_populates="kpi")

class Actuals(Base):
    __tablename__ = "actuals"

    hour_utc = Column(DateTime, primary_key=True)
    kwh = Column(Float, nullable=False)
