from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import get_current_user
from app.models import Agreement, User
from app.services import trade

router = APIRouter(prefix="/agreements", tags=["agreements"])

def _party(a: Agreement, u: User) -> bool:
    return u.role == "admin" or u.id in (a.buyer_id, a.seller_id)

@router.get("")
def list_agreements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Agreement).order_by(Agreement.id.desc())
    if user.role != "admin":
        q = q.where(or_(Agreement.buyer_id == user.id, Agreement.seller_id == user.id))
    return [trade.agreement_dict(db, a) for a in db.scalars(q).all()]

@router.get("/{agreement_id}")
def get_one(agreement_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Agreement, agreement_id)
    if not a or not _party(a, user):
        raise HTTPException(404, "Agreement not found")
    return trade.agreement_dict(db, a)
