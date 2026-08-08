"""Model package. Importing here registers mappers with SQLAlchemy metadata,
which Alembic's autogenerate relies on."""

from .activity import Appointment, CartItem, ConsentScope, Conversation, Message
from .catalog import CareWorker, Doctor, Medicine, OutbreakSignal
from .health import (
    Biomarker,
    ClinicalFinding,
    Predisposition,
    Report,
    TwinNode,
    TwinSummary,
    VitalReading,
)
from .user import User

__all__ = [
    "Appointment",
    "Biomarker",
    "CareWorker",
    "CartItem",
    "ClinicalFinding",
    "ConsentScope",
    "Conversation",
    "Doctor",
    "Medicine",
    "Message",
    "OutbreakSignal",
    "Predisposition",
    "Report",
    "TwinNode",
    "TwinSummary",
    "User",
    "VitalReading",
]
