from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import get_current_user
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
def list_notifications(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)).all()
    unread = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read == False))  # noqa: E712
    return {"unread": unread, "items": [{"id": n.id, "kind": n.kind, "message": n.message, "is_read": n.is_read, "created_at": n.created_at} for n in rows]}

@router.post("/read-all")
def read_all(user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True)); db.commit()
    return {"ok": True}

@router.post("/{nid}/read")
def read_one(nid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True; db.commit()
    return {"ok": True}
