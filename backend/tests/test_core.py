import unittest
from app.ml.price_model import PriceModel, make_synthetic_data, InsufficientDataError, UnsupportedInputError
from app.adapters.ledger import SimulatedLedger, LedgerError, metadata_hash, get_ledger

class MLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = PriceModel(); cls.metrics = cls.m.train(make_synthetic_data())
    def test_prediction_shape_and_labels(self):
        r = self.m.predict("rice", "tamil_nadu", 6, 1000)
        self.assertEqual(r["data_source"], "SYNTHETIC_DEMO_DATASET"); self.assertTrue(r["is_demonstration"])
        self.assertEqual(r["unit"], "INR/quintal"); self.assertLess(r["range_80pct"][0], r["range_80pct"][1])
    def test_mae_reasonable(self):
        self.assertLess(self.metrics["mae"] / self.metrics["mean_price"], 0.10)
    def test_unsupported(self):
        with self.assertRaises(UnsupportedInputError): self.m.predict("durian", "tamil_nadu", 6, 1000)
        with self.assertRaises(UnsupportedInputError): self.m.predict("rice", "mars", 6, 1000)
        with self.assertRaises(UnsupportedInputError): self.m.predict("rice", "punjab", 13, 1000)
    def test_insufficient_data(self):
        with self.assertRaises(InsufficientDataError): PriceModel().train(make_synthetic_data().head(10))
        with self.assertRaises(InsufficientDataError): PriceModel().predict("rice", "punjab", 1, 10)

class LedgerTests(unittest.TestCase):
    def test_hash_deterministic(self):
        self.assertEqual(metadata_hash({"a": 1, "b": 2}), metadata_hash({"b": 2, "a": 1}))
    def test_lifecycle_and_labels(self):
        L = SimulatedLedger()
        for s in ["REGISTERED", "HARVEST_RECORDED", "QUALITY_PENDING", "QUALITY_VERIFIED", "LISTED"]:
            tx = L.record("B1", s, "farmer1", {"s": s})
        self.assertEqual(tx["status"], "SIMULATED"); self.assertTrue(tx["transaction_ref"].startswith("SIM-"))
        self.assertIsNone(tx["explorer_url"]); self.assertIsNone(tx["block_number"])
    def test_invalid_transition(self):
        L = SimulatedLedger(); L.record("B2", "REGISTERED", "f", {})
        with self.assertRaises(LedgerError): L.record("B2", "SOLD", "f", {})
        with self.assertRaises(LedgerError): L.record("B3", "LISTED", "f", {})
    def test_fallback_without_credentials(self):
        self.assertIsInstance(get_ledger(), SimulatedLedger)

if __name__ == "__main__": unittest.main()
