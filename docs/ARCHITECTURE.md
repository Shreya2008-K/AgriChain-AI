# Architecture
- **Frontend**: React 18, Vite, TypeScript, Tailwind 3, React Router, Recharts, Lucide. API base URL from `VITE_API_URL`.
  Pages in `src/pages` (Public, Workspace, More), shared UI in `src/components`.
- **Backend**: FastAPI, SQLAlchemy 2, Pydantic 2, JWT (PyJWT), bcrypt. Routers in `app/routers`, models in `app/models.py`,
  business logic in `app/services` (batch lifecycle, trade/inventory, notifications), ML in `app/ml`, ledger in `app/adapters`.
- **Database**: SQLite locally by default, PostgreSQL (Neon) via `DATABASE_URL`. Tables created with `create_all`.
- **Ledger**: every batch lifecycle event, agreement and delivery step stores a canonical-JSON SHA-256 metadata hash and a
  `SIM-` transaction reference. These are simulator records. They show that an event was recorded and do not prove a
  physical claim. Personal data is never placed in the hashed metadata beyond ids, statuses and notes.
- **Consistency**: offer acceptance uses conditional UPDATEs in one transaction (offer must still be PENDING and enough
  quantity must remain), preventing double acceptance and overselling. Rewards are unique per claim.
- **Privacy**: farm reports are readable only by the owner or a grantee with an ACTIVE, unexpired permission. Admins get
  no automatic access. Revocation blocks future access; prior disclosure cannot be recalled.
- **ML**: gradient boosting on SYNTHETIC data (INR/quintal), time-based holdout, 80% range from holdout residuals.
