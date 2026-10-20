from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import CoopMembership, User
from app.services.notify import notify

router = APIRouter(prefix="/cooperatives", tags=["cooperatives"])

class JoinIn(BaseModel):
    coop_id: int

class DecisionIn(BaseModel):
    approve: bool

def _d(db, m):
    return {"id": m.id, "coop_id": m.coop_id, "coop_name": db.get(User, m.coop_id).name, "farmer_id": m.farmer_id,
            "farmer_name": db.get(User, m.farmer_id).name, "status": m.status, "created_at": m.created_at}

@router.post("/join", status_code=201)
def join(body: JoinIn, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    coop = db.get(User, body.coop_id)
    if not coop or coop.role != "cooperative":
        raise HTTPException(404, "Cooperative not found")
    if db.scalar(select(CoopMembership).where(CoopMembership.coop_id == coop.id, CoopMembership.farmer_id == user.id)):
        raise HTTPException(409, "Membership already requested")
    m = CoopMembership(coop_id=coop.id, farmer_id=user.id)
    db.add(m); db.flush()
    notify(db, coop.id, "membership_request", f"{user.name} requested to join")
    audit(db, user.id, "coop_join_request", "membership", m.id); db.commit()
    return _d(db, m)

@router.get("/members")
def members(user=Depends(require_roles("farmer", "cooperative", "admin")), db: Session = Depends(get_db)):
    q = select(CoopMembership).order_by(CoopMembership.id.desc())
    if user.role == "farmer": q = q.where(CoopMembership.farmer_id == user.id)
    elif user.role == "cooperative": q = q.where(CoopMembership.coop_id == user.id)
    return [_d(db, m) for m in db.scalars(q).all()]

@router.post("/members/{mid}/decision")
def decide(mid: int, body: DecisionIn, user=Depends(require_roles("cooperative")), db: Session = Depends(get_db)):
    m = db.get(CoopMembership, mid)
    if not m or m.coop_id != user.id:
        raise HTTPException(404, "Membership not found")
    r = db.execute(update(CoopMembership).where(CoopMembership.id == m.id, CoopMembership.status == "PENDING")
                   .values(status="APPROVED" if body.approve else "REJECTED"))
    if r.rowcount != 1:
        raise HTTPException(409, "Membership was already decided")
    notify(db, m.farmer_id, "membership_decision", f"Your membership request was {'approved' if body.approve else 'rejected'}")
    audit(db, user.id, "coop_decision", "membership", m.id); db.commit(); db.refresh(m)
    return _d(db, m)
