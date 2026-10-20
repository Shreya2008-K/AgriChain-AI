from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, get_current_user, audit
from app.models import DataPermission, User, Farm, CropBatch, SustainabilityClaim, RewardTransaction
from app.services.notify import notify

router = APIRouter(prefix="/permissions", tags=["permissions"])
GRANTEE_ROLES = ("lender", "insurer", "cooperative", "agronomist")
REVOKE_NOTE = ("Revoking stops all future access. Information the recipient already viewed, copied or exported "
               "before revocation cannot be technically recalled.")

def _naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class GrantIn(BaseModel):
    grantee_email: str
    purpose: str = Field(min_length=3, max_length=300)
    days: Optional[int] = Field(default=None, ge=1, le=365)

def _dict(db, p: DataPermission) -> dict:
    g, o = db.get(User, p.grantee_id), db.get(User, p.owner_id)
    return {"id": p.id, "owner_id": p.owner_id, "owner_name": o.name, "grantee_id": p.grantee_id, "grantee_name": g.name,
            "grantee_role": g.role, "scope": p.scope, "purpose": p.purpose, "status": p.status,
            "expires_at": p.expires_at, "created_at": p.created_at, "revoked_at": p.revoked_at}

@router.post("", status_code=201)
def grant(body: GrantIn, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    g = db.scalar(select(User).where(User.email == body.grantee_email.strip().lower()))
    if not g or g.role not in GRANTEE_ROLES:
        raise HTTPException(422, f"Recipient must be an existing {', '.join(GRANTEE_ROLES)} account")
    if db.scalar(select(DataPermission).where(DataPermission.owner_id == user.id, DataPermission.grantee_id == g.id,
                                              DataPermission.status == "ACTIVE")):
        raise HTTPException(409, "An active permission for this recipient already exists")
    p = DataPermission(owner_id=user.id, grantee_id=g.id, purpose=body.purpose,
                       expires_at=_naive_now() + timedelta(days=body.days) if body.days else None)
    db.add(p); db.flush()
    notify(db, g.id, "permission_granted", f"{user.name} shared a farm report with you")
    audit(db, user.id, "permission_grant", "permission", p.id, g.email); db.commit()
    return {**_dict(db, p), "note": REVOKE_NOTE}

@router.get("")
def list_permissions(user=Depends(get_current_user), db: Session = Depends(get_db)):
    col = DataPermission.owner_id if user.role == "farmer" else DataPermission.grantee_id
    return [_dict(db, p) for p in db.scalars(select(DataPermission).where(col == user.id).order_by(DataPermission.id.desc())).all()]

@router.post("/{perm_id}/revoke")
def revoke(perm_id: int, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    p = db.get(DataPermission, perm_id)
    if not p or p.owner_id != user.id:
        raise HTTPException(404, "Permission not found")
    r = db.execute(update(DataPermission).where(DataPermission.id == p.id, DataPermission.status == "ACTIVE")
                   .values(status="REVOKED", revoked_at=_naive_now()))
    if r.rowcount != 1:
        raise HTTPException(409, "Permission is already revoked")
    notify(db, p.grantee_id, "permission_revoked", f"{user.name} revoked your access to their farm report")
    audit(db, user.id, "permission_revoke", "permission", p.id); db.commit(); db.refresh(p)
    return {**_dict(db, p), "note": REVOKE_NOTE}

@router.get("/report/{farmer_id}")
def farm_report(farmer_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    allowed = user.id == farmer_id and user.role == "farmer"
    if not allowed:  # admins get no automatic access to private farm data
        now = _naive_now()
        allowed = db.scalar(select(func.count()).select_from(DataPermission).where(
            DataPermission.owner_id == farmer_id, DataPermission.grantee_id == user.id, DataPermission.scope == "farm_report",
            DataPermission.status == "ACTIVE", (DataPermission.expires_at.is_(None)) | (DataPermission.expires_at > now))) > 0
    if not allowed:
        raise HTTPException(403, "No active permission to view this report")
    owner = db.get(User, farmer_id)
    farms = db.scalars(select(Farm).where(Farm.owner_id == farmer_id)).all()
    batches = db.scalars(select(CropBatch).where(CropBatch.owner_id == farmer_id)).all()
    by_status = {}
    for b in batches: by_status[b.status] = by_status.get(b.status, 0) + 1
    verified = db.scalar(select(func.count()).select_from(SustainabilityClaim).join(Farm, Farm.id == SustainabilityClaim.farm_id)
                         .where(Farm.owner_id == farmer_id, SustainabilityClaim.status == "VERIFIED"))
    pts = db.scalars(select(RewardTransaction.points).where(RewardTransaction.user_id == farmer_id)).all()
    audit(db, user.id, "report_view", "farm_report", farmer_id); db.commit()
    return {"farmer": owner.name, "farms": [{"name": f.name, "region": f.region, "area_acres": f.area_acres, "practices": f.practices} for f in farms],
            "batches_by_status": by_status, "verified_sustainability_claims": verified, "reward_points": round(sum(pts), 2),
            "note": "Shared with consent. Exact field locations and personal details are not included."}
