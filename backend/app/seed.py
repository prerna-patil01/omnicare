"""Database provisioning.

Two distinct jobs:

- `seed_catalog()` loads shared reference data (doctors, care workers,
  medicines, regional signals). Idempotent; safe to run on every boot.
- `provision_consent()` creates a user's consent scopes at registration.

No clinical values are generated here, ever. A user's vitals, twin scores, and
findings come only from readings they entered themselves (see `derive.py`).
Fabricating a physiological measurement and storing it in the database does not
make it real — it makes it indistinguishable from a real one downstream, which
is worse than having none.

The catalogue below is the one seeded set: a marketplace needs listings before
a partner integration exists. It is reference data about providers, not claims
about any user's body.
"""

from datetime import date, datetime, timedelta, timezone

from .extensions import db
from .models import CareWorker, ConsentScope, Doctor, Medicine, OutbreakSignal


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
# Per-user provisioning — consent only
# ---------------------------------------------------------------------------

CONSENT_SCOPES = [
    ("records", "Medical records",
     "Lets Omni read reports and biomarkers you have added."),
    ("lifestyle", "Lifestyle & vitals",
     "Sleep, heart rate, hydration, and stress readings you log yourself."),
    ("family_history", "Family history",
     "Hereditary conditions you record, used to weight long-term risk."),
    ("reports_vision", "Report analysis",
     "Allows Omni to read biomarker values off reports you upload."),
    ("digital_twin", "Digital twin modelling",
     "Permits your entered readings to be combined into a model of your physiology."),
    ("regional", "Regional health signals",
     "Shares your city (never your address) to match you against local outbreak data."),
]


def provision_consent(user):
    """Create the user's consent scopes. This is the only thing registration
    writes on their behalf — no clinical data is created for a new account."""
    for key, title, description in CONSENT_SCOPES:
        db.session.add(ConsentScope(
            user_id=user.id, key=key, title=title, description=description, granted=True,
        ))
    db.session.commit()
