from app.infrastructure.database.engine import engine
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.user import User


def initialize_database() -> None:
    """Create database tables for registered SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)