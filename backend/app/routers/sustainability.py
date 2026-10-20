from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.adapters.ledger import metadata_hash
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import Farm, SustainabilityClaim, RewardTransaction
from app.services.notify import notify

router = APIRouter(prefix="/sustainability", tags=["sustainability"])
reviewer = require_roles("quality_verifier", "admin")
farmer_only = require_roles("farmer")

# Configurable, transparent reward rules (edit here to change the policy).
RULES = {
    "water_saving": {"label": "Water saving", "type": "per_unit", "rate": 0.01, "cap": 500.0, "unit": "litres saved",
                     "method": "0.01 points per litre saved, capped at 500 points", "evidence": "Irrigation log or meter reading reference"},
    "soil_health": {"label": "Soil health", "type": "flat", "points": 50.0,
                    "method": "50 points per verified soil-test or soil-improvement claim", "evidence": "Soil test report reference"},
    "regenerative": {"label": "Regenerative practice", "type": "flat", "points": 75.0,
                     "method": "75 points per verified regenerative-practice claim", "evidence": "Practice record or photo reference"},
}
LEDGER_NOTE = ("Reward ledger entries are SIMULATED. A ledger entry shows that a reward was recorded; it does not "
               "independently validate the physical measurement behind a claim.")

def compute(claim_type: str, amount: float):
    r = RULES[claim_type]
    if r["type"] == "per_unit":
        raw = amount * r["rate"]; pts = min(round(raw, 2), r["cap"])
        return pts, f"{amount} {r['unit']} x {r['rate']} = {round(raw, 2)}, cap {r['cap']} -> {pts} points"
    return r["points"], f"Flat rule: {r['points']} points"

def issue_reward(db: Session, claim: SustainabilityClaim) -> RewardTransaction:
    if claim.status != "VERIFIED":
        raise HTTPException(409, "Only verified claims are eligible for rewards")
    if db.scalar(select(RewardTransaction).where(RewardTransaction.claim_id == claim.id)):
        raise HTTPException(409, "A reward was already issued for this claim")
    farm = db.get(Farm, claim.farm_id)
    pts, text = compute(claim.claim_type, claim.amount)
    h = metadata_hash({"claim_id": claim.id, "type": claim.claim_type, "points": pts})
    rw = RewardTransaction(claim_id=claim.id, user_id=farm.owner_id, points=pts, rule=text)
    db.add(rw)
    try:
        db.flush()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A reward was already issued for this claim")
    rw.transaction_ref = f"SIM-RWD-{rw.id:06d}-{h[2:10]}"
    notify(db, farm.owner_id, "reward_issued", f"{pts} reward points issued for claim #{claim.id}")
    return rw

def claim_dict(db: Session, c: SustainabilityClaim) -> dict:
    farm = db.get(Farm, c.farm_id)
    rw = db.scalar(select(RewardTransaction).where(RewardTransaction.claim_id == c.id))
    return {"id": c.id, "farm_id": c.farm_id, "farm": farm.name, "claim_type": c.claim_type, "amount": c.amount,
            "description": c.description, "evidence_ref": c.evidence_ref, "status": c.status,
            "verification_source": "Quality verifier review" if c.reviewer_id else None,
            "review_notes": c.review_notes, "reviewed_at": c.reviewed_at, "created_at": c.created_at,
            "reward_points": rw.points if rw else None}

class FarmIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=60)
    area_acres: float = Field(default=0, ge=0)
    practices: str = Field(default="", max_length=1000)

class ClaimIn(BaseModel):
    farm_id: int
    claim_type: Literal["water_saving", "soil_health", "regenerative"]
    amount: float = Field(default=0, ge=0)
    description: str = Field(default="", max_length=1000)
    evidence_ref: str = Field(min_length=3, max_length=500)

class ReviewIn(BaseModel):
    approve: bool
    notes: Optional[str] = Field(default=None, max_length=500)

@router.get("/rules")
def rules():
    return {"rules": RULES, "note": LEDGER_NOTE}

@router.post("/farms", status_code=201)
def create_farm(body: FarmIn, user=Depends(farmer_only), db: Session = Depends(get_db)):
    f = Farm(owner_id=user.id, name=body.name.strip(), region=body.region.strip().lower(), area_acres=body.area_acres, practices=body.practices)
    db.add(f); db.flush(); audit(db, user.id, "farm_create", "farm", f.id); db.commit()
    return {"id": f.id, "name": f.name, "region": f.region, "area_acres": f.area_acres, "practices": f.practices}

@router.get("/farms")
def list_farms(user=Depends(farmer_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(Farm).where(Farm.owner_id == user.id).order_by(Farm.id)).all()
    return [{"id": f.id, "name": f.name, "region": f.region, "area_acres": f.area_acres, "practices": f.practices} for f in rows]

@router.post("/claims", status_code=201)
def submit_claim(body: ClaimIn, user=Depends(farmer_only), db: Session = Depends(get_db)):
    farm = db.get(Farm, body.farm_id)
    if not farm or farm.owner_id != user.id:
        raise HTTPException(404, "Farm not found")
    if body.claim_type == "water_saving" and body.amount <= 0:
        raise HTTPException(422, "Water-saving claims need the litres saved (amount > 0)")
    c = SustainabilityClaim(farm_id=farm.id, submitted_by=user.id, claim_type=body.claim_type, amount=body.amount,
                            description=body.description, evidence_ref=body.evidence_ref)
    db.add(c); db.flush(); audit(db, user.id, "claim_submit", "claim", c.id); db.commit()
    return claim_dict(db, c)

@router.get("/claims")
def list_claims(user=Depends(require_roles("farmer", "quality_verifier", "admin")), db: Session = Depends(get_db)):
    q = select(SustainabilityClaim).order_by(SustainabilityClaim.id.desc())
    if user.role == "farmer":
        q = q.join(Farm, Farm.id == SustainabilityClaim.farm_id).where(Farm.owner_id == user.id)
    return [claim_dict(db, c) for c in db.scalars(q).all()]

@router.post("/claims/{claim_id}/review")
def review(claim_id: int, body: ReviewIn, user=Depends(reviewer), db: Session = Depends(get_db)):
    c = db.get(SustainabilityClaim, claim_id)
    if not c:
        raise HTTPException(404, "Claim not found")
    if not body.approve and not (body.notes and body.notes.strip()):
        raise HTTPException(422, "Notes are required when rejecting a claim")
    r = db.execute(update(SustainabilityClaim).where(SustainabilityClaim.id == c.id, SustainabilityClaim.status == "SUBMITTED")
                   .values(status="VERIFIED" if body.approve else "REJECTED", reviewer_id=user.id,
                           review_notes=body.notes, reviewed_at=datetime.now(timezone.utc)))
    if r.rowcount != 1:
        raise HTTPException(409, "Claim was already reviewed")
    db.refresh(c)
    farm = db.get(Farm, c.farm_id)
    if body.approve:
        issue_reward(db, c)
    else:
        notify(db, farm.owner_id, "claim_rejected", f"Sustainability claim #{c.id} was rejected")
    audit(db, user.id, "claim_approve" if body.approve else "claim_reject", "claim", c.id, body.notes or ""); db.commit()
    return claim_dict(db, c)

@router.post("/claims/{claim_id}/issue-reward", status_code=201)
def issue(claim_id: int, user=Depends(reviewer), db: Session = Depends(get_db)):
    c = db.get(SustainabilityClaim, claim_id)
    if not c:
        raise HTTPException(404, "Claim not found")
    rw = issue_reward(db, c)
    audit(db, user.id, "reward_issue", "claim", c.id); db.commit()
    return {"claim_id": c.id, "points": rw.points, "transaction_ref": rw.transaction_ref}

@router.get("/rewards")
def rewards(user=Depends(farmer_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(RewardTransaction).where(RewardTransaction.user_id == user.id).order_by(RewardTransaction.id.desc())).all()
    return [{"id": r.id, "claim_id": r.claim_id, "points": r.points, "rule": r.rule, "transaction_ref": r.transaction_ref,
             "ledger_status": r.ledger_status, "created_at": r.created_at} for r in rows]

@router.get("/report")
def report(user=Depends(farmer_only), db: Session = Depends(get_db)):
    claims = db.scalars(select(SustainabilityClaim).join(Farm, Farm.id == SustainabilityClaim.farm_id)
                        .where(Farm.owner_id == user.id)).all()
    verified = [c for c in claims if c.status == "VERIFIED"]
    pending = [c for c in claims if c.status == "SUBMITTED"]
    pts = db.scalars(select(RewardTransaction.points).where(RewardTransaction.user_id == user.id)).all()
    missing = []
    if not claims: missing.append("No sustainability claims submitted yet")
    if pending: missing.append(f"{len(pending)} claim(s) awaiting review are excluded")
    return {"period": "All recorded activity", "calculation_date": datetime.now(timezone.utc).isoformat(),
            "verified_claims": len(verified), "pending_claims": len(pending), "total_points": round(sum(pts), 2),
            "by_type": {t: len([c for c in verified if c.claim_type == t]) for t in RULES},
            "method": {t: RULES[t]["method"] for t in RULES},
            "data_sources": "Farmer-submitted evidence references reviewed by a quality verifier",
            "assumptions": "Quantities are as declared by the farmer; evidence files are references, not uploaded documents",
            "missing_data": missing,
            "limitations": "Reward points are programme points, not certified carbon credits. " + LEDGER_NOTE}
