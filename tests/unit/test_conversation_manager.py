"""Unit tests for conversation manager."""

import pytest
from datetime import datetime
from uuid import uuid4

from packages.database.models import ConversationModel, SessionModel, UserModel
from packages.qa_service import context


@pytest.fixture
def test_session_id(db_session):
    """Create a test session in the database and return its ID."""
    # Create a test user
    user = UserModel(
        id=str(uuid4()),
        username="testuser",
        password_hash="hashed_password",
        created_at=datetime.utcnow(),
    )
    db_session.add(user)

    # Create a test session
    session = SessionModel(
        id=str(uuid4()),
        user_id=user.id,
        token="test_token",
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        is_valid=True,
    )
    db_session.add(session)
    db_session.commit()

    return session.id


class TestAddMessage:
    """Tests for adding messages to conversation history."""

    @pytest.mark.asyncio
    async def test_add_message_success(self, db_session, test_session_id):
        """Test adding a message to conversation history."""
        session_id = test_session_id

        await context.add_message(
            db_session, session_id, "user", "What is the cost breakdown?"
        )

        # Verify message was added
        messages = (
            db_session.query(ConversationModel)
            .filter(ConversationModel.session_id == session_id)
            .all()
        )
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "What is the cost breakdown?"
        assert messages[0].timestamp is not None

    @pytest.mark.asyncio
    async def test_add_message_with_configuration_id(self, db_session, test_session_id):
        """Test adding a message with configuration ID."""
        session_id = test_session_id
        config_id = str(uuid4())

        await context.add_message(
            db_session, session_id, "assistant", "Here is the answer", config_id
        )

        messages = (
            db_session.query(ConversationModel)
            .filter(ConversationModel.session_id == session_id)
            .all()
        )
        assert len(messages) == 1
        assert messages[0].configuration_id == config_id

    @pytest.mark.asyncio
    async def test_add_message_invalid_role(self, db_session, test_session_id):
        """Test that invalid role raises ValueError."""
        session_id = test_session_id

        with pytest.raises(ValueError, match="Invalid role"):
            await context.add_message(
                db_session, session_id, "invalid_role", "Test message"
            )

    @pytest.mark.asyncio
    async def test_add_message_user_role(self, db_session, test_session_id):
        """Test adding a user message."""
        session_id = test_session_id

        await context.add_message(db_session, session_id, "user", "User question")

        messages = (
            db_session.query(ConversationModel)
            .filter(ConversationModel.session_id == session_id)
            .all()
        )
        assert messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_add_message_assistant_role(self, db_session, test_session_id):
        """Test adding an assistant message."""
        session_id = test_session_id

        await context.add_message(
            db_session, session_id, "assistant", "Assistant response"
        )

        messages = (
            db_session.query(ConversationModel)
            .filter(ConversationModel.session_id == session_id)
            .all()
        )
        assert messages[0].role == "assistant"


class TestGetHistory:
    """Tests for retrieving conversation history."""

    @pytest.mark.asyncio
    async def test_get_history_multiple_messages(self, db_session, test_session_id):
        """Test retrieving conversation history with multiple messages."""
        session_id = test_session_id

        # Add multiple messages
        await context.add_message(db_session, session_id, "user", "First question")
        await context.add_message(db_session, session_id, "assistant", "First answer")
        await context.add_message(db_session, session_id, "user", "Second question")

        # Get history
        history = await context.get_history(db_session, session_id)

        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "First question"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "First answer"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "Second question"

    @pytest.mark.asyncio
    async def test_get_history_contains_required_fields(
        self, db_session, test_session_id
    ):
        """Test that history messages contain all required fields."""
        session_id = test_session_id

        await context.add_message(db_session, session_id, "user", "Test message")

        history = await context.get_history(db_session, session_id)

        assert len(history) == 1
        msg = history[0]
        assert "id" in msg
        assert "role" in msg
        assert "content" in msg
        assert "timestamp" in msg

    @pytest.mark.asyncio
    async def test_get_history_empty(self, db_session, test_session_id):
        """Test retrieving history for session with no messages."""
        session_id = test_session_id

        history = await context.get_history(db_session, session_id)

        assert len(history) == 0
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_chronological_order(self, db_session, test_session_id):
        """Test that conversation history maintains chronological order."""
        session_id = test_session_id

        # Add messages
        messages = [
            ("user", "Message 1"),
            ("assistant", "Message 2"),
            ("user", "Message 3"),
            ("assistant", "Message 4"),
        ]

        for role, content in messages:
            await context.add_message(db_session, session_id, role, content)

        # Get history
        history = await context.get_history(db_session, session_id)

        # Verify order is maintained
        assert len(history) == 4
        for i, (expected_role, expected_content) in enumerate(messages):
            assert history[i]["role"] == expected_role
            assert history[i]["content"] == expected_content

        # Verify timestamps are in ascending order
        timestamps = [msg["timestamp"] for msg in history]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_get_history_different_sessions(self, db_session, test_session_id):
        """Test that history is isolated per session."""
        session_id_1 = test_session_id
        session_id_2 = str(uuid4())

        # Add messages to first session
        await context.add_message(db_session, session_id_1, "user", "Session 1 message")

        # Add messages to second session
        await context.add_message(db_session, session_id_2, "user", "Session 2 message")

        # Get history for first session
        history_1 = await context.get_history(db_session, session_id_1)
        assert len(history_1) == 1
        assert history_1[0]["content"] == "Session 1 message"

        # Get history for second session
        history_2 = await context.get_history(db_session, session_id_2)
        assert len(history_2) == 1
        assert history_2[0]["content"] == "Session 2 message"


class TestClearHistory:
    """Tests for clearing conversation history."""

    @pytest.mark.asyncio
    async def test_clear_history_success(self, db_session, test_session_id):
        """Test clearing conversation history."""
        session_id = test_session_id

        # Add messages
        await context.add_message(db_session, session_id, "user", "Question 1")
        await context.add_message(db_session, session_id, "assistant", "Answer 1")

        # Verify messages exist
        history = await context.get_history(db_session, session_id)
        assert len(history) == 2

        # Clear history
        await context.clear_history(db_session, session_id)

        # Verify history is empty
        history = await context.get_history(db_session, session_id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_clear_history_empty_session(self, db_session, test_session_id):
        """Test clearing history for session with no messages."""
        session_id = test_session_id

        # Clear history (should not raise error)
        await context.clear_history(db_session, session_id)

        # Verify history is still empty
        history = await context.get_history(db_session, session_id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_clear_history_only_affects_target_session(
        self, db_session, test_session_id
    ):
        """Test that clearing history only affects the target session."""
        session_id_1 = test_session_id
        session_id_2 = str(uuid4())

        # Add messages to both sessions
        await context.add_message(db_session, session_id_1, "user", "Session 1 message")
        await context.add_message(db_session, session_id_2, "user", "Session 2 message")

        # Clear history for first session
        await context.clear_history(db_session, session_id_1)

        # Verify first session is empty
        history_1 = await context.get_history(db_session, session_id_1)
        assert len(history_1) == 0

        # Verify second session still has messages
        history_2 = await context.get_history(db_session, session_id_2)
        assert len(history_2) == 1
        assert history_2[0]["content"] == "Session 2 message"
