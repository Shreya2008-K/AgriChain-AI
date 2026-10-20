import os, tempfile
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db").replace("\\", "/"))
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

def make_listed(qty):
    f, v = login("farmer"), login("quality_verifier")
    bid = client.post(f"{P}/batches", headers=f, json={"crop": "rice", "quantity": qty, "region": "tamil_nadu"}).json()["id"]
    client.post(f"{P}/batches/{bid}/harvest", headers=f, json={"harvest_date": "2026-10-01"})
    client.post(f"{P}/batches/{bid}/submit-verification", headers=f)
    client.post(f"{P}/verification/{bid}/decision", headers=v, json={"approve": True, "reason": "ok"})
    assert client.post(f"{P}/batches/{bid}/list", headers=f, json={"asking_price": 2000}).status_code == 200
    return bid

def offer(bid, qty, price=2000, who="buyer"):
    return client.post(f"{P}/offers", headers=login(who), json={"batch_id": bid, "quantity": qty, "price_per_unit": price})

def available(bid):
    return client.get(f"{P}/marketplace/{bid}").json()["available_quantity"]

def deliver_all(did):
    t = login("transporter")
    assert client.post(f"{P}/deliveries/{did}/claim", headers=t).status_code == 200
    for s in ["PICKED_UP", "IN_TRANSIT", "DELIVERED"]:
        r = client.post(f"{P}/deliveries/{did}/update", headers=t, json={"status": s, "note": s})
        assert r.status_code == 200, r.text

class TradeTests(unittest.TestCase):
    def test_partial_sale_and_delivery(self):
        bid = make_listed(100)
        o = offer(bid, 40); self.assertEqual(o.status_code, 201)
        oid = o.json()["id"]
        r = client.post(f"{P}/offers/{oid}/accept", headers=login("farmer"))
        self.assertEqual(r.status_code, 201); a = r.json()
        self.assertEqual(a["total_price"], 80000); self.assertIn("SIMULATED", a["payment_note"])
        self.assertEqual(available(bid), 60)
        self.assertEqual(client.post(f"{P}/offers/{oid}/accept", headers=login("farmer")).status_code, 409)  # duplicate
        self.assertEqual(available(bid), 60)
        deliver_all(a["delivery_id"])
        self.assertEqual(client.get(f"{P}/agreements/{a['id']}", headers=login("buyer")).json()["status"], "COMPLETED")
        events = [e["event_type"] for e in client.get(f"{P}/marketplace/{bid}").json()["provenance"]]
        for expected in ["AGREEMENT_CREATED", "DELIVERY_PICKED_UP", "DELIVERY_IN_TRANSIT", "DELIVERY_DELIVERED"]:
            self.assertIn(expected, events)
        cust = client.get(f"{P}/deliveries/{a['delivery_id']}/custody", headers=login("buyer")).json()
        self.assertEqual([e["event"] for e in cust["events"]], ["PICKED_UP", "IN_TRANSIT", "DELIVERED"])
    def test_no_overselling(self):
        bid = make_listed(50)
        a, b = offer(bid, 30).json()["id"], offer(bid, 30).json()["id"]
        f = login("farmer")
        self.assertEqual(client.post(f"{P}/offers/{a}/accept", headers=f).status_code, 201)
        self.assertEqual(client.post(f"{P}/offers/{b}/accept", headers=f).status_code, 409)
        self.assertEqual(available(bid), 20)
        mine = {o["id"]: o["status"] for o in client.get(f"{P}/offers", headers=login("buyer")).json()}
        self.assertEqual(mine[b], "PENDING"); self.assertEqual(mine[a], "ACCEPTED")
    def test_full_allocation_then_sold(self):
        bid = make_listed(50)
        oid = offer(bid, 50).json()["id"]
        other = offer(bid, 10).json()["id"]
        a = client.post(f"{P}/offers/{oid}/accept", headers=login("farmer")).json()
        f = login("farmer")
        self.assertEqual(client.get(f"{P}/batches/{bid}", headers=f).json()["status"], "OFFER_ACCEPTED")
        self.assertEqual(client.get(f"{P}/marketplace/{bid}").status_code, 404)  # no longer listed
        self.assertEqual(offer(bid, 1).status_code, 409)
        mine = {o["id"]: o["status"] for o in client.get(f"{P}/offers", headers=login("buyer")).json()}
        self.assertEqual(mine[other], "REJECTED")
        deliver_all(a["delivery_id"])
        self.assertEqual(client.get(f"{P}/batches/{bid}", headers=f).json()["status"], "SOLD")
        prov = client.get(f"{P}/batches/{bid}/provenance", headers=f).json()["events"]
        self.assertEqual(prov[-1]["to_status"], "SOLD")
        for e in prov: self.assertEqual(e["ledger_status"], "SIMULATED")

class OfferRuleTests(unittest.TestCase):
    def test_offer_too_large_or_unlisted(self):
        bid = make_listed(10)
        self.assertEqual(offer(bid, 11).status_code, 409)
        f = login("farmer")
        draft = client.post(f"{P}/batches", headers=f, json={"crop": "rice", "quantity": 5, "region": "punjab"}).json()["id"]
        self.assertEqual(offer(draft, 1).status_code, 409)
        self.assertEqual(offer(bid, 0).status_code, 422)
    def test_roles(self):
        bid = make_listed(10)
        oid = offer(bid, 5).json()["id"]
        self.assertEqual(offer(bid, 1, who="farmer").status_code, 403)
        self.assertEqual(client.post(f"{P}/offers/{oid}/accept", headers=login("buyer")).status_code, 403)
        tok = client.post(f"{P}/auth/register", json={"email": "f3@y.test", "name": "Farmer Three", "password": "password123", "role": "farmer"}).json()["access_token"]
        self.assertEqual(client.post(f"{P}/offers/{oid}/accept", headers={"Authorization": "Bearer " + tok}).status_code, 404)
    def test_reject_and_withdraw(self):
        bid = make_listed(10)
        o1, o2 = offer(bid, 2).json()["id"], offer(bid, 2).json()["id"]
        self.assertEqual(client.post(f"{P}/offers/{o1}/reject", headers=login("farmer"), json={"reason": "low"}).json()["status"], "REJECTED")
        self.assertEqual(client.post(f"{P}/offers/{o1}/accept", headers=login("farmer")).status_code, 409)
        tok = client.post(f"{P}/auth/register", json={"email": "b2@y.test", "name": "Buyer Two", "password": "password123", "role": "buyer"}).json()["access_token"]
        self.assertEqual(client.post(f"{P}/offers/{o2}/withdraw", headers={"Authorization": "Bearer " + tok}).status_code, 404)
        self.assertEqual(client.post(f"{P}/offers/{o2}/withdraw", headers=login("buyer")).json()["status"], "WITHDRAWN")
        self.assertEqual(client.post(f"{P}/offers/{o2}/accept", headers=login("farmer")).status_code, 409)
    def test_agreement_privacy(self):
        bid = make_listed(10)
        a = client.post(f"{P}/offers/{offer(bid, 2).json()['id']}/accept", headers=login("farmer")).json()
        tok = client.post(f"{P}/auth/register", json={"email": "b3@y.test", "name": "Buyer Three", "password": "password123", "role": "buyer"}).json()["access_token"]
        self.assertEqual(client.get(f"{P}/agreements/{a['id']}", headers={"Authorization": "Bearer " + tok}).status_code, 404)
        self.assertEqual(client.get(f"{P}/agreements/{a['id']}", headers=login("buyer")).status_code, 200)

class DeliveryRuleTests(unittest.TestCase):
    def test_sequence_and_assignment(self):
        bid = make_listed(10)
        a = client.post(f"{P}/offers/{offer(bid, 2).json()['id']}/accept", headers=login("farmer")).json()
        did, t = a["delivery_id"], login("transporter")
        self.assertEqual(client.post(f"{P}/deliveries/{did}/update", headers=t, json={"status": "PICKED_UP"}).status_code, 403)  # unclaimed
        self.assertEqual(client.post(f"{P}/deliveries/{did}/claim", headers=t).status_code, 200)
        self.assertEqual(client.post(f"{P}/deliveries/{did}/claim", headers=t).status_code, 409)
        self.assertEqual(client.post(f"{P}/deliveries/{did}/update", headers=t, json={"status": "DELIVERED"}).status_code, 409)  # skip
        self.assertEqual(client.post(f"{P}/deliveries/{did}/update", headers=login("buyer"), json={"status": "PICKED_UP"}).status_code, 403)
        self.assertEqual(client.post(f"{P}/deliveries/{did}/update", headers=t, json={"status": "PICKED_UP"}).status_code, 200)

if __name__ == "__main__":
    unittest.main()
