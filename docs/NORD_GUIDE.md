# EMERGENCE — Guide Nord

## 0. Vérité du projet
- **Code source** = dépôt Git (branche `main`).
- **Plan d’architecture** = dernier fichier `arborescence_synchronisée_*.txt` versionné.
- **ARBO-LOCK**: on ne crée/déplace/supprime rien sans l’annoncer et snapshotter.

## 1. Boot local (Windows/PowerShell 5.1, venv active)
where python
where uvicorn
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000

# Health
curl.exe -s http://127.0.0.1:8000/api/health

## 2. Frontend (Vite)
npm ci
npm run dev
# ou build
npm run build

## 3. Conventions
- **Commits**: `type(scope): message` (ex: `feat(docs): ...`, `fix(costs): ...`, `chore(arbo): ...`)
- **EOL**: LF par défaut, CRLF pour `.ps1/.bat` (voir `.gitattributes`)
- **Pas de refactor sauvage**. Chirurgical, modules isolés, zéro dette.

## 4. Flux de travail Git
- Branche de feature depuis `main`
- PR → review → squash merge
- Après ajout/suppression/déplacement de fichiers → **snapshot ARBO**:
  (tree /F /A | Out-String) | Set-Content -Encoding UTF8 .\arborescence_synchronisée_YYYYMMDD.txt
  git add .\arborescence_synchronisée_YYYYMMDD.txt
  git commit -m "chore(arbo): snapshot YYYY-MM-DD"
  git push

## 5. Cartographie des dossiers (résumé)
- `src/backend` FastAPI + services
- `src/frontend` Vite + JS natif + CSS modularisé
- `docs` documentation projet
- `tests` scripts PS et fichiers de test
- `tmp_tests` artefacts temporaires
- racine: `.gitattributes`, `.gitignore`, `LICENSE`, `README.md`, `requirements.txt`, `package.json`

## 6. Roadmap courte
- [ ] Corriger bug d’affichage synthèse “Débats Autonomes”
- [ ] CI minimale (lint + tests smoke)
- [ ] Snapshot ARBO à chaque évolution d’assets
- [ ] Préparer release `v0.1.0`

## 7. Sécurité & données (rappel)
- Pas de secrets en clair dans le repo
- Variables via `.env` (voir `.env.example`)
- Sauvegardes scripts: `scripts/backup.py`
