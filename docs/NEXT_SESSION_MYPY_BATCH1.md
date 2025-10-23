# 🔍 SESSION SUIVANTE - P1.2 Mypy Batch 1 Fixes

**Date création:** 2025-10-23
**Contexte:** Continuation P1.2 - Setup Mypy Type Checking
**Objectif:** Fixer 73 erreurs mypy dans 3 fichiers Core critical
**Durée estimée:** 2-3h

---

## 📊 ÉTAT ACTUEL

### Configuration Mypy ✅
- ✅ `mypy.ini` créé avec config strict progressif
- ✅ Pre-commit hook mypy actif (WARNING mode non-bloquant)
- ✅ **484 erreurs identifiées** dans 79 fichiers

### Progression P1.2
- ✅ Setup config mypy (fait)
- ✅ Audit complet (fait)
- ✅ Hook pre-commit (fait)
- ⏳ **Batch 1 fixes** (à faire maintenant)

---

## 🎯 BATCH 1 - CORE CRITICAL (73 erreurs)

### Fichiers à fixer (ordre prioritaire)

#### 1. `src/backend/shared/dependencies.py` - 30 erreurs
**Lignes de code:** 639 lignes
**Types d'erreurs:**
- `[no-untyped-def]` - Fonctions sans type hints args (lignes 33, 66, 81, 135, 147, 157, 168, 237, etc.)
- `[type-arg]` - Generic types incomplets (`dict` → `dict[str, Any]`) (lignes 103, 109, 120)
- `[unused-ignore]` - Type ignore comments inutiles (lignes 170, 287, 564, 577, 584, 590, 602, 609)
- `[no-any-return]` - Return Any au lieu de type précis (lignes 105, 183, 571)

**Fonctions à typer (liste complète):**
```python
# Ligne 33
def _normalize_identifier(value) -> Optional[str]:  # ❌ value sans type
    # FIX: def _normalize_identifier(value: Any) -> Optional[str]:

# Ligne 66
async def _resolve_user_id_from_session(session_id: Optional[str], scope_holder) -> Optional[str]:  # ❌ scope_holder
    # FIX: async def _resolve_user_id_from_session(session_id: Optional[str], scope_holder: Any) -> Optional[str]:

# Ligne 81
async def _ensure_user_id_in_claims(claims: Dict[str, Any], scope_holder) -> Optional[str]:  # ❌ scope_holder
    # FIX: async def _ensure_user_id_in_claims(claims: Dict[str, Any], scope_holder: Any) -> Optional[str]:

# Ligne 103
def _try_json(s: str) -> dict:  # ❌ dict sans params
    # FIX: def _try_json(s: str) -> dict[str, Any]:

# Ligne 109
def _read_bearer_claims_from_token(token: str) -> dict:  # ❌ dict sans params
    # FIX: def _read_bearer_claims_from_token(token: str) -> dict[str, Any]:

# Ligne 120
def _read_bearer_claims(request: Request) -> dict:  # ❌ dict sans params
    # FIX: def _read_bearer_claims(request: Request) -> dict[str, Any]:

# Ligne 135
def _is_global_dev_mode(scope_holder) -> bool:  # ❌ scope_holder
    # FIX: def _is_global_dev_mode(scope_holder: Any) -> bool:

# Ligne 147
def _has_dev_bypass(headers) -> bool:  # ❌ headers
    # FIX: def _has_dev_bypass(headers: Any) -> bool:

# Ligne 157
def _has_dev_bypass_query(params) -> bool:  # ❌ params
    # FIX: def _has_dev_bypass_query(params: Any) -> bool:

# Ligne 168
def _maybe_get_auth_service(scope_holder) -> Optional["AuthService"]:  # ❌ scope_holder
    # FIX: def _maybe_get_auth_service(scope_holder: Any) -> Optional["AuthService"]:

# Ligne 237
async def _resolve_token_claims(token: str, scope_holder, *, allow_revoked: bool = False) -> Dict[str, Any]:  # ❌ scope_holder
    # FIX: async def _resolve_token_claims(token: str, scope_holder: Any, *, allow_revoked: bool = False) -> Dict[str, Any]:

# Autres fonctions sans return type (à compléter):
# Ligne 309: def _check_dev_bypass(...) -> None:
# Ligne 436: def _prepare_session_context(...) -> SessionContext:
# Ligne 535: def _validate_ws_token(...) -> None:
# Ligne 576: def get_current_user_email(...) -> str:
# Ligne 582: def get_current_user_role(...) -> str:
# Ligne 589: def get_current_session_id(...) -> str:
# Ligne 601: def require_admin_role(...) -> None:
# Ligne 607: def require_session_id(...) -> str:
```

**Unused type:ignore à supprimer:**
```python
# Lignes: 170, 287, 564, 577, 584, 590, 602, 609
# Simplement supprimer les commentaires "# type: ignore" si mypy ne se plaint plus
```

**Commande pour voir toutes les erreurs:**
```bash
python -m mypy src/backend/shared/dependencies.py 2>&1 | grep "^src\\backend\\shared\\dependencies.py"
```

---

#### 2. `src/backend/core/session_manager.py` - 27 erreurs
**Lignes de code:** 942 lignes
**Types d'erreurs:**
- `[no-untyped-def]` - Fonctions sans type hints (ligne 57, etc.)
- `[type-arg]` - `Task` sans params (ligne 72)
- `[assignment]` - Incompatible types (ligne 164)
- `[attr-defined]` - Attribut inexistant `_warning_sent` (ligne 166)
- `[unreachable]` - Code unreachable (lignes 170, 265, 350, 492, 622, 632, 921)
- `[unused-ignore]` - Type ignore inutiles (lignes 64, 407, 412, 595, 597, 624, 626, 628)

**Problèmes critiques:**
```python
# Ligne 57
def __init__(self, db, alert_service, ...):  # ❌ Pas de types args
    # FIX: def __init__(self, db: Any, alert_service: Any, ...):

# Ligne 72
self._cleanup_task: Task = None  # type: ignore  # ❌ Task sans params
    # FIX: self._cleanup_task: Optional[Task[None]] = None

# Ligne 164
session = result.scalar_one_or_none()  # ❌ Type Session | None → Session
    # FIX: Ajouter check if session is None avant usage

# Ligne 166
if not session._warning_sent:  # ❌ Attribut inexistant
    # FIX: Vérifier si l'attribut existe ou utiliser getattr()

# Lignes 170, 265, etc. - Code unreachable
    # Investiguer pourquoi mypy pense que c'est unreachable
    # Peut-être des return/raise avant ou conditions toujours False
```

**Fonctions sans return type:**
```python
# Ligne 217: def _schedule_cleanup(self) -> None:
# Ligne 278: def _get_active_count(self) -> int:
# Ligne 551: def get_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]:
# Ligne 685: def cleanup_expired_sessions(self) -> None:
# Ligne 849: def update_session_metadata(self, session_id: str, metadata: dict) -> None:
# Ligne 911: def close_all_user_sessions(self, user_id: str) -> None:
# Ligne 931: def get_session_stats(self) -> dict[str, int]:
```

**Commande:**
```bash
python -m mypy src/backend/core/session_manager.py 2>&1 | grep "^src\\backend\\core\\session_manager.py"
```

---

#### 3. `src/backend/core/monitoring.py` - 16 erreurs
**Lignes de code:** 383 lignes
**Types d'erreurs similaires aux 2 autres fichiers**

**Commande:**
```bash
python -m mypy src/backend/core/monitoring.py 2>&1 | grep "^src\\backend\\core\\monitoring.py"
```

---

## 🛠️ STRATÉGIE DE FIX RECOMMANDÉE

### Approche Progressive (2-3h)

**Phase 1 - Quick Wins (30 min):**
1. Fixer tous les `dict` → `dict[str, Any]` (rechercher/remplacer)
2. Supprimer tous les `# type: ignore` unused
3. Ajouter `-> None` aux fonctions qui ne retournent rien

**Phase 2 - Type hints args (1h):**
1. Ajouter types aux params `scope_holder: Any`, `headers: Any`, `params: Any`
2. Fixer generic types `Task` → `Task[None]`, `Queue` → `Queue[Any]`

**Phase 3 - Problèmes complexes (1h):**
1. Fixer attributs inexistants (`_warning_sent`)
2. Investiguer code unreachable (peut-être faux positifs)
3. Fixer assignment incompatibles

**Commandes utiles:**
```bash
# Voir toutes les erreurs Batch 1
python -m mypy src/backend/shared/dependencies.py src/backend/core/session_manager.py src/backend/core/monitoring.py 2>&1 | grep "error:"

# Count erreurs après fixes
python -m mypy 2>&1 | tail -1

# Tester pre-commit hook
git add . && git commit -m "test"
```

---

## ✅ CRITÈRES DE SUCCÈS

**Objectif:** Réduire 484 → ~410 erreurs (-15%)

- [ ] dependencies.py: 30 → 0 erreurs ✅
- [ ] session_manager.py: 27 → 0 erreurs ✅
- [ ] monitoring.py: 16 → 0 erreurs ✅
- [ ] Pre-commit hook mypy fonctionne (warnings mais pas de crash)
- [ ] Tests backend passent (`pytest src/backend/`)
- [ ] Commit + push avec message clair

---

## 📝 APRÈS BATCH 1

**Mettre à jour:**
1. `ROADMAP.md` - P1.2 status (3/4 → batch 1 complété)
2. `AGENT_SYNC.md` - Session batch 1 complète
3. `docs/passation.md` - Entrée détaillée batch 1

**Prochaines étapes:**
- **Batch 2 (P2):** `chat/service.py` (17), `chat/rag_cache.py` (13), `auth/service.py` (12) - ~42 erreurs, 1h30
- **Batch 3 (P3):** Reste 73 fichiers - ~369 erreurs, 4-5h sur plusieurs sessions

---

## 🚀 COMMANDES RAPIDES

```bash
# Démarrer session
cd c:/dev/emergenceV8
git status
git pull

# Vérifier état mypy
python -m mypy 2>&1 | tail -1

# Éditer fichiers
code src/backend/shared/dependencies.py
code src/backend/core/session_manager.py
code src/backend/core/monitoring.py

# Test après fixes
python -m mypy src/backend/shared/dependencies.py 2>&1 | grep "error:" | wc -l
pytest src/backend/ -v

# Commit final
git add src/backend/shared/dependencies.py src/backend/core/session_manager.py src/backend/core/monitoring.py ROADMAP.md AGENT_SYNC.md docs/passation.md
git commit -m "fix(types): P1.2 Batch 1 mypy fixes - 73 erreurs corrigées"
git push
```

---

## 💡 ASTUCES

1. **Rechercher/remplacer global:**
   - `) -> dict:` → `) -> dict[str, Any]:`
   - `Dict` → `dict` (moderniser si besoin)
   - `# type: ignore` → (vide) pour les unused

2. **Pattern commun scope_holder:**
   ```python
   # Avant
   def func(scope_holder) -> bool:

   # Après
   def func(scope_holder: Any) -> bool:
   ```

3. **Si erreur persiste:**
   - Ajouter `# type: ignore[error-code]` spécifique
   - Documenter pourquoi dans commentaire

4. **Code unreachable:**
   - Souvent faux positif mypy
   - Vérifier logique, sinon ajouter `# type: ignore[unreachable]`

---

## 📚 RÉFÉRENCES

- [mypy.ini](../mypy.ini) - Config actuelle
- [ROADMAP.md](../ROADMAP.md#L201-L222) - P1.2 détails
- [reports/mypy_report.txt](../reports/mypy_report.txt) - Rapport complet (généré par hook)
- Mypy docs: https://mypy.readthedocs.io/en/stable/

---

**🔥 Allez, on va dégommer ces 73 erreurs ! Let's fucking go! 🚀**
