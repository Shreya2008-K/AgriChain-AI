from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import InsurancePolicy, InsuranceClaim, User
from app.services.notify import notify

router = APIRouter(prefix="/insurance", tags=["insurance"])
PAYOUT_NOTE = "No payment integration is configured: an approved claim records a decision only and no money is paid."

class PolicyIn(BaseModel):
    farmer_email: str
    crop: str = Field(min_length=2, max_length=60)
    coverage_amount: float = Field(gt=0)
    terms: str = Field(default="", max_length=1000)

class ClaimIn(BaseModel):
    policy_id: int
    description: str = Field(min_length=3, max_length=1000)
    evidence_ref: str = Field(default="", max_length=500)

class DecisionIn(BaseModel):
    approve: bool
    notes: Optional[str] = Field(default=None, max_length=500)

def _p(db, p):
    return {"id": p.id, "farmer_id": p.farmer_id, "farmer_name": db.get(User, p.farmer_id).name, "insurer_id": p.insurer_id,
            "insurer_name": db.get(User, p.insurer_id).name, "crop": p.crop, "coverage_amount": p.coverage_amount, "terms": p.terms, "status": p.status}

def _c(db, c):
    p = db.get(InsurancePolicy, c.policy_id)
    return {"id": c.id, "policy_id": c.policy_id, "crop": p.crop, "farmer_name": db.get(User, p.farmer_id).name, "description": c.description,
            "evidence_ref": c.evidence_ref, "status": c.status, "payout_status": c.payout_status, "payout_note": PAYOUT_NOTE,
            "decision_notes": c.decision_notes, "created_at": c.created_at}

@router.post("/policies", status_code=201)
def create_policy(body: PolicyIn, user=Depends(require_roles("insurer")), db: Session = Depends(get_db)):
    f = db.scalar(select(User).where(User.email == body.farmer_email.strip().lower()))
    if not f or f.role != "farmer":
        raise HTTPException(422, "Farmer account not found for that email")
    p = InsurancePolicy(farmer_id=f.id, insurer_id=user.id, crop=body.crop.strip().lower(), coverage_amount=body.coverage_amount, terms=body.terms)
    db.add(p); db.flush(); notify(db, f.id, "policy_issued", f"{user.name} issued an insurance policy for {p.crop}")
    audit(db, user.id, "policy_create", "policy", p.id); db.commit()
    return _p(db, p)

@router.get("/policies")
def policies(user=Depends(require_roles("farmer", "insurer")), db: Session = Depends(get_db)):
    col = InsurancePolicy.farmer_id if user.role == "farmer" else InsurancePolicy.insurer_id
    return [_p(db, p) for p in db.scalars(select(InsurancePolicy).where(col == user.id).order_by(InsurancePolicy.id.desc())).all()]

@router.post("/claims", status_code=201)
def file_claim(body: ClaimIn, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    p = db.get(InsurancePolicy, body.policy_id)
    if not p or p.farmer_id != user.id or p.status != "ACTIVE":
        raise HTTPException(404, "Active policy not found")
    c = InsuranceClaim(policy_id=p.id, description=body.description, evidence_ref=body.evidence_ref)
    db.add(c); db.flush(); notify(db, p.insurer_id, "claim_filed", f"New claim on policy #{p.id}")
    audit(db, user.id, "claim_file", "insurance_claim", c.id); db.commit()
    return _c(db, c)

@router.get("/claims")
def claims(user=Depends(require_roles("farmer", "insurer")), db: Session = Depends(get_db)):
    col = InsurancePolicy.farmer_id if user.role == "farmer" else InsurancePolicy.insurer_id
    q = select(InsuranceClaim).join(InsurancePolicy, InsurancePolicy.id == InsuranceClaim.policy_id).where(col == user.id).order_by(InsuranceClaim.id.desc())
    return [_c(db, c) for c in db.scalars(q).all()]

@router.post("/claims/{cid}/decision")
def decide(cid: int, body: DecisionIn, user=Depends(require_roles("insurer")), db: Session = Depends(get_db)):
    c = db.get(InsuranceClaim, cid)
    p = db.get(InsurancePolicy, c.policy_id) if c else None
    if not c or p.insurer_id != user.id:
        raise HTTPException(404, "Claim not found")
    if not body.approve and not (body.notes and body.notes.strip()):
        raise HTTPException(422, "Notes are required when rejecting")
    r = db.execute(update(InsuranceClaim).where(InsuranceClaim.id == c.id, InsuranceClaim.status == "SUBMITTED")
                   .values(status="APPROVED" if body.approve else "REJECTED", decision_notes=body.notes, decided_at=datetime.now(timezone.utc)))
    if r.rowcount != 1:
        raise HTTPException(409, "Claim was already decided")
    notify(db, p.farmer_id, "claim_decision", f"Insurance claim #{c.id} was {'approved' if body.approve else 'rejected'}")
    audit(db, user.id, "claim_decision", "insurance_claim", c.id); db.commit(); db.refresh(c)
    return _c(db, c)
