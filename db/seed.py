import os
from .session import engine, SessionLocal, Base
from .models import Building, OccupancyHourly, Settings
from engine.config_modes import DEFAULT_SETTINGS, MAX_CAPACITY

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_db():
    init_db()
    db = SessionLocal()
    try:
        # 1. Building
        building = db.query(Building).first()
        if not building:
            idf_rel_path = "data/building.idf"
            epw_rel_path = "data/base_delhi.epw"
            floor_area_m2 = 4982.19
            volume_m3 = 15000.0

            building = Building(
                id=1,
                name="DOE Medium Office (Delhi)",
                idf_path=idf_rel_path,
                epw_path=epw_rel_path,
                lat=28.6139,
                lon=77.2090,
                floor_area_m2=floor_area_m2,
                volume_m3=volume_m3,
                max_capacity=MAX_CAPACITY
            )
            db.add(building)

        # 2. Settings
        settings = db.query(Settings).first()
        if not settings:
            settings = Settings(
                id=1,
                comfort_min_c=DEFAULT_SETTINGS["comfort_min_c"],
                comfort_max_c=DEFAULT_SETTINGS["comfort_max_c"],
                pm25_limit=DEFAULT_SETTINGS["pm25_limit"],
                peak_start_h=DEFAULT_SETTINGS["peak_start_h"],
                peak_end_h=DEFAULT_SETTINGS["peak_end_h"],
                filter_eff=DEFAULT_SETTINGS["filter_eff"],
                infiltration_ach=DEFAULT_SETTINGS["infiltration_ach"],
                penetration=DEFAULT_SETTINGS["penetration"],
                deposition_per_h=DEFAULT_SETTINGS["deposition_per_h"],
                person_source_ugps=DEFAULT_SETTINGS["person_source_ugps"],
                lambda_peak=DEFAULT_SETTINGS["lambda_peak"],
                gamma_switch=DEFAULT_SETTINGS["gamma_switch"],
                violation_penalty=DEFAULT_SETTINGS["violation_penalty"]
            )
            db.add(settings)

        # 3. Occupancy Hourly (24 hours)
        count_occ = db.query(OccupancyHourly).count()
        if count_occ < 24:
            db.query(OccupancyHourly).delete()
            default_headcount = (
                [0] * 8 +
                [MAX_CAPACITY] * 10 +
                [0] * 6
            )
            for h in range(24):
                db.add(OccupancyHourly(hour=h, headcount=default_headcount[h]))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
    print("Database initialized and seeded successfully.")
