import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["ADMIN_KEY"] = "test_admin_key"
os.environ["FORECAST_SOURCE"] = "fixture"
os.environ["FIXTURE_PATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "fixtures"))

from db.session import Base, get_db
from db.seed import seed_db
from backend.app import app

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    # Seed
    db = TestingSessionLocal()
    from db.models import Building, Settings, OccupancyHourly
    from engine.config_modes import DEFAULT_SETTINGS, MAX_CAPACITY

    db.add(Building(
        id=1,
        name="Test Building",
        idf_path="data/building.idf",
        epw_path="data/base_delhi.epw",
        lat=28.6139,
        lon=77.2090,
        floor_area_m2=4982.19,
        volume_m3=15000.0,
        max_capacity=MAX_CAPACITY
    ))

    db.add(Settings(
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
    ))

    for h in range(24):
        db.add(OccupancyHourly(hour=h, headcount=MAX_CAPACITY if 8 <= h < 18 else 0))

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
