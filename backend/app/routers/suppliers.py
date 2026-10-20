from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.deps import require_roles, audit
from app.models import SupplierProduct, User

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=40)
    price: float = Field(gt=0)
    unit: str = Field(default="kg", max_length=20)

def _d(db, p):
    return {"id": p.id, "supplier_id": p.supplier_id, "supplier": db.get(User, p.supplier_id).name, "name": p.name, "category": p.category,
            "price": p.price, "unit": p.unit, "authenticity_note": p.authenticity_note, "created_at": p.created_at}

@router.get("/products")
def products(db: Session = Depends(get_db)):
    return [_d(db, p) for p in db.scalars(select(SupplierProduct).order_by(SupplierProduct.id.desc())).all()]

@router.post("/products", status_code=201)
def create(body: ProductIn, user=Depends(require_roles("supplier")), db: Session = Depends(get_db)):
    p = SupplierProduct(supplier_id=user.id, name=body.name.strip(), category=body.category.strip().lower(), price=body.price, unit=body.unit)
    db.add(p); db.flush(); audit(db, user.id, "product_create", "product", p.id); db.commit()
    return _d(db, p)

@router.delete("/products/{pid}")
def delete(pid: int, user=Depends(require_roles("supplier")), db: Session = Depends(get_db)):
    p = db.get(SupplierProduct, pid)
    if not p or p.supplier_id != user.id:
        raise HTTPException(404, "Product not found")
    db.delete(p); audit(db, user.id, "product_delete", "product", pid); db.commit()
    return {"deleted": pid}
