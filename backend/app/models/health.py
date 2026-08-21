"""Per-user clinical state: readings the user logged, reports they uploaded,
and biomarkers read off those reports. Every row is scoped to a user id.

There is deliberately no table for twin scores, findings, or predictions — they
are computed on read in `derive.py` from the rows here, so a stored number can
never drift from the measurements behind it, or exist without any.
"""

import json
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .user import _uuid4_str


def _utcnow():
    return datetime.now(timezone.utc)


class VitalReading(db.Model):
    __tablename__ = "vital_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # A user may log only the measures they actually have. Missing is distinct
    # from zero: zero would be invented clinical data and must never enter a
    # trend, average, or downstream evidence context.
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hydration_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    extraction: Mapped["ReportExtraction | None"] = relationship(
        back_populates="report", cascade="all, delete-orphan", uselist=False
    )
    pages: Mapped[list["ReportPage"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportPage.page_number"
    )

    def to_dict(self, biomarkers=None, extraction=None):
        payload = {
            "id": self.id,
            "filename": self.filename,
            "contentType": self.content_type,
            "sizeBytes": self.size_bytes,
            "observation": self.observation,
            "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "biomarkers": [b.to_dict() for b in (biomarkers or [])],
        }
        extraction = extraction if extraction is not None else self.extraction
        if extraction:
            payload["extraction"] = extraction.to_dict()
        return payload


class ReportExtraction(db.Model):
    """The status and page-aware text extracted from one uploaded report."""

    __tablename__ = "report_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    parser: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A labelled convenience representation. Exact citation boundaries remain
    # in ReportPage rather than being inferred from this field.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=_utcnow
    )
    report: Mapped["Report"] = relationship(back_populates="extraction")

    def to_dict(self, include_pages=False):
        payload = {
            "status": self.status,
            "parser": self.parser,
            "pageCount": self.page_count,
            "error": self.error,
            "extractedAt": self.extracted_at.isoformat() if self.extracted_at else None,
        }
        if include_pages:
            payload["pages"] = [page.to_dict() for page in self.report.pages]
        return payload


class ReportPage(db.Model):
    """One source page, retained for future report citations and retrieval."""

    __tablename__ = "report_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report: Mapped["Report"] = relationship(back_populates="pages")

    def to_dict(self):
        return {"pageNumber": self.page_number, "characterCount": self.character_count}


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
    # extracted = parsed out of the uploaded file; manual = typed in by the
    # user. Never anything else — there is no generated source.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="extracted")

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "referenceRange": self.reference_range,
            "flag": self.flag,
            "source": self.source,
        }
