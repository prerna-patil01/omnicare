"""User activity: appointments, pharmacy cart, Omni conversations, consent."""

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .user import _uuid4_str


class Appointment(db.Model):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="in_person")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self, doctor=None):
        return {
            "id": self.id,
            "scheduledFor": self.scheduled_for.isoformat(),
            "mode": self.mode,
            "status": self.status,
            "location": self.location,
            "doctor": doctor.to_dict() if doctor else None,
        }


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def to_dict(self, medicine=None):
        return {
            "id": self.id,
            "quantity": self.quantity,
            "medicine": medicine.to_dict() if medicine else None,
            "lineTotal": (medicine.price_inr * self.quantity) if medicine else 0,
        }


class Conversation(db.Model):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="New conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(db.Model):
    """One turn. Omni turns carry structured blocks (deliberation, verdict)
    alongside prose, so the UI can render specialist cards and staged plans."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|omni
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # {"followUp":..., "whyAsking":..., "deliberation":[...], "verdict":{...}, "abstained":bool}
    blocks_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "body": self.body,
            "blocks": json.loads(self.blocks_json or "{}"),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class ConsentScope(db.Model):
    """A permission the user grants Omni. Enforced above the model layer —
    see SRS §6.2; nothing reads records without checking these."""

    __tablename__ = "consent_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "granted": self.granted,
        }
