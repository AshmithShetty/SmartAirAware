import os
import pytest
from datetime import datetime
from unittest.mock import patch
import httpx
from engine.ingest import ingest_forecast, _load_fixture
from db.models import Run, Forecast

def test_load_all_fixtures():
    fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "fixtures"))
    for fix_name in ["clean_air.json", "high_pm25.json", "hot_day.json", "default.json"]:
        p = os.path.join(fixtures_dir, fix_name)
        assert os.path.exists(p), f"Missing fixture {fix_name}"
        data = _load_fixture(p)
        assert len(data) >= 24
        sample = data[0]
        assert "hour_utc" in sample
        assert "temp_c" in sample
        assert "pm25" in sample
        assert "rh_pct" in sample
        assert "dewpoint_c" in sample

def test_ingest_from_fixture_source():
    data, is_stale = ingest_forecast(forecast_source="fixture")
    assert not is_stale
    assert len(data) >= 24

def test_live_failure_without_db_raises():
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(RuntimeError) as exc_info:
            ingest_forecast(db=None, forecast_source="live")
        assert "No database session" in str(exc_info.value)

def test_live_failure_fallback_to_stale_forecast(db_session):
    # Seed DB with a previous successful run
    run_id = "run_past_success"
    db_session.add(Run(
        id=run_id,
        started_utc=datetime.utcnow(),
        status="success"
    ))
    for h in range(24):
        db_session.add(Forecast(
            run_id=run_id,
            hour_utc=datetime(2026, 10, 8, h, 0),
            temp_c=26.0,
            rh_pct=45.0,
            dewpoint_c=13.0,
            pm25=18.0,
            us_aqi=55
        ))
    db_session.commit()

    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Timeout")):
        data, is_stale = ingest_forecast(db=db_session, forecast_source="live")
        assert is_stale is True
        assert len(data) == 24
        assert data[0]["pm25"] == 18.0
