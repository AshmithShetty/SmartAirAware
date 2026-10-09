import uuid
from datetime import datetime, timezone
from db.models import Run, Schedule, KPI, Forecast

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_settings_get_and_put(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "comfort_min_c" in data
    assert "comfort_max_c" in data

    # Unauthorized PUT
    res = client.put("/api/settings", json={"comfort_min_c": 22.0, "comfort_max_c": 26.0, "pm25_limit": 30.0, "peak_start_h": 14, "peak_end_h": 18})
    assert res.status_code == 401

    # Validation failure: comfort_min >= comfort_max
    res = client.put(
        "/api/settings",
        json={"comfort_min_c": 28.0, "comfort_max_c": 24.0, "pm25_limit": 30.0, "peak_start_h": 14, "peak_end_h": 18},
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 422

    # Validation failure: peak_start >= peak_end
    res = client.put(
        "/api/settings",
        json={"comfort_min_c": 23.0, "comfort_max_c": 27.0, "pm25_limit": 30.0, "peak_start_h": 18, "peak_end_h": 14},
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 422

    # Valid update
    valid_payload = {
        "comfort_min_c": 22.5,
        "comfort_max_c": 26.5,
        "pm25_limit": 30.0,
        "peak_start_h": 13,
        "peak_end_h": 17,
        "filter_eff": 0.85
    }
    res = client.put(
        "/api/settings",
        json=valid_payload,
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 200
    assert res.json()["comfort_min_c"] == 22.5

def test_occupancy_validation(client):
    res = client.get("/api/occupancy")
    assert res.status_code == 200
    data = res.json()
    assert len(data["occupancy"]) == 24

    # Validation failure: less than 24 hours
    bad_payload = {
        "occupancy": [{"hour": 0, "headcount": 10}],
        "max_capacity": 268
    }
    res = client.put(
        "/api/occupancy",
        json=bad_payload,
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 422

    # Validation failure: headcount > max_capacity
    bad_headcount = {
        "occupancy": [{"hour": h, "headcount": 300 if h == 10 else 0} for h in range(24)],
        "max_capacity": 250
    }
    res = client.put(
        "/api/occupancy",
        json=bad_headcount,
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 422

    # Valid occupancy update
    valid_occ = {
        "occupancy": [{"hour": h, "headcount": 200 if 9 <= h < 17 else 0} for h in range(24)],
        "max_capacity": 268
    }
    res = client.put(
        "/api/occupancy",
        json=valid_occ,
        headers={"X-Admin-Key": "test_admin_key"}
    )
    assert res.status_code == 200

def test_queue_run(client):
    res = client.post("/api/run", headers={"X-Admin-Key": "test_admin_key"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert "run_id" in data

def test_latest_run_and_failed_run_isolation(client, db_session):
    # When empty
    res = client.get("/api/schedule/latest")
    assert res.status_code == 200
    assert res.json()["schedule"] == []

    # Insert a successful run
    run1_id = f"run_{uuid.uuid4().hex[:8]}"
    t1 = datetime.utcnow()
    run1 = Run(id=run1_id, started_utc=t1, ended_utc=t1, status="success")
    db_session.add(run1)

    kpi1 = KPI(
        run_id=run1_id,
        baseline_kwh=300.0,
        optimized_kwh=270.0,
        baseline_peak_kw=25.0,
        optimized_peak_kw=22.0,
        comfort_hours_met=10,
        occupied_hours=10,
        iaq_violations=0,
        flexible_kw=8.0
    )
    db_session.add(kpi1)

    for h in range(24):
        dt_h = datetime(2026, 10, 8, h, 0)
        db_session.add(Forecast(
            run_id=run1_id,
            hour_utc=dt_h,
            temp_c=25.0,
            rh_pct=50.0,
            dewpoint_c=14.0,
            pm25=15.0,
            us_aqi=40
        ))
        db_session.add(Schedule(
            run_id=run1_id,
            hour_utc=dt_h,
            mode="Maintain",
            cooling_setpoint_c=24.5,
            outdoor_air_lps=1200.0,
            action="Set now" if h == 0 else "No change",
            headcount=200 if 8 <= h < 18 else 0,
            expected_zone_temp_c=24.5,
            expected_indoor_pm25=12.0,
            expected_kw=15.0
        ))
    db_session.commit()

    # Query latest: should see run1
    res = client.get("/api/schedule/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run1_id
    assert len(data["schedule"]) == 24
    assert data["summary"]["optimized_kwh"] == 270.0

    # CSV download
    res_csv = client.get("/api/schedule/latest.csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "datetime,mode_label,cooling_setpoint_c" in res_csv.text

    # Now simulate a subsequent FAILED run
    run2_id = f"run_{uuid.uuid4().hex[:8]}"
    t2 = datetime.utcnow()
    run2 = Run(
        id=run2_id,
        started_utc=t2,
        ended_utc=t2,
        status="failed",
        error_text="EnergyPlus simulation failed"
    )
    db_session.add(run2)
    db_session.commit()

    # Query latest again: MUST STILL return run1!
    res_after_fail = client.get("/api/schedule/latest")
    assert res_after_fail.status_code == 200
    assert res_after_fail.json()["run_id"] == run1_id
    assert len(res_after_fail.json()["schedule"]) == 24
