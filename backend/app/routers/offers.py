from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import Offer, CropBatch, User
from app.schemas import OfferCreate, RejectIn
from app.services import trade
from app.services.notify import notify

router = APIRouter(prefix="/offers", tags=["offers"])

@router.post("", status_code=201)
def create(body: OfferCreate, user: User = Depends(require_roles("buyer")), db: Session = Depends(get_db)):
    o = trade.create_offer(db, user, body.batch_id, body.quantity, body.price_per_unit)
    nb = db.get(CropBatch, o.batch_id)
    notify(db, nb.owner_id, "offer_received", f"New offer on batch #{nb.id} ({nb.crop})")
    audit(db, user.id, "offer_create", "offer", o.id); db.commit()
    return trade.offer_dict(db, o)

@router.get("")
def list_offers(user: User = Depends(require_roles("buyer", "farmer", "admin")), db: Session = Depends(get_db)):
    q = select(Offer).order_by(Offer.id.desc())
    if user.role == "buyer":
        q = q.where(Offer.buyer_id == user.id)
    elif user.role == "farmer":
        q = q.join(CropBatch, CropBatch.id == Offer.batch_id).where(CropBatch.owner_id == user.id)
    return [trade.offer_dict(db, o) for o in db.scalars(q).all()]

@router.post("/{offer_id}/accept", status_code=201)
def accept(offer_id: int, user: User = Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    a = trade.accept_offer(db, user, offer_id)
    notify(db, a.buyer_id, "offer_accepted", f"Your offer #{offer_id} was accepted (agreement #{a.id})")
    audit(db, user.id, "offer_accept", "offer", offer_id, f"agreement {a.id}"); db.commit()
    return trade.agreement_dict(db, a)

@router.post("/{offer_id}/reject")
def reject(offer_id: int, body: RejectIn, user: User = Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    o = db.get(Offer, offer_id)
    if not o or db.get(CropBatch, o.batch_id).owner_id != user.id:
        raise HTTPException(404, "Offer not found")
    r = db.execute(update(Offer).where(Offer.id == o.id, Offer.status == "PENDING")
                   .values(status="REJECTED", decided_at=datetime.now(timezone.utc)))
    if r.rowcount != 1:
        raise HTTPException(409, "Offer is no longer pending")
    notify(db, o.buyer_id, "offer_rejected", f"Your offer #{o.id} was rejected")
    audit(db, user.id, "offer_reject", "offer", o.id, body.reason or ""); db.commit(); db.refresh(o)
    return trade.offer_dict(db, o)

@router.post("/{offer_id}/withdraw")
def withdraw(offer_id: int, user: User = Depends(require_roles("buyer")), db: Session = Depends(get_db)):
    o = db.get(Offer, offer_id)
    if not o or o.buyer_id != user.id:
        raise HTTPException(404, "Offer not found")
    r = db.execute(update(Offer).where(Offer.id == o.id, Offer.status == "PENDING")
                   .values(status="WITHDRAWN", decided_at=datetime.now(timezone.utc)))
    if r.rowcount != 1:
        raise HTTPException(409, "Offer is no longer pending")
    audit(db, user.id, "offer_withdraw", "offer", o.id); db.commit(); db.refresh(o)
    return trade.offer_dict(db, o)
