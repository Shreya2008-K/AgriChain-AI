from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import LoanApplication, User
from app.services.notify import notify

router = APIRouter(prefix="/lending", tags=["lending"])

class ApplyIn(BaseModel):
    lender_id: int
    amount: float = Field(gt=0)
    purpose: str = Field(min_length=3, max_length=500)

class DecisionIn(BaseModel):
    approve: bool
    notes: Optional[str] = Field(default=None, max_length=500)

def _d(db, a):
    return {"id": a.id, "farmer_id": a.farmer_id, "farmer_name": db.get(User, a.farmer_id).name, "lender_id": a.lender_id,
            "lender_name": db.get(User, a.lender_id).name, "amount": a.amount, "purpose": a.purpose, "status": a.status,
            "decision_notes": a.decision_notes, "created_at": a.created_at,
            "note": "Farm reports are visible to the lender only if the farmer has granted an active permission."}

@router.post("/applications", status_code=201)
def apply(body: ApplyIn, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    l = db.get(User, body.lender_id)
    if not l or l.role != "lender":
        raise HTTPException(404, "Lender not found")
    a = LoanApplication(farmer_id=user.id, lender_id=l.id, amount=body.amount, purpose=body.purpose)
    db.add(a); db.flush(); notify(db, l.id, "loan_application", f"New loan application from {user.name}")
    audit(db, user.id, "loan_apply", "loan", a.id); db.commit()
    return _d(db, a)

@router.get("/applications")
def list_apps(user=Depends(require_roles("farmer", "lender")), db: Session = Depends(get_db)):
    col = LoanApplication.farmer_id if user.role == "farmer" else LoanApplication.lender_id
    return [_d(db, a) for a in db.scalars(select(LoanApplication).where(col == user.id).order_by(LoanApplication.id.desc())).all()]

@router.post("/applications/{aid}/decision")
def decide(aid: int, body: DecisionIn, user=Depends(require_roles("lender")), db: Session = Depends(get_db)):
    a = db.get(LoanApplication, aid)
    if not a or a.lender_id != user.id:
        raise HTTPException(404, "Application not found")
    if not body.approve and not (body.notes and body.notes.strip()):
        raise HTTPException(422, "Notes are required when rejecting")
    r = db.execute(update(LoanApplication).where(LoanApplication.id == a.id, LoanApplication.status == "SUBMITTED")
                   .values(status="APPROVED" if body.approve else "REJECTED", decision_notes=body.notes, decided_at=datetime.now(timezone.utc)))
    if r.rowcount != 1:
        raise HTTPException(409, "Application was already decided")
    notify(db, a.farmer_id, "loan_decision", f"Loan application #{a.id} was {'approved' if body.approve else 'rejected'}")
    audit(db, user.id, "loan_decision", "loan", a.id); db.commit(); db.refresh(a)
    return _d(db, a)
