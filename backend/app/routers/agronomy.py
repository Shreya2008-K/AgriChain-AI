from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, get_current_user, audit
from app.models import AgroCase, AgroNote, User
from app.services.notify import notify

router = APIRouter(prefix="/agronomy", tags=["agronomy"])

class CaseIn(BaseModel):
    agronomist_id: int
    topic: str = Field(min_length=3, max_length=200)

class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    kind: Literal["OBSERVATION", "RECOMMENDATION"] = "OBSERVATION"

def _case_dict(db, c):
    return {"id": c.id, "topic": c.topic, "status": c.status, "farmer_id": c.farmer_id, "farmer_name": db.get(User, c.farmer_id).name,
            "agronomist_id": c.agronomist_id, "agronomist_name": db.get(User, c.agronomist_id).name, "created_at": c.created_at}

def _party(db, case_id, user):
    c = db.get(AgroCase, case_id)
    if not c or user.id not in (c.farmer_id, c.agronomist_id):
        raise HTTPException(404, "Case not found")
    return c

@router.post("/cases", status_code=201)
def open_case(body: CaseIn, user=Depends(require_roles("farmer")), db: Session = Depends(get_db)):
    a = db.get(User, body.agronomist_id)
    if not a or a.role != "agronomist":
        raise HTTPException(404, "Agronomist not found")
    c = AgroCase(farmer_id=user.id, agronomist_id=a.id, topic=body.topic)
    db.add(c); db.flush(); notify(db, a.id, "case_assigned", f"New field case from {user.name}")
    audit(db, user.id, "case_open", "case", c.id); db.commit()
    return _case_dict(db, c)

@router.get("/cases")
def cases(user=Depends(require_roles("farmer", "agronomist")), db: Session = Depends(get_db)):
    col = AgroCase.farmer_id if user.role == "farmer" else AgroCase.agronomist_id
    return [_case_dict(db, c) for c in db.scalars(select(AgroCase).where(col == user.id).order_by(AgroCase.id.desc())).all()]

@router.get("/cases/{cid}")
def case_detail(cid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = _party(db, cid, user)
    notes = db.scalars(select(AgroNote).where(AgroNote.case_id == c.id).order_by(AgroNote.id)).all()
    return {**_case_dict(db, c), "notes": [{"kind": n.kind, "text": n.text, "author": db.get(User, n.author_id).name, "created_at": n.created_at} for n in notes]}

@router.post("/cases/{cid}/notes", status_code=201)
def add_note(cid: int, body: NoteIn, user=Depends(require_roles("farmer", "agronomist")), db: Session = Depends(get_db)):
    c = _party(db, cid, user)
    if c.status != "OPEN":
        raise HTTPException(409, "Case is closed")
    kind = body.kind if user.role == "agronomist" else "FARMER_NOTE"
    db.add(AgroNote(case_id=c.id, author_id=user.id, kind=kind, text=body.text))
    other = c.farmer_id if user.role == "agronomist" else c.agronomist_id
    notify(db, other, "case_note", f"New note on case #{c.id}")
    audit(db, user.id, "case_note", "case", c.id); db.commit()
    return {"ok": True}

@router.post("/cases/{cid}/close")
def close(cid: int, user=Depends(require_roles("agronomist")), db: Session = Depends(get_db)):
    c = _party(db, cid, user)
    if c.status != "OPEN":
        raise HTTPException(409, "Case already closed")
    c.status = "CLOSED"; audit(db, user.id, "case_close", "case", c.id); db.commit()
    return _case_dict(db, c)
