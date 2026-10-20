from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/directory", tags=["directory"])
ALLOWED = {"lender", "insurer", "cooperative", "agronomist"}

@router.get("/{role}")
def directory(role: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if role not in ALLOWED:
        raise HTTPException(404, "Unknown directory")
    rows = db.scalars(select(User).where(User.role == role, User.is_active == True).order_by(User.name)).all()  # noqa: E712
    return [{"id": u.id, "name": u.name, "email": u.email} for u in rows]
