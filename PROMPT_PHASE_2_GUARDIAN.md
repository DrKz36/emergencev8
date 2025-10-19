# 🚀 PROMPT PHASE 2 - GUARDIAN CLOUD (USAGE TRACKING SYSTEM)

**Date:** 2025-10-19
**Contexte:** Suite Phase 1 (Email Unification ✅ COMPLÈTE)
**Objectif Phase 2:** Implémenter système de tracking utilisateurs (sessions, features, erreurs)

---

## 📋 CONTEXTE - PHASE 1 TERMINÉE

**Phase 1 (COMPLÈTE ✅) - Email Unification:**
- ✅ 2 systèmes email unifiés → 1 seul service Jinja2
- ✅ EmailService refactoré (881 → 414 lignes, -53%)
- ✅ 8 templates Jinja2 créés (email_base, guardian_report, beta_invitation, etc.)
- ✅ GuardianEmailService créé (email_report.py)
- ✅ Doublons supprimés (1220 lignes)
- ✅ Documentation complète (EMAIL_UNIFICATION.md, GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md)

**Commit:** `ea48fb9` - "feat(email): Phase 1 Guardian Cloud - Unification système email ✅"

---

## 🎯 MISSION PHASE 2 (3 JOURS)

**Objectif:** Créer un système de tracking des utilisateurs pour monitorer l'activité dans ÉMERGENCE V8

**Ce qu'il faut tracker:**
- Sessions utilisateur (login/logout, durée)
- Features utilisées (endpoints appelés)
- Erreurs rencontrées par user
- **PAS** le contenu des messages (privacy)

**Livrables attendus:**
1. Base de données (Firestore collections)
2. Middleware de tracking automatique
3. UsageGuardian agent (agrège stats)
4. Endpoint API pour dashboard admin

---

## 📖 DOCUMENTS À LIRE EN PRIORITÉ

**OBLIGATOIRE (dans l'ordre) :**

1. **`AGENT_SYNC.md`** - État actuel du dépôt
2. **`docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md`** - Plan complet (aller section PHASE 2 lignes 156-241)
3. **`docs/passation.md`** - 3 dernières entrées (voir session Phase 1)
4. **`docs/EMAIL_UNIFICATION.md`** - Comprendre architecture email unifiée
5. **`git log --oneline -5`** - Derniers commits

**RECOMMANDÉ :**
- `CLAUDE.md` - Ton mode opératoire
- `src/backend/features/auth/router.py` - Voir JWT auth existant
- `src/backend/main.py` - Voir middleware actuel

---

## 🏗️ PLAN PHASE 2 (DÉTAILS)

### **TÂCHE 2.1 - Base de données (1 jour)**

**Créer 3 collections Firestore:**

**Collection `user_sessions` :**
```python
{
    "id": str,  # UUID session
    "user_email": str,  # Email utilisateur
    "session_start": datetime,
    "session_end": datetime | None,
    "duration_seconds": int | None,
    "ip_address": str | None,  # Optionnel
    "user_agent": str | None,
}
```

**Collection `feature_usage` :**
```python
{
    "id": str,  # UUID
    "user_email": str,
    "feature_name": str,  # Ex: "chat_message", "document_upload", "thread_create"
    "endpoint": str,  # Ex: "/api/chat/message"
    "timestamp": datetime,
    "success": bool,
    "error_message": str | None,
    "duration_ms": int | None,
}
```

**Collection `user_errors` :**
```python
{
    "id": str,  # UUID
    "user_email": str,
    "endpoint": str,
    "method": str,  # GET, POST, etc.
    "error_type": str,  # "ValidationError", "HTTPException", etc.
    "error_code": int,  # 400, 500, etc.
    "error_message": str,
    "stack_trace": str | None,
    "timestamp": datetime,
}
```

**Fichiers à créer:**
- `src/backend/features/usage/models.py` - Pydantic models
- `src/backend/features/usage/repository.py` - Firestore CRUD

---

### **TÂCHE 2.2 - Middleware Tracking (1 jour)**

**Créer middleware qui capture automatiquement:**
- Toutes les requêtes API
- User email depuis JWT token
- Endpoint appelé + méthode
- Succès/erreur (status code)
- Durée de la requête

**IMPORTANT - Privacy:**
- ✅ Capturer `/api/chat/message` (endpoint)
- ❌ NE PAS capturer le `body` (contenu message)
- ✅ Capturer `/api/documents/upload` (endpoint)
- ❌ NE PAS capturer le fichier

**Fichier à créer:**
- `src/backend/middleware/usage_tracking.py`

**Exemple structure:**
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from features.usage.repository import UsageRepository

class UsageTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract user email from JWT
        user_email = extract_user_from_token(request)

        # Track feature usage
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log success
            await log_feature_usage(
                user_email=user_email,
                endpoint=request.url.path,
                success=True,
                duration_ms=duration_ms
            )

            return response

        except Exception as e:
            # Log error
            await log_user_error(
                user_email=user_email,
                endpoint=request.url.path,
                error=e
            )
            raise
```

**Intégrer dans `main.py` :**
```python
from middleware.usage_tracking import UsageTrackingMiddleware

app.add_middleware(UsageTrackingMiddleware)
```

---

### **TÂCHE 2.3 - UsageGuardian Agent (1 jour)**

**Créer agent qui agrège stats toutes les 2h:**

**Fichier à créer:**
- `src/backend/features/usage/guardian.py`
- `src/backend/features/usage/router.py`

**Fonctionnalités:**
```python
class UsageGuardian:
    async def generate_report(self, hours: int = 2) -> dict:
        """
        Génère rapport usage dernières N heures

        Returns:
            {
                "period": "2025-10-19 14:00 - 16:00",
                "active_users": 5,
                "total_requests": 1234,
                "total_errors": 12,
                "users": [
                    {
                        "email": "user@example.com",
                        "total_time_minutes": 45,
                        "features_used": ["chat", "documents", "voice"],
                        "requests_count": 234,
                        "errors_count": 2,
                        "errors": [
                            {
                                "endpoint": "/api/documents/upload",
                                "error": "File too large",
                                "timestamp": "2025-10-19 15:30:12"
                            }
                        ]
                    }
                ],
                "top_features": [
                    {"name": "chat_message", "count": 567},
                    {"name": "thread_create", "count": 123},
                ],
                "error_breakdown": {
                    "400": 5,
                    "500": 2,
                    "503": 1
                }
            }
        """
```

**Endpoint API:**
```python
@router.get("/api/usage/summary")
async def get_usage_summary(
    hours: int = 2,
    current_user = Depends(require_admin)
) -> dict:
    """Retourne rapport usage pour dashboard admin"""
    guardian = UsageGuardian()
    return await guardian.generate_report(hours=hours)
```

**Sauvegarder rapport JSON:**
- `reports/usage_report.json` (pour email Guardian Phase 5)

---

## 📊 INTÉGRATION AVEC PHASE 1 (EMAIL)

**Le rapport usage sera intégré dans l'email Guardian:**

Le template `guardian_report_email.html` a déjà une section `{% if usage_stats %}` prête !

**Phase 5 appellera:**
```python
# Charge usage report
usage_report = load_report('usage_report.json')

# Envoie email Guardian avec usage stats
await email_service.send_guardian_report(
    to_email="admin@example.com",
    reports={
        'prod_report.json': prod_data,
        'usage_stats': usage_report,  # ← ICI
    }
)
```

---

## ✅ CHECKLIST PHASE 2

### Base de données (1j)
- [ ] Créer `src/backend/features/usage/__init__.py`
- [ ] Créer `src/backend/features/usage/models.py` (Pydantic models)
- [ ] Créer `src/backend/features/usage/repository.py` (Firestore CRUD)
- [ ] Créer collections Firestore (user_sessions, feature_usage, user_errors)
- [ ] Tests unitaires repository

### Middleware (1j)
- [ ] Créer `src/backend/middleware/usage_tracking.py`
- [ ] Implémenter `UsageTrackingMiddleware`
- [ ] Extract user email depuis JWT token
- [ ] Log feature usage (success)
- [ ] Log user errors (exceptions)
- [ ] Intégrer dans `main.py`
- [ ] Tester en local (vérifier Firestore populated)

### UsageGuardian (1j)
- [ ] Créer `src/backend/features/usage/guardian.py`
- [ ] Créer `src/backend/features/usage/router.py`
- [ ] Implémenter `generate_report()` (agrège 2h)
- [ ] Endpoint `/api/usage/summary` (admin only)
- [ ] Sauvegarder `reports/usage_report.json`
- [ ] Tests endpoint (mock data)

### Documentation
- [ ] Mettre à jour `docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md` (status Phase 2)
- [ ] Créer `docs/USAGE_TRACKING.md` (documentation système)
- [ ] Mettre à jour `AGENT_SYNC.md`
- [ ] Mettre à jour `docs/passation.md`

### Tests finaux
- [ ] Test middleware capture requêtes
- [ ] Test privacy (pas de body capturé)
- [ ] Test UsageGuardian génère rapport valide
- [ ] Test endpoint admin (require_admin works)
- [ ] Vérifier Firestore collections

---

## 🚨 POINTS D'ATTENTION CRITIQUES

### PRIVACY (ULTRA IMPORTANT)
⚠️ **NE JAMAIS CAPTURER:**
- Contenu messages chat (`/api/chat/message` body)
- Contenu fichiers uploadés
- Mots de passe
- Tokens JWT complets

✅ **CAPTURER UNIQUEMENT:**
- Endpoint appelé
- User email
- Timestamp
- Success/error
- Durée requête

### PERFORMANCE
- Middleware doit être **ultra rapide** (<10ms overhead)
- Utiliser Firestore batch writes si possible
- Fire-and-forget logging (pas de `await` bloquant)

### ADMIN ONLY
- Endpoint `/api/usage/summary` doit require admin role
- Utiliser `Depends(require_admin)` (déjà existant dans codebase)

---

## 🛠️ COMMANDES UTILES

```bash
# Lire état sync
cat AGENT_SYNC.md | head -50

# Voir plan complet Phase 2
cat docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md | sed -n '156,241p'

# Voir dernières entrées passation
cat docs/passation.md | head -200

# Tester Firestore local
python -c "from google.cloud import firestore; db = firestore.Client(); print('Firestore OK')"

# Tester middleware
# (lancer backend puis curl /api/health)
curl http://localhost:8000/api/health
```

---

## 📞 CONTACT / AIDE

**Questions architecture :**
- Lire `docs/architecture/10-Components.md`
- Lire `docs/architecture/30-Contracts.md`

**Questions Firestore :**
- Exemple existant : `src/backend/features/threads/repository.py`
- Exemple existant : `src/backend/features/memory/repository.py`

**Questions JWT auth :**
- Exemple existant : `src/backend/features/auth/router.py`
- Fonction `get_current_user()` déjà implémentée

---

## 🎯 RÉSULTAT ATTENDU

**À la fin de Phase 2, on doit avoir:**

1. ✅ Système tracking automatique fonctionnel
2. ✅ 3 collections Firestore peuplées avec vraie data
3. ✅ UsageGuardian génère rapport JSON toutes les 2h
4. ✅ Endpoint `/api/usage/summary` accessible admin
5. ✅ Privacy respectée (pas de contenu capturé)
6. ✅ Documentation complète (`USAGE_TRACKING.md`)
7. ✅ Tests passent
8. ✅ Commit propre + passation.md à jour

**Métriques de succès:**
- Middleware overhead < 10ms
- Rapport usage contient stats utilisateurs réels
- Privacy OK (audit code review)
- Admin peut voir dashboard usage

---

## 🚀 COMMANDE DE LANCEMENT

**Copie-colle ce prompt dans la prochaine instance Claude Code :**

```
Je reprends le projet ÉMERGENCE V8 sur la PHASE 2 du Guardian Cloud Implementation Plan.

Phase 1 (Email Unification) est COMPLÈTE ✅

Je dois maintenant implémenter le **Usage Tracking System** (Phase 2 - 3 jours).

Lis en priorité:
1. AGENT_SYNC.md (état dépôt)
2. docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md section PHASE 2 (lignes 156-241)
3. docs/passation.md (3 dernières entrées)
4. PROMPT_PHASE_2_GUARDIAN.md (ce fichier)

Objectif Phase 2:
- Créer 3 collections Firestore (user_sessions, feature_usage, user_errors)
- Créer middleware tracking automatique (privacy-compliant)
- Créer UsageGuardian agent (agrège stats 2h)
- Créer endpoint /api/usage/summary (admin only)

Fonce direct, pas besoin de demander permission. Suis le plan détaillé dans PROMPT_PHASE_2_GUARDIAN.md !

Attaque Phase 2 copain ! 🔥
```

---

**🤖 Document généré par Claude Code - Phase 1 terminée**
**Date:** 2025-10-19
**Prêt pour Phase 2 ! 🚀**
