"""Shared catalogue data: the doctor directory, care workforce, medicine list,
and regional signals. These rows are not owned by any one user.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .user import _uuid4_str


class Doctor(db.Model):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    hospital: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    fee_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_slot: Mapped[str] = mapped_column(String(60), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    photo_seed: Mapped[str] = mapped_column(String(40), nullable=False)
    supports_video: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "hospital": self.hospital,
            "city": self.city,
            "fee": self.fee_inr,
            "distanceKm": self.distance_km,
            "rating": self.rating,
            "reviews": self.reviews,
            "nextSlot": self.next_slot,
            "experienceYears": self.experience_years,
            "photoSeed": self.photo_seed,
            "supportsVideo": self.supports_video,
        }


class CareWorker(db.Model):
    __tablename__ = "care_workers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # nurse | asha | physiotherapist | lab_technician | dietician
    worker_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    role_label: Mapped[str] = mapped_column(String(80), nullable=False)
    rate_per_hour_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    availability: Mapped[str] = mapped_column(String(40), nullable=False)
    experience_note: Mapped[str] = mapped_column(String(200), nullable=False)
    photo_seed: Mapped[str] = mapped_column(String(40), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "workerType": self.worker_type,
            "role": self.role_label,
            "ratePerHour": self.rate_per_hour_inr,
            "availability": self.availability,
            "experienceNote": self.experience_note,
            "photoSeed": self.photo_seed,
        }


class Medicine(db.Model):
    __tablename__ = "medicines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    generic_salt: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    price_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_eta: Mapped[str] = mapped_column(String(40), nullable=False)
    pack_size: Mapped[str] = mapped_column(String(60), nullable=False)
    # Surfaced in the "Recommended for you" strip.
    recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "genericSalt": self.generic_salt,
            "category": self.category,
            "price": self.price_inr,
            "requiresPrescription": self.requires_prescription,
            "deliveryEta": self.delivery_eta,
            "packSize": self.pack_size,
            "recommended": self.recommended,
        }


class OutbreakSignal(db.Model):
    """Regional disease intelligence, keyed by city."""

    __tablename__ = "outbreak_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(120), nullable=False)
    change_pct: Mapped[float] = mapped_column(Float, nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    radius_km: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_index: Mapped[int] = mapped_column(Integer, nullable=False)
    air_quality_note: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "city": self.city,
            "condition": self.condition,
            "changePct": self.change_pct,
            "caseCount": self.case_count,
            "radiusKm": self.radius_km,
            "airQualityIndex": self.air_quality_index,
            "airQualityNote": self.air_quality_note,
        }
