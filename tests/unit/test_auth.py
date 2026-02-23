"""Unit tests for authentication service."""

from datetime import datetime, timedelta

import pytest

from packages.security import auth


class TestRegisterUser:
    """Tests for user registration."""

    def test_register_user_success(self, db_session):
        """Test successful user registration with bcrypt hashing."""
        username = "testuser"
        password = "securepassword123"

        user = auth.register_user(db_session, username, password)

        assert user.id is not None
        assert user.username == username
        assert user.password_hash != password  # Password should be hashed
        assert user.password_hash.startswith("$2b$")  # bcrypt hash format
        assert user.created_at is not None

    def test_register_user_duplicate_username(self, db_session):
        """Test that duplicate usernames are rejected."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)

        with pytest.raises(ValueError, match="already exists"):
            auth.register_user(db_session, username, "differentpassword")

    def test_register_user_empty_username(self, db_session):
        """Test that empty username is rejected."""
        with pytest.raises(ValueError, match="required"):
            auth.register_user(db_session, "", "password123")

    def test_register_user_empty_password(self, db_session):
        """Test that empty password is rejected."""
        with pytest.raises(ValueError, match="required"):
            auth.register_user(db_session, "testuser", "")


class TestAuthenticate:
    """Tests for user authentication."""

    def test_authenticate_success(self, db_session):
        """Test successful authentication creates a session."""
        username = "testuser"
        password = "securepassword123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        assert session.id is not None
        assert session.user_id is not None
        assert session.token is not None
        assert len(session.token) > 0
        assert session.is_valid is True
        assert session.created_at is not None
        assert session.last_activity is not None

    def test_authenticate_invalid_username(self, db_session):
        """Test authentication fails with invalid username."""
        with pytest.raises(ValueError, match="Invalid credentials"):
            auth.authenticate(db_session, "nonexistent", "password123")

    def test_authenticate_invalid_password(self, db_session):
        """Test authentication fails with invalid password."""
        username = "testuser"
        password = "correctpassword"

        auth.register_user(db_session, username, password)

        with pytest.raises(ValueError, match="Invalid credentials"):
            auth.authenticate(db_session, username, "wrongpassword")

    def test_authenticate_empty_credentials(self, db_session):
        """Test authentication fails with empty credentials."""
        with pytest.raises(ValueError, match="required"):
            auth.authenticate(db_session, "", "password")

        with pytest.raises(ValueError, match="required"):
            auth.authenticate(db_session, "username", "")


class TestValidateSession:
    """Tests for session validation."""

    def test_validate_session_success(self, db_session):
        """Test successful session validation."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        validated_session = auth.validate_session(db_session, session.token)

        assert validated_session is not None
        assert validated_session.id == session.id
        assert validated_session.is_valid is True

    def test_validate_session_invalid_token(self, db_session):
        """Test validation fails with invalid token."""
        result = auth.validate_session(db_session, "invalid_token")
        assert result is None

    def test_validate_session_empty_token(self, db_session):
        """Test validation fails with empty token."""
        result = auth.validate_session(db_session, "")
        assert result is None

    def test_validate_session_updates_last_activity(self, db_session):
        """Test that validation updates last_activity timestamp."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)
        original_activity = session.last_activity

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.1)

        validated_session = auth.validate_session(db_session, session.token)

        assert validated_session.last_activity > original_activity


class TestInvalidateSession:
    """Tests for session invalidation."""

    def test_invalidate_session_success(self, db_session):
        """Test successful session invalidation."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        auth.invalidate_session(db_session, session.token)

        validated_session = auth.validate_session(db_session, session.token)
        assert validated_session is None

    def test_invalidate_session_invalid_token(self, db_session):
        """Test invalidating non-existent token doesn't raise error."""
        auth.invalidate_session(db_session, "nonexistent_token")
        # Should not raise an error

    def test_invalidate_session_empty_token(self, db_session):
        """Test invalidating empty token doesn't raise error."""
        auth.invalidate_session(db_session, "")
        # Should not raise an error


class TestCheckSessionTimeout:
    """Tests for session timeout checking."""

    def test_check_session_timeout_not_expired(self, db_session):
        """Test that recent session is not timed out."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        is_timed_out = auth.check_session_timeout(session)
        assert is_timed_out is False

    def test_check_session_timeout_expired(self, db_session):
        """Test that old session is timed out."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        # Manually set last_activity to 31 minutes ago
        session.last_activity = datetime.utcnow() - timedelta(minutes=31)
        db_session.commit()

        is_timed_out = auth.check_session_timeout(session)
        assert is_timed_out is True

    def test_check_session_timeout_just_under_30_minutes(self, db_session):
        """Test session just under 30 minutes is not timed out."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        # Set last_activity to 29 minutes 59 seconds ago
        session.last_activity = datetime.utcnow() - timedelta(minutes=29, seconds=59)
        db_session.commit()

        is_timed_out = auth.check_session_timeout(session)
        assert is_timed_out is False

    def test_validate_session_with_timeout(self, db_session):
        """Test that validate_session invalidates timed out sessions."""
        username = "testuser"
        password = "password123"

        auth.register_user(db_session, username, password)
        session = auth.authenticate(db_session, username, password)

        # Set last_activity to 31 minutes ago
        session.last_activity = datetime.utcnow() - timedelta(minutes=31)
        db_session.commit()

        validated_session = auth.validate_session(db_session, session.token)
        assert validated_session is None

    def test_check_session_timeout_none_session(self):
        """Test that None session is considered timed out."""
        is_timed_out = auth.check_session_timeout(None)
        assert is_timed_out is True
