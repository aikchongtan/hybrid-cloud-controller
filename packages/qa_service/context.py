"""Conversation manager for Q&A service.

This module manages conversation history for Q&A sessions, storing messages
with role (user/assistant) and timestamp in the database.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from packages.database.models import ConversationModel


async def add_message(
    db_session: Session,
    session_id: str,
    role: str,
    content: str,
    configuration_id: str = "",
) -> None:
    """Add a message to conversation history.

    Args:
        db_session: Database session
        session_id: The session identifier for the conversation
        role: The role of the message sender (user or assistant)
        content: The message content
        configuration_id: The configuration ID associated with the conversation
                         (optional, defaults to empty string)

    Raises:
        ValueError: If role is not 'user' or 'assistant'
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

    message = ConversationModel(
        id=str(uuid4()),
        session_id=session_id,
        configuration_id=configuration_id,
        role=role,
        content=content,
        timestamp=datetime.utcnow(),
    )
    db_session.add(message)
    db_session.commit()


async def get_history(db_session: Session, session_id: str) -> list[dict[str, str]]:
    """Get conversation history for a session.

    Args:
        db_session: Database session
        session_id: The session identifier for the conversation

    Returns:
        List of messages in chronological order, each containing:
        - id: Message ID
        - role: Message role (user or assistant)
        - content: Message content
        - timestamp: ISO format timestamp
    """
    messages = (
        db_session.query(ConversationModel)
        .filter(ConversationModel.session_id == session_id)
        .order_by(ConversationModel.timestamp)
        .all()
    )

    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in messages
    ]


async def clear_history(db_session: Session, session_id: str) -> None:
    """Clear conversation history for a session.

    Args:
        db_session: Database session
        session_id: The session identifier for the conversation
    """
    db_session.query(ConversationModel).filter(
        ConversationModel.session_id == session_id
    ).delete()
    db_session.commit()
