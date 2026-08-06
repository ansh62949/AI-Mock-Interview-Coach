import uuid
from typing import Dict, Optional
from schemas.state import InterviewState
from utils.logger import logger


class SessionManager:
    """In-memory session manager storing active InterviewState objects by session UUID."""

    def __init__(self) -> None:
        self._sessions: Dict[str, InterviewState] = {}

    def create_session(self, initial_state: InterviewState) -> str:
        """Initializes and registers a new interview session state."""
        session_id: str = str(uuid.uuid4())
        self._sessions[session_id] = initial_state
        logger.info(f"SessionManager: Created session {session_id} for target role '{initial_state.get('target_role')}'.")
        return session_id

    def get_session(self, session_id: str) -> Optional[InterviewState]:
        """Retrieves session state by UUID, returning None if missing."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updated_state: InterviewState) -> None:
        """Persists updated state for an active session."""
        if session_id in self._sessions:
            self._sessions[session_id] = updated_state
            logger.info(f"SessionManager: Updated session {session_id} (turn={updated_state.get('turn_count')}).")


session_manager = SessionManager()
