"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    # Add new columns to existing databases without needing migrations
    new_columns = [('last_email_from', 'VARCHAR'), ('last_email_body', 'TEXT')]
    with engine.connect() as conn:
        for col, coltype in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE job_applications ADD COLUMN {col} {coltype}"))
                conn.commit()
            except Exception:
                pass  # Column already exists
