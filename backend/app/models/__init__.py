"""Model package. Importing here registers mappers with SQLAlchemy metadata,
which Alembic's autogenerate relies on."""

from .user import User

__all__ = ["User"]
