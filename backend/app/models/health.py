"""Per-user clinical state: vitals, the digital twin, findings, reports,
biomarkers, and trend series. Every row is scoped to a user id.
"""

import json
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .user import _uuid4_str


class VitalReading(db.Model):
    __tablename__ = "vital_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    hrv_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    spo2: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    stress_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hydration_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "date": self.recorded_on.isoformat(),
            "heartRate": self.heart_rate,
            "hrv": self.hrv_ms,
            "spo2": self.spo2,
            "sleepHours": self.sleep_hours,
            "stress": self.stress_score,
            "hydrationMl": self.hydration_ml,
        }


class ClinicalFinding(db.Model):
    """The hero-panel finding: what Omni currently believes and why."""

    __tablename__ = "clinical_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    suspected_condition: Mapped[str] = mapped_column(String(160), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)  # critical|watch|stable
    reasoning_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(40), nullable=False)
    suggested_next_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    saved: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "headline": self.headline,
            "suspectedCondition": self.suspected_condition,
            "severity": self.severity,
            "reasoning": json.loads(self.reasoning_json),
            "riskScore": self.risk_score,
            "riskBand": self.risk_band,
            "suggestedNext": json.loads(self.suggested_next_json),
            "saved": self.saved,
        }


class TwinNode(db.Model):
    """One of the six body-system nodes on the digital twin."""

    __tablename__ = "twin_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(30), nullable=False)  # brain|heart|liver|kidney|metabolic|immune
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    risk_pct: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # normal|caution|warning
    note: Mapped[str] = mapped_column(String(300), nullable=False)
    # Position on the silhouette, 0-100 in each axis.
    x_pct: Mapped[float] = mapped_column(Float, nullable=False)
    y_pct: Mapped[float] = mapped_column(Float, nullable=False)

    def to_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "riskPct": self.risk_pct,
            "status": self.status,
            "note": self.note,
            "x": self.x_pct,
            "y": self.y_pct,
        }


class TwinSummary(db.Model):
    __tablename__ = "twin_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    biological_age: Mapped[float] = mapped_column(Float, nullable=False)
    actual_age: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "healthScore": self.health_score,
            "biologicalAge": self.biological_age,
            "actualAge": self.actual_age,
            "modelVersion": self.model_version,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class Predisposition(db.Model):
    """'What you're prone to' — a 10-year probability with drivers and a lever."""

    __tablename__ = "predispositions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition: Mapped[str] = mapped_column(String(120), nullable=False)
    probability_pct: Mapped[float] = mapped_column(Float, nullable=False)
    drivers_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    lever: Mapped[str] = mapped_column(String(300), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "condition": self.condition,
            "probabilityPct": self.probability_pct,
            "drivers": json.loads(self.drivers_json),
            "lever": self.lever,
        }


class Report(db.Model):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self, biomarkers=None):
        return {
            "id": self.id,
            "filename": self.filename,
            "contentType": self.content_type,
            "sizeBytes": self.size_bytes,
            "observation": self.observation,
            "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "biomarkers": [b.to_dict() for b in (biomarkers or [])],
        }


class Biomarker(db.Model):
    __tablename__ = "biomarkers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_range: Mapped[str] = mapped_column(String(60), nullable=False)
    flag: Mapped[str] = mapped_column(String(20), nullable=False)  # normal|high|low

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "referenceRange": self.reference_range,
            "flag": self.flag,
        }
