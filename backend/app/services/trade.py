"""Offers, agreements, inventory and delivery logic. Payments are SIMULATED (none are collected).
Overselling and duplicate acceptance are prevented with conditional UPDATEs inside one transaction."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from app.models import CropBatch, Offer, Agreement, Delivery, CustodyEvent, User
from app.services import batches as svc

EPS = 1e-9
NEXT_DELIVERY = {"PENDING": "PICKED_UP", "PICKED_UP": "IN_TRANSIT", "IN_TRANSIT": "DELIVERED"}

def _now():
    return datetime.now(timezone.utc)

def offer_dict(db: Session, o: Offer) -> dict:
    b = db.get(CropBatch, o.batch_id)
    return {"id": o.id, "batch_id": o.batch_id, "crop": b.crop, "unit": b.unit, "buyer_id": o.buyer_id,
            "quantity": o.quantity, "price_per_unit": o.price_per_unit, "status": o.status,
            "created_at": o.created_at, "decided_at": o.decided_at}

def agreement_dict(db: Session, a: Agreement) -> dict:
    b = db.get(CropBatch, a.batch_id)
    d = db.scalar(select(Delivery).where(Delivery.agreement_id == a.id))
    return {"id": a.id, "offer_id": a.offer_id, "batch_id": a.batch_id, "crop": b.crop, "unit": b.unit,
            "quantity": a.quantity, "price_per_unit": a.price_per_unit, "total_price": a.total_price,
            "status": a.status, "payment_note": a.payment_note, "delivery_id": d.id if d else None,
            "delivery_status": d.status if d else None, "created_at": a.created_at}

def delivery_dict(db: Session, d: Delivery) -> dict:
    a = db.get(Agreement, d.agreement_id); b = db.get(CropBatch, a.batch_id)
    return {"id": d.id, "agreement_id": a.id, "batch_id": b.id, "crop": b.crop, "quantity": a.quantity,
            "unit": b.unit, "region": b.region, "status": d.status, "transporter_id": d.transporter_id,
            "created_at": d.created_at}

def create_offer(db: Session, buyer: User, batch_id: int, quantity: float, price: float) -> Offer:
    b = db.get(CropBatch, batch_id)
    if not b or b.status != "LISTED":
        raise HTTPException(409, "Batch is not available for offers")
    if quantity > (b.available_quantity or 0) + EPS:
        raise HTTPException(409, f"Only {b.available_quantity} {b.unit} available")
    o = Offer(batch_id=b.id, buyer_id=buyer.id, quantity=quantity, price_per_unit=price)
    db.add(o); db.flush()
    return o

def accept_offer(db: Session, farmer: User, offer_id: int) -> Agreement:
    o = db.get(Offer, offer_id)
    b = db.get(CropBatch, o.batch_id) if o else None
    if not o or b.owner_id != farmer.id:
        raise HTTPException(404, "Offer not found")
    # 1) claim the offer exactly once
    r = db.execute(update(Offer).where(Offer.id == o.id, Offer.status == "PENDING")
                   .values(status="ACCEPTED", decided_at=_now()))
    if r.rowcount != 1:
        raise HTTPException(409, "Offer is no longer pending")
    # 2) reserve inventory atomically; fails (and the whole transaction rolls back) if not enough remains
    r = db.execute(update(CropBatch).where(CropBatch.id == b.id, CropBatch.status == "LISTED",
                                           CropBatch.available_quantity >= o.quantity - EPS)
                   .values(available_quantity=CropBatch.available_quantity - o.quantity))
    if r.rowcount != 1:
        raise HTTPException(409, "Insufficient available quantity")
    db.refresh(b); db.refresh(o)
    a = Agreement(offer_id=o.id, batch_id=b.id, buyer_id=o.buyer_id, seller_id=farmer.id, quantity=o.quantity,
                  price_per_unit=o.price_per_unit, total_price=round(o.quantity * o.price_per_unit, 2))
    db.add(a); db.flush()
    db.add(Delivery(agreement_id=a.id)); db.flush()
    svc.note_event(db, b, farmer, "AGREEMENT_CREATED",
                   f"Agreement #{a.id}: {o.quantity} {b.unit} at {o.price_per_unit}/{b.unit} (payment simulated)",
                   {"agreement_id": a.id, "quantity": o.quantity, "price_per_unit": o.price_per_unit})
    if b.available_quantity <= EPS:
        b.available_quantity = 0.0
        svc.advance(db, b, "OFFER_ACCEPTED", farmer, "Entire quantity allocated to agreements")
        db.execute(update(Offer).where(Offer.batch_id == b.id, Offer.status == "PENDING")
                   .values(status="REJECTED", decided_at=_now()))
    return a

def advance_delivery(db: Session, user: User, d: Delivery, new_status: str, note: str) -> Delivery:
    if d.transporter_id != user.id:
        raise HTTPException(403, "This delivery is not assigned to you")
    if NEXT_DELIVERY.get(d.status) != new_status:
        raise HTTPException(409, f"Invalid delivery transition {d.status} -> {new_status}")
    d.status = new_status
    db.add(CustodyEvent(delivery_id=d.id, actor_id=user.id, actor_role=user.role, event=new_status, note=note))
    a = db.get(Agreement, d.agreement_id); b = db.get(CropBatch, a.batch_id)
    svc.note_event(db, b, user, f"DELIVERY_{new_status}", note or f"Delivery {new_status.lower()}", {"agreement_id": a.id})
    if new_status == "DELIVERED":
        a.status = "COMPLETED"
        db.flush()
        open_count = db.scalar(select(func.count()).select_from(Agreement)
                               .where(Agreement.batch_id == b.id, Agreement.status != "COMPLETED"))
        if b.status == "OFFER_ACCEPTED" and open_count == 0:
            svc.advance(db, b, "SOLD", user, "All agreements delivered")
    return d
