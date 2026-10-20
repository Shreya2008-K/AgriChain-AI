# Run from the repo root:  .\scripts\start-backend.ps1
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
