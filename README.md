# EMERGENCE V8

Multi agent conversation stack (Anima, Neo, Nexus) with cockpit, retrieval augmented generation, and document tools.

## Local environment

The project targets Python 3.11 and Node.js 18 or newer. Always isolate work inside a virtual environment and a dedicated node installation to keep parity with CI.

### Python setup

Windows PowerShell 5.1+
```powershell
cd C:\dev\emergenceV8
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux
```bash
cd ~/dev/emergenceV8
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional: capture the exact wheel set once everything works with `pip freeze > requirements-dev.txt` or maintain a `requirements.lock` to document the environment used for a successful session.

### Node setup

Use Node 18 with nvm (or a compatible manager) and reinstall dependencies after each rebase if `package-lock.json` changed.
```bash
nvm install 18
nvm use 18
npm ci
npm run build
```

### Running the stack locally

Backend (FastAPI + Uvicorn)
```powershell
python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000
```

Frontend build smoke test
```bash
npm run build
```

Health check
```powershell
curl.exe -s http://127.0.0.1:8000/api/health
```

## Git workflow and branch hygiene

1. Start on a clean tree: `git status` should report no changes.
2. Discover the upstream default branch: `git remote show origin` highlights the HEAD (usually `main`).
3. Synchronise with upstream before coding.
   ```powershell
   git fetch --all --prune
   git checkout main
   git pull --rebase origin main
   git checkout your_feature_branch
   git rebase origin/main
   ```
4. Prefer rebases over merge commits when updating feature branches. If a rebase rewrites history, use `git push --force-with-lease` once tests pass.
5. Resolve conflicts locally, rerun tests, and document any decisions in the commit message.
6. Clean merged branches periodically.
   ```powershell
   git branch --merged
   git branch -d obsolete_branch
   git push origin --delete obsolete_branch
   ```

## Daily development checklist

1. `git status`
2. `git fetch --all` and `git rebase origin/<base_branch>`
3. Activate the Python virtual environment.
4. `python -m pip install -r requirements.txt` (repeat after rebases that touch `requirements.txt`).
5. `npm ci` (repeat after rebases that touch `package-lock.json`).
6. Run back end test and lint commands that match the scope (`pytest`, `ruff`, `mypy`).
7. Run `npm run build` to catch front end issues.
8. Develop the feature, commit with an explicit message, and rerun `git rebase origin/<base_branch>` if long running work drifted.
9. `git push origin <branch>` and open the pull request.

Keeping these steps in sync between cloud and local runs eliminates version drift and makes conflicts predictable.
