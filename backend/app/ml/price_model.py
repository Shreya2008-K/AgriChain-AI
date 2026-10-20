"""Crop price prediction baseline. DATA IS SYNTHETIC (demonstration only), units: INR per quintal."""
import numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

DATA_SOURCE = "SYNTHETIC_DEMO_DATASET"
UNIT = "INR/quintal"
BASE = {"rice": 2200, "wheat": 2300, "tomato": 1800, "maize": 1900}
REGIONS = {"tamil_nadu": 1.00, "karnataka": 0.97, "punjab": 1.04}

class InsufficientDataError(ValueError): pass
class UnsupportedInputError(ValueError): pass

def make_synthetic_data(seed=42, years=4):
    rng = np.random.default_rng(seed)
    rows = []
    for crop, b in BASE.items():
        for region, rf in REGIONS.items():
            for i in range(years * 12):
                m = i % 12 + 1
                season = 1 + 0.08 * np.sin(2 * np.pi * m / 12)
                supply = float(rng.uniform(500, 2000))
                price = b * rf * season * (1 - 0.00003 * (supply - 1250)) * (1 + 0.0025 * i) + rng.normal(0, 25)
                rows.append(dict(crop=crop, region=region, month_index=i, month=m, supply=supply, price=price))
    return pd.DataFrame(rows)

def _features(df):
    X = pd.get_dummies(df[["crop", "region"]]).astype(float)
    X["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    X["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    X["month_index"] = df["month_index"]
    X["supply"] = df["supply"]
    return X

class PriceModel:
    def __init__(self):
        self.model = GradientBoostingRegressor(random_state=0)
        self.columns = None; self.metrics = None; self.resid_q = None; self.max_index = 0

    def train(self, df, holdout_months=6):
        if len(df) < 100: raise InsufficientDataError("Need at least 100 rows to train.")
        cut = df["month_index"].max() - holdout_months
        tr, te = df[df.month_index <= cut], df[df.month_index > cut]
        X = _features(tr); self.columns = list(X.columns)
        self.model.fit(X, tr["price"])
        pred = self.model.predict(_features(te).reindex(columns=self.columns, fill_value=0))
        res = te["price"].values - pred
        self.metrics = {"mae": float(mean_absolute_error(te["price"], pred)), "holdout_rows": int(len(te)),
                        "mean_price": float(te["price"].mean()), "split": "time-based holdout"}
        self.resid_q = (float(np.quantile(res, 0.1)), float(np.quantile(res, 0.9)))
        self.model.fit(_features(df).reindex(columns=self.columns, fill_value=0), df["price"])
        self.max_index = int(df["month_index"].max())
        return self.metrics

    def predict(self, crop, region, month, supply, horizon_months=1):
        if self.columns is None: raise InsufficientDataError("Model not trained.")
        if crop not in BASE: raise UnsupportedInputError(f"Unsupported crop: {crop}")
        if region not in REGIONS: raise UnsupportedInputError(f"Unsupported region: {region}")
        if not 1 <= month <= 12: raise UnsupportedInputError("month must be 1-12")
        if supply <= 0: raise UnsupportedInputError("supply must be positive")
        if not 1 <= horizon_months <= 12: raise UnsupportedInputError("horizon_months must be 1-12")
        row = pd.DataFrame([dict(crop=crop, region=region, month=month, supply=supply,
                                 month_index=self.max_index + horizon_months)])
        X = _features(row).reindex(columns=self.columns, fill_value=0)
        p = float(self.model.predict(X)[0])
        return {"predicted_price": round(p, 2), "unit": UNIT, "data_source": DATA_SOURCE, "is_demonstration": True,
                "range_80pct": [round(p + self.resid_q[0], 2), round(p + self.resid_q[1], 2)],
                "range_method": "10th-90th percentile of holdout residuals; uncertain, not a guarantee",
                "model_mae": round(self.metrics["mae"], 2),
                "limitations": "Trained on synthetic data; not a real market forecast."}
