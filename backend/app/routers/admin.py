from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import User, AuditEvent

router = APIRouter(prefix="/admin", tags=["admin"])
admin = require_roles("admin")

class StatusIn(BaseModel):
    is_active: bool

@router.get("/users")
def users(user=Depends(admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at}
            for u in db.scalars(select(User).order_by(User.id)).all()]

@router.post("/users/{uid}/status")
def set_status(uid: int, body: StatusIn, user=Depends(admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == user.id:
        raise HTTPException(409, "You cannot change your own account status")
    u.is_active = body.is_active
    audit(db, user.id, "user_activate" if body.is_active else "user_deactivate", "user", u.id); db.commit()
    return {"id": u.id, "is_active": u.is_active}

@router.get("/audit")
def audit_log(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)).all()
    return [{"id": a.id, "actor_id": a.actor_id, "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
             "detail": a.detail, "created_at": a.created_at} for a in rows]
