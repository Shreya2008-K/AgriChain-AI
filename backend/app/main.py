from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import APP_ENV, CORS_ORIGINS
from app.core.db import Base, engine, SessionLocal
from app import models  # noqa: F401  (register tables)
from app.seed import seed
from sqlalchemy import select
from app.routers import auth, batches, verification, marketplace, predictions, offers, agreements, deliveries, sustainability, permissions, notifications, admin, analytics, directory, cooperatives, agronomy, suppliers, lending, insurance

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(models.User)):
            seed(db)
    yield

prod = APP_ENV == "production"
app = FastAPI(title="AgriChain AI API", version="0.2.0", lifespan=lifespan,
              docs_url=None if prod else "/docs", redoc_url=None if prod else "/redoc")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "ledger": "LOCAL_SIMULATOR"}

for r in (auth, batches, verification, marketplace, predictions, offers, agreements, deliveries, sustainability, permissions, notifications, admin, analytics, directory, cooperatives, agronomy, suppliers, lending, insurance):
    app.include_router(r.router, prefix="/api/v1")
