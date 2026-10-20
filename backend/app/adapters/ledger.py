
"""Ledger adapters for simulated and real EVM blockchain transactions."""
import hashlib
import json
import os
import itertools
from pathlib import Path
from abc import ABC, abstractmethod

from web3 import Web3


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def metadata_hash(obj) -> str:
    return "0x" + hashlib.sha256(canonical_json(obj).encode()).hexdigest()


TRANSITIONS = {
    "REGISTERED": {"HARVEST_RECORDED"},
    "HARVEST_RECORDED": {"QUALITY_PENDING"},
    "QUALITY_PENDING": {"QUALITY_VERIFIED", "QUALITY_REJECTED"},
    "QUALITY_VERIFIED": {"LISTED"},
    "LISTED": {"OFFER_ACCEPTED", "CANCELLED"},
    "OFFER_ACCEPTED": {"SOLD"},
}

# These values must match the enum order in AgriChainRegistry.sol.
CONTRACT_STATES = {
    "REGISTERED": 1,
    "HARVEST_RECORDED": 2,
    "QUALITY_PENDING": 3,
    "QUALITY_VERIFIED": 4,
    "QUALITY_REJECTED": 5,
    "LISTED": 6,
    "OFFER_ACCEPTED": 7,
    "SOLD": 8,
    "CANCELLED": 9,
}


class LedgerError(Exception):
    pass


class NotConfigured(LedgerError):
    pass


class LedgerAdapter(ABC):
    @abstractmethod
    def record(self, batch_id: str, new_state: str, actor: str, metadata: dict) -> dict:
        ...


class SimulatedLedger(LedgerAdapter):
    network = "LOCAL_SIMULATOR"

    def __init__(self):
        self.states, self.txs, self._n = {}, [], itertools.count(1)

    def record(self, batch_id, new_state, actor, metadata):
        cur = self.states.get(batch_id)

        if cur is None and new_state != "REGISTERED":
            raise LedgerError("Batch not registered")

        if cur is not None and new_state not in TRANSITIONS.get(cur, set()):
            raise LedgerError(f"Invalid transition {cur} -> {new_state}")

        h = metadata_hash(metadata)
        tx = {
            "transaction_ref": f"SIM-{next(self._n):06d}-{h[2:10]}",
            "status": "SIMULATED",
            "network": self.network,
            "batch_id": batch_id,
            "record_type": new_state,
            "actor": actor,
            "metadata_hash": h,
            "block_number": None,
            "explorer_url": None,
        }
        self.states[batch_id] = new_state
        self.txs.append(tx)
        return tx


class Web3Ledger(LedgerAdapter):
    """Records batch state and metadata hashes in AgriChainRegistry."""

    network = "LOCAL_HARDHAT"

    def __init__(self):
        self.rpc = os.getenv("WEB3_RPC_URL")
        self.addr = os.getenv("REGISTRY_CONTRACT_ADDRESS")
        self.private_key = os.getenv("WEB3_PRIVATE_KEY")

        if not self.rpc or not self.addr or not self.private_key:
            raise NotConfigured(
                "Set WEB3_RPC_URL, REGISTRY_CONTRACT_ADDRESS, and WEB3_PRIVATE_KEY"
            )

        self.w3 = Web3(Web3.HTTPProvider(self.rpc))

        if not self.w3.is_connected():
            raise NotConfigured(f"Cannot connect to blockchain RPC: {self.rpc}")

        try:
            self.account = self.w3.eth.account.from_key(self.private_key)
            self.addr = Web3.to_checksum_address(self.addr)

            artifact_path = Path(__file__).resolve().parents[2] / "AgriChainRegistry.json"
            with artifact_path.open("r", encoding="utf-8") as f:
                artifact = json.load(f)

            abi = artifact["abi"] if isinstance(artifact, dict) and "abi" in artifact else artifact

            self.contract = self.w3.eth.contract(
                address=self.addr,
                abi=abi,
            )

            if self.w3.eth.get_code(self.addr) in (b"", b"\x00"):
                raise NotConfigured(
                    "No contract code found at REGISTRY_CONTRACT_ADDRESS. Redeploy the contract."
                )

        except NotConfigured:
            raise
        except Exception as exc:
            raise NotConfigured(f"Could not initialize Web3 ledger: {exc}") from exc

    def record(self, batch_id, new_state, actor, metadata):
        if new_state not in CONTRACT_STATES:
            raise LedgerError(f"Unsupported contract state: {new_state}")

        # Check the application's allowed transitions before submitting.
        batch_key = Web3.keccak(text=str(batch_id))
        current = self.contract.functions.batches(batch_key).call()
        current_state = int(current[0])

        if current_state == 0 and new_state != "REGISTERED":
            raise LedgerError("Batch not registered on the blockchain")

        if current_state != 0:
            reverse_states = {v: k for k, v in CONTRACT_STATES.items()}
            current_name = reverse_states.get(current_state)

            if new_state not in TRANSITIONS.get(current_name, set()):
                raise LedgerError(f"Invalid transition {current_name} -> {new_state}")

        digest = bytes.fromhex(metadata_hash(metadata)[2:])
        state_number = CONTRACT_STATES[new_state]

        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = self.contract.functions.record(
                batch_key,
                state_number,
                digest,
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "chainId": self.w3.eth.chain_id,
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status != 1:
                raise LedgerError("Blockchain transaction failed")

            return {
                "transaction_ref": tx_hash.hex(),
                "status": "CONFIRMED",
                "network": self.network,
                "batch_id": batch_id,
                "record_type": new_state,
                "actor": actor,
                "metadata_hash": "0x" + digest.hex(),
                "block_number": receipt.blockNumber,
                "explorer_url": None,
            }

        except LedgerError:
            raise
        except Exception as exc:
            raise LedgerError(f"Blockchain recording failed: {exc}") from exc


def get_ledger():
    try:
        return Web3Ledger()
    except NotConfigured:
        return SimulatedLedger()
