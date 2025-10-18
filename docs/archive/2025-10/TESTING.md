# 🧪 GUIDE DES TESTS - ÉMERGENCE V8

## 📊 État Actuel de la Couverture

### Frontend
- ✅ 7 fichiers de tests
- ✅ Tests pour App, WebSocket, State-Manager
- ✅ Tests pour modules Admin, Chat, Threads, i18n
- 🎯 **Nouveau**: Tests complets pour StateManager

### Backend
- ✅ 4 fichiers de tests
- ✅ Tests pour SessionManager, AuthService, DatabaseManager
- ✅ Tests pour StreamYield
- 🟡 **Statut**: 9/14 tests SessionManager ✅ | 5 à adapter

---

## 🚀 Lancer les Tests

### Tests Frontend (Node.js)

```bash
# Tous les tests
npm test

# Test spécifique
node --test src/frontend/core/__tests__/state-manager.test.js
```

### Tests Backend (Python/Pytest)

```bash
# Tous les tests backend
cd src && python -m pytest backend/tests/ -v

# Test spécifique
cd src && python -m pytest backend/tests/test_session_manager.py -v

# Avec couverture
cd src && python -m pytest backend/tests/ --cov=backend --cov-report=html
```

---

## 📁 Structure des Tests

```
src/
├── frontend/
│   ├── core/__tests__/
│   │   ├── app.ensureCurrentThread.test.js     ✅
│   │   ├── websocket.dedupe.test.js            ✅
│   │   ├── state-manager.test.js               🆕
│   │   └── helpers/
│   │       └── dom-shim.js
│   ├── features/
│   │   ├── admin/__tests__/
│   │   ├── chat/__tests__/
│   │   └── threads/__tests__/
│   └── shared/__tests__/
│       └── i18n.test.js
│
└── backend/
    └── tests/
        ├── test_session_manager.py             🆕
        ├── test_auth_service.py                🆕
        ├── test_database_manager.py            🆕
        └── test_stream_yield.py                ✅
```

---

## 🎯 Tests Critiques Ajoutés

### 1. **test_session_manager.py** (14 tests)

**Couverture:**
- Initialisation avec/sans MemoryAnalyzer
- Création de sessions
- Récupération (get/ensure)
- Gestion des messages
- Système d'alias
- Cas limites

**Statut:** 9/14 passent ✅

**À corriger:**
- Adapter les mocks pour `fetch_one()` au lieu de `fetchone()`
- Corriger la construction de `ChatMessage` (Pydantic validation)
- Adapter les méthodes `add_message()` et `register_session_alias()`

### 2. **test_auth_service.py** (15+ tests)

**Couverture:**
- Hashing de mots de passe (bcrypt)
- Génération/validation de tokens JWT
- Inscription utilisateur
- Authentification
- Autorisation par rôle

**Statut:** À exécuter après adaptation

### 3. **test_database_manager.py** (12+ tests)

**Couverture:**
- Connexion/déconnexion
- Opérations CRUD (Create, Read, Update, Delete)
- Transactions (commit/rollback)
- Gestion d'erreurs
- Base de données mémoire

**Statut:** À exécuter après adaptation

### 4. **test state-manager.js** (16 tests)

**Couverture:**
- get/set basiques et imbriqués
- Système de subscription
- Unsubscribe
- Gestion des types primitifs
- Isolation entre instances

**Statut:** À exécuter

---

## 🔧 Commandes Utiles

### Pytest

```bash
# Tests avec output détaillé
pytest -v

# Tests en mode watch (avec pytest-watch)
ptw

# Tests avec markers
pytest -m "slow"  # Seulement tests lents
pytest -m "not slow"  # Skip tests lents

# Arrêter au premier échec
pytest -x

# Reruns (avec pytest-rerunfailures)
pytest --reruns 3
```

### Node Test Runner

```bash
# Mode watch
node --test --watch

# Avec reporter custom
node --test --test-reporter=spec

# Parallel
node --test --test-concurrency=4
```

---

## 📝 Bonnes Pratiques

### Tests Backend

1. **Isolation**: Utiliser des fixtures pour DB temporaires
2. **Mocks**: AsyncMock pour les opérations async
3. **Cleanup**: Toujours fermer les connexions dans `finally` ou fixtures
4. **Nommage**: `test_<composant>_<scenario>_<résultat_attendu>`

```python
@pytest.fixture
async def temp_db():
    db = await create_test_db()
    yield db
    await db.cleanup()
```

### Tests Frontend

1. **DOM Shim**: Utiliser `dom-shim.js` pour tests sans navigateur
2. **Assertions strictes**: `assert.strictEqual()` plutôt que `assert.equal()`
3. **Async**: Toujours utiliser done() callback ou async/await
4. **Isolation**: Ne pas partager d'état entre tests

```javascript
test('Ma feature', async (t) => {
    const result = await maFonction();
    assert.strictEqual(result, expected);
});
```

---

## 🎭 Mocking

### Backend (unittest.mock)

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock async
mock_db = AsyncMock()
mock_db.execute.return_value = {"result": "data"}

# Patch
with patch('module.function') as mock_func:
    mock_func.return_value = "mocked"
```

### Frontend (Manual Mocks)

```javascript
const mockApi = {
    get: async () => ({ data: [] }),
    post: async () => ({ ok: true })
};
```

---

## 📈 Prochaines Étapes

### Phase 1 - Stabilisation (En cours)
- [x] Créer tests SessionManager
- [x] Créer tests AuthService
- [x] Créer tests DatabaseManager
- [x] Créer tests StateManager
- [ ] Adapter et corriger les tests existants
- [ ] Atteindre 80% couverture composants critiques

### Phase 2 - Extension
- [ ] Tests WebSocket (connexion, reconnexion, messages)
- [ ] Tests API client (retry, error handling)
- [ ] Tests routing (navigation, guards)
- [ ] Tests composants UI critiques

### Phase 3 - Intégration
- [ ] Tests end-to-end (Playwright)
- [ ] Tests de performance
- [ ] Tests de charge
- [ ] CI/CD automatisé

---

## 🐛 Debugging

### Tests qui échouent

```bash
# Mode verbose avec traceback complet
pytest -vv --tb=long

# Avec pdb (debugger)
pytest --pdb

# Logs
pytest --log-cli-level=DEBUG
```

### Tests qui pendent

```bash
# Avec timeout
pytest --timeout=10
```

---

## 📚 Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [Node Test Runner](https://nodejs.org/api/test.html)
- [AsyncIO Testing](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/models/)

---

**Dernière mise à jour:** 2025-10-08
**Couverture cible:** 80%
**Status:** 🟡 En progression
