from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.ml.price_model import make_synthetic_data, BASE, REGIONS, DATA_SOURCE, UNIT
from app.models import CropBatch

router = APIRouter(prefix="/analytics", tags=["analytics"])

@lru_cache(maxsize=1)
def _history():
    return make_synthetic_data()

@router.get("/market")
def market(db: Session = Depends(get_db)):
    rows = db.execute(select(CropBatch.crop, func.count(), func.coalesce(func.sum(CropBatch.available_quantity), 0), func.avg(CropBatch.asking_price))
                      .where(CropBatch.status == "LISTED").group_by(CropBatch.crop).order_by(CropBatch.crop)).all()
    return {"source": "Live listings in this application's database",
            "crops": [{"crop": c, "listings": n, "available_quantity": float(q), "avg_asking_price": round(float(p), 2) if p is not None else None} for c, n, q, p in rows]}

@router.get("/prices")
def prices(crop: str = "rice", region: str = "tamil_nadu"):
    crop, region = crop.lower(), region.lower()
    if crop not in BASE or region not in REGIONS:
        raise HTTPException(422, "Unsupported crop or region")
    df = _history()
    d = df[(df.crop == crop) & (df.region == region)].sort_values("month_index")
    return {"crop": crop, "region": region, "unit": UNIT, "data_source": DATA_SOURCE, "is_demonstration": True,
            "note": "Synthetic demonstration history (month 1 = start of the generated series), not real market prices.",
            "history": [{"month_index": int(r.month_index) + 1, "price": round(float(r.price), 2)} for r in d.itertuples()]}
