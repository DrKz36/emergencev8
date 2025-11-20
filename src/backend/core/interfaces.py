from typing import Protocol, Dict, Any

class NotificationService(Protocol):
    """Interface for sending notifications to connected clients."""
    
    async def send_personal_message(self, message: Dict[str, Any], session_id: str) -> None:
        ...

    async def broadcast(self, message: Dict[str, Any]) -> None:
        ...

    async def close_session(self, session_id: str, code: int = 1000, reason: str = "") -> None:
        ...

class MessageHandler(Protocol):
    """Interface for handling WebSocket messages."""
    
    async def handle_message(self, session_id: str, payload: Dict[str, Any]) -> None:
        ...
