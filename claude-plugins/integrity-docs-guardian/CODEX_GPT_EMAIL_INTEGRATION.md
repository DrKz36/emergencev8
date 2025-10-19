# 🤖 Codex GPT Email Integration - Rapports Production Enrichis

**Version:** 1.0.0
**Date:** 2025-10-19
**Auteur:** Claude Code

---

## 📋 Vue d'Ensemble

Ce système permet d'envoyer des **rapports de production ultra-détaillés** à Codex GPT via email, contenant **tout le contexte nécessaire** pour qu'il puisse débugger de manière autonome sans avoir besoin de poser des questions.

### Problème Résolu

**AVANT (Rapport minimal) :**
```json
{
  "status": "CRITICAL",
  "errors": [
    {
      "time": "2025-10-19T14:25:32Z",
      "severity": "ERROR",
      "msg": "KeyError: 'user_id' in process..." // ← Seulement 300 chars!
    }
  ]
}
```

❌ **Impossible pour Codex GPT de faire quoi que ce soit avec ça.**

---

**MAINTENANT (Rapport enrichi) :**
```json
{
  "status": "CRITICAL",
  "errors_detailed": [
    {
      "timestamp": "2025-10-19T14:25:32.123456Z",
      "severity": "ERROR",
      "message": "KeyError: 'user_id'\n\nFailed to process chat message...",
      "stack_trace": "Traceback (most recent call last):\n  File \"...service.py\", line 142...",
      "endpoint": "https://emergence-app.../api/chat/message",
      "http_method": "POST",
      "status_code": 500,
      "error_type": "KeyError",
      "file_path": "src/backend/features/chat/service.py",
      "line_number": 142,
      "request_id": "req_abc123xyz"
    }
  ],
  "error_patterns": {
    "by_endpoint": {
      "https://.../api/chat/message": 5  // ← Cet endpoint échoue 5 fois!
    },
    "by_error_type": {
      "KeyError": 5  // ← Toujours le même type d'erreur
    },
    "by_file": {
      "src/backend/features/chat/service.py": 5  // ← Fichier responsable
    },
    "most_common_error": "KeyError"
  },
  "code_snippets": [
    {
      "file": "src/backend/features/chat/service.py",
      "line": 142,
      "code_snippet": "...\nuser_id = context['user_id']  # ← Ligne qui plante!\n...",
      "error_count": 5
    }
  ],
  "recent_commits": [
    {
      "hash": "a1b2c3d4",
      "author": "Fernando Gonzales",
      "time": "2 hours ago",
      "message": "feat(chat): Add context-aware message processing"  // ← Suspect!
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "action": "Fix recurring KeyError error",
      "details": "This error type accounts for most failures (5 occurrences)",
      "suggested_files_to_check": [...code snippets...],
      "suggested_fix": "Check request validation, error handling..."
    }
  ]
}
```

✅ **Codex GPT peut maintenant débugger de manière autonome !**

---

## 🚀 Installation

### 1. Prérequis

- Service email configuré (Gmail avec App Password)
- Variables d'environnement dans `.env` :

```env
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # App password, pas mot de passe compte

# Email où Codex GPT récupère ses tâches
CODEX_GPT_EMAIL=gonzalefernando@gmail.com
```

### 2. Scripts Créés/Modifiés

| Fichier | Description |
|---------|-------------|
| **check_prod_logs.py** | ✅ **MODIFIÉ** - Génère rapports enrichis avec full context |
| **generate_html_report.py** | ✨ **NOUVEAU** - Génère HTML riche depuis JSON |
| **send_prod_report_to_codex.py** | ✨ **NOUVEAU** - Envoie rapport à Codex GPT |

---

## 📊 Nouveau Format de Rapport

### Champs Enrichis Ajoutés

#### 1. **errors_detailed** (au lieu de errors[:300])

Chaque erreur contient maintenant :
- ✅ **Message complet** (pas juste 300 chars)
- ✅ **Stack trace complète**
- ✅ **Endpoint HTTP** (URL + méthode + status code)
- ✅ **Type d'erreur** (KeyError, ValueError, etc.)
- ✅ **Fichier + ligne** où l'erreur se produit
- ✅ **Request ID** pour traçage
- ✅ **User agent** et contexte HTTP complet
- ✅ **Payload JSON complet** (pour analyse approfondie)

#### 2. **error_patterns** (analyse de patterns)

Permet de voir d'un coup d'œil :
- Quels **endpoints** échouent le plus souvent
- Quels **types d'erreur** sont les plus fréquents
- Quels **fichiers** sont responsables
- L'erreur la plus commune (`most_common_error`)

#### 3. **code_snippets** (extraits de code suspects)

Pour les top 3 fichiers qui plantent :
- Extrait du code source (±5 lignes autour de l'erreur)
- Ligne exacte qui plante
- Nombre d'erreurs dans ce fichier

**Codex GPT peut voir directement le code bugué !**

#### 4. **recent_commits** (commits récents)

Les 5 derniers commits pour identifier le coupable potentiel :
- Hash du commit
- Auteur (Codex GPT, Fernando, etc.)
- Date relative ("2 hours ago")
- Message de commit

#### 5. **recommendations** (recommandations enrichies)

Chaque recommandation contient maintenant :
- **Fichiers affectés** (liste complète)
- **Endpoints affectés** (liste complète)
- **Commandes** à exécuter (rollback, augmenter mémoire, etc.)
- **Suggestions de fix** concrètes
- **Commits suspects** (si rollback recommandé)

---

## 🎯 Utilisation

### Méthode 1 : Envoi Manuel

```powershell
# Envoyer le rapport actuel à Codex GPT
python claude-plugins/integrity-docs-guardian/scripts/send_prod_report_to_codex.py
```

**Comportement :**
- Si status = `OK` → **Pas d'envoi** (évite le spam)
- Si status = `DEGRADED` ou `CRITICAL` → **Envoi automatique**
- Utilise `--force` pour envoyer même si OK :

```powershell
python send_prod_report_to_codex.py --force
```

### Méthode 2 : Automatique (via Cloud Scheduler)

Le système Guardian peut être configuré pour envoyer automatiquement les rapports à Codex GPT :

**Option A - Modification du hook pre-push :**

Éditer `.git/hooks/pre-push` :

```bash
#!/bin/sh
# ...existing code...

# Si production CRITICAL, envoyer rapport à Codex GPT
if [ $exit_code -eq 2 ]; then
    echo "🤖 Envoi rapport production à Codex GPT..."
    python claude-plugins/integrity-docs-guardian/scripts/send_prod_report_to_codex.py
fi
```

**Option B - Task Scheduler dédié :**

```powershell
# Créer une tâche planifiée pour vérifier prod et notifier Codex GPT toutes les 2h
schtasks /create /tn "Guardian_Codex_GPT_Alert" /tr "python c:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\send_prod_report_to_codex.py" /sc hourly /mo 2
```

### Méthode 3 : Cloud Run (Future)

Déployer le Guardian sur Cloud Run pour monitoring 24/7 et envoi automatique à Codex GPT.

---

## 📧 Format Email Reçu par Codex GPT

### Sujet

```
🚨 [CODEX GPT] Production CRITICAL - EMERGENCE V8 (19/10 14:30)
```

Le sujet contient :
- Emoji de status (✅ OK, ⚠️ DEGRADED, 🚨 CRITICAL)
- Tag `[CODEX GPT]` pour filtrage email
- Status production
- Date/heure

### Corps (HTML Enrichi)

Le rapport HTML contient :

1. **🛡️ Header** - Badge de status + timestamp
2. **📊 Summary** - Grille avec métriques (errors, warnings, critical signals)
3. **🔍 Error Patterns Analysis** - Visualisation des patterns par endpoint/fichier/type
4. **❌ Detailed Errors** - Chaque erreur avec :
   - Timestamp
   - Endpoint complet
   - Type d'erreur
   - Fichier + ligne
   - Message complet
   - Stack trace complète
   - Request ID pour traçage
5. **💻 Suspect Code Snippets** - Code source avec ligne qui plante
6. **🔀 Recent Commits** - Commits récents (potentiels coupables)
7. **💡 Recommendations** - Actions concrètes avec commandes

### Corps (Texte Brut - Fallback)

Version texte pour clients email qui ne supportent pas HTML.

---

## 🧪 Test avec Erreurs Simulées

Un rapport de test avec des erreurs simulées a été créé :

```powershell
# Générer le HTML depuis le rapport de test
python scripts/generate_html_report.py reports/prod_report_test_with_errors.json > test_report.html

# Ouvrir le HTML dans un navigateur pour visualiser
start test_report.html
```

Le fichier **test_report.html** montre exactement ce que Codex GPT recevra en cas d'erreurs.

---

## 🎨 Visualisation

### Exemple de Rapport Enrichi (Dark Theme)

Le rapport HTML utilise un **dark theme** professionnel avec :

- 🎨 **Couleurs sémantiques** :
  - 🟢 Vert = OK
  - 🟡 Orange = DEGRADED
  - 🔴 Rouge = CRITICAL

- 📦 **Cards structurées** :
  - Error cards (fond rouge foncé)
  - Warning cards (fond orange foncé)
  - Pattern boxes (fond bleu foncé)
  - Code blocks (style GitHub dark)

- 🏷️ **Tags colorés** :
  - Endpoints (bleu)
  - Fichiers (orange)
  - Types d'erreur (rouge)

- 📊 **Grilles responsives** pour patterns

---

## 🔄 Workflow Complet : Guardian → Codex GPT

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PRODGUARDIAN analyse Cloud Run logs (toutes les 6h)     │
│    → Détecte 8 erreurs + 1 crash                            │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. check_prod_logs.py génère rapport enrichi               │
│    - Extrait full context (stack traces, endpoint, etc.)   │
│    - Analyse patterns (quels endpoints/fichiers échouent)  │
│    - Extrait code source des fichiers suspects             │
│    - Récupère commits récents via git log                  │
│    → prod_report.json (ENRICHI)                             │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. send_prod_report_to_codex.py                             │
│    - Charge prod_report.json                                │
│    - Génère HTML riche via generate_html_report.py         │
│    - Envoie email à CODEX_GPT_EMAIL                         │
│    → Sujet: 🚨 [CODEX GPT] Production CRITICAL              │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Codex GPT reçoit l'email avec :                          │
│    ✅ Stack traces complètes                                │
│    ✅ Code source des lignes qui plantent                   │
│    ✅ Patterns d'erreurs (5x KeyError sur /chat/message)    │
│    ✅ Commits récents (coupable potentiel identifié)        │
│    ✅ Recommandations actionnables                          │
│    → Peut débugger AUTONOMEMENT                             │
└─────────────────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Codex GPT agit :                                         │
│    - Clone le dépôt GitHub                                  │
│    - Ouvre src/backend/features/chat/service.py:142         │
│    - Voit: user_id = context['user_id']  # ← KeyError!     │
│    - Fix: user_id = context.get('user_id', None)           │
│    - Commit + Push                                          │
│    → Problème résolu sans intervention humaine !           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Exemple de Scénario Réel

### Erreur Détectée

```
🚨 CRITICAL: 5x KeyError sur /api/chat/message
```

### Rapport Envoyé à Codex GPT

**Pattern Analysis :**
- Endpoint : `POST /api/chat/message` (5 erreurs)
- Type : `KeyError: 'user_id'` (5 occurrences)
- Fichier : `src/backend/features/chat/service.py` ligne 142

**Code Snippet :**
```python
async def process_message(self, message: str, context: dict) -> dict:
    try:
        user_id = context['user_id']  # ← LINE 142: KeyError!
        session_id = context.get('session_id')
```

**Recent Commit (2h ago) :**
```
a1b2c3d4 by Fernando Gonzales
feat(chat): Add context-aware message processing
```

**Recommendation :**
```
[HIGH] Fix recurring KeyError error
- This error accounts for most failures (5 occurrences)
- Suggested fix: Check request validation, use .get() instead of []
- Affected file: src/backend/features/chat/service.py:142
```

### Action de Codex GPT

1. Clone le dépôt
2. Ouvre `src/backend/features/chat/service.py`
3. Identifie le problème : `context['user_id']` plante si clé absente
4. Fix :
   ```python
   user_id = context.get('user_id')
   if not user_id:
       raise ValueError("Missing user_id in context")
   ```
5. Commit : `fix(chat): Handle missing user_id in context (fixes KeyError)`
6. Push

**🎉 Problème résolu en 5 minutes sans intervention humaine !**

---

## 🔧 Configuration Avancée

### Personnaliser l'Email

Modifier `send_prod_report_to_codex.py` :

```python
# Ligne 35
CODEX_GPT_EMAIL = os.getenv("CODEX_GPT_EMAIL", "ton-email-codex@gmail.com")
```

### Filtrer par Sévérité

Envoyer seulement si CRITICAL (pas DEGRADED) :

```python
# Dans send_prod_report_to_codex.py, fonction main()
if not force:
    report = load_prod_report()
    if report and report.get("status") != "CRITICAL":
        print("ℹ️  Status not CRITICAL - No email sent")
        sys.exit(0)
```

### Ajouter des Destinataires

```python
# Envoyer à plusieurs personnes
recipients = [
    os.getenv("CODEX_GPT_EMAIL"),
    "admin@example.com",
    "devops@example.com"
]

for recipient in recipients:
    await email_service.send_custom_email(
        to_email=recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )
```

---

## 🚀 Prochaines Étapes

### Phase 1 : Test en Local ✅
- [x] Enrichir check_prod_logs.py
- [x] Créer generate_html_report.py
- [x] Créer send_prod_report_to_codex.py
- [x] Tester avec erreurs simulées

### Phase 2 : Automatisation
- [ ] Ajouter hook pre-push qui envoie si CRITICAL
- [ ] Task Scheduler pour monitoring continu (2h)
- [ ] Configurer filtre Gmail pour Codex GPT

### Phase 3 : Cloud Run Guardian
- [ ] Déployer Guardian sur Cloud Run
- [ ] Cloud Scheduler → trigger toutes les 2h
- [ ] Intégration Slack (optionnel)
- [ ] Dashboard web pour visualiser rapports

---

## 📚 Fichiers Clés

```
claude-plugins/integrity-docs-guardian/
├── scripts/
│   ├── check_prod_logs.py              ← Script enrichi (analyse logs + patterns)
│   ├── generate_html_report.py         ← Générateur HTML riche
│   ├── send_prod_report_to_codex.py    ← Envoi email à Codex GPT
│   └── send_guardian_reports_email.py  ← Email Guardian générique (existant)
│
├── reports/
│   ├── prod_report.json                ← Rapport actuel (enrichi si erreurs)
│   ├── prod_report_test_with_errors.json  ← Rapport de test simulé
│   └── test_report.html                ← Rendu HTML du rapport de test
│
└── CODEX_GPT_EMAIL_INTEGRATION.md      ← Ce document
```

---

## ❓ FAQ

### Q: Codex GPT reçoit-il un email même si production OK ?

**R:** Non. Par défaut, l'email n'est envoyé que si status = `DEGRADED` ou `CRITICAL`.
Utilisez `--force` pour envoyer même si OK (pour tests).

### Q: Le rapport contient-il des secrets (API keys, mots de passe) ?

**R:** Non. Les logs Cloud Run sont filtrés pour ne pas inclure de secrets.
Si un secret apparaît quand même, il faut le redacter dans Cloud Logging avant.

### Q: Combien de temps le rapport est-il valide ?

**R:** Les rapports sont générés à chaque exécution de `check_prod_logs.py`.
Par défaut, analyse les **logs de la dernière heure** (`FRESHNESS = "1h"`).

### Q: Codex GPT peut-il répondre automatiquement après avoir fixé le bug ?

**R:** Oui, il peut envoyer un email de confirmation ou créer un commentaire dans GitHub PR.
À configurer dans Codex GPT lui-même.

### Q: Quelle est la taille maximale du rapport HTML ?

**R:** Le HTML fait généralement **50-200 KB** selon le nombre d'erreurs.
Tous les clients email modernes supportent cette taille.

---

## 🎉 Conclusion

**Ce système permet à Codex GPT de recevoir des rapports de production ultra-détaillés avec tout le contexte nécessaire pour débugger de manière autonome.**

**Avant** : "Il y a une erreur KeyError" → Codex GPT doit demander plus d'infos.
**Maintenant** : "KeyError ligne 142 dans service.py, voici le code, le stack trace complet, les commits récents, et une recommandation de fix" → Codex GPT peut agir immédiatement.

**🚀 Débogage autonome activé !**

---

**Auteur:** Claude Code
**Version:** 1.0.0
**Date:** 2025-10-19
**Projet:** ÉMERGENCE V8
