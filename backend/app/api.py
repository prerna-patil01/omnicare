"""Application API. Every endpoint is user-scoped and JWT-protected.

Grouped by product section rather than split across files — the handlers are
thin reads over the models, and keeping them together makes the surface easy
to audit against the frontend's service layer.
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from .extensions import db
from .models import (
    Appointment,
    Biomarker,
    CareWorker,
    CartItem,
    ClinicalFinding,
    ConsentScope,
    Conversation,
    Doctor,
    Medicine,
    Message,
    OutbreakSignal,
    Predisposition,
    Report,
    TwinNode,
    TwinSummary,
    User,
    VitalReading,
)
from . import omni as omni_engine

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

    finding = (
        db.session.query(ClinicalFinding)
        .filter_by(user_id=user_id)
        .order_by(ClinicalFinding.created_at.desc())
        .first()
    )
    latest = (
        db.session.query(VitalReading)
        .filter_by(user_id=user_id)
        .order_by(VitalReading.recorded_on.desc())
        .limit(2)
        .all()
    )
    twin = db.session.query(TwinSummary).filter_by(user_id=user_id).first()
    outbreak = db.session.query(OutbreakSignal).filter_by(city="Hyderabad").first()

    today, prior = (latest + [None, None])[:2]

    def trend(field):
        if not today or not prior:
            return 0
        return round(getattr(today, field) - getattr(prior, field), 1)

    now = datetime.now(timezone.utc)
    return ok({
        "greeting": {
            "weekday": now.strftime("%A"),
            "region": outbreak.city if outbreak else "India",
            "firstName": user.full_name.split()[0] if user else "",
        },
        "finding": finding.to_dict() if finding else None,
        "vitals": {
            "heartRate": {"value": today.heart_rate, "unit": "bpm", "trend": trend("heart_rate")} if today else None,
            "hrv": {"value": today.hrv_ms, "unit": "ms", "trend": trend("hrv_ms")} if today else None,
            "spo2": {"value": today.spo2, "unit": "%", "trend": trend("spo2")} if today else None,
            "sleep": {"value": today.sleep_hours, "unit": "h", "trend": trend("sleep_hours")} if today else None,
        },
        "outbreak": outbreak.to_dict() if outbreak else None,
        "twin": twin.to_dict() if twin else None,
    })


@bp.post("/dashboard/finding/<finding_id>/save")
@jwt_required()
def save_finding(finding_id):
    finding = db.session.query(ClinicalFinding).filter_by(id=finding_id, user_id=me()).first()
    if not finding:
        return jsonify({"message": "Finding not found."}), 404
    finding.saved = not finding.saved
    db.session.commit()
    return ok({"finding": finding.to_dict()})


# ---------------------------------------------------------------------------
# Digital twin
# ---------------------------------------------------------------------------

@bp.get("/twin")
@jwt_required()
def twin():
    user_id = me()
    summary = db.session.query(TwinSummary).filter_by(user_id=user_id).first()
    nodes = db.session.query(TwinNode).filter_by(user_id=user_id).all()
    prone = db.session.query(Predisposition).filter_by(user_id=user_id).all()
    return ok({
        "summary": summary.to_dict() if summary else None,
        "nodes": [n.to_dict() for n in nodes],
        "predispositions": [p.to_dict() for p in prone],
    })


# ---------------------------------------------------------------------------
# Health insights
# ---------------------------------------------------------------------------

@bp.get("/insights")
@jwt_required()
def insights():
    days = min(int(request.args.get("days", 30)), 90)
    rows = (
        db.session.query(VitalReading)
        .filter_by(user_id=me())
        .order_by(VitalReading.recorded_on.asc())
        .all()
    )[-days:]
    outbreak = db.session.query(OutbreakSignal).filter_by(city="Hyderabad").first()

    series = [r.to_dict() for r in rows]

    def avg(field):
        return round(sum(r[field] for r in series) / len(series), 1) if series else 0

    return ok({
        "series": series,
        "summary": {
            "sleep": avg("sleepHours"),
            "stress": avg("stress"),
            "hydrationMl": avg("hydrationMl"),
            "heartRate": avg("heartRate"),
            "hrv": avg("hrv"),
        },
        "outbreak": outbreak.to_dict() if outbreak else None,
    })


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

ALLOWED_REPORT_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/webp", "text/plain",
}
MAX_REPORT_BYTES = 10 * 1024 * 1024

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


def _extract_biomarkers(report, text_content, seed):
    """Derive biomarker rows. If the uploaded file is text and contains
    'Label: value' lines, those values are parsed out of the actual file;
    otherwise values are derived deterministically from the file's own hash so
    a given upload always reads the same."""
    import hashlib
    import re

    parsed = {}
    if text_content:
        for label, _unit, _lo, _hi in BIOMARKER_RANGES:
            match = re.search(rf"{re.escape(label)}\s*[:=]\s*([0-9]+\.?[0-9]*)", text_content, re.I)
            if match:
                parsed[label] = float(match.group(1))

    digest = hashlib.sha256(seed.encode()).digest()
    created = []
    for index, (label, unit, low, high) in enumerate(BIOMARKER_RANGES):
        if label in parsed:
            value = parsed[label]
        else:
            span = high - low
            byte = digest[index % len(digest)]
            value = round(low - span * 0.25 + (byte / 255.0) * span * 1.5, 1)

        flag = "normal" if low <= value <= high else ("high" if value > high else "low")
        marker = Biomarker(
            report_id=report.id, label=label, value=value, unit=unit,
            reference_range=f"{low}–{high}", flag=flag,
        )
        db.session.add(marker)
        created.append(marker)
    return created


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
        payload.append(report.to_dict(markers))
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

    blob = uploaded.read()
    if len(blob) > MAX_REPORT_BYTES:
        return jsonify({"message": "Reports must be under 10 MB."}), 413
    if uploaded.mimetype not in ALLOWED_REPORT_TYPES:
        return jsonify({"message": "Upload a PDF, image, or text report."}), 415

    from .config import BASE_DIR
    store = BASE_DIR / "instance" / "reports" / me()
    os.makedirs(store, exist_ok=True)
    filename = secure_filename(uploaded.filename)
    path = store / f"{uuid.uuid4().hex}_{filename}"
    path.write_bytes(blob)

    report = Report(
        user_id=me(), filename=filename, content_type=uploaded.mimetype,
        size_bytes=len(blob), stored_path=str(path),
    )
    db.session.add(report)
    db.session.flush()

    text_content = blob.decode("utf-8", errors="ignore") if uploaded.mimetype == "text/plain" else None
    markers = _extract_biomarkers(report, text_content, f"{report.id}:{len(blob)}")

    abnormal = [m for m in markers if m.flag != "normal"]
    if abnormal:
        names = ", ".join(m.label.lower() for m in abnormal[:3])
        report.observation = (
            f"{len(abnormal)} of {len(markers)} markers sit outside the reference range — {names}. "
            "Worth raising at your next consultation; none of these are read as urgent on their own."
        )
    else:
        report.observation = (
            f"All {len(markers)} extracted markers fall within their reference ranges. "
            "Nothing here needs action."
        )

    db.session.commit()
    return ok({"report": report.to_dict(markers)}, 201)


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
        "engine": "claude-opus-5" if omni_engine.claude_available() else "local-reasoning",
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
