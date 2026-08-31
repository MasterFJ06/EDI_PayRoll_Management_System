from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from app.core.config import get_settings


settings = get_settings()


database_url = URL.create(
    drivername="mysql+pymysql",
    username=settings.database_user,
    password=settings.database_password,
    host=settings.database_host,
    port=settings.database_port,
    database=settings.database_name,
)


engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    echo=False,
)