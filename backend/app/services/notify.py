from app.models import Notification

def notify(db, user_id: int, kind: str, message: str) -> None:
    """Queue an in-app notification in the caller's transaction."""
    db.add(Notification(user_id=user_id, kind=kind, message=message))
