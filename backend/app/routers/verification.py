from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import CropBatch, User
from app.schemas import BatchOut, VerifyIn
from app.services import batches as svc
from app.services.notify import notify

router = APIRouter(prefix="/verification", tags=["verification"])
verifier = require_roles("quality_verifier", "admin")

@router.get("/queue", response_model=list[BatchOut])
def queue(user: User = Depends(verifier), db: Session = Depends(get_db)):
    return db.scalars(select(CropBatch).where(CropBatch.status == "QUALITY_PENDING").order_by(CropBatch.id)).all()

@router.post("/{batch_id}/decision", response_model=BatchOut)
def decide(batch_id: int, body: VerifyIn, user: User = Depends(verifier), db: Session = Depends(get_db)):
    b = db.get(CropBatch, batch_id)
    if not b:
        raise HTTPException(404, "Batch not found")
    if not body.approve and not (body.reason and body.reason.strip()):
        raise HTTPException(422, "A reason is required when rejecting a batch")
    if body.approve:
        svc.advance(db, b, "QUALITY_VERIFIED", user, body.reason or "Approved")
    else:
        svc.advance(db, b, "QUALITY_REJECTED", user, body.reason)
        b.rejection_reason = body.reason
    audit(db, user.id, "verification_approve" if body.approve else "verification_reject", "batch", b.id, body.reason or "")
    notify(db, b.owner_id, "verification_decision", f"Batch #{b.id} was {'approved' if body.approve else 'rejected'}")
    db.commit()
    return b
