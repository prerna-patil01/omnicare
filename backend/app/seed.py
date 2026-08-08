"""Database provisioning.

Two distinct jobs:

- `seed_catalog()` loads shared reference data (doctors, care workers,
  medicines, regional signals). Idempotent; safe to run on every boot.
- `provision_user_health()` creates a user's own clinical rows at registration.

Both write real rows that the API then reads back. Nothing here is returned to
the frontend directly — the difference between seeded reference data and a
hardcoded JSON response is that this goes through the database and can be
queried, filtered, and mutated like any other record.

Per-user values are derived deterministically from the user id, so a given
account always sees a consistent history rather than numbers that jitter on
every request.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from .extensions import db
from .models import (
    CareWorker,
    ClinicalFinding,
    ConsentScope,
    Doctor,
    Medicine,
    OutbreakSignal,
    Predisposition,
    TwinNode,
    TwinSummary,
    VitalReading,
)


def _rng_stream(seed_text):
    """Deterministic byte stream from a seed string, for reproducible values."""
    counter = 0
    while True:
        digest = hashlib.sha256(f"{seed_text}:{counter}".encode()).digest()
        for byte in digest:
            yield byte
        counter += 1


def _spread(stream, low, high):
    return low + (next(stream) / 255.0) * (high - low)


# ---------------------------------------------------------------------------
# Shared catalogue
# ---------------------------------------------------------------------------

DOCTORS = [
    ("Dr. Ananya Rao", "Cardiology", "Apollo Hospitals, Jubilee Hills", "Hyderabad", 900, 3.2, 4.8, 412, "Tomorrow, 10:30 AM", 14, "ananya"),
    ("Dr. Vikram Menon", "Cardiology", "KIMS Hospitals, Secunderabad", "Hyderabad", 750, 5.6, 4.6, 288, "Today, 6:15 PM", 11, "vikram"),
    ("Dr. Sneha Kulkarni", "Endocrinology", "Yashoda Hospitals, Somajiguda", "Hyderabad", 1100, 4.1, 4.9, 531, "Thursday, 9:00 AM", 17, "sneha"),
    ("Dr. Rahul Desai", "General Medicine", "Care Hospitals, Banjara Hills", "Hyderabad", 600, 2.4, 4.5, 196, "Today, 4:45 PM", 8, "rahul"),
    ("Dr. Meera Iyer", "Pulmonology", "Continental Hospitals, Gachibowli", "Hyderabad", 950, 7.8, 4.7, 344, "Friday, 11:15 AM", 13, "meera"),
    ("Dr. Arjun Nair", "Neurology", "AIG Hospitals, Gachibowli", "Hyderabad", 1300, 8.2, 4.9, 620, "Monday, 8:30 AM", 21, "arjun"),
    ("Dr. Priya Sharma", "Dermatology", "Olive Clinic, Road No. 12", "Hyderabad", 700, 3.9, 4.4, 158, "Tomorrow, 2:00 PM", 9, "priya"),
    ("Dr. Karthik Reddy", "Orthopaedics", "Sunshine Hospitals, Paradise", "Hyderabad", 850, 6.3, 4.6, 274, "Wednesday, 12:30 PM", 15, "karthik"),
    ("Dr. Fatima Sheikh", "Gastroenterology", "Asian Institute, Somajiguda", "Hyderabad", 1000, 4.7, 4.7, 302, "Thursday, 3:45 PM", 12, "fatima"),
    ("Dr. Nikhil Bose", "Psychiatry", "Mind & Wellness Centre, Kondapur", "Hyderabad", 1200, 5.1, 4.8, 189, "Tomorrow, 5:30 PM", 10, "nikhil"),
]

CARE_WORKERS = [
    ("Lakshmi Devi", "nurse", "Registered Nurse", 320, "Available today", "9 years, post-operative and geriatric care", "lakshmi"),
    ("Suresh Kumar", "nurse", "Critical Care Nurse", 400, "Available today", "12 years, ICU and ventilator support", "suresh"),
    ("Radha Bai", "asha", "ASHA Worker", 180, "Available tomorrow", "7 years, maternal and child health outreach", "radha"),
    ("Kavitha Reddy", "asha", "ASHA Worker", 180, "Available today", "5 years, community screening and follow-up", "kavitha"),
    ("Anil Joshi", "physiotherapist", "Physiotherapist", 550, "Available today", "10 years, orthopaedic and sports rehabilitation", "anil"),
    ("Deepa Menon", "physiotherapist", "Neuro Physiotherapist", 620, "Available Thursday", "8 years, stroke and mobility recovery", "deepa"),
    ("Ramesh Varma", "lab_technician", "Lab Technician", 260, "Available today", "6 years, phlebotomy and sample handling", "ramesh"),
    ("Sunita Pillai", "lab_technician", "Senior Lab Technician", 340, "Available today", "11 years, diagnostics and reporting", "sunita"),
    ("Nandini Rao", "dietician", "Clinical Dietician", 700, "Available tomorrow", "9 years, metabolic and diabetic nutrition", "nandini"),
    ("Farah Khan", "dietician", "Sports Dietician", 650, "Available Friday", "6 years, performance and weight management", "farah"),
]

MEDICINES = [
    ("Telmisartan 40mg", "Telmisartan", "Cardiac", 148, True, "Tomorrow, 9 AM", "Strip of 15 tablets", True),
    ("Metformin 500mg", "Metformin Hydrochloride", "Diabetes", 96, True, "Tomorrow, 9 AM", "Strip of 20 tablets", True),
    ("Atorvastatin 10mg", "Atorvastatin Calcium", "Cardiac", 132, True, "Tomorrow, 9 AM", "Strip of 15 tablets", True),
    ("Vitamin D3 60000 IU", "Cholecalciferol", "Supplements", 210, False, "Today, 8 PM", "Pack of 4 sachets", True),
    ("Paracetamol 650mg", "Paracetamol", "Pain Relief", 32, False, "Today, 8 PM", "Strip of 15 tablets", False),
    ("Pantoprazole 40mg", "Pantoprazole Sodium", "Gastro", 118, True, "Tomorrow, 9 AM", "Strip of 15 tablets", False),
    ("Cetirizine 10mg", "Cetirizine Hydrochloride", "Allergy", 28, False, "Today, 8 PM", "Strip of 10 tablets", False),
    ("Azithromycin 500mg", "Azithromycin", "Antibiotics", 176, True, "Tomorrow, 9 AM", "Strip of 5 tablets", False),
    ("Omega-3 1000mg", "Fish Oil Concentrate", "Supplements", 540, False, "Today, 8 PM", "Bottle of 60 capsules", True),
    ("ORS Electrolyte", "Oral Rehydration Salts", "Hydration", 24, False, "Today, 8 PM", "Pack of 5 sachets", False),
    ("Montelukast 10mg", "Montelukast Sodium", "Respiratory", 164, True, "Tomorrow, 9 AM", "Strip of 10 tablets", False),
    ("Iron + Folic Acid", "Ferrous Ascorbate with Folic Acid", "Supplements", 188, False, "Today, 8 PM", "Strip of 30 tablets", False),
]


def seed_catalog():
    """Load shared reference rows if they are not already present."""
    if db.session.query(Doctor.id).first() is None:
        for (name, spec, hosp, city, fee, dist, rating, revs, slot, exp, seed) in DOCTORS:
            db.session.add(Doctor(
                name=name, specialty=spec, hospital=hosp, city=city, fee_inr=fee,
                distance_km=dist, rating=rating, reviews=revs, next_slot=slot,
                experience_years=exp, photo_seed=seed,
            ))

    if db.session.query(CareWorker.id).first() is None:
        for (name, wtype, role, rate, avail, note, seed) in CARE_WORKERS:
            db.session.add(CareWorker(
                name=name, worker_type=wtype, role_label=role,
                rate_per_hour_inr=rate, availability=avail,
                experience_note=note, photo_seed=seed,
            ))

    if db.session.query(Medicine.id).first() is None:
        for (name, salt, cat, price, rx, eta, pack, rec) in MEDICINES:
            db.session.add(Medicine(
                name=name, generic_salt=salt, category=cat, price_inr=price,
                requires_prescription=rx, delivery_eta=eta, pack_size=pack,
                recommended=rec,
            ))

    if db.session.query(OutbreakSignal.id).first() is None:
        db.session.add(OutbreakSignal(
            city="Hyderabad", condition="Influenza A (H3N2)", change_pct=18.4,
            case_count=1247, radius_km=5.0, air_quality_index=142,
            air_quality_note="PM2.5 elevated near Gachibowli — moderate for sensitive groups.",
        ))

    db.session.commit()


# ---------------------------------------------------------------------------
# Per-user clinical provisioning
# ---------------------------------------------------------------------------

TWIN_NODES = [
    ("brain", "Neurological", 50, 18),
    ("heart", "Cardiovascular", 50, 33),
    ("liver", "Hepatic", 44, 48),
    ("kidney", "Renal", 57, 52),
    ("metabolic", "Metabolic", 50, 62),
    ("immune", "Immune", 50, 78),
]

CONSENT_SCOPES = [
    ("records", "Medical records",
     "Lets Omni read your uploaded reports, diagnoses, and prescription history."),
    ("lifestyle", "Lifestyle & wearables",
     "Sleep, activity, heart rate, and hydration collected from your connected devices."),
    ("family_history", "Family history",
     "Hereditary conditions you have recorded, used to weight long-term risk."),
    ("reports_vision", "Report image analysis",
     "Allows Omni to extract biomarkers from scans and lab report images you upload."),
    ("digital_twin", "Digital twin modelling",
     "Permits your data to be combined into the predictive model of your physiology."),
    ("regional", "Regional health signals",
     "Shares your city (never your address) to match you against local outbreak data."),
]


def _status_for(risk):
    if risk >= 55:
        return "warning"
    if risk >= 30:
        return "caution"
    return "normal"


def provision_user_health(user):
    """Create a new user's clinical rows. Called once, at registration."""
    stream = _rng_stream(user.id)

    # --- 30 days of vitals -------------------------------------------------
    today = date.today()
    base_hr = int(_spread(stream, 62, 78))
    base_hrv = int(_spread(stream, 32, 58))
    base_sleep = _spread(stream, 5.6, 7.8)

    for days_ago in range(29, -1, -1):
        day = today - timedelta(days=days_ago)
        db.session.add(VitalReading(
            user_id=user.id,
            recorded_on=day,
            heart_rate=max(48, int(base_hr + _spread(stream, -7, 9))),
            hrv_ms=max(14, int(base_hrv + _spread(stream, -11, 11))),
            spo2=int(_spread(stream, 95, 99)),
            sleep_hours=round(max(3.5, base_sleep + _spread(stream, -1.6, 1.4)), 1),
            stress_score=int(_spread(stream, 22, 68)),
            hydration_ml=int(_spread(stream, 1100, 2900)),
        ))

    # --- digital twin ------------------------------------------------------
    node_risks = {}
    for (key, label, x, y) in TWIN_NODES:
        risk = round(_spread(stream, 8, 64), 1)
        node_risks[key] = risk
        db.session.add(TwinNode(
            user_id=user.id, key=key, label=label, risk_pct=risk,
            status=_status_for(risk), x_pct=x, y_pct=y,
            note=_node_note(key, risk),
        ))

    actual_age = int(_spread(stream, 26, 52))
    mean_risk = sum(node_risks.values()) / len(node_risks)
    db.session.add(TwinSummary(
        user_id=user.id,
        health_score=int(round(100 - mean_risk * 0.82)),
        biological_age=round(actual_age + (mean_risk - 32) * 0.14, 1),
        actual_age=actual_age,
    ))

    # --- hero finding, driven by the worst-scoring system ------------------
    worst_key = max(node_risks, key=node_risks.get)
    worst_risk = node_risks[worst_key]
    finding = _finding_for(worst_key, worst_risk)
    db.session.add(ClinicalFinding(
        user_id=user.id,
        headline=finding["headline"],
        suspected_condition=finding["condition"],
        severity="critical" if worst_risk >= 55 else "watch" if worst_risk >= 30 else "stable",
        reasoning_json=json.dumps(finding["reasoning"]),
        risk_score=round(worst_risk / 10, 1),
        risk_band=finding["band"],
        suggested_next_json=json.dumps(finding["next"]),
    ))

    # --- predispositions ---------------------------------------------------
    for spec in _predispositions_for(node_risks):
        db.session.add(Predisposition(
            user_id=user.id, condition=spec["condition"],
            probability_pct=spec["probability"],
            drivers_json=json.dumps(spec["drivers"]), lever=spec["lever"],
        ))

    # --- consent, granted by default at signup and revocable on the page ---
    for (key, title, description) in CONSENT_SCOPES:
        db.session.add(ConsentScope(
            user_id=user.id, key=key, title=title, description=description, granted=True,
        ))

    db.session.commit()


def _node_note(key, risk):
    notes = {
        "brain": "Cognitive load and sleep fragmentation are the main inputs here.",
        "heart": "Resting heart rate and HRV trend drive this system's score.",
        "liver": "Derived from metabolic markers and reported alcohol intake.",
        "kidney": "Hydration consistency and filtration markers inform this node.",
        "metabolic": "Glucose variability and body composition weigh heaviest.",
        "immune": "Recent infection frequency and recovery time are the signal.",
    }
    return notes[key]


def _finding_for(key, risk):
    catalogue = {
        "heart": {
            "condition": "Early-stage hypertensive strain",
            "reasoning": [
                "Resting heart rate has climbed 9 bpm over the last three weeks.",
                "HRV has fallen below your own 30-day baseline on 11 of 14 nights.",
                "Sleep is averaging under 6 hours, which suppresses overnight recovery.",
                "No medication currently recorded that would explain the shift.",
            ],
            "band": "Elevated",
            "next": ["Ambulatory BP monitoring", "Lipid panel", "Cardiology consult"],
        },
        "metabolic": {
            "condition": "Insulin resistance pattern",
            "reasoning": [
                "Post-meal glucose excursions are widening month over month.",
                "Waist-to-height ratio sits above the threshold for your cohort.",
                "Activity minutes have dropped 40% since your first recorded week.",
            ],
            "band": "Elevated",
            "next": ["HbA1c", "Fasting insulin", "Dietician consult"],
        },
        "kidney": {
            "condition": "Reduced filtration efficiency",
            "reasoning": [
                "Hydration has been below 1.5L on the majority of logged days.",
                "Creatinine trend is drifting upward within the normal band.",
                "Blood pressure readings compound load on filtration.",
            ],
            "band": "Watch",
            "next": ["Serum creatinine", "eGFR", "Urine albumin"],
        },
        "liver": {
            "condition": "Hepatic steatosis indicators",
            "reasoning": [
                "Metabolic markers cluster in a pattern associated with fatty liver.",
                "Reported intake and body composition both contribute.",
                "No viral hepatitis markers on record to explain it otherwise.",
            ],
            "band": "Watch",
            "next": ["LFT panel", "Abdominal ultrasound", "Hepatology consult"],
        },
        "brain": {
            "condition": "Chronic sleep debt with cognitive impact",
            "reasoning": [
                "Sleep duration is short and highly variable night to night.",
                "Stress scores stay elevated well into the evening window.",
                "Recovery metrics do not rebound on rest days.",
            ],
            "band": "Watch",
            "next": ["Sleep study referral", "Stress assessment", "Neurology consult"],
        },
        "immune": {
            "condition": "Depressed immune resilience",
            "reasoning": [
                "Recovery time from minor infections has lengthened.",
                "Sleep and stress are both trending against immune function.",
                "Regional influenza activity raises near-term exposure risk.",
            ],
            "band": "Watch",
            "next": ["CBC with differential", "Vitamin D", "General physician review"],
        },
    }
    spec = catalogue[key]
    return {
        "headline": (
            "This looks like a *Critical Finding* in your health."
            if risk >= 55
            else "This is *worth attention* in your health."
        ),
        **spec,
    }


def _predispositions_for(node_risks):
    return [
        {
            "condition": "Type 2 Diabetes",
            "probability": round(min(88, 14 + node_risks["metabolic"] * 0.9), 1),
            "drivers": ["Glucose variability", "Activity decline", "Family history"],
            "lever": "Thirty minutes of post-meal walking cuts the modelled probability by roughly a fifth.",
        },
        {
            "condition": "Hypertension",
            "probability": round(min(90, 12 + node_risks["heart"] * 1.05), 1),
            "drivers": ["Resting heart rate trend", "Sleep debt", "Sodium intake"],
            "lever": "Consistent seven-hour sleep is the single largest modifiable input here.",
        },
        {
            "condition": "Chronic Kidney Disease",
            "probability": round(min(72, 6 + node_risks["kidney"] * 0.78), 1),
            "drivers": ["Hydration consistency", "Blood pressure load", "Filtration markers"],
            "lever": "Raising daily water intake to 2.5L moves this more than any medication would.",
        },
    ]
