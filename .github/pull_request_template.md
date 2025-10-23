# PR - Emergence V8

## Description
> Décris précisément ce que fait cette PR : corrections, nouvelles fonctionnalités, ajustements UI, etc.

---

## Checklist qualité code
- [ ] Fichiers complets fournis (pas d'ellipses `...`, code complet).
- [ ] Architecture respectée (voir `docs/architecture/`).
- [ ] Contrats API respectés (voir `docs/architecture/30-Contracts.md`).
- [ ] Type hints corrects (mypy clean).

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
