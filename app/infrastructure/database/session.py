from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.engine import engine


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)