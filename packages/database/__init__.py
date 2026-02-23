"""Database package for Hybrid Cloud Controller.

This package provides database initialization, models, and migrations
for the Hybrid Cloud Controller application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import os

from packages.database.models import Base

# Database engine and session factory
_engine: Optional[object] = None
_session_factory: Optional[sessionmaker] = None


def init_database(database_url: Optional[str] = None) -> None:
    """Initialize the database engine and session factory.
    
    Args:
        database_url: Database connection URL. If None, reads from DATABASE_URL
                     environment variable or defaults to SQLite.
    """
    global _engine, _session_factory
    
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///hybrid_cloud_controller.db")
    
    _engine = create_engine(database_url, echo=False)
    _session_factory = sessionmaker(bind=_engine)


def create_tables() -> None:
    """Create all database tables based on SQLAlchemy models."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    """Get a new database session.
    
    Returns:
        A new SQLAlchemy session instance.
        
    Raises:
        RuntimeError: If database is not initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _session_factory()


def drop_tables() -> None:
    """Drop all database tables. Use with caution!"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    Base.metadata.drop_all(_engine)


__all__ = [
    "init_database",
    "create_tables",
    "get_session",
    "drop_tables",
    "Base",
]
