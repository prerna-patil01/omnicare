"""User identity model.

Scope note: this holds *identity* only — no clinical data, no consent grants.
Per SRS §6.2 consent scopes get their own table and are enforced at a boundary
above this model, so nothing here should grow a `can_view_records`-style flag.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


def _uuid4_str():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)

    # Stored lowercased and stripped (see normalize_email) so the unique index
    # is genuinely case-insensitive without relying on collation.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # scrypt via werkzeug. Long enough for scrypt output plus future rehashes.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=_utcnow,
    )

    # --- password handling ------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        # scrypt is werkzeug's default since 2.3 and is what we want here;
        # naming it explicitly means a werkzeug default change can't silently
        # downgrade every new signup's hash.
        self.password_hash = generate_password_hash(raw_password, method="scrypt")

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def to_dict(self) -> dict:
        """Public representation. password_hash must never appear here."""
        return {
            "id": self.id,
            "email": self.email,
            "fullName": self.full_name,
            "phone": self.phone,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"
