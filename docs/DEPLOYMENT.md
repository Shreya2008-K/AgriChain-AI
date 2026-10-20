# Deployment guide (Vercel + Render + Neon)

Nothing has been deployed by the author. These steps are written from the project's configuration and have not been
executed against live accounts. Follow them in this order.

## 1. Neon (PostgreSQL)
1. Create a project at neon.tech and copy the connection string (`postgresql://user:pass@host/db?sslmode=require`).
2. Keep it secret. It goes only into Render's environment variables.

## 2. Render (backend)
1. Push the repo to GitHub (the `.gitignore` excludes `.env`, databases and `node_modules`).
2. In Render choose New > Blueprint and select the repo (it reads `render.yaml`), or create a Web Service manually:
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
3. Environment variables (Render dashboard):
   - `APP_ENV=production` (disables /docs and refuses the insecure development JWT secret)
   - `DATABASE_URL` = the Neon string
   - `JWT_SECRET` = a long random value (the blueprint generates one)
   - `CORS_ORIGINS` = your Vercel URL, comma-separated if several (no trailing slash)
4. Tables are created automatically at startup (`create_all`). Alembic migrations are NOT included yet, so schema
   changes on an existing production database need manual handling.
5. Optional demo data (Render Shell): set `DEMO_PASSWORD` to a private value first, then run `python -m app.seed`.
   Seeding in production is refused unless `DEMO_PASSWORD` is set. Do not use the published demo password in production.

## 3. Vercel (frontend)
1. Import the repo in Vercel. Root directory: `frontend`. Framework preset: Vite.
   Build command `npm run build`, output directory `dist`.
2. Environment variable: `VITE_API_URL` = your Render URL (https, no trailing slash, no `/api/v1`).
   It is read at build time, so redeploy after changing it. Production builds never fall back to localhost.
3. `frontend/vercel.json` rewrites all paths to `index.html` so client-side routes work after refresh.
4. Add the final Vercel URL to `CORS_ORIGINS` on Render.

## 4. Verify (after deploying)
Open `<render-url>/health`, then the Vercel site, then register and log in. Only after this works end to end is it
accurate to say the site is deployed.

## Blockchain
Demo mode uses the local ledger simulator and needs no keys. `Web3Ledger` in `backend/app/adapters/ledger.py` is a
placeholder that reports "not configured" without `WEB3_RPC_URL` and `REGISTRY_CONTRACT_ADDRESS`; real submission is
not implemented. `contracts/contracts/AgriChainRegistry.sol` has not been compiled, tested or deployed, and there is
no Hardhat project yet.
