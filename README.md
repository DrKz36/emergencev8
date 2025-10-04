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

### Backend quality checks

Run all backend quality gates in one go (pytest, ruff, mypy).

```powershell
./scripts/run_backend_quality.ps1
```

Add `-FailFast` to stop after the first failure, or use `-Python` to point to a custom interpreter. Pass `-Paths src/backend` if you need to lint the whole backend.

## Git remote configuration

When cloning from an archive or copying the folder you need to add the remote manually so that pulls and pushes work. Configure it once with git or use the helper scripts included in `scripts/`.

```powershell
git remote add origin https://github.com/DrKz36/emergencev8.git
```

```bash
git remote add origin https://github.com/DrKz36/emergencev8.git
```

On Windows/PowerShell you can run `pwsh -File scripts/bootstrap.ps1` and the script will ensure the `origin` remote points to `https://github.com/DrKz36/emergencev8.git` before starting `npm run start`. On Unix shells run `./scripts/bootstrap.sh` for the same behaviour. Pass `-SkipStart`/`--skip-start` if you only need to configure git or override the remote settings via the corresponding flags.

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
6. Run `./scripts/run_backend_quality.ps1` to execute pytest/ruff/mypy together (or the individual commands if you only touched a subset).
7. Run `npm run build` to catch front end issues.
8. Develop the feature, commit with an explicit message, and rerun `git rebase origin/<base_branch>` if long running work drifted.
9. `git push origin <branch>` and open the pull request.

Keeping these steps in sync between cloud and local runs eliminates version drift and makes conflicts predictable.

### Politique de merge

Le depot applique le **squash merge** pour toutes les Pull Requests. Apres merge, vos commits individuels sont regroupes dans un seul commit sur `main`. Pour connaitre la procedure complete (verification, suppression des branches, relance du script de sync), consulter `docs/git-workflow.md`.
