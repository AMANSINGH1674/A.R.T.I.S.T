"""
Long-term memory service — stores and retrieves per-user conversation history
from PostgreSQL so agents can reference past interactions across sessions.
"""

import structlog
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from ..database.models import ConversationMemory

logger = structlog.get_logger()

# Number of recent turns to inject into each new workflow
DEFAULT_HISTORY_TURNS = 6  # 3 user + 3 assistant


class MemoryService:
    """Read/write conversation memory backed by PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    def get_history(self, user_id: str, n: int = DEFAULT_HISTORY_TURNS) -> List[Dict[str, Any]]:
        """Return the last n memory rows for a user, oldest-first."""
        try:
            rows = (
                self.db.query(ConversationMemory)
                .filter(ConversationMemory.user_id == user_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(n)
                .all()
            )
            # Reverse so oldest is first (chronological order for LLM context)
            return [
                {"role": r.role, "content": r.content, "run_id": r.run_id}
                for r in reversed(rows)
            ]
        except Exception as e:
            logger.warning("Failed to retrieve conversation history", user_id=user_id, error=str(e))
            return []

    def save_turn(
        self,
        user_id: str,
        run_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Persist a user/assistant exchange to the database."""
        try:
            self.db.add(ConversationMemory(user_id=user_id, role="user", content=user_message, run_id=run_id))
            self.db.add(ConversationMemory(user_id=user_id, role="assistant", content=assistant_message[:4000], run_id=run_id))
            self.db.commit()
            logger.info("Conversation turn saved", user_id=user_id, run_id=run_id)
        except Exception as e:
            self.db.rollback()
            logger.warning("Failed to save conversation turn", user_id=user_id, error=str(e))
