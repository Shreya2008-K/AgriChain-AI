# AgriChain AI

### Decentralized Agricultural Marketplace with AI Intelligence & Blockchain Provenance

> **B.Tech Computer Science and Engineering — Final Year Capstone Project**  
> **Specialization:** Blockchain Architecture, Smart Contract Engineering & Applied Machine Learning  
> **Status:** Fully functional, verified, compiled, and tested (All 45 backend tests passed; All 8 Hardhat smart contract tests passed; Frontend production bundle verified).

---

## 1. System Architecture

AgriChain AI integrates an off-chain relational database, an AI-powered pricing and decision support engine, and an Ethereum-compatible (EVM) blockchain layer.

```mermaid
graph TD
    subgraph Client ["Frontend Layer (React 18 + Vite + Tailwind + Lucide)"]
        UI["Role-Specific Dashboards (10 Roles)"]
        Passport["Product Passport & QR Provenance Viewer"]
        AIUI["AI Assistant & Price Forecast Charts"]
    end

    subgraph Server ["Backend API Layer (FastAPI + Python 3.11)"]
        Auth["JWT Authentication & RBAC Engine"]
        API["REST Endpoints (Batches, Trade, Governance)"]
        ML["Random Forest Regressor (Scikit-Learn)"]
        DualAdapter{"Dual Blockchain Adapter"}
    end

    subgraph Storage ["Off-Chain Storage"]
        DB[("SQLite / PostgreSQL (Operational Data)")]
    end

    subgraph Blockchain ["On-Chain Layer (Solidity + Hardhat)"]
        Contract["AgriChainRegistry.sol"]
        LedgerEvents["BatchEvent Logs (Keccak-256 Hashes)"]
        Simulator["Simulated Ledger (Demo Fallback)"]
    end

    UI -->|REST / JSON| Auth
    UI -->|REST / JSON| API
    UI -->|Predictions| ML
    API -->|CRUD| DB
    API --> DualAdapter
    DualAdapter -->|Web3.py (Live Node)| Contract
    DualAdapter -->|Offline Fallback| Simulator
    Contract --> LedgerEvents
```

### Architectural Separation of Concerns
1. **Off-Chain Operational Data (SQLite / PostgreSQL):** High-volume data, user credentials, farm boundary metadata, photos, and chat queries.
2. **On-Chain Truth (Solidity Smart Contract on Hardhat / EVM):** Cryptographic state machine transitions, metadata hashes (Keccak-256), actor wallets, and timestamped event logs.
3. **AI Estimation (Scikit-Learn):** Machine-learning generated price forecasts and advisory recommendations. *Explicitly distinguished from immutable blockchain proofs.*
4. **Transparent Dual-Mode Ledger:** Automatically runs in `REAL` Web3 mode when a local Hardhat node is running, or falls back to `LOCAL_SIMULATOR` with deterministic `SIM-` identifiers so the platform never crashes during vivas or presentations without an active RPC.

---

## 2. 10 Platform Roles & RBAC Matrix

| Role | Access & Capabilities | Default Login Email | Password |
|---|---|---|---|
| **Farmer** | Register crops, log harvest, list verified batches, accept offers, manage farm fields, view AI insights. | `farmer@demo.agrichain.test` | `Demo@12345` |
| **Buyer** | Browse marketplace, inspect provenance, submit purchase offers, sign agreements, track delivery. | `buyer@demo.agrichain.test` | `Demo@12345` |
| **Quality Verifier** | Inspect pending harvests, record lab results/grades, approve or reject with explicit reasons on-chain. | `quality_verifier@demo.agrichain.test` | `Demo@12345` |
| **Transporter** | Claim delivery orders, log custody transitions (`IN_TRANSIT`, `DELIVERED`), verify QR codes. | `transporter@demo.agrichain.test` | `Demo@12345` |
| **Cooperative** | Coordinate group pool selling, manage memberships, negotiate bulk volume pricing. | `cooperative@demo.agrichain.test` | `Demo@12345` |
| **Agronomist** | Review farmer field cases, provide tailored pest/disease advisories, recommend soil treatment. | `agronomist@demo.agrichain.test` | `Demo@12345` |
| **Input Supplier** | List certified seeds, bio-fertilizers, and tools; supply inputs to verified farmers. | `supplier@demo.agrichain.test` | `Demo@12345` |
| **Lender** | Review consent-shared yield and financial reports, assess credit risk, approve agricultural input loans. | `lender@demo.agrichain.test` | `Demo@12345` |
| **Insurer** | Underwrite parametric weather/crop insurance policies, review verified disaster claims. | `insurer@demo.agrichain.test` | `Demo@12345` |
| **Administrator** | Authorize verifier wallets, monitor on-chain transaction volume, resolve disputes, manage users. | `admin@demo.agrichain.test` | `Demo@12345` |

---

## 3. Smart Contract Design (`AgriChainRegistry.sol`)

The smart contract is written in Solidity `^0.8.20` using OpenZeppelin's `AccessControl`.

### 8-Stage Enforced Lifecycle

```
None
  │ (record by RECORDER_ROLE)
  ▼
Registered
  │ (record by RECORDER_ROLE)
  ▼
HarvestRecorded
  │ (record by RECORDER_ROLE)
  ▼
QualityPending
  │
  ├──► QualityVerified (by VERIFIER_ROLE)
  │      │
  │      ▼
  │    Listed
  │      │
  │      ├──► OfferAccepted ──► Sold
  │      └──► Cancelled
  │
  └──► QualityRejected (by VERIFIER_ROLE)
```

### Key Contract Guarantees
* **Strict Role Segregation:** Quality verification requires `VERIFIER_ROLE`. Standard batch updates require `RECORDER_ROLE`. Administrative functions require `DEFAULT_ADMIN_ROLE`.
* **Transition Enforcement:** Skipping stages (e.g. `Registered` directly to `Sold`) or re-listing rejected crops reverts with `"Invalid transition"`.
* **Zero PII on Blockchain:** The contract stores only `bytes32 batchId`, `uint8 state`, `bytes32 metadataHash`, and `address recorder`. Personal farmer data and photos remain off-chain.
* **Audit Trail:** Every state change emits an indexed `BatchEvent(bytes32 indexed batchId, State state, bytes32 metadataHash, address indexed actor)`.

---

## 4. Machine Learning Price Prediction

* **Algorithm:** Random Forest Regressor (`n_estimators=200`, `min_samples_leaf=3`).
* **Input Features:** `crop_name`, `location`, `season`, `quality_grade`, `quantity_kg`, `historical_price`, `demand_index`.
* **Evaluation Metrics:**
  - Test Set $R^2$ Score: **0.9952**
  - Mean Absolute Error (MAE): **₹ 1.44 / kg** (outperforming the baseline average error of ₹ 4.21 / kg).
* **Transparency Notice:** Model outputs are explicitly marked as *probabilistic AI estimates* and separated from cryptographic blockchain facts.

---

## 5. Quick Start & Execution Guide

### Prerequisites
* **Python 3.11+**
* **Node.js 18+** (with npm)
* **Windows PowerShell** (or Linux/macOS bash)

### 1. Smart Contract (Terminal 1)
```powershell
cd contracts
npm install
npx hardhat compile
npx hardhat test
```
*Expected Output: `8 passing (737ms)`*

To run a local EVM node:
```powershell
npx hardhat node
```

### 2. Backend Server (Terminal 2)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run all 45 automated backend tests:
python -m unittest discover -v tests

# Start FastAPI server (auto-seeds demo accounts and data on launch):
python -m uvicorn app.main:app --reload --port 8000
```
* API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/health`

### 3. Frontend Client (Terminal 3)
```powershell
cd frontend
npm install
npm run build
npm run dev
```
* Open your browser at: `http://localhost:5173`

---

## 6. End-to-End Walkthrough

1. **Farmer Batch Registration:**
   - Log in as `farmer@demo.agrichain.test`.
   - Navigate to **Crop batches > New batch**. Enter crop details (e.g., Tomato, 40 quintals, Karnataka).
   - Click **Record Harvest** -> **Submit for Verification**.
2. **Quality Verification:**
   - Switch account or open incognito window as `quality_verifier@demo.agrichain.test`.
   - Open **Verification queue**. Inspect the harvest parameters and click **Approve** (assigns Grade A and writes proof on-chain).
3. **Marketplace Listing & Buyer Offer:**
   - Farmer opens the batch and clicks **List for sale**.
   - Log in as `buyer@demo.agrichain.test`, navigate to **Marketplace**, inspect the transparent provenance timeline, and submit an offer for 20 quintals.
4. **Agreement & Custody Delivery:**
   - Farmer navigates to **Offers** and clicks **Accept**. An escrow agreement and delivery order are created.
   - Log in as `transporter@demo.agrichain.test`, open **Deliveries**, claim the job, and update status (`Picked up` -> `In transit` -> `Delivered`).
5. **Data Permissions & Sustainability:**
   - Farmer shares soil/yield report with Lender under **Data permissions**.
   - Lender logs in as `lender@demo.agrichain.test` to review report. Farmer can revoke permission anytime.

---

## 7. Viva & Academic Defense FAQ

### Q1: Why use blockchain for agriculture? Why not just use a traditional database?
**Answer:** A central database is controlled by a single party (e.g., the marketplace operator or a retail corporate), creating a single point of failure and potential conflict of interest where records can be altered post-facto. Blockchain provides a shared, append-only, tamper-evident ledger across mistrusting stakeholders (farmers, multiple competing buyers, certification bodies, and banks) ensuring that once a quality grade or harvest date is certified, no single participant can tamper with that historical proof.

### Q2: Does recording crop data on the blockchain prove the crop is actually organic or Grade A?
**Answer:** No. This is the classic **"Garbage In, Garbage Out"** or **Oracle Problem** of blockchains. Blockchain only proves *data immutability*—that the record was signed by an authorized verifier's key at a specific timestamp and has not been altered since. To mitigate false claims, our architecture enforces strict role-based access control where only certified `VERIFIER_ROLE` accounts can approve quality grades, and all approvals are permanently attributed to that verifier's wallet.

### Q3: Why store metadata hashes on-chain instead of complete crop data?
**Answer:** Storing raw text, descriptions, and images on an EVM blockchain is cost-prohibitive in gas fees, unscalable, and violates data privacy standards (e.g., GDPR). By hashing the canonical JSON metadata using Keccak-256 (`0x...`), we store a constant 32-byte hash on-chain. Anyone with the off-chain record can verify integrity in $O(1)$ time by recomputing the hash and comparing it to the contract's stored state.

### Q4: How does the platform handle demonstrations without an active local Ethereum node?
**Answer:** The platform features an adapter pattern (`backend/app/adapters/ledger.py`). The `Web3Ledger` connects to a real EVM node when configured. If the node is unreachable, the system automatically switches to `SimulatedLedger`, generating deterministic `SIM-` cryptographic references. This ensures flawless academic demonstrations without system crashes while clearly labeling simulated operations.

---

## 8. License & Academic Declaration

This project was developed for academic capstone purposes in Computer Science & Engineering. All rights reserved.
