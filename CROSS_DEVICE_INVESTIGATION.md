# Investigation: Problème de Persistance Cross-Device

**Date:** 2025-11-01
**Agent:** Claude Code
**Issue:** Les interactions/documents créés sur mobile ne se retrouvent pas sur desktop

---

## 🔍 Investigation Complète

### Résumé Rapide

**Verdict:** Le code est **théoriquement correct** pour la persistance cross-device, MAIS il peut y avoir un problème avec les anciens JWT ou avec la résolution du `user_id`.

---

## 📊 Analyse du Code

### 1. Backend - Génération JWT

**Fichier:** `src/backend/features/auth/service.py:951-1079`

Le JWT contient un `sub` (user_id) qui est un **hash constant de l'email** :

```python
"sub": self._hash_subject(email),  # ligne 969
```

✅ **Verdict:** Le `sub` est **constant** pour un même email → OK pour cross-device

### 2. Backend - LoginResponse

**Fichier:** `src/backend/features/auth/models.py:56-63`

```python
class LoginResponse(BaseModel):
    token: str
    session_id: str
    user_id: str  # ← INCLUS dans la réponse
    email: str
```

✅ **Verdict:** Le backend renvoie bien le `user_id` au frontend

### 3. Frontend - Stockage user_id

**Fichier:** `src/frontend/main.js:1273-1299`

```javascript
const normalizedUserId = this.normalizeUserId(
  payload?.userId ?? payload?.user_id ?? ...
);
this.state?.set?.('user.id', normalizedUserId);
```

✅ **Verdict:** Le frontend stocke le `user_id` dans le state

### 4. Backend - Queries avec user_id

**Fichier:** `src/backend/core/database/queries.py:177-192`

```python
def _build_scope_condition(user_id, session_id):
    if normalized_user:
        # PRIORITÉ AU user_id !
        return f"{user_column} = ?", (normalized_user,)
    if normalized_session:
        return f"{session_column} = ?", (normalized_session,)
```

✅ **Verdict:** Les queries **priorisent user_id** s'il est fourni

### 5. Backend - Récupération user_id dans les routers

**Fichier:** `src/backend/features/threads/router.py:53-61`

```python
items = await queries.get_threads(
    db,
    session_id=session.session_id,
    user_id=session.user_id,  # ← PASSÉ !
    ...
)
```

✅ **Verdict:** Les routers passent bien le `user_id` aux queries

### 6. Backend - SessionContext et user_id

**Fichier:** `src/backend/shared/dependencies.py:381-428`

```python
async def get_session_context(request: Request) -> SessionContext:
    claims = await _get_claims_from_request(request)
    user_id = await _ensure_user_id_in_claims(claims, request)  # ligne 419
    return SessionContext(
        session_id=session_id,
        user_id=user_id,  # ← Peut être None !
        ...
    )
```

⚠️ **PROBLÈME POTENTIEL:** Si `_ensure_user_id_in_claims()` renvoie `None`, alors `user_id=None` dans le `SessionContext` !

### 7. Fonction _ensure_user_id_in_claims()

**Fichier:** `src/backend/shared/dependencies.py:81-97`

```python
async def _ensure_user_id_in_claims(claims, scope_holder):
    user_candidate = _normalize_identifier(claims.get("sub") or claims.get("user_id"))
    if user_candidate:
        return user_candidate  # ✅ OK si JWT contient sub

    # ❌ Sinon, essaie de résoudre via session_id
    session_candidate = _normalize_identifier(claims.get("session_id") or ...)
    if not session_candidate:
        return None  # ← user_id sera None !

    resolved = await _resolve_user_id_from_session(session_candidate, scope_holder)
    return resolved  # ← Peut être None si résolution échoue
```

⚠️ **PROBLÈME IDENTIFIÉ:**

Si :
1. Le JWT ne contient PAS de `sub` (anciens JWT ?)
2. ET la résolution via `session_id` échoue

Alors `user_id=None` → Les queries utilisent `session_id` → **Pas de cross-device !**

---

## 🐛 Cause Racine Probable

### Scénario 1: Anciens JWT sans `sub`

Si l'utilisateur a un JWT créé **avant** que le système n'inclue le `sub`, alors :
- Le JWT ne contient pas de `sub`
- `_ensure_user_id_in_claims()` essaie de résoudre via `session_id`
- Si échec → `user_id=None`
- Les queries utilisent `session_id` → **Isolation par session !**

### Scénario 2: Table auth_sessions sans colonne user_id

Si la table `auth_sessions` n'a pas la colonne `user_id` (ancienne DB), alors :
- `_resolve_user_id_from_session()` ne peut pas résoudre le `user_id`
- `user_id=None`
- Isolation par `session_id`

---

## ✅ Solutions Proposées

### Solution 1: Vérifier JWT Actuel

```bash
# Dans la console navigateur (mobile + desktop)
localStorage.getItem('emergence.id_token')

# Décoder le JWT (partie 2, base64)
# Vérifier si le JWT contient "sub"
```

### Solution 2: Forcer Re-Login

Si les JWT actuels n'ont pas de `sub`, forcer un logout/login pour tous les users :

```javascript
// Frontend
if (!hasValidUserIdInJWT()) {
  clearAuth();
  location.reload();
}
```

### Solution 3: Migration DB

Assurer que la table `auth_sessions` a la colonne `user_id` :

```sql
-- Vérifier
PRAGMA table_info(auth_sessions);

-- Si user_id manque
ALTER TABLE auth_sessions ADD COLUMN user_id TEXT;
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);
```

### Solution 4: Backfill user_id

Populer les `user_id` manquants dans les tables existantes :

```sql
-- Threads
UPDATE threads
SET user_id = (SELECT user_id FROM auth_sessions WHERE auth_sessions.id = threads.session_id)
WHERE user_id IS NULL AND session_id IS NOT NULL;

-- Documents
UPDATE documents
SET user_id = (SELECT user_id FROM auth_sessions WHERE auth_sessions.id = documents.session_id)
WHERE user_id IS NULL AND session_id IS NOT NULL;
```

### Solution 5: Logging pour Debug

Ajouter des logs temporaires pour vérifier :

```python
# Dans _ensure_user_id_in_claims()
logger.info(f"[DEBUG] JWT claims: sub={claims.get('sub')}, user_id={claims.get('user_id')}, session_id={claims.get('session_id')}")
logger.info(f"[DEBUG] Resolved user_id: {user_candidate or resolved}")
```

---

## 🧪 Tests à Faire

### Test 1: Vérifier JWT sur 2 Devices

1. Se connecter avec le même email sur mobile
2. Copier le JWT (localStorage)
3. Se connecter avec le même email sur desktop
4. Copier le JWT
5. Décoder les 2 JWT et vérifier que le `sub` est **identique**

### Test 2: Vérifier DB auth_sessions

```sql
SELECT id, email, user_id, issued_at
FROM auth_sessions
WHERE user_id IS NULL
LIMIT 10;
```

Si des lignes existent avec `user_id=NULL`, c'est le problème !

### Test 3: Vérifier Threads Cross-Device

1. Mobile: Créer un thread
2. Desktop: Lister les threads avec le même email
3. Si le thread n'apparaît PAS → Confirme le bug

```sql
-- Vérifier
SELECT id, type, user_id, session_id, created_at
FROM threads
WHERE user_id = '<hash_email>';
```

---

## 📝 Recommandations

1. **URGENT:** Tester avec 2 devices (mobile + desktop, même email)
2. **URGENT:** Vérifier le schéma DB (`auth_sessions`, `threads`, `documents`)
3. **Ajouter logs:** Temporairement dans `_ensure_user_id_in_claims()` pour debug
4. **Si bug confirmé:** Forcer re-login de tous les users + backfill DB
5. **Long terme:** Ajouter un test e2e pour vérifier cross-device

---

## 🔗 Fichiers Clés à Vérifier

- `src/backend/features/auth/service.py` (ligne 969 - génération sub)
- `src/backend/shared/dependencies.py` (ligne 81-97 - _ensure_user_id_in_claims)
- `src/backend/core/database/queries.py` (ligne 177-192 - _build_scope_condition)
- `src/frontend/main.js` (ligne 1273-1299 - handleLoginSuccess)
- `src/frontend/shared/api-client.js` (ligne 154-158 - headers X-Session-Id + X-User-Id)

---

## 🎯 Conclusion

**Le code est architecturalement correct pour la persistance cross-device.**

Mais il peut y avoir un problème avec :
- Anciens JWT sans `sub`
- Table `auth_sessions` sans colonne `user_id`
- Données existantes sans `user_id` backfillé

**Action immédiate:** Tester sur 2 devices + vérifier DB + ajouter logs pour confirmer le bug.
