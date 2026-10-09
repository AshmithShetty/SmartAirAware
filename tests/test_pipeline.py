import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.session import Base
from db.models import Run, Forecast, ModeTable, Schedule, KPI, Building, Settings, OccupancyHourly
from engine.config_modes import DEFAULT_SETTINGS, MAX_CAPACITY
from worker.pipeline import run_pipeline


def _make_test_session():
    """Creates an isolated in-memory SQLite session for pipeline tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragmas(conn, _):
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed required rows
    session.add(Building(
        id=1, name="Test", idf_path="data/building.idf", epw_path="data/base_delhi.epw",
        lat=28.6139, lon=77.2090, floor_area_m2=4982.19, volume_m3=15000.0, max_capacity=MAX_CAPACITY
    ))
    session.add(Settings(
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
        session.add(OccupancyHourly(hour=h, headcount=MAX_CAPACITY if 8 <= h < 18 else 0))
    session.commit()

    return session


def test_pipeline_atomic_execution():
    session = _make_test_session()

    mock_mode_data = [
        {
            "local_hour": h,
            "kwh": 12.0,
            "kw": 12.0,
            "zone_temp_mean_c": 24.0,
            "zone_temp_max_c": 25.0,
            "zone_temp_min_c": 23.0
        }
        for h in range(24)
    ]

    with patch("worker.pipeline.SessionLocal", return_value=session), \
         patch("worker.pipeline.build_epw"), \
         patch("worker.pipeline.build_mode_idfs"), \
         patch("worker.pipeline.run_all_modes"), \
         patch("worker.pipeline.parse_sql", return_value=mock_mode_data), \
         patch("worker.pipeline.verify_loop", return_value=(["Maintain"] * 24, mock_mode_data)):

        run_id = f"test_pipe_{uuid.uuid4().hex[:8]}"
        res_id = run_pipeline(existing_run_id=run_id)

        assert res_id == run_id

        run_record = session.query(Run).filter(Run.id == run_id).first()
        assert run_record is not None
        assert run_record.status == "success"
        assert run_record.ended_utc is not None
        assert run_record.error_text is None

        fc_count = session.query(Forecast).filter(Forecast.run_id == run_id).count()
        assert fc_count == 24

        mt_count = session.query(ModeTable).filter(ModeTable.run_id == run_id).count()
        assert mt_count == 4 * 24

        sched_count = session.query(Schedule).filter(Schedule.run_id == run_id).count()
        assert sched_count == 24

        kpi = session.query(KPI).filter(KPI.run_id == run_id).first()
        assert kpi is not None
        assert kpi.optimized_kwh > 0

    session.close()


def test_pipeline_error_handling():
    # Use a fully independent in-memory session so the rollback in the pipeline
    # does not interact with the shared test-fixture transaction.
    main_session = _make_test_session()
    fail_session = _make_test_session()

    # Return main_session on first call, fail_session on second call (for the except block).
    session_factory = MagicMock(side_effect=[main_session, fail_session])

    with patch("worker.pipeline.SessionLocal", session_factory), \
         patch("worker.pipeline.ingest_forecast", side_effect=RuntimeError("Simulated weather failure")):

        run_id = f"test_fail_{uuid.uuid4().hex[:8]}"
        with pytest.raises(RuntimeError):
            run_pipeline(existing_run_id=run_id)

    # The failure record is written through fail_session
    run_record = fail_session.query(Run).filter(Run.id == run_id).first()
    assert run_record is not None
    assert run_record.status == "failed"
    assert "Simulated weather failure" in run_record.error_text

    main_session.close()
    fail_session.close()
