"""Seed demo data. Usage (from backend/):  python -m app.seed [--reset]
Demo passwords are for LOCAL DEMONSTRATION ONLY."""
import os, sys
from datetime import date
from sqlalchemy import select
from app.core.db import Base, engine, SessionLocal
from app import models
from app.core.security import hash_password
from app.services import batches as svc

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@12345")
ROLES = ["farmer", "buyer", "admin", "cooperative", "agronomist", "supplier", "transporter",
         "lender", "insurer", "quality_verifier"]

def seed(db):
    users = {}
    for role in ROLES:
        email = f"{role}@demo.agrichain.test"
        u = db.scalar(select(models.User).where(models.User.email == email))
        if not u:
            u = models.User(email=email, name=f"Demo {role.replace('_', ' ').title()}", role=role,
                            password_hash=hash_password(DEMO_PASSWORD))
            db.add(u); db.flush()
        users[role] = u
    if not db.scalar(select(models.CropBatch)):
        f, v = users["farmer"], users["quality_verifier"]
        first = None
        for crop, variety, qty, price, region in [("rice", "Ponni", 120, 2300, "tamil_nadu"),
                                                  ("tomato", "Hybrid", 40, 1900, "karnataka")]:
            b = svc.register(db, f, crop=crop, variety=variety, quantity=qty, unit="quintal",
                             expected_price=price, region=region)
            svc.advance(db, b, "HARVEST_RECORDED", f, "Demo harvest"); b.harvest_date = date(2026, 9, 20)
            svc.advance(db, b, "QUALITY_PENDING", f, "Submitted for quality verification")
            svc.advance(db, b, "QUALITY_VERIFIED", v, "Demo approval")
            svc.list_batch(db, b, f, price)
            first = first or b
        db.add(models.Offer(batch_id=first.id, buyer_id=users["buyer"].id, quantity=20, price_per_unit=2250))
        b = svc.register(db, f, crop="wheat", variety="Sharbati", quantity=60, unit="quintal",
                         expected_price=2400, region="punjab")
        svc.advance(db, b, "HARVEST_RECORDED", f, "Demo harvest"); b.harvest_date = date(2026, 10, 5)
        svc.advance(db, b, "QUALITY_PENDING", f, "Submitted for quality verification")
    if not db.scalar(select(models.Farm)):
        farm = models.Farm(owner_id=users["farmer"].id, name="Demo Farm", region="tamil_nadu", area_acres=5,
                           practices="Drip irrigation, mulching")
        db.add(farm); db.flush()
        db.add(models.SustainabilityClaim(farm_id=farm.id, submitted_by=users["farmer"].id, claim_type="water_saving",
                                          amount=8000, description="Switched to drip irrigation",
                                          evidence_ref="demo-irrigation-log-001"))
    db.commit()

if __name__ == "__main__":
    if os.getenv("APP_ENV") == "production" and "DEMO_PASSWORD" not in os.environ:
        sys.exit("Refusing to seed demo accounts in production without DEMO_PASSWORD set.")
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    print("Seeded. Demo logins: <role>@demo.agrichain.test / " + DEMO_PASSWORD + " (local demo only)")
