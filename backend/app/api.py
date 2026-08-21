"""Application API. Every endpoint is user-scoped and JWT-protected.

Grouped by product section rather than split across files — the handlers are
thin reads over the models, and keeping them together makes the surface easy
to audit against the frontend's service layer.
"""

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from .extensions import db
from .models import (
    Appointment,
    Biomarker,
    CareWorker,
    CartItem,
    ConsentScope,
    Conversation,
    Doctor,
    Medicine,
    Message,
    OutbreakSignal,
    Report,
    ReportExtraction,
    User,
    VitalReading,
)
from . import derive
from . import omni as omni_engine
from .report_extraction import extract_report, is_readable_pdf

bp = Blueprint("api", __name__, url_prefix="/api")


def me():
    return get_jwt_identity()


def ok(data, status=200):
    return jsonify({"data": data}), status


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.get("/dashboard")
@jwt_required()
def dashboard():
    user_id = me()
    user = db.session.get(User, user_id)

    latest = (
        db.session.query(VitalReading)
        .filter_by(user_id=user_id)
        .order_by(VitalReading.recorded_on.desc())
        .limit(2)
        .all()
    )
    today, prior = (latest + [None, None])[:2]

    def measure(field, unit):
        if not today or getattr(today, field) is None:
            return None
        delta = None
        if prior is not None and getattr(prior, field) is not None:
            delta = round(getattr(today, field) - getattr(prior, field), 1)
        return {"value": getattr(today, field), "unit": unit, "trend": delta}

    outbreak = db.session.query(OutbreakSignal).filter_by(city="Hyderabad").first()
    twin = derive.twin_for(user_id)
    now = datetime.now(timezone.utc)

    return ok({
        "greeting": {
            "weekday": now.strftime("%A"),
            "region": outbreak.city if outbreak else "India",
            "firstName": user.full_name.split()[0] if user else "",
        },
        # None until the user has logged enough to support a conclusion.
        "finding": derive.finding_for(user_id),
        "hasReadings": today is not None,
        "readingCount": twin["readingCount"],
        "readingsNeeded": derive.MIN_READINGS_FOR_TWIN,
        "lastReadingOn": today.recorded_on.isoformat() if today else None,
        "vitals": {
            "heartRate": measure("heart_rate", "bpm"),
            "hrv": measure("hrv_ms", "ms"),
            "spo2": measure("spo2", "%"),
            "sleep": measure("sleep_hours", "h"),
        },
        "outbreak": outbreak.to_dict() if outbreak else None,
        "twin": twin["summary"],
    })


# ---------------------------------------------------------------------------
# Digital twin
# ---------------------------------------------------------------------------

@bp.get("/twin")
@jwt_required()
def twin():
    return ok(derive.twin_for(me()))


# ---------------------------------------------------------------------------
# Health insights
# ---------------------------------------------------------------------------

@bp.get("/insights")
@jwt_required()
def insights():
    days = min(int(request.args.get("days", 30)), 90)
    payload = derive.vitals_summary(me(), days)
    outbreak = db.session.query(OutbreakSignal).filter_by(city="Hyderabad").first()
    payload["outbreak"] = outbreak.to_dict() if outbreak else None
    payload["minForTrend"] = derive.MIN_READINGS_FOR_TREND
    return ok(payload)


# ---------------------------------------------------------------------------
# Vitals — the only way clinical numbers enter the system
# ---------------------------------------------------------------------------

VITAL_FIELDS = {
    "heartRate":   ("heart_rate", 25, 220, "Resting heart rate"),
    "hrv":         ("hrv_ms", 5, 250, "HRV"),
    "spo2":        ("spo2", 50, 100, "SpO\u2082"),
    "sleepHours":  ("sleep_hours", 0, 24, "Sleep"),
    "stress":      ("stress_score", 0, 100, "Stress"),
    "hydrationMl": ("hydration_ml", 0, 10000, "Hydration"),
}


@bp.get("/vitals")
@jwt_required()
def list_vitals():
    rows = (
        db.session.query(VitalReading)
        .filter_by(user_id=me())
        .order_by(VitalReading.recorded_on.desc())
        .limit(120)
        .all()
    )
    return ok({"readings": [r.to_dict() for r in rows], "fields": [
        {"key": k, "label": label, "min": lo, "max": hi}
        for k, (_col, lo, hi, label) in VITAL_FIELDS.items()
    ]})


@bp.post("/vitals")
@jwt_required()
def log_vitals():
    payload = request.get_json(silent=True) or {}
    errors = {}
    values = {}

    for key, (column, low, high, label) in VITAL_FIELDS.items():
        raw = payload.get(key)
        if raw is None or raw == "":
            continue
        try:
            number = float(raw)
        except (TypeError, ValueError):
            errors[key] = f"{label} must be a number."
            continue
        if not (low <= number <= high):
            errors[key] = f"{label} must be between {low} and {high}."
            continue
        values[column] = number

    if not values and not errors:
        errors["_"] = "Enter at least one reading."
    if errors:
        return jsonify({"message": "Please correct the highlighted fields.",
                        "errors": errors}), 400

    try:
        recorded_on = (
            datetime.fromisoformat(payload["date"]).date()
            if payload.get("date") else date.today()
        )
    except ValueError:
        return jsonify({"message": "That date could not be read.",
                        "errors": {"date": "Use YYYY-MM-DD."}}), 400

    if recorded_on > date.today():
        return jsonify({"message": "You cannot log a reading in the future.",
                        "errors": {"date": "Pick today or an earlier date."}}), 400

    # One row per day: logging the same date again updates it rather than
    # creating a duplicate the averages would double-count.
    row = db.session.query(VitalReading).filter_by(
        user_id=me(), recorded_on=recorded_on
    ).first()
    created = row is None
    if created:
        row = VitalReading(user_id=me(), recorded_on=recorded_on)
        db.session.add(row)

    for column, number in values.items():
        setattr(row, column, number if column == "sleep_hours" else int(number))

    db.session.commit()
    return ok({"reading": row.to_dict(), "created": created}, 201 if created else 200)


@bp.delete("/vitals/<reading_date>")
@jwt_required()
def delete_vitals(reading_date):
    try:
        target = datetime.fromisoformat(reading_date).date()
    except ValueError:
        return jsonify({"message": "Bad date."}), 400
    row = db.session.query(VitalReading).filter_by(user_id=me(), recorded_on=target).first()
    if not row:
        return jsonify({"message": "No reading on that date."}), 404
    db.session.delete(row)
    db.session.commit()
    return ok({"deleted": reading_date})


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------

@bp.get("/doctors")
@jwt_required()
def doctors():
    q = (request.args.get("q") or "").strip().lower()
    specialty = request.args.get("specialty")
    sort = request.args.get("sort", "rating")

    query = db.session.query(Doctor)
    if specialty and specialty != "All":
        query = query.filter(Doctor.specialty == specialty)

    rows = query.all()
    if q:
        rows = [
            d for d in rows
            if q in d.name.lower() or q in d.specialty.lower() or q in d.hospital.lower()
        ]

    key = {
        "rating": lambda d: -d.rating,
        "fee": lambda d: d.fee_inr,
        "distance": lambda d: d.distance_km,
        "experience": lambda d: -d.experience_years,
    }.get(sort, lambda d: -d.rating)
    rows.sort(key=key)

    specialties = sorted({d.specialty for d in db.session.query(Doctor)})
    return ok({"doctors": [d.to_dict() for d in rows], "specialties": ["All"] + specialties})


# ---------------------------------------------------------------------------
# Care services
# ---------------------------------------------------------------------------

CARE_GROUPS = [
    ("nurse", "Nurses"),
    ("asha", "ASHA Workers"),
    ("physiotherapist", "Physiotherapists"),
    ("lab_technician", "Lab Technicians"),
    ("dietician", "Dieticians"),
]


@bp.get("/care-services")
@jwt_required()
def care_services():
    workers = db.session.query(CareWorker).all()
    groups = [
        {
            "key": key,
            "label": label,
            "workers": [w.to_dict() for w in workers if w.worker_type == key],
        }
        for key, label in CARE_GROUPS
    ]
    return ok({
        "groups": groups,
        "homeSampleCollection": {
            "title": "Home sample collection",
            "description": "A trained phlebotomist collects your sample at home and delivers it to a NABL-accredited lab. Reports land in your OmniCare records automatically.",
            "price": 249,
            "eta": "Next available slot: tomorrow, 7:00 AM",
        },
    })


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@bp.get("/appointments")
@jwt_required()
def list_appointments():
    rows = (
        db.session.query(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .filter(Appointment.user_id == me())
        .order_by(Appointment.scheduled_for.desc())
        .all()
    )
    now = datetime.now(timezone.utc)

    def when(appt):
        stamp = appt.scheduled_for
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)

    upcoming = [a.to_dict(d) for a, d in rows if when(a) >= now and a.status != "cancelled"]
    past = [a.to_dict(d) for a, d in rows if when(a) < now or a.status == "cancelled"]
    return ok({"upcoming": upcoming, "past": past})


@bp.post("/appointments")
@jwt_required()
def book_appointment():
    payload = request.get_json(silent=True) or {}
    doctor = db.session.get(Doctor, payload.get("doctorId") or "")
    if not doctor:
        return jsonify({"message": "That doctor is no longer available."}), 404

    mode = payload.get("mode", "in_person")
    if mode == "video" and not doctor.supports_video:
        return jsonify({"message": "This doctor does not offer video consultations."}), 400

    # Offset from the doctor's advertised slot so bookings land at distinct times.
    existing = db.session.query(Appointment).filter_by(user_id=me(), doctor_id=doctor.id).count()
    scheduled = datetime.now(timezone.utc) + timedelta(days=1 + existing, hours=2)

    appt = Appointment(
        user_id=me(),
        doctor_id=doctor.id,
        scheduled_for=scheduled,
        mode=mode,
        location=doctor.hospital,
    )
    db.session.add(appt)
    db.session.commit()
    return ok({"appointment": appt.to_dict(doctor)}, 201)


@bp.post("/appointments/<appointment_id>/cancel")
@jwt_required()
def cancel_appointment(appointment_id):
    appt = db.session.query(Appointment).filter_by(id=appointment_id, user_id=me()).first()
    if not appt:
        return jsonify({"message": "Appointment not found."}), 404
    if appt.status == "cancelled":
        return jsonify({"message": "This appointment is already cancelled."}), 409
    appt.status = "cancelled"
    db.session.commit()
    doctor = db.session.get(Doctor, appt.doctor_id)
    return ok({"appointment": appt.to_dict(doctor)})


@bp.get("/appointments/<appointment_id>/rides")
@jwt_required()
def ride_options(appointment_id):
    appt = db.session.query(Appointment).filter_by(id=appointment_id, user_id=me()).first()
    if not appt:
        return jsonify({"message": "Appointment not found."}), 404
    doctor = db.session.get(Doctor, appt.doctor_id)
    km = doctor.distance_km if doctor else 5.0
    return ok({
        "destination": appt.location,
        "distanceKm": km,
        "options": [
            {"key": "auto", "label": "Auto", "eta": "4 min", "fare": int(28 + km * 11), "seats": 3},
            {"key": "cab", "label": "Cab (AC)", "eta": "7 min", "fare": int(65 + km * 17), "seats": 4},
            {"key": "assisted", "label": "Assisted ride", "eta": "12 min", "fare": int(120 + km * 22),
             "seats": 3, "note": "Wheelchair accessible, attendant included"},
        ],
    })


# ---------------------------------------------------------------------------
# Pharmacy
# ---------------------------------------------------------------------------

@bp.get("/pharmacy/medicines")
@jwt_required()
def medicines():
    q = (request.args.get("q") or "").strip().lower()
    category = request.args.get("category")

    rows = db.session.query(Medicine).all()
    if category and category != "All":
        rows = [m for m in rows if m.category == category]
    if q:
        rows = [m for m in rows if q in m.name.lower() or q in m.generic_salt.lower()]

    categories = sorted({m.category for m in db.session.query(Medicine)})
    return ok({
        "medicines": [m.to_dict() for m in rows],
        "recommended": [m.to_dict() for m in db.session.query(Medicine).filter_by(recommended=True)],
        "categories": ["All"] + categories,
    })


def _cart_payload(user_id):
    rows = (
        db.session.query(CartItem, Medicine)
        .join(Medicine, CartItem.medicine_id == Medicine.id)
        .filter(CartItem.user_id == user_id)
        .all()
    )
    items = [c.to_dict(m) for c, m in rows]
    subtotal = sum(i["lineTotal"] for i in items)
    delivery = 0 if subtotal >= 500 or subtotal == 0 else 40
    return {
        "items": items,
        "count": sum(i["quantity"] for i in items),
        "subtotal": subtotal,
        "delivery": delivery,
        "total": subtotal + delivery,
        "requiresPrescription": any(i["medicine"]["requiresPrescription"] for i in items),
    }


@bp.get("/pharmacy/cart")
@jwt_required()
def get_cart():
    return ok(_cart_payload(me()))


@bp.post("/pharmacy/cart")
@jwt_required()
def add_to_cart():
    payload = request.get_json(silent=True) or {}
    medicine = db.session.get(Medicine, payload.get("medicineId") or "")
    if not medicine:
        return jsonify({"message": "That medicine is unavailable."}), 404

    item = db.session.query(CartItem).filter_by(user_id=me(), medicine_id=medicine.id).first()
    if item:
        item.quantity += int(payload.get("quantity", 1))
    else:
        db.session.add(CartItem(
            user_id=me(), medicine_id=medicine.id, quantity=int(payload.get("quantity", 1))
        ))
    db.session.commit()
    return ok(_cart_payload(me()), 201)


@bp.patch("/pharmacy/cart/<item_id>")
@jwt_required()
def update_cart_item(item_id):
    item = db.session.query(CartItem).filter_by(id=item_id, user_id=me()).first()
    if not item:
        return jsonify({"message": "Item not in cart."}), 404
    quantity = int((request.get_json(silent=True) or {}).get("quantity", 1))
    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return ok(_cart_payload(me()))


@bp.delete("/pharmacy/cart/<item_id>")
@jwt_required()
def remove_cart_item(item_id):
    item = db.session.query(CartItem).filter_by(id=item_id, user_id=me()).first()
    if not item:
        return jsonify({"message": "Item not in cart."}), 404
    db.session.delete(item)
    db.session.commit()
    return ok(_cart_payload(me()))


@bp.post("/pharmacy/checkout")
@jwt_required()
def checkout():
    cart = _cart_payload(me())
    if not cart["items"]:
        return jsonify({"message": "Your cart is empty."}), 400

    payload = request.get_json(silent=True) or {}
    address = (payload.get("address") or "").strip()
    if len(address) < 10:
        return jsonify({
            "message": "Please provide a complete delivery address.",
            "errors": {"address": "Enter a full address including area and pincode."},
        }), 400

    order_id = f"OMC{uuid.uuid4().hex[:8].upper()}"
    db.session.query(CartItem).filter_by(user_id=me()).delete()
    db.session.commit()

    return ok({
        "orderId": order_id,
        "total": cart["total"],
        "itemCount": cart["count"],
        "address": address,
        "eta": "Tomorrow, 9:00 AM",
    }, 201)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

MAX_REPORT_BYTES = 10 * 1024 * 1024
REPORT_TYPE_RULES = {
    ".pdf": {"mime": {"application/pdf"}},
    ".txt": {"mime": {"text/plain"}},
    ".png": {"mime": {"image/png"}},
    ".jpg": {"mime": {"image/jpeg"}},
    ".jpeg": {"mime": {"image/jpeg"}},
    ".webp": {"mime": {"image/webp"}},
}

# Reference ranges used to flag extracted values. Real vision extraction is a
# later phase (SRS FR-8.2); this reads what is actually in the uploaded file
# and flags against these ranges rather than inventing values.
BIOMARKER_RANGES = [
    ("Haemoglobin", "g/dL", 13.0, 17.0),
    ("Fasting glucose", "mg/dL", 70.0, 100.0),
    ("Total cholesterol", "mg/dL", 125.0, 200.0),
    ("HDL", "mg/dL", 40.0, 60.0),
    ("Triglycerides", "mg/dL", 0.0, 150.0),
    ("Serum creatinine", "mg/dL", 0.7, 1.3),
    ("Vitamin D", "ng/mL", 30.0, 100.0),
    ("TSH", "mIU/L", 0.4, 4.0),
]


def _extract_biomarkers(report, text_content):
    """Read biomarker values *out of the uploaded file*.

    Only parses values it can actually find. There is no fallback that
    generates a plausible number — an unparseable file yields zero biomarkers
    and the user is asked to enter them by hand. A fabricated lab value is
    indistinguishable from a measured one once it is in the table, which is
    exactly why it must never be written.
    """
    import re

    if not text_content:
        return []

    created = []
    for label, unit, low, high in BIOMARKER_RANGES:
        match = re.search(
            rf"{re.escape(label)}\s*[:=]?\s*([0-9]+\.?[0-9]*)", text_content, re.I
        )
        if not match:
            continue
        value = float(match.group(1))
        flag = "normal" if low <= value <= high else ("high" if value > high else "low")
        marker = Biomarker(
            report_id=report.id, label=label, value=value, unit=unit,
            reference_range=f"{low}\u2013{high}", flag=flag, source="extracted",
        )
        db.session.add(marker)
        created.append(marker)
    return created


def _validate_report_upload(uploaded, blob):
    """Validate extension, browser MIME claim, and binary signature together."""
    filename = secure_filename(uploaded.filename or "")
    extension = Path(filename).suffix.lower()
    rule = REPORT_TYPE_RULES.get(extension)
    if not filename or not rule:
        return None, "Upload a PDF, PNG, JPEG, WEBP, or text report."
    if uploaded.mimetype not in rule["mime"]:
        return None, "The file type does not match its extension."

    if extension == ".pdf" and not blob.startswith(b"%PDF-"):
        return None, "This file is not a valid PDF."
    if extension == ".pdf" and not is_readable_pdf(blob):
        return None, "This file is not a readable PDF."
    if extension == ".png" and not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, "This file is not a valid PNG."
    if extension in {".jpg", ".jpeg"} and not blob.startswith(b"\xff\xd8\xff"):
        return None, "This file is not a valid JPEG."
    if extension == ".webp" and not (blob.startswith(b"RIFF") and blob[8:12] == b"WEBP"):
        return None, "This file is not a valid WEBP image."
    return filename, None


@bp.post("/reports/<report_id>/biomarkers")
@jwt_required()
def add_biomarker(report_id):
    """Manual entry, for the reports we could not parse."""
    report = db.session.query(Report).filter_by(id=report_id, user_id=me()).first()
    if not report:
        return jsonify({"message": "Report not found."}), 404

    payload = request.get_json(silent=True) or {}
    label = (payload.get("label") or "").strip()
    known = {name: (unit, lo, hi) for name, unit, lo, hi in BIOMARKER_RANGES}
    if label not in known:
        return jsonify({
            "message": "Choose a marker from the list.",
            "errors": {"label": "Unknown marker."},
        }), 400

    try:
        value = float(payload.get("value"))
    except (TypeError, ValueError):
        return jsonify({"message": "Enter a numeric value.",
                        "errors": {"value": "Must be a number."}}), 400

    unit, low, high = known[label]
    flag = "normal" if low <= value <= high else ("high" if value > high else "low")

    existing = db.session.query(Biomarker).filter_by(report_id=report.id, label=label).first()
    if existing:
        existing.value, existing.flag, existing.source = value, flag, "manual"
        marker = existing
    else:
        marker = Biomarker(
            report_id=report.id, label=label, value=value, unit=unit,
            reference_range=f"{low}\u2013{high}", flag=flag, source="manual",
        )
        db.session.add(marker)

    db.session.flush()
    markers = db.session.query(Biomarker).filter_by(report_id=report.id).all()
    report.observation = _observation_for(markers)
    db.session.commit()
    return ok({"report": report.to_dict(markers)}, 201)


def _observation_for(markers):
    if not markers:
        return ""
    abnormal = [m for m in markers if m.flag != "normal"]
    if abnormal:
        names = ", ".join(m.label.lower() for m in abnormal[:3])
        return (
            f"{len(abnormal)} of {len(markers)} recorded markers sit outside the reference "
            f"range \u2014 {names}. Worth raising at your next consultation."
        )
    return f"All {len(markers)} recorded markers fall within their reference ranges."


@bp.get("/reports")
@jwt_required()
def list_reports():
    rows = (
        db.session.query(Report)
        .filter_by(user_id=me())
        .order_by(Report.uploaded_at.desc())
        .all()
    )
    payload = []
    for report in rows:
        markers = db.session.query(Biomarker).filter_by(report_id=report.id).all()
        extraction = db.session.query(ReportExtraction).filter_by(report_id=report.id).first()
        payload.append(report.to_dict(markers, extraction))
    return ok({"reports": payload})


@bp.post("/reports")
@jwt_required()
def upload_report():
    scope = db.session.query(ConsentScope).filter_by(user_id=me(), key="reports_vision").first()
    if scope and not scope.granted:
        return jsonify({
            "message": "Report analysis is switched off in your consent settings.",
            "code": "consent_required",
        }), 403

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"message": "Choose a file to upload."}), 400

    blob = uploaded.read(MAX_REPORT_BYTES + 1)
    if len(blob) > MAX_REPORT_BYTES:
        return jsonify({"message": "Reports must be under 10 MB."}), 413
    filename, error = _validate_report_upload(uploaded, blob)
    if error:
        return jsonify({"message": error}), 415

    from .config import BASE_DIR
    store = BASE_DIR / "instance" / "reports" / me()
    os.makedirs(store, exist_ok=True)
    path = store / f"{uuid.uuid4().hex}_{filename}"
    path.write_bytes(blob)

    report = Report(
        user_id=me(), filename=filename, content_type=uploaded.mimetype,
        size_bytes=len(blob), stored_path=str(path),
    )
    db.session.add(report)
    db.session.flush()

    extraction = extract_report(report, blob)
    markers = []
    if extraction.status == "completed":
        markers = _extract_biomarkers(report, extraction.extracted_text)
        report.observation = _observation_for(markers)

    db.session.commit()
    return ok({"report": report.to_dict(markers, extraction)}, 201)


@bp.get("/reports/<report_id>/extraction")
@jwt_required()
def get_report_extraction(report_id):
    report = db.session.query(Report).filter_by(id=report_id, user_id=me()).first()
    if not report:
        return jsonify({"message": "Report not found."}), 404
    extraction = db.session.query(ReportExtraction).filter_by(report_id=report.id).first()
    if not extraction:
        return jsonify({"message": "No extraction record exists for this report."}), 404
    return ok({"reportId": report.id, "filename": report.filename,
               "extraction": extraction.to_dict(include_pages=True)})


@bp.delete("/reports/<report_id>")
@jwt_required()
def delete_report(report_id):
    report = db.session.query(Report).filter_by(id=report_id, user_id=me()).first()
    if not report:
        return jsonify({"message": "Report not found."}), 404
    try:
        os.remove(report.stored_path)
    except OSError:
        pass  # File already gone; the row is what matters.
    db.session.delete(report)
    db.session.commit()
    return ok({"deleted": report_id})


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

@bp.get("/consent")
@jwt_required()
def get_consent():
    scopes = db.session.query(ConsentScope).filter_by(user_id=me()).all()
    return ok({
        "scopes": [s.to_dict() for s in scopes],
        "grantedCount": sum(1 for s in scopes if s.granted),
        "totalCount": len(scopes),
    })


@bp.patch("/consent/<scope_key>")
@jwt_required()
def update_consent(scope_key):
    scope = db.session.query(ConsentScope).filter_by(user_id=me(), key=scope_key).first()
    if not scope:
        return jsonify({"message": "Unknown consent scope."}), 404

    granted = (request.get_json(silent=True) or {}).get("granted")
    if not isinstance(granted, bool):
        return jsonify({"message": "granted must be true or false."}), 400

    scope.granted = granted
    scope.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    scopes = db.session.query(ConsentScope).filter_by(user_id=me()).all()
    return ok({
        "scopes": [s.to_dict() for s in scopes],
        "grantedCount": sum(1 for s in scopes if s.granted),
        "totalCount": len(scopes),
    })


# ---------------------------------------------------------------------------
# Ask Omni
# ---------------------------------------------------------------------------

@bp.get("/omni/conversations")
@jwt_required()
def list_conversations():
    rows = (
        db.session.query(Conversation)
        .filter_by(user_id=me())
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    scopes = db.session.query(ConsentScope).filter_by(user_id=me()).all()
    return ok({
        "conversations": [c.to_dict() for c in rows],
        "access": {
            "canRead": [s.title for s in scopes if s.granted],
            "cannotRead": [s.title for s in scopes if not s.granted],
        },
        "engine": omni_engine.engine_name(),
    })


@bp.post("/omni/conversations")
@jwt_required()
def create_conversation():
    convo = Conversation(user_id=me())
    db.session.add(convo)
    db.session.commit()
    return ok({"conversation": convo.to_dict()}, 201)


@bp.get("/omni/conversations/<conversation_id>")
@jwt_required()
def get_conversation(conversation_id):
    convo = db.session.query(Conversation).filter_by(id=conversation_id, user_id=me()).first()
    if not convo:
        return jsonify({"message": "Conversation not found."}), 404
    messages = (
        db.session.query(Message)
        .filter_by(conversation_id=convo.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ok({"conversation": convo.to_dict(), "messages": [m.to_dict() for m in messages]})


@bp.post("/omni/conversations/<conversation_id>/messages")
@jwt_required()
def send_message(conversation_id):
    convo = db.session.query(Conversation).filter_by(id=conversation_id, user_id=me()).first()
    if not convo:
        return jsonify({"message": "Conversation not found."}), 404

    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if not body:
        return jsonify({"message": "Type a question first."}), 400
    if len(body) > 4000:
        return jsonify({"message": "That message is too long."}), 400

    history = [
        m.to_dict()
        for m in db.session.query(Message)
        .filter_by(conversation_id=convo.id)
        .order_by(Message.created_at.asc())
    ]

    user_message = Message(conversation_id=convo.id, role="user", body=body)
    db.session.add(user_message)

    context = omni_engine.gather_context(me())
    reply_body, blocks = omni_engine.respond(body, context, history)

    omni_message = Message(
        conversation_id=convo.id, role="omni", body=reply_body,
        blocks_json=json.dumps(blocks),
    )
    db.session.add(omni_message)

    if convo.title == "New conversation":
        convo.title = body[:60] + ("…" if len(body) > 60 else "")
    convo.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return ok({"messages": [user_message.to_dict(), omni_message.to_dict()]}, 201)


@bp.delete("/omni/conversations/<conversation_id>")
@jwt_required()
def delete_conversation(conversation_id):
    convo = db.session.query(Conversation).filter_by(id=conversation_id, user_id=me()).first()
    if not convo:
        return jsonify({"message": "Conversation not found."}), 404
    db.session.delete(convo)
    db.session.commit()
    return ok({"deleted": conversation_id})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@bp.patch("/profile")
@jwt_required()
def update_profile():
    user = db.session.get(User, me())
    if not user:
        return jsonify({"message": "Account not found."}), 404

    payload = request.get_json(silent=True) or {}
    errors = {}

    if "fullName" in payload:
        name = (payload.get("fullName") or "").strip()
        if len(name) < 2:
            errors["fullName"] = "Name must be at least 2 characters."
        else:
            user.full_name = name

    if "phone" in payload:
        phone = (payload.get("phone") or "").strip()
        if phone:
            digits = phone.lstrip("+").replace(" ", "").replace("-", "")
            if not digits.isdigit() or not (7 <= len(digits) <= 15):
                errors["phone"] = "Please enter a valid phone number."
            else:
                user.phone = phone
        else:
            user.phone = None

    if errors:
        db.session.rollback()
        return jsonify({"message": "Please correct the highlighted fields.", "errors": errors}), 400

    db.session.commit()
    return ok({"user": user.to_dict()})
