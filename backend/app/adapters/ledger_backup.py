"""Ledger adapters. SimulatedLedger is NOT a blockchain; ids are prefixed SIM- and never look like 0x hashes."""
import hashlib, json, os, itertools
from abc import ABC, abstractmethod

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def metadata_hash(obj) -> str:
    return "0x" + hashlib.sha256(canonical_json(obj).encode()).hexdigest()

TRANSITIONS = {"REGISTERED": {"HARVEST_RECORDED"}, "HARVEST_RECORDED": {"QUALITY_PENDING"},
               "QUALITY_PENDING": {"QUALITY_VERIFIED", "QUALITY_REJECTED"}, "QUALITY_VERIFIED": {"LISTED"},
               "LISTED": {"OFFER_ACCEPTED", "CANCELLED"}, "OFFER_ACCEPTED": {"SOLD"}}

class LedgerError(Exception): pass
class NotConfigured(LedgerError): pass

class LedgerAdapter(ABC):
    @abstractmethod
    def record(self, batch_id: str, new_state: str, actor: str, metadata: dict) -> dict: ...

class SimulatedLedger(LedgerAdapter):
    network = "LOCAL_SIMULATOR"
    def __init__(self):
        self.states, self.txs, self._n = {}, [], itertools.count(1)
    def record(self, batch_id, new_state, actor, metadata):
        cur = self.states.get(batch_id)
        if cur is None and new_state != "REGISTERED": raise LedgerError("Batch not registered")
        if cur is not None and new_state not in TRANSITIONS.get(cur, set()):
            raise LedgerError(f"Invalid transition {cur} -> {new_state}")
        h = metadata_hash(metadata)
        tx = {"transaction_ref": f"SIM-{next(self._n):06d}-{h[2:10]}", "status": "SIMULATED", "network": self.network,
              "batch_id": batch_id, "record_type": new_state, "actor": actor, "metadata_hash": h,
              "block_number": None, "explorer_url": None}
        self.states[batch_id] = new_state; self.txs.append(tx)
        return tx

class Web3Ledger(LedgerAdapter):
    """Placeholder. UNIMPLEMENTED/UNTESTED: raises NotConfigured gracefully without credentials."""
    def __init__(self):
        self.rpc, self.addr = os.getenv("WEB3_RPC_URL"), os.getenv("REGISTRY_CONTRACT_ADDRESS")
        if not (self.rpc and self.addr): raise NotConfigured("WEB3_RPC_URL / REGISTRY_CONTRACT_ADDRESS not set")
    def record(self, *a, **k): raise NotImplementedError("Real Web3 submission is not implemented in this package")

def get_ledger():
    try: return Web3Ledger()
    except NotConfigured: return SimulatedLedger()
