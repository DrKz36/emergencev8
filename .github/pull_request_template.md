# 🔍 PR — ÉMERGENCE (ARBO-LOCK)

## 📌 Description
> Décris précisément ce que fait cette PR : corrections, nouvelles fonctionnalités, ajustements UI, etc.

---

## ✅ Checklist ARBO-LOCK

- [ ] **Fichiers complets fournis** — pas de `...`, remplacement 1:1.
- [ ] **Aucune dérive d’architecture** — chemins/imports conformes à `arborescence_synchronisée_*.txt`.
- [ ] **Nouveau snapshot ARBO** ajouté si création/déplacement/suppression de fichiers :
  ```powershell
  (tree /F /A | Out-String) | Set-Content -Encoding UTF8 .\arborescence_synchronisée_YYYYMMDD.txt
  git add .\arborescence_synchronisée_YYYYMMDD.txt
  git commit -m "chore(arbo): snapshot YYYY-MM-DD"
  git push
