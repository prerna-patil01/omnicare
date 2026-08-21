"""Per-user provisioning for the live application."""

from .extensions import db
from .models import ConsentScope


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
    """Create a new user's consent scopes without creating clinical data."""
    for key, title, description in CONSENT_SCOPES:
        db.session.add(ConsentScope(
            user_id=user.id, key=key, title=title, description=description, granted=True,
        ))
    db.session.commit()
