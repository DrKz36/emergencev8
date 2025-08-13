# ÉMERGENCE V8

Interface de dialogue multi‑agents (Anima, Neo, Nexus) + cockpit + RAG + documents.  
**Backend**: FastAPI/UVicorn — **Frontend**: (web static + CSS glassmorphism unifié).

## Démarrage (Windows / PowerShell 5.1)
```powershell
cd C:\dev\emergenceV8
& C:/dev/emergenceV8/.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000
# Smoke test :
curl.exe -s http://127.0.0.1:8000/api/health
