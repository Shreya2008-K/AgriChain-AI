# Run from the repo root:  .\scripts\start-frontend.ps1   (backend must already be running on port 8000)
Set-Location "$PSScriptRoot\..\frontend"
if (-not (Test-Path .env) -and (Test-Path .env.example)) { Copy-Item .env.example .env }
npm install
npm run dev
