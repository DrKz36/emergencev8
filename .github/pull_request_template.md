# PR - Emergence (ARBO-LOCK)

## Description
> Decris precisement ce que fait cette PR : corrections, nouvelles fonctionnalites, ajustements UI, etc.

---

## Checklist ARBO-LOCK
- [ ] Fichiers complets fournis (pas de `...`, remplacement 1:1).
- [ ] Aucune derive d''architecture (chemins et imports conformes a `arborescence_synchronisee_*.txt`).
- [ ] Snapshot ARBO ajoute si creation/deplacement/suppression de fichiers :
  ```powershell
  (tree /F /A | Out-String) | Set-Content -Encoding UTF8 .\arborescence_synchronisee_YYYYMMDD.txt
  git add .\arborescence_synchronisee_YYYYMMDD.txt
  git commit -m "chore(arbo): snapshot YYYY-MM-DD"
  git push
  ```

---

## Checklist pre-merge
- [ ] Rebase sur `origin/main` effectue (`scripts/sync-workdir.ps1` ou commandes manuelles).
- [ ] Tests executes et reussis (pytest, npm run build, scripts specifiques).
- [ ] Documentation mise a jour (docs, passation, README, etc.).
- [ ] Changements sensibles annonces dans le compte-rendu de session.
- [ ] Historique pret pour squash merge (commits nettoyes, pas de WIP).

## Checklist post-merge (a remplir apres merge)
- [ ] PR en statut `Merged` et numero note dans la passation.
- [ ] `main` local mis a jour (`git checkout main && git pull origin main`).
- [ ] Branche feature supprimee en local (`git branch -d`).
- [ ] Branche feature supprimee sur le remote (`git push origin --delete`).
- [ ] `scripts/sync-workdir.ps1` relance si necessaire (possible `-AllowDirty`).
- [ ] Documentation/passation mise a jour avec les actions de cleanup.

-> Voir `docs/git-workflow.md` pour le detail complet du workflow Git et du squash merge.
