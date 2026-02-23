"""Authentication service for user registration, login, and session management."""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from packages.database.models import SessionModel, UserModel


def register_user(db: Session, username: str, password: str) -> UserModel:
    """
    Register a new user with bcrypt-hashed password.

    Args:
        db: Database session
        username: Username for the new user
        password: Plain text password to be hashed

    Returns:
        UserModel: The created user record

    Raises:
        ValueError: If username already exists or inputs are invalid
    """
    if not username or not password:
        raise ValueError("Username and password are required")

    # Check if username already exists
    existing_user = db.query(UserModel).filter(UserModel.username == username).first()
    if existing_user:
        raise ValueError(f"Username '{username}' already exists")

    # Hash password with bcrypt
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    # Create user record
    user = UserModel(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=password_hash,
        created_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate(db: Session, username: str, password: str) -> SessionModel:
    """
    Authenticate user and create a new session.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password to verify

    Returns:
        SessionModel: The created session with token

    Raises:
        ValueError: If credentials are invalid
    """
    if not username or not password:
        raise ValueError("Username and password are required")

    # Find user by username
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise ValueError("Invalid credentials")

    # Verify password with bcrypt
    password_bytes = password.encode("utf-8")
    password_hash_bytes = user.password_hash.encode("utf-8")

    if not bcrypt.checkpw(password_bytes, password_hash_bytes):
        raise ValueError("Invalid credentials")

    # Generate secure random token
    token = secrets.token_urlsafe(32)

    # Create session
    now = datetime.utcnow()
    session = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token=token,
        created_at=now,
        last_activity=now,
        is_valid=True,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def validate_session(db: Session, token: str) -> Optional[SessionModel]:
    """
    Validate a session token and check for timeout.

    Args:
        db: Database session
        token: Session token to validate

    Returns:
        Optional[SessionModel]: The session if valid, None otherwise
    """
    if not token:
        return None

    # Find session by token
    session = db.query(SessionModel).filter(SessionModel.token == token).first()

    if not session or not session.is_valid:
        return None

    # Check for 30-minute inactivity timeout
    if check_session_timeout(session):
        invalidate_session(db, token)
        return None

    # Update last activity timestamp
    session.last_activity = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return session


def invalidate_session(db: Session, token: str) -> None:
    """
    Invalidate a session (logout).

    Args:
        db: Database session
        token: Session token to invalidate
    """
    if not token:
        return

    session = db.query(SessionModel).filter(SessionModel.token == token).first()

    if session:
        session.is_valid = False
        db.commit()


def check_session_timeout(session: SessionModel) -> bool:
    """
    Check if a session has exceeded the 30-minute inactivity timeout.

    Args:
        session: Session to check

    Returns:
        bool: True if session has timed out, False otherwise
    """
    if not session:
        return True

    timeout_threshold = timedelta(minutes=30)
    time_since_activity = datetime.utcnow() - session.last_activity

    return time_since_activity > timeout_threshold
