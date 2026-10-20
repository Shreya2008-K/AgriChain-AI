from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.models import CropBatch
from app.schemas import EventOut
from app.services.batches import NOTICE

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

def _pub(b: CropBatch):
    return {"id": b.id, "crop": b.crop, "variety": b.variety, "quantity": b.quantity, "available_quantity": b.available_quantity, "unit": b.unit,
            "asking_price": b.asking_price, "region": b.region, "harvest_date": b.harvest_date,
            "status": b.status, "farmer": b.owner.name}

@router.get("")
def browse(crop: Optional[str] = None, region: Optional[str] = None, max_price: Optional[float] = None,
           db: Session = Depends(get_db)):
    q = select(CropBatch).where(CropBatch.status == "LISTED")
    if crop: q = q.where(CropBatch.crop == crop.lower())
    if region: q = q.where(CropBatch.region == region.lower())
    if max_price is not None: q = q.where(CropBatch.asking_price <= max_price)
    return [_pub(b) for b in db.scalars(q.order_by(CropBatch.id.desc())).all()]

@router.get("/{batch_id}")
def detail(batch_id: int, db: Session = Depends(get_db)):
    b = db.get(CropBatch, batch_id)
    if not b or b.status != "LISTED":
        raise HTTPException(404, "Listing not found")
    events = [EventOut.model_validate(e).model_dump(exclude={"id"}) for e in b.events]
    return {**_pub(b), "notice": NOTICE, "provenance": events}
