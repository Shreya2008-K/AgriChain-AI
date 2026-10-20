"""Lifecycle service. Reuses the ledger adapter's canonical hashing and state machine.
Ledger entries are SIMULATED (SIM- ids); they are persisted in provenance_events."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.adapters.ledger import TRANSITIONS, metadata_hash, SimulatedLedger
from app.models import CropBatch, ProvenanceEvent, User

NETWORK = SimulatedLedger.network
NOTICE = ("Ledger entries are SIMULATED by a local simulator, not a real blockchain. A ledger entry records that a "
          "status change was submitted; it does not prove the physical accuracy of any crop claim.")

def _record(db: Session, batch: CropBatch, from_status, to_status, user: User, note: str, extra=None, event_type=None) -> ProvenanceEvent:
    meta = {"batch_id": batch.id, "from": from_status, "to": to_status, "actor_id": user.id, "note": note, **(extra or {})}
    h = metadata_hash(meta)
    ev = ProvenanceEvent(batch_id=batch.id, event_type=event_type or to_status, actor_id=user.id, actor_role=user.role, from_status=from_status,
                         to_status=to_status, note=note, metadata_hash=h, transaction_ref=f"PENDING-{h[2:18]}",
                         ledger_status="SIMULATED", network=NETWORK)
    db.add(ev); db.flush()
    ev.transaction_ref = f"SIM-{ev.id:06d}-{h[2:10]}"
    return ev

def register(db: Session, user: User, **fields) -> CropBatch:
    batch = CropBatch(owner_id=user.id, status="REGISTERED", **fields)
    db.add(batch); db.flush()
    _record(db, batch, None, "REGISTERED", user, "Batch registered")
    return batch

def advance(db: Session, batch: CropBatch, to_status: str, user: User, note: str = "", extra=None) -> ProvenanceEvent:
    if to_status not in TRANSITIONS.get(batch.status, set()):
        raise HTTPException(409, f"Invalid transition {batch.status} -> {to_status}")
    ev = _record(db, batch, batch.status, to_status, user, note, extra)
    batch.status = to_status
    return ev

def get_owned(db: Session, batch_id: int, user: User) -> CropBatch:
    b = db.get(CropBatch, batch_id)
    if not b or (b.owner_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Batch not found")  # 404 avoids leaking existence
    return b


def note_event(db: Session, batch: CropBatch, user: User, event_type: str, note: str, extra=None) -> ProvenanceEvent:
    """Provenance/ledger entry that does not change the batch status (agreements, custody)."""
    return _record(db, batch, batch.status, batch.status, user, note, extra, event_type=event_type)

def list_batch(db: Session, batch: CropBatch, user: User, asking_price: float) -> None:
    advance(db, batch, "LISTED", user, "Listed on marketplace", {"asking_price": asking_price})
    batch.asking_price = asking_price
    batch.available_quantity = batch.quantity
