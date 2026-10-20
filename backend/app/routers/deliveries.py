from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import get_current_user, require_roles, audit
from app.models import Delivery, Agreement, CustodyEvent, User
from app.schemas import DeliveryUpdate
from app.services import trade
from app.services.notify import notify

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

def _can_view(db: Session, d: Delivery, u: User) -> bool:
    a = db.get(Agreement, d.agreement_id)
    return (u.role == "admin" or u.id in (a.buyer_id, a.seller_id) or d.transporter_id == u.id
            or (u.role == "transporter" and d.transporter_id is None))

@router.get("")
def list_deliveries(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Delivery).order_by(Delivery.id.desc())
    if user.role == "transporter":
        q = q.where(or_(Delivery.transporter_id == user.id, Delivery.transporter_id.is_(None)))
    elif user.role != "admin":
        q = q.join(Agreement, Agreement.id == Delivery.agreement_id).where(
            or_(Agreement.buyer_id == user.id, Agreement.seller_id == user.id))
    return [trade.delivery_dict(db, d) for d in db.scalars(q).all()]

@router.post("/{delivery_id}/claim")
def claim(delivery_id: int, user: User = Depends(require_roles("transporter")), db: Session = Depends(get_db)):
    r = db.execute(update(Delivery).where(Delivery.id == delivery_id, Delivery.transporter_id.is_(None),
                                          Delivery.status == "PENDING").values(transporter_id=user.id))
    if r.rowcount != 1:
        raise HTTPException(409, "Delivery not found or already claimed")
    audit(db, user.id, "delivery_claim", "delivery", delivery_id); db.commit()
    return trade.delivery_dict(db, db.get(Delivery, delivery_id))

@router.post("/{delivery_id}/update")
def update_status(delivery_id: int, body: DeliveryUpdate, user: User = Depends(require_roles("transporter")),
                  db: Session = Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    trade.advance_delivery(db, user, d, body.status, body.note)
    ag = db.get(Agreement, d.agreement_id)
    for uid in (ag.buyer_id, ag.seller_id):
        notify(db, uid, "delivery_update", f"Delivery #{d.id} is now {body.status}")
    audit(db, user.id, "delivery_" + body.status.lower(), "delivery", d.id); db.commit()
    return trade.delivery_dict(db, d)

@router.get("/{delivery_id}/custody")
def custody(delivery_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d or not _can_view(db, d, user):
        raise HTTPException(404, "Delivery not found")
    evs = db.scalars(select(CustodyEvent).where(CustodyEvent.delivery_id == d.id).order_by(CustodyEvent.id)).all()
    return {"delivery_id": d.id, "status": d.status,
            "note": "Custody events are application records; live GPS tracking is not integrated.",
            "events": [{"event": e.event, "actor_role": e.actor_role, "note": e.note, "created_at": e.created_at} for e in evs]}
