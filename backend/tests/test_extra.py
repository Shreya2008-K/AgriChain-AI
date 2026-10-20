import os, tempfile, uuid
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

def H(role):
    r = client.post(f"{P}/auth/login", json={"email": f"{role}@demo.agrichain.test", "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}

def reg(role):
    email = f"{role}-{uuid.uuid4().hex[:8]}@y.test"
    r = client.post(f"{P}/auth/register", json={"email": email, "name": f"Test {role}", "password": "password123", "role": role})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}, email, r.json()["user"]["id"]

def demo_id(role, name):
    return next(x["id"] for x in client.get(f"{P}/directory/{role}", headers=H("farmer")).json() if x["name"] == name)


def make_farm(h):
    r = client.post(
        f"{P}/sustainability/farms",
        headers=h,
        json={"name": "Farm Test", "region": "punjab", "area_acres": 2}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class SustainabilityTests(unittest.TestCase):
    def test_review_reward_and_duplicates(self):
        f, v = H("farmer"), H("quality_verifier")
        fid = make_farm(f)
        self.assertEqual(client.post(f"{P}/sustainability/claims", headers=f, json={"farm_id": fid, "claim_type": "water_saving", "amount": 0, "evidence_ref": "log-1"}).status_code, 422)
        c = client.post(f"{P}/sustainability/claims", headers=f, json={"farm_id": fid, "claim_type": "water_saving", "amount": 10000, "evidence_ref": "log-1"})
        self.assertEqual(c.status_code, 201); cid = c.json()["id"]
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/review", headers=f, json={"approve": True}).status_code, 403)
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/issue-reward", headers=v).status_code, 409)  # not verified yet
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/review", headers=v, json={"approve": False}).status_code, 422)
        r = client.post(f"{P}/sustainability/claims/{cid}/review", headers=v, json={"approve": True, "notes": "ok"}).json()
        self.assertEqual(r["status"], "VERIFIED"); self.assertEqual(r["reward_points"], 100.0)
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/issue-reward", headers=v).status_code, 409)  # duplicate
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/review", headers=v, json={"approve": True}).status_code, 409)
        rewards = [x for x in client.get(f"{P}/sustainability/rewards", headers=f).json() if x["claim_id"] == cid]
        self.assertEqual(len(rewards), 1); self.assertTrue(rewards[0]["transaction_ref"].startswith("SIM-RWD-"))
        self.assertEqual(rewards[0]["ledger_status"], "SIMULATED")
    def test_rejected_gets_no_reward_and_ownership(self):
        f, v = H("farmer"), H("quality_verifier")
        fid = make_farm(f)
        cid = client.post(f"{P}/sustainability/claims", headers=f, json={"farm_id": fid, "claim_type": "soil_health", "evidence_ref": "soil-1"}).json()["id"]
        client.post(f"{P}/sustainability/claims/{cid}/review", headers=v, json={"approve": False, "notes": "no evidence"})
        self.assertEqual(client.post(f"{P}/sustainability/claims/{cid}/issue-reward", headers=v).status_code, 409)
        other, _, _ = reg("farmer")
        self.assertEqual(client.post(f"{P}/sustainability/claims", headers=other, json={"farm_id": fid, "claim_type": "soil_health", "evidence_ref": "x-1"}).status_code, 404)
    def test_report_and_rules(self):
        rep = client.get(f"{P}/sustainability/report", headers=H("farmer")).json()
        self.assertIn("not certified carbon credits", rep["limitations"])
        self.assertIn("water_saving", client.get(f"{P}/sustainability/rules").json()["rules"])

class PermissionTests(unittest.TestCase):
    def test_grant_access_revoke(self):
        f = H("farmer"); fid = client.get(f"{P}/auth/me", headers=f).json()["id"]
        lender = H("lender")
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=lender).status_code, 403)
        self.assertEqual(client.post(f"{P}/permissions", headers=f, json={"grantee_email": "buyer@demo.agrichain.test", "purpose": "loan review"}).status_code, 422)
        g = client.post(f"{P}/permissions", headers=f, json={"grantee_email": "lender@demo.agrichain.test", "purpose": "loan review", "days": 30})
        self.assertEqual(g.status_code, 201); pid = g.json()["id"]
        self.assertEqual(client.post(f"{P}/permissions", headers=f, json={"grantee_email": "lender@demo.agrichain.test", "purpose": "again"}).status_code, 409)
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=lender).status_code, 200)
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=H("insurer")).status_code, 403)
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=H("admin")).status_code, 403)
        self.assertEqual(client.post(f"{P}/permissions/{pid}/revoke", headers=lender).status_code, 403)
        self.assertEqual(client.post(f"{P}/permissions/{pid}/revoke", headers=f).status_code, 200)
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=lender).status_code, 403)
        self.assertEqual(client.post(f"{P}/permissions/{pid}/revoke", headers=f).status_code, 409)
        notes = client.get(f"{P}/notifications", headers=lender).json()["items"]
        self.assertIn("permission_revoked", [n["kind"] for n in notes])
    def test_owner_can_view_own_report(self):
        f = H("farmer"); fid = client.get(f"{P}/auth/me", headers=f).json()["id"]
        self.assertEqual(client.get(f"{P}/permissions/report/{fid}", headers=f).status_code, 200)

class NotificationTests(unittest.TestCase):
    def test_offer_creates_notification_and_read(self):
        listing = client.get(f"{P}/marketplace").json()[0]
        before = client.get(f"{P}/notifications", headers=H("farmer")).json()["unread"]
        r = client.post(f"{P}/offers", headers=H("buyer"), json={"batch_id": listing["id"], "quantity": 1, "price_per_unit": 1000})
        self.assertEqual(r.status_code, 201)
        n = client.get(f"{P}/notifications", headers=H("farmer")).json()
        self.assertEqual(n["unread"], before + 1)
        self.assertEqual(n["items"][0]["kind"], "offer_received")
        self.assertEqual(client.post(f"{P}/notifications/{n['items'][0]['id']}/read", headers=H("farmer")).status_code, 200)
        self.assertEqual(client.post(f"{P}/notifications/{n['items'][0]['id']}/read", headers=H("buyer")).status_code, 404)
        self.assertEqual(client.get(f"{P}/notifications", headers=H("farmer")).json()["unread"], before)
        client.post(f"{P}/notifications/read-all", headers=H("farmer"))
        self.assertEqual(client.get(f"{P}/notifications", headers=H("farmer")).json()["unread"], 0)

class AdminTests(unittest.TestCase):
    def test_admin_only_and_deactivate(self):
        self.assertEqual(client.get(f"{P}/admin/users", headers=H("farmer")).status_code, 403)
        a = H("admin")
        self.assertGreaterEqual(len(client.get(f"{P}/admin/users", headers=a).json()), 10)
        h, email, uid = reg("buyer")
        self.assertEqual(client.post(f"{P}/admin/users/{uid}/status", headers=a, json={"is_active": False}).status_code, 200)
        self.assertEqual(client.get(f"{P}/auth/me", headers=h).status_code, 401)
        self.assertEqual(client.post(f"{P}/auth/login", json={"email": email, "password": "password123"}).status_code, 403)
        me = client.get(f"{P}/auth/me", headers=a).json()["id"]
        self.assertEqual(client.post(f"{P}/admin/users/{me}/status", headers=a, json={"is_active": False}).status_code, 409)
        self.assertGreater(len(client.get(f"{P}/admin/audit", headers=a).json()), 0)

class RoleWorkflowTests(unittest.TestCase):
    def test_lending(self):
        f, l = H("farmer"), H("lender")
        lid = demo_id("lender", "Demo Lender")
        a = client.post(f"{P}/lending/applications", headers=f, json={"lender_id": lid, "amount": 50000, "purpose": "Seed and fertiliser"})
        self.assertEqual(a.status_code, 201); aid = a.json()["id"]
        other, _, _ = reg("lender")
        self.assertEqual(client.post(f"{P}/lending/applications/{aid}/decision", headers=other, json={"approve": True}).status_code, 404)
        self.assertEqual(client.post(f"{P}/lending/applications/{aid}/decision", headers=l, json={"approve": False}).status_code, 422)
        self.assertEqual(client.post(f"{P}/lending/applications/{aid}/decision", headers=l, json={"approve": True}).json()["status"], "APPROVED")
        self.assertEqual(client.post(f"{P}/lending/applications/{aid}/decision", headers=l, json={"approve": True}).status_code, 409)
        mine = [x for x in client.get(f"{P}/lending/applications", headers=f).json() if x["id"] == aid]
        self.assertEqual(mine[0]["status"], "APPROVED")
    def test_insurance(self):
        f, i = H("farmer"), H("insurer")
        p = client.post(f"{P}/insurance/policies", headers=i, json={"farmer_email": "farmer@demo.agrichain.test", "crop": "rice", "coverage_amount": 100000})
        self.assertEqual(p.status_code, 201); pid = p.json()["id"]
        other, _, _ = reg("farmer")
        self.assertEqual(client.post(f"{P}/insurance/claims", headers=other, json={"policy_id": pid, "description": "flood damage"}).status_code, 404)
        c = client.post(f"{P}/insurance/claims", headers=f, json={"policy_id": pid, "description": "flood damage", "evidence_ref": "photo-1"})
        self.assertEqual(c.status_code, 201); cid = c.json()["id"]
        self.assertEqual(client.post(f"{P}/insurance/claims/{cid}/decision", headers=f, json={"approve": True}).status_code, 403)
        d = client.post(f"{P}/insurance/claims/{cid}/decision", headers=i, json={"approve": True}).json()
        self.assertEqual(d["status"], "APPROVED"); self.assertEqual(d["payout_status"], "NOT_PAID")
        self.assertEqual(client.post(f"{P}/insurance/claims/{cid}/decision", headers=i, json={"approve": True}).status_code, 409)
    def test_cooperative(self):
        f, c = H("farmer"), H("cooperative")
        coop = demo_id("cooperative", "Demo Cooperative")
        m = client.post(f"{P}/cooperatives/join", headers=f, json={"coop_id": coop})
        self.assertEqual(m.status_code, 201); mid = m.json()["id"]
        self.assertEqual(client.post(f"{P}/cooperatives/join", headers=f, json={"coop_id": coop}).status_code, 409)
        self.assertEqual(client.post(f"{P}/cooperatives/members/{mid}/decision", headers=f, json={"approve": True}).status_code, 403)
        self.assertEqual(client.post(f"{P}/cooperatives/members/{mid}/decision", headers=c, json={"approve": True}).json()["status"], "APPROVED")
        self.assertEqual(client.post(f"{P}/cooperatives/members/{mid}/decision", headers=c, json={"approve": False}).status_code, 409)
    def test_agronomy(self):
        f, a = H("farmer"), H("agronomist")
        aid = demo_id("agronomist", "Demo Agronomist")
        cs = client.post(f"{P}/agronomy/cases", headers=f, json={"agronomist_id": aid, "topic": "Leaf spots on tomato"})
        self.assertEqual(cs.status_code, 201); cid = cs.json()["id"]
        self.assertEqual(client.post(f"{P}/agronomy/cases/{cid}/notes", headers=a, json={"text": "Apply neem spray", "kind": "RECOMMENDATION"}).status_code, 201)
        detail = client.get(f"{P}/agronomy/cases/{cid}", headers=f).json()
        self.assertEqual(detail["notes"][0]["kind"], "RECOMMENDATION")
        stranger, _, _ = reg("agronomist")
        self.assertEqual(client.get(f"{P}/agronomy/cases/{cid}", headers=stranger).status_code, 404)
        self.assertEqual(client.post(f"{P}/agronomy/cases/{cid}/close", headers=f).status_code, 403)
        self.assertEqual(client.post(f"{P}/agronomy/cases/{cid}/close", headers=a).json()["status"], "CLOSED")
        self.assertEqual(client.post(f"{P}/agronomy/cases/{cid}/notes", headers=a, json={"text": "late"}).status_code, 409)
    def test_suppliers(self):
        s = H("supplier")
        p = client.post(f"{P}/suppliers/products", headers=s, json={"name": "Urea 50kg", "category": "fertiliser", "price": 300})
        self.assertEqual(p.status_code, 201); pid = p.json()["id"]
        listed = client.get(f"{P}/suppliers/products").json()
        self.assertIn("not independently verified", [x for x in listed if x["id"] == pid][0]["authenticity_note"])
        other, _, _ = reg("supplier")
        self.assertEqual(client.delete(f"{P}/suppliers/products/{pid}", headers=other).status_code, 404)
        self.assertEqual(client.delete(f"{P}/suppliers/products/{pid}", headers=s).status_code, 200)
        self.assertEqual(client.post(f"{P}/suppliers/products", headers=H("buyer"), json={"name": "X", "category": "seed", "price": 1}).status_code, 403)

class AnalyticsTests(unittest.TestCase):
    def test_market_and_prices(self):
        m = client.get(f"{P}/analytics/market").json()
        self.assertIn("rice", [c["crop"] for c in m["crops"]])
        p = client.get(f"{P}/analytics/prices?crop=rice&region=tamil_nadu").json()
        self.assertTrue(p["is_demonstration"]); self.assertEqual(len(p["history"]), 48)
        self.assertEqual(client.get(f"{P}/analytics/prices?crop=durian").status_code, 422)

if __name__ == "__main__":
    unittest.main()
