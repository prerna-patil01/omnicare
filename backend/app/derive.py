"""Derived clinical state.

Nothing in this module invents a number. Every output is computed from rows the
user actually entered — vital readings they logged, biomarkers they recorded off
a report. When there is not enough entered data to support a conclusion, the
functions return `None` and the API says so rather than filling the gap.

That rule is the whole point of the file: a health platform that manufactures a
plausible-looking reading is worse than one that shows an empty state, because
the fabrication is indistinguishable from a real measurement downstream.
"""

from datetime import date, timedelta
from statistics import mean

from .extensions import db
from .models import Biomarker, Report, VitalReading

# Below this many readings we do not model a body system at all. Three weeks of
# entries is the floor for saying anything about a trend.
MIN_READINGS_FOR_TWIN = 7
MIN_READINGS_FOR_TREND = 3

# Population reference bands used to score an entered reading. These are
# published clinical ranges, not per-user invention.
BANDS = {
    "heart_rate": (60, 80, "lower is better"),
    "hrv_ms": (40, 100, "higher is better"),
    "spo2": (95, 100, "higher is better"),
    "sleep_hours": (7.0, 9.0, "higher is better"),
    "stress_score": (0, 40, "lower is better"),
    "hydration_ml": (2000, 3500, "higher is better"),
}


def _readings(user_id, days=90):
    cutoff = date.today() - timedelta(days=days)
    return (
        db.session.query(VitalReading)
        .filter(VitalReading.user_id == user_id, VitalReading.recorded_on >= cutoff)
        .order_by(VitalReading.recorded_on.asc())
        .all()
    )


def _field_mean(rows, field):
    values = [getattr(r, field) for r in rows if getattr(r, field) is not None]
    return round(mean(values), 1) if values else None


def _score_against_band(value, field):
    """0-100 risk contribution for one measure. None when unmeasured."""
    if value is None:
        return None
    low, high, direction = BANDS[field]
    if direction == "higher is better":
        if value >= high:
            return 0.0
        if value <= low * 0.6:
            return 100.0
        return round(max(0.0, min(100.0, (high - value) / (high - low * 0.6) * 100)), 1)
    if value <= low:
        return 0.0
    if value >= high * 1.6:
        return 100.0
    return round(max(0.0, min(100.0, (value - low) / (high * 1.6 - low) * 100)), 1)


# Which entered measures feed which body system. A system with no contributing
# measurement is not scored — it is reported as unmeasured.
SYSTEM_INPUTS = {
    "heart":      ("Cardiovascular", ["heart_rate", "hrv_ms"], 50, 33),
    "brain":      ("Neurological", ["sleep_hours", "stress_score"], 50, 18),
    "metabolic":  ("Metabolic", ["hydration_ml", "stress_score"], 50, 62),
    "kidney":     ("Renal", ["hydration_ml"], 57, 52),
    "immune":     ("Immune", ["sleep_hours", "spo2"], 50, 78),
    "liver":      ("Hepatic", [], 44, 48),   # needs bloodwork; never guessed
}

SYSTEM_NOTES = {
    "heart": "Scored from your logged resting heart rate and HRV.",
    "brain": "Scored from your logged sleep duration and stress ratings.",
    "metabolic": "Scored from your logged hydration and stress ratings.",
    "kidney": "Scored from your logged hydration.",
    "immune": "Scored from your logged sleep and SpO₂.",
    "liver": "Needs liver-function bloodwork. Add an LFT report to score this system.",
}


def _status(risk):
    if risk >= 55:
        return "warning"
    if risk >= 30:
        return "caution"
    return "normal"


def twin_for(user_id):
    """Digital twin computed from entered readings. None until there are enough."""
    rows = _readings(user_id)
    if len(rows) < MIN_READINGS_FOR_TWIN:
        return {
            "sufficient": False,
            "readingCount": len(rows),
            "readingsNeeded": MIN_READINGS_FOR_TWIN,
            "nodes": [],
            "summary": None,
            "predispositions": [],
        }

    nodes = []
    scored = {}
    for key, (label, fields, x, y) in SYSTEM_INPUTS.items():
        parts = [
            _score_against_band(_field_mean(rows, field), field)
            for field in fields
        ]
        parts = [p for p in parts if p is not None]
        if not parts:
            nodes.append({
                "key": key, "label": label, "riskPct": None, "status": "unmeasured",
                "note": SYSTEM_NOTES[key], "x": x, "y": y, "measured": False,
            })
            continue
        risk = round(mean(parts), 1)
        scored[key] = risk
        nodes.append({
            "key": key, "label": label, "riskPct": risk, "status": _status(risk),
            "note": SYSTEM_NOTES[key], "x": x, "y": y, "measured": True,
        })

    if not scored:
        return {
            "sufficient": False, "readingCount": len(rows),
            "readingsNeeded": MIN_READINGS_FOR_TWIN,
            "nodes": nodes, "summary": None, "predispositions": [],
        }

    overall = mean(scored.values())
    return {
        "sufficient": True,
        "readingCount": len(rows),
        "nodes": nodes,
        "summary": {
            "healthScore": int(round(100 - overall)),
            "measuredSystems": len(scored),
            "totalSystems": len(SYSTEM_INPUTS),
            "basedOnReadings": len(rows),
            "firstReading": rows[0].recorded_on.isoformat(),
            "lastReading": rows[-1].recorded_on.isoformat(),
        },
        "predispositions": predispositions_for(user_id, scored, rows),
    }


def predispositions_for(user_id, scored, rows):
    """Only surfaced for systems that were actually measured, and always with
    the measures they were computed from named."""
    out = []

    if "heart" in scored:
        hr = _field_mean(rows, "heart_rate")
        sleep = _field_mean(rows, "sleep_hours")
        out.append({
            "id": "hypertension",
            "condition": "Elevated blood pressure risk",
            "signalPct": scored["heart"],
            "basedOn": [f"Resting heart rate {hr} bpm", f"Sleep {sleep} h"],
            "lever": "Consistent seven-hour sleep is the largest modifiable input to this score.",
            "caveat": "Derived from resting heart rate and sleep only — not a blood pressure measurement.",
        })

    if "kidney" in scored:
        hydration = _field_mean(rows, "hydration_ml")
        out.append({
            "id": "hydration",
            "condition": "Chronic under-hydration",
            "signalPct": scored["kidney"],
            "basedOn": [f"Hydration {hydration} ml/day across {len(rows)} days"],
            "lever": "Raising daily intake toward 2.5 L moves this more than anything else.",
            "caveat": "Renal function needs creatinine and eGFR to assess properly.",
        })

    if "brain" in scored:
        sleep = _field_mean(rows, "sleep_hours")
        stress = _field_mean(rows, "stress_score")
        out.append({
            "id": "sleep_debt",
            "condition": "Accumulated sleep debt",
            "signalPct": scored["brain"],
            "basedOn": [f"Sleep {sleep} h", f"Stress {stress}/100"],
            "lever": "A fixed wake time does more for this than a fixed bedtime.",
            "caveat": "Self-reported sleep duration, not measured sleep stages.",
        })

    return out


def finding_for(user_id):
    """The dashboard's headline. Points at the worst *measured* system and says
    which readings produced it. None when nothing is measurable yet."""
    twin = twin_for(user_id)
    if not twin["sufficient"]:
        return None

    measured = [n for n in twin["nodes"] if n["measured"]]
    if not measured:
        return None

    worst = max(measured, key=lambda n: n["riskPct"])
    if worst["riskPct"] < 30:
        return {
            "severity": "stable",
            "headline": "Nothing in your readings is *asking for attention*.",
            "leadSystem": worst["label"],
            "riskScore": round(worst["riskPct"] / 10, 1),
            "riskBand": "Stable",
            "reasoning": [
                f"All {len(measured)} measured systems score below the caution threshold.",
                f"Computed from {twin['summary']['basedOnReadings']} readings you logged.",
            ],
            "suggestedNext": ["Keep logging — trends need continuity to stay meaningful."],
            "basedOnReadings": twin["summary"]["basedOnReadings"],
        }

    rows = _readings(user_id)
    fields = SYSTEM_INPUTS[worst["key"]][1]
    reasoning = []
    for field in fields:
        value = _field_mean(rows, field)
        if value is None:
            continue
        low, high, direction = BANDS[field]
        label = field.replace("_", " ")
        reasoning.append(
            f"Your mean {label} is {value} against a reference band of {low}–{high} ({direction})."
        )
    reasoning.append(
        f"Computed from {len(rows)} readings between "
        f"{twin['summary']['firstReading']} and {twin['summary']['lastReading']}."
    )

    return {
        "severity": "critical" if worst["riskPct"] >= 55 else "watch",
        "headline": (
            f"Your *{worst['label'].lower()}* readings are *worth attention*."
            if worst["riskPct"] < 55
            else f"Your *{worst['label'].lower()}* readings need *review*."
        ),
        "leadSystem": worst["label"],
        "riskScore": round(worst["riskPct"] / 10, 1),
        "riskBand": "Elevated" if worst["riskPct"] >= 55 else "Watch",
        "reasoning": reasoning,
        "suggestedNext": [
            "Take these readings to a general physician",
            "Ask about baseline bloodwork",
        ],
        "basedOnReadings": len(rows),
    }


def vitals_summary(user_id, days=30):
    rows = _readings(user_id, days)
    if not rows:
        return {"readings": [], "summary": None, "readingCount": 0}
    return {
        "readings": [r.to_dict() for r in rows],
        "readingCount": len(rows),
        "summary": {
            "heartRate": _field_mean(rows, "heart_rate"),
            "hrv": _field_mean(rows, "hrv_ms"),
            "spo2": _field_mean(rows, "spo2"),
            "sleep": _field_mean(rows, "sleep_hours"),
            "stress": _field_mean(rows, "stress_score"),
            "hydrationMl": _field_mean(rows, "hydration_ml"),
        },
        "sufficientForTrend": len(rows) >= MIN_READINGS_FOR_TREND,
    }
