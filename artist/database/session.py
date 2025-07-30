"""
Database session and connection management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artist.config import settings

# Create a SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Check connection before using
    pool_recycle=3600,   # Recycle connections every hour
    connect_args={"options": "-c timezone=utc"} if "postgresql" in settings.database_url else {}
)

# Create a sessionmaker
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def get_db():
    """FastAPI dependency to get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Create all database tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
