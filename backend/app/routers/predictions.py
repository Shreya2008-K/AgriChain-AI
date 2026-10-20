from functools import lru_cache
from fastapi import APIRouter, HTTPException
from app.ml.price_model import (PriceModel, make_synthetic_data, BASE, REGIONS, DATA_SOURCE, UNIT,
                                UnsupportedInputError, InsufficientDataError)
from app.schemas import PredictIn

router = APIRouter(prefix="/predictions", tags=["predictions"])

@lru_cache(maxsize=1)
def get_model() -> PriceModel:
    m = PriceModel(); m.train(make_synthetic_data()); return m

@router.get("/options")
def options():
    m = get_model()
    return {"crops": sorted(BASE), "regions": sorted(REGIONS), "unit": UNIT, "data_source": DATA_SOURCE,
            "is_demonstration": True, "evaluation": m.metrics,
            "limitations": "Trained on synthetic data; not a real market forecast."}

@router.post("")
def predict(body: PredictIn):
    try:
        return get_model().predict(body.crop.lower(), body.region.lower(), body.month, body.supply, body.horizon_months)
    except UnsupportedInputError as e:
        raise HTTPException(422, str(e))
    except InsufficientDataError as e:
        raise HTTPException(503, str(e))
