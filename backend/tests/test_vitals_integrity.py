from app.extensions import db
from app.models import VitalReading


def test_partial_vital_entry_keeps_unrecorded_measurements_null(client, app, auth_headers):
    response = client.post(
        "/api/vitals",
        headers=auth_headers,
        json={"date": "2026-08-20", "sleepHours": 7.5},
    )

    assert response.status_code == 201
    assert response.json["data"]["reading"] == {
        "date": "2026-08-20",
        "heartRate": None,
        "hrv": None,
        "spo2": None,
        "sleepHours": 7.5,
        "stress": None,
        "hydrationMl": None,
    }

    with app.app_context():
        row = db.session.query(VitalReading).one()
        assert row.heart_rate is None
        assert row.hrv_ms is None
        assert row.spo2 is None
        assert row.stress_score is None
        assert row.hydration_ml is None


def test_summary_does_not_average_missing_measurements_as_zero(client, auth_headers):
    client.post(
        "/api/vitals",
        headers=auth_headers,
        json={"date": "2026-08-20", "sleepHours": 7.5},
    )

    response = client.get("/api/insights?days=30", headers=auth_headers)

    assert response.status_code == 200
    assert response.json["data"]["summary"] == {
        "heartRate": None,
        "hrv": None,
        "spo2": None,
        "sleep": 7.5,
        "stress": None,
        "hydrationMl": None,
    }
