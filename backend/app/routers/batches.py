from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import CropBatch, User
from app.schemas import BatchCreate, BatchOut, HarvestIn, ListIn, EventOut
from app.services import batches as svc

router = APIRouter(prefix="/batches", tags=["batches"])
farmer = require_roles("farmer")
staff = require_roles("farmer", "admin", "quality_verifier")

@router.post("", response_model=BatchOut, status_code=201)
def create(body: BatchCreate, user: User = Depends(farmer), db: Session = Depends(get_db)):
    data = body.model_dump()
    data["crop"] = data["crop"].strip().lower(); data["region"] = data["region"].strip().lower()
    b = svc.register(db, user, **data)
    audit(db, user.id, "batch_create", "batch", b.id); db.commit()
    return b

@router.get("", response_model=list[BatchOut])
def list_batches(user: User = Depends(staff), db: Session = Depends(get_db)):
    q = select(CropBatch).order_by(CropBatch.id.desc())
    if user.role == "farmer":
        q = q.where(CropBatch.owner_id == user.id)
    return db.scalars(q).all()

def _readable(db, batch_id, user):
    b = db.get(CropBatch, batch_id)
    if not b or (user.role == "farmer" and b.owner_id != user.id):
        raise HTTPException(404, "Batch not found")
    return b

@router.get("/{batch_id}", response_model=BatchOut)
def get_one(batch_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return _readable(db, batch_id, user)

@router.get("/{batch_id}/provenance")
def provenance(batch_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    b = _readable(db, batch_id, user)
    return {"batch_id": b.id, "status": b.status, "notice": svc.NOTICE,
            "events": [EventOut.model_validate(e) for e in b.events]}

@router.post("/{batch_id}/harvest", response_model=BatchOut)
def harvest(batch_id: int, body: HarvestIn, user: User = Depends(farmer), db: Session = Depends(get_db)):
    b = svc.get_owned(db, batch_id, user)
    svc.advance(db, b, "HARVEST_RECORDED", user, body.note, {"harvest_date": body.harvest_date.isoformat()})
    b.harvest_date = body.harvest_date
    audit(db, user.id, "harvest_record", "batch", b.id); db.commit()
    return b

@router.post("/{batch_id}/submit-verification", response_model=BatchOut)
def submit(batch_id: int, user: User = Depends(farmer), db: Session = Depends(get_db)):
    b = svc.get_owned(db, batch_id, user)
    svc.advance(db, b, "QUALITY_PENDING", user, "Submitted for quality verification")
    audit(db, user.id, "verification_request", "batch", b.id); db.commit()
    return b

@router.post("/{batch_id}/list", response_model=BatchOut)
def list_for_sale(batch_id: int, body: ListIn, user: User = Depends(farmer), db: Session = Depends(get_db)):
    b = svc.get_owned(db, batch_id, user)
    svc.list_batch(db, b, user, body.asking_price)
    audit(db, user.id, "batch_list", "batch", b.id); db.commit()
    return b
