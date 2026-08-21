"""Model package. Importing here registers mappers with SQLAlchemy metadata,
which Alembic's autogenerate relies on."""

from .activity import Appointment, CartItem, ConsentScope, Conversation, Message
from .catalog import CareWorker, Doctor, Medicine, OutbreakSignal
from .health import (
    Biomarker,
    Report,
    ReportExtraction,
    ReportPage,
    VitalReading,
)
from .user import User

__all__ = [
    "Appointment",
    "Biomarker",
    "CareWorker",
    "CartItem",
    "ConsentScope",
    "Conversation",
    "Doctor",
    "Medicine",
    "Message",
    "OutbreakSignal",
    "Report",
    "ReportExtraction",
    "ReportPage",
    "User",
    "VitalReading",
]
