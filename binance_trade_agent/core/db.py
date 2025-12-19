"""
Database Configuration Module
Provides centralized database URL management and engine/session creation
for both SQLite (local dev) and PostgreSQL (production)
"""

import logging
import os
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Get database URL from environment or fall back to SQLite.
    
    Priority:
    1. DATABASE_URL environment variable (for PostgreSQL)
    2. DB_PATH environment variable (for SQLite)
    3. Default SQLite path
    
    Returns:
        Database URL string (e.g., postgresql://... or sqlite:///.../db.db)
    """
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        logger.info(f"Using DATABASE_URL from environment: {database_url.split('@')[0]}***")
        return database_url
    
    # Fallback to SQLite
    db_path = os.getenv("DB_PATH", "/app/data/portfolio.db")
    sqlite_url = f"sqlite:///{db_path}"
    logger.info(f"Using SQLite fallback: {sqlite_url}")
    return sqlite_url


def create_engine_from_url(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_pre_ping: bool = True,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
) -> Engine:
    """
    Create SQLAlchemy engine with appropriate settings for SQLite or PostgreSQL.
    
    Args:
        database_url: Database URL (if None, uses get_database_url())
        echo: Enable SQL query logging
        pool_pre_ping: Enable connection health checks (PostgreSQL)
        pool_size: Number of connections to maintain (PostgreSQL)
        max_overflow: Max connections beyond pool_size (PostgreSQL)
        pool_timeout: Seconds to wait for connection (PostgreSQL)
        
    Returns:
        Configured SQLAlchemy engine
    """
    if database_url is None:
        database_url = get_database_url()
    
    # Determine if SQLite or PostgreSQL
    is_sqlite = database_url.startswith("sqlite")
    
    if is_sqlite:
        # SQLite-specific configuration
        engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},  # Allow multi-threading
            poolclass=NullPool,  # No connection pooling for SQLite
        )
        
        # Enable foreign keys for SQLite (optional but recommended)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
        logger.info("Created SQLite engine")
        
    else:
        # PostgreSQL-specific configuration
        # Override pool settings from environment if available
        pool_size = int(os.getenv("DB_POOL_SIZE", pool_size))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", max_overflow))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", pool_timeout))
        
        engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=pool_pre_ping,  # Verify connections before use
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            poolclass=QueuePool,
        )
        
        logger.info(
            f"Created PostgreSQL engine (pool_size={pool_size}, "
            f"max_overflow={max_overflow}, pool_timeout={pool_timeout})"
        )
    
    return engine


def create_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """
    Create a sessionmaker configured for the database engine.
    
    Args:
        engine: SQLAlchemy engine (if None, creates default engine)
        
    Returns:
        Configured sessionmaker
    """
    if engine is None:
        engine = create_engine_from_url()
    
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,  # Prevent lazy-loading issues after commit
    )


# Global engine and session factory
# These are initialized lazily and can be overridden for testing
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine_from_url()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the global session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


def reset_engine():
    """Reset global engine and session factory (useful for testing)."""
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
    _engine = None
    _session_factory = None


# Convenience alias for application code
SessionLocal = None  # Will be set when first accessed


def get_session():
    """
    Get a new database session.
    
    Usage:
        session = get_session()
        try:
            # do work
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
            
    Or use context manager (recommended):
        with get_session() as session:
            with session.begin():
                # work is atomic
    """
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = get_session_factory()
    return SessionLocal()
