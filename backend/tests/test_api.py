import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db").replace("\\", "/")
import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import Base, engine, SessionLocal
from app.seed import seed, DEMO_PASSWORD

P = "/api/v1"
client = TestClient(app)

def setUpModule():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)

def login(role):
    r = client.post(f"{P}/auth/login", json={"email": f"{role}@demo.agrichain.test", "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}

class AuthTests(unittest.TestCase):
    def test_login_and_me(self):
        r = client.get(f"{P}/auth/me", headers=login("buyer"))
        self.assertEqual(r.json()["role"], "buyer")
    def test_all_demo_roles_login(self):
        for role in ["farmer","buyer","admin","cooperative","agronomist","supplier","transporter","lender","insurer","quality_verifier"]:
            login(role)
    def test_bad_password(self):
        r = client.post(f"{P}/auth/login", json={"email": "farmer@demo.agrichain.test", "password": "wrong-pass"})
        self.assertEqual(r.status_code, 401)
    def test_no_token(self):
        self.assertEqual(client.get(f"{P}/auth/me").status_code, 401)
    def test_cannot_self_register_admin(self):
        r = client.post(f"{P}/auth/register", json={"email": "x@y.test", "name": "Eve", "password": "password123", "role": "admin"})
        self.assertEqual(r.status_code, 403)
    def test_register_and_duplicate(self):
        body = {"email": "new.buyer@y.test", "name": "New Buyer", "password": "password123", "role": "buyer"}
        self.assertEqual(client.post(f"{P}/auth/register", json=body).status_code, 201)
        self.assertEqual(client.post(f"{P}/auth/register", json=body).status_code, 409)

class WorkflowTests(unittest.TestCase):
    def test_farmer_to_marketplace(self):
        f, v = login("farmer"), login("quality_verifier")
        b = client.post(f"{P}/batches", headers=f, json={"crop": "Maize", "quantity": 30, "region": "Tamil_Nadu", "expected_price": 1900}).json()
        bid = b["id"]
        self.assertEqual(b["status"], "REGISTERED")
        self.assertEqual(client.post(f"{P}/batches/{bid}/harvest", headers=f, json={"harvest_date": "2026-10-01"}).status_code, 200)
        self.assertEqual(client.post(f"{P}/batches/{bid}/submit-verification", headers=f).status_code, 200)
        r = client.post(f"{P}/verification/{bid}/decision", headers=v, json={"approve": True, "reason": "Looks good"})
        self.assertEqual(r.json()["status"], "QUALITY_VERIFIED")
        self.assertEqual(client.post(f"{P}/batches/{bid}/list", headers=f, json={"asking_price": 2000}).json()["status"], "LISTED")
        listing = client.get(f"{P}/marketplace/{bid}").json()   # public, no auth
        self.assertEqual(len(listing["provenance"]), 5)
        for e in listing["provenance"]:
            self.assertEqual(e["ledger_status"], "SIMULATED"); self.assertTrue(e["transaction_ref"].startswith("SIM-"))
        self.assertIn(bid, [x["id"] for x in client.get(f"{P}/marketplace").json()])
    def test_invalid_transition(self):
        f = login("farmer")
        bid = client.post(f"{P}/batches", headers=f, json={"crop": "rice", "quantity": 5, "region": "punjab"}).json()["id"]
        self.assertEqual(client.post(f"{P}/batches/{bid}/list", headers=f, json={"asking_price": 10}).status_code, 409)
    def test_unverified_not_public(self):
        f = login("farmer")
        bid = client.post(f"{P}/batches", headers=f, json={"crop": "rice", "quantity": 5, "region": "punjab"}).json()["id"]
        self.assertEqual(client.get(f"{P}/marketplace/{bid}").status_code, 404)
    def test_reject_needs_reason(self):
        f, v = login("farmer"), login("quality_verifier")
        bid = client.post(f"{P}/batches", headers=f, json={"crop": "rice", "quantity": 5, "region": "punjab"}).json()["id"]
        client.post(f"{P}/batches/{bid}/harvest", headers=f, json={"harvest_date": "2026-10-01"})
        client.post(f"{P}/batches/{bid}/submit-verification", headers=f)
        self.assertEqual(client.post(f"{P}/verification/{bid}/decision", headers=v, json={"approve": False}).status_code, 422)
        r = client.post(f"{P}/verification/{bid}/decision", headers=v, json={"approve": False, "reason": "Moisture too high"})
        self.assertEqual(r.json()["status"], "QUALITY_REJECTED")
        self.assertEqual(client.post(f"{P}/batches/{bid}/list", headers=f, json={"asking_price": 10}).status_code, 409)

class AuthorizationTests(unittest.TestCase):
    def test_buyer_cannot_create_batch(self):
        r = client.post(f"{P}/batches", headers=login("buyer"), json={"crop": "rice", "quantity": 5, "region": "punjab"})
        self.assertEqual(r.status_code, 403)
    def test_farmer_cannot_verify(self):
        self.assertEqual(client.post(f"{P}/verification/1/decision", headers=login("farmer"), json={"approve": True}).status_code, 403)
    def test_other_farmer_cannot_see_batch(self):
        body = {"email": "farmer2@y.test", "name": "Farmer Two", "password": "password123", "role": "farmer"}
        tok = client.post(f"{P}/auth/register", json=body).json()["access_token"]
        h2 = {"Authorization": "Bearer " + tok}
        bid = client.post(f"{P}/batches", headers=login("farmer"), json={"crop": "rice", "quantity": 5, "region": "punjab"}).json()["id"]
        self.assertEqual(client.get(f"{P}/batches/{bid}", headers=h2).status_code, 404)
        self.assertEqual(client.post(f"{P}/batches/{bid}/harvest", headers=h2, json={"harvest_date": "2026-10-01"}).status_code, 404)

class PredictionTests(unittest.TestCase):
    def test_predict_ok(self):
        r = client.post(f"{P}/predictions", json={"crop": "rice", "region": "tamil_nadu", "month": 6, "supply": 1000})
        self.assertEqual(r.status_code, 200); self.assertEqual(r.json()["data_source"], "SYNTHETIC_DEMO_DATASET")
    def test_unsupported(self):
        r = client.post(f"{P}/predictions", json={"crop": "durian", "region": "tamil_nadu", "month": 6, "supply": 1000})
        self.assertEqual(r.status_code, 422)
    def test_options_and_health(self):
        self.assertIn("rice", client.get(f"{P}/predictions/options").json()["crops"])
        self.assertEqual(client.get("/health").json()["status"], "ok")

if __name__ == "__main__":
    unittest.main()
