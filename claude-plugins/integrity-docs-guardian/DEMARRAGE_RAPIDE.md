# Démarrage Rapide - Guardian de l'Intégrité & Docs

**Version:** 1.0.0
**Pour:** Application ÉMERGENCE

---

## 🚀 Setup en 5 Minutes Chrono

### Étape 1: Vérifier l'Installation ✅

Le plugin est déjà installé, vérifie juste:

```bash
ls -la claude-plugins/integrity-docs-guardian/
```

T'as besoin de voir:
- `Claude.md` - Le manifeste du plugin
- `README.md` - La doc complète
- `hooks/` - Les hooks Git
- `agents/` - Les prompts des agents (Anima, Neo, Nexus)
- `scripts/` - L'implémentation Python
- `reports/` - Les rapports générés (après la 1ère exec)

### Étape 2: Tester le Plugin 🧪

Lance un test rapide pour voir si ça marche:

```bash
# Test Anima (DocKeeper)
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Test Neo (IntegrityWatcher)
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Test Nexus (Coordinator)
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

**Ce que tu vas voir:**
```
🔍 ANIMA (DocKeeper) - Scan des gaps de documentation...
📝 X fichier(s) modifié(s) détecté(s)
✅ Rapport généré: .../reports/docs_report.json
📊 Résumé: ...

🔐 NEO (IntegrityWatcher) - Vérif de l'intégrité système...
📝 X fichier(s) modifié(s) détecté(s)
✅ Rapport généré: .../reports/integrity_report.json
📊 Résumé: ...

🎯 NEXUS (Coordinator) - Génération du rapport unifié...
✅ Rapport unifié généré: .../reports/unified_report.json
📊 Résumé exécutif: ...
```

### Étape 3: Les Hooks Sont DÉJÀ Activés! 🔗

**Bonne nouvelle:** Les hooks Git sont déjà installés et actifs! 🎉

Vérifie:
```bash
ls -la .git/hooks/ | grep -E "(pre-commit|post-commit)"
```

Tu devrais voir:
```
-rwxr-xr-x ... post-commit
-rwxr-xr-x ... pre-commit
```

Si jamais tu veux les réinstaller:

```bash
# Copie les hooks
cp claude-plugins/integrity-docs-guardian/hooks/post-commit.sh .git/hooks/post-commit
cp claude-plugins/integrity-docs-guardian/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/post-commit .git/hooks/pre-commit
```

### Étape 4: Test en Conditions Réelles 📝

Fais un commit bidon pour voir la magie opérer:

```bash
# Crée un fichier de test
echo "# Test du guardian" >> test-guardian.md

# Commit
git add test-guardian.md
git commit -m "test: vérif du guardian d'intégrité"

# Regarde le show! 🎉
```

**Tu vas voir:**
```
🔍 ÉMERGENCE Integrity Guardian: Vérification Post-Commit
==========================================================
📝 Commit: abc123...
   Message: test: vérif du guardian d'intégrité

📚 [1/3] Lancement d'Anima (DocKeeper)...
   ✅ Anima a terminé avec succès

🔐 [2/3] Lancement de Neo (IntegrityWatcher)...
   ✅ Neo a terminé avec succès

🎯 [3/3] Lancement de Nexus (Coordinator)...
   ✅ Nexus a terminé avec succès

📊 Rapports disponibles:
   - Anima:  claude-plugins/integrity-docs-guardian/reports/docs_report.json
   - Neo:    claude-plugins/integrity-docs-guardian/reports/integrity_report.json
   - Nexus:  claude-plugins/integrity-docs-guardian/reports/unified_report.json
```

---

## 📊 Lire les Rapports

### Le Rapport Unifié (C'est le Plus Important)

```bash
# Joli affichage avec jq (si t'as)
jq '.' claude-plugins/integrity-docs-guardian/reports/unified_report.json

# Ou brut
cat claude-plugins/integrity-docs-guardian/reports/unified_report.json
```

**Les Sections Clés:**
- `executive_summary` - Le statut global et le titre
- `priority_actions` - Ce que t'as à faire (trié par priorité)
- `agent_status` - Les résultats individuels des agents
- `recommendations` - Suggestions court/moyen/long terme

### Niveaux de Priorité

| Priorité | Signification | Timeline |
|----------|---------------|----------|
| **P0** | Critique - Bloque le déploiement | TOUT DE SUITE |
| **P1** | Important - À fixer ASAP | Dans la journée |
| **P2** | Moyen - À planifier | Cette semaine |
| **P3** | Bas - Backlog | Dans le sprint |
| **P4** | Info - Nice to have | Backlog |

---

## 🎯 Cas d'Usage Typiques

### Cas 1: J'ai Ajouté un Nouvel Endpoint API

**Ce que le Guardian Fait:**
1. **Anima** détecte le changement de fichier router
2. **Anima** vérifie si la doc existe pour l'endpoint
3. **Neo** vérifie que le schéma OpenAPI est à jour
4. **Neo** cherche l'intégration frontend
5. **Nexus** priorise la mise à jour de doc

**Ton Action:**
1. Check `unified_report.json`
2. Suis les actions P1 (maj de la doc)
3. Suis les actions P2 (vérif frontend)

### Cas 2: J'ai Modifié un Modèle Pydantic

**Ce que le Guardian Fait:**
1. **Anima** flag le changement de schéma
2. **Neo** cherche les mismatches de types frontend
3. **Neo** alerte si breaking change détecté
4. **Nexus** escalade en P0 si critique

**Ton Action:**
1. Review les problèmes d'alignement de schéma
2. Update les types TypeScript du frontend
3. Test backend ET frontend

### Cas 3: J'ai Refactoré du Code

**Ce que le Guardian Fait:**
1. **Anima** vérifie si les interfaces ont changé
2. **Neo** vérifie qu'il n'y a pas de breaking changes
3. **Nexus** rapporte "OK" si le refacto est clean

**Ton Action:**
- Si status OK: Rien! ✅
- Si warnings: Review et corrige

---

## 🔧 Configuration

### Ajuster la Sensibilité de Détection

Édite ces fichiers pour personnaliser:

**Anima (Documentation):**
```bash
# Édite les règles de détection
vim claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Cherche: analyze_backend_changes(), analyze_frontend_changes()
```

**Neo (Intégrité):**
```bash
# Édite les règles de détection
vim claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Cherche: detect_integrity_issues()
```

**Nexus (Priorisation):**
```bash
# Édite le mapping de priorité
vim claude-plugins/integrity-docs-guardian/scripts/generate_report.py

# Cherche: generate_priority_actions()
```

### Exclure des Fichiers

Ajoute dans les scripts:

```python
# Dans scan_docs.py ou check_integrity.py
EXCLUDED_PATTERNS = [
    "**/test_*.py",
    "**/__pycache__/**",
    "**/node_modules/**"
]
```

---

## 🐛 Dépannage

### "Pas de changements détectés" alors que j'ai commit

**Solution:**
```bash
# Vérifie que git diff fonctionne
git diff --name-only HEAD~1 HEAD

# Si vide, faut peut-être commit quelque chose d'abord
git log --oneline -5  # Check les commits récents
```

### Les Scripts ne Marchent pas sur Windows

**Solution:**
```bash
# Assure-toi que Python 3.8+ est installé
python --version

# Lance avec python explicite
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
```

### Les Emoji ne S'affichent pas

**Solution:**
- Utilise Windows Terminal (supporte UTF-8)
- Ou Git Bash avec encodage UTF-8
- Les rapports marchent quand même, c'est juste l'affichage

### Les Hooks ne s'Exécutent pas Auto

**Solution:**
```bash
# Vérifie que le hook existe
ls -la .git/hooks/post-commit

# Rend exécutable
chmod +x .git/hooks/post-commit

# Test manuel
.git/hooks/post-commit
```

---

## 📚 Prochaines Étapes

1. ✅ **Teste le plugin** - Fais un commit et vérifie les rapports
2. 📖 **Lis la doc complète** - Voir [README.md](README.md) pour les détails
3. 🎨 **Personnalise les agents** - Édite `agents/*.md` pour ajuster le comportement
4. 🔗 **Les hooks sont actifs** - Ils tournent auto sur chaque commit
5. 📊 **Review les rapports** - Check `reports/unified_report.json` régulièrement

---

## 🤝 Besoin d'Aide?

- **Doc Complète:** [README.md](README.md)
- **Détails des Agents:** [agents/](agents/)
- **Config:** [Claude.md](Claude.md)

---

## 🎉 C'est Parti!

Le Guardian de l'Intégrité & Docs protège maintenant ton codebase ÉMERGENCE!

**Ce qui se passe maintenant:**
- 🔍 Chaque commit est analysé
- 📚 Les gaps de doc sont détectés
- 🔐 Les problèmes d'intégrité sont flagués
- 🎯 Des rapports actionnables sont générés
- ✅ Tu maintiens une codebase saine

**Rencontre tes agents:**
- **Anima** 📚 - Ta gardienne de documentation
- **Neo** 🔐 - Ton watchdog d'intégrité
- **Nexus** 🎯 - Ton centre de coordination

---

**Bon code! 🚀**

*ÉMERGENCE - Là où le code et la conscience convergent*

---

## 💬 Note sur le Langage

On parle cash ici. Pas de langue de bois, pas de bullshit. Les rapports sont directs, les recommandations sont claires, et si ton code a des problèmes, les agents te le diront sans détour.

**Exemples de messages typiques:**

- ✅ **OK**: "Tout est clean, go!"
- ⚠️ **Warning**: "Yo, t'as oublié de doc ton endpoint"
- 🚨 **Critical**: "STOP! Breaking change détecté - fix ça avant de push!"

Les agents sont là pour t'aider, pas pour te faire chier. Mais ils vont te dire les vraies affaires. 😎
