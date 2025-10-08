# Limitations connues et solutions de contournement

## 📊 État actuel des tests

### Résumé
- **Frontend:** 7/7 tests ✅ (100%)
- **Backend:** 78/85 tests ✅ (91.8%)
- **Sécurité:** Tests créés, à exécuter
- **E2E:** Tests créés, à exécuter

---

## ⚠️ Limitations techniques

### 1. Tests Backend (8.2% d'échecs)

#### 1.1 Tests de migration DB (2 tests)
**Fichier:** `tests/test_memory_archives.py`

**Problème:**
```python
AttributeError: 'async_generator' object has no attribute 'fetch_all'
```

**Cause:** Configuration pytest incompatible avec fixtures async

**Impact:** ❌ Faible - Les migrations fonctionnent en production

**Solution de contournement:**
- Utiliser `@pytest_asyncio.fixture` au lieu de `@pytest.fixture`
- Ou migrer vers pytest-asyncio strict mode

**Code à modifier:**
```python
# Avant
@pytest.fixture
async def db_manager():
    ...

# Après
@pytest_asyncio.fixture
async def db_manager():
    ...
```

---

#### 1.2 Tests Concept Search (7 tests)
**Fichier:** `tests/backend/features/test_memory_concept_search.py`

**Problème:**
```
fixture 'app' not found
```

**Cause:** Fixture `app` non définie dans conftest.py local

**Impact:** ❌ Faible - Le endpoint fonctionne (testé manuellement)

**Solution de contournement:**
- Utiliser `auth_app_factory` existant
- Ou créer fixture `app` dans `conftest.py`

**Code à ajouter:**
```python
# Dans tests/backend/features/conftest.py
@pytest.fixture
def app():
    from backend.main import create_app
    return create_app()
```

---

#### 1.3 User Scope Persistence (4 tests)
**Fichier:** `tests/backend/features/test_user_scope_persistence.py`

**Problème:** Tests échouent sur certaines validations de scope utilisateur

**Impact:** ⚠️ Moyen - Peut affecter isolation multi-utilisateurs

**Solution de contournement:**
- Vérifier en E2E avec test `test_multiple_users_isolated`
- Monitoring en production de fuites de données inter-utilisateurs

---

### 2. Limitations fonctionnelles

#### 2.1 Rate Limiting
**Statut:** ✅ Implémenté partiellement

**Limitations:**
- Rate limiting uniquement sur `/api/auth/login`
- Pas de protection sur autres endpoints

**Risques:**
- Abus possible sur `/api/chat` (spam)
- DDoS possible sur endpoints publics

**Solutions recommandées:**
```python
# Ajouter middleware global
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.route("/api/chat")
@limiter.limit("100/minute")
async def chat():
    ...
```

---

#### 2.2 Validation des entrées
**Statut:** ⚠️ Partielle

**Limitations:**
- Pas de limite de taille sur messages chat
- Pas de sanitization XSS côté serveur
- Validation JSON basique

**Risques:**
- Messages géants peuvent crasher le serveur
- XSS possible si rendu HTML côté client

**Solutions recommandées:**
```python
# Dans models/chat.py
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=50000)  # 50KB max

    @validator('message')
    def sanitize_message(cls, v):
        import bleach
        return bleach.clean(v)
```

---

#### 2.3 Gestion d'erreurs IA
**Statut:** ⚠️ À améliorer

**Limitations:**
- Timeout AI non configuré
- Retry logic basique
- Pas de fallback si modèle indisponible

**Risques:**
- Requêtes qui pendent indéfiniment
- Expérience utilisateur dégradée

**Solutions recommandées:**
```python
# Ajouter timeout et retry
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_ai_with_timeout(message):
    async with timeout(30):  # 30s max
        return await ai_service.generate(message)
```

---

### 3. Limitations de performance

#### 3.1 Recherche vectorielle
**Statut:** ⚠️ Non optimisée

**Limitations:**
- Pas d'index HNSW pour recherche rapide
- Calcul de similarité en mémoire
- Pas de cache pour requêtes fréquentes

**Impact:** 🐌 Lenteur sur gros corpus (>10K concepts)

**Solutions recommandées:**
```sql
-- Créer index HNSW (si ChromaDB ou Qdrant)
CREATE INDEX idx_vector_hnsw ON embeddings
USING hnsw (embedding vector_cosine_ops);

-- Ou utiliser cache Redis
import redis
cache = redis.Redis()

@lru_cache(maxsize=1000)
def search_concepts(query: str):
    ...
```

---

#### 3.2 Database pooling
**Statut:** ❓ Non vérifié

**Limitations:**
- Configuration pool de connexions SQLite non optimale
- Pas de monitoring des connexions actives

**Solutions recommandées:**
```python
# Dans database/manager.py
class DatabaseManager:
    def __init__(self, db_path: str):
        self.pool = create_pool(
            db_path,
            min_size=5,
            max_size=20,
            timeout=30
        )
```

---

## 🔒 Limitations de sécurité

### 3.1 Authentification
**Statut:** ✅ Bonne mais améliorable

**Limitations:**
- Pas de 2FA (authentification à deux facteurs)
- Pas de récupération de mot de passe
- Tokens JWT sans rotation

**Risques:**
- Compte compromis si mot de passe volé
- Token volé valide jusqu'à expiration

**Solutions recommandées:**
- Implémenter TOTP 2FA (pyotp)
- Rotation de refresh tokens
- Email de récupération sécurisée

---

### 3.2 Encryption
**Statut:** ⚠️ Données en clair

**Limitations:**
- Messages stockés non chiffrés en DB
- Pas de chiffrement at-rest
- Embeddings vectoriels en clair

**Risques:**
- Si DB compromise, toutes les conversations exposées

**Solutions recommandées:**
```python
from cryptography.fernet import Fernet

# Chiffrer avant stockage
cipher = Fernet(ENCRYPTION_KEY)
encrypted_message = cipher.encrypt(message.encode())

# Déchiffrer à la lecture
decrypted = cipher.decrypt(encrypted_message).decode()
```

---

## 📈 Monitoring recommandé

### Métriques critiques à surveiller

#### 4.1 Performance
```python
# À instrumenter avec Prometheus/Grafana
- Latence p50/p95/p99 par endpoint
- Taux d'erreur 5xx
- Durée appels IA (timeout)
- Utilisation mémoire/CPU
```

#### 4.2 Sécurité
```python
# Alertes à configurer
- Tentatives login échouées (>5/min)
- Requêtes SQL suspectes (détection pattern)
- Requêtes géantes (>1MB)
- Accès non autorisés (401/403)
```

#### 4.3 Business
```python
# KPIs à tracker
- Nombre de threads actifs
- Messages/jour par utilisateur
- Temps de réponse IA moyen
- Taux de rétention utilisateurs
```

---

## 🔧 Quick Fixes prioritaires

### Top 3 à implémenter immédiatement

1. **Rate limiting global** (2h)
   ```python
   pip install slowapi
   # Appliquer sur tous endpoints
   ```

2. **Validation taille messages** (1h)
   ```python
   max_length=50000 dans Pydantic models
   ```

3. **Timeout AI requests** (1h)
   ```python
   asyncio.timeout(30) sur appels IA
   ```

---

## 📝 Checklist avant production

### Sécurité
- [ ] Rate limiting activé sur tous endpoints
- [ ] Validation entrées stricte (taille, format)
- [ ] Headers sécurité (CORS, CSP, HSTS)
- [ ] Secrets en variables d'env (pas hardcodé)
- [ ] HTTPS obligatoire

### Performance
- [ ] Index DB optimisés
- [ ] Cache Redis pour requêtes fréquentes
- [ ] CDN pour assets statiques
- [ ] Compression gzip activée

### Monitoring
- [ ] Logging structuré (JSON)
- [ ] Alertes erreurs critiques (Sentry)
- [ ] Métriques business (Mixpanel/Amplitude)
- [ ] Uptime monitoring (UptimeRobot)

### Tests
- [ ] Tests sécurité passent (100%)
- [ ] Tests E2E passent (100%)
- [ ] Load test 100 users simultanés
- [ ] Disaster recovery testé

---

## 📚 Ressources

### Documentation interne
- [Architecture](./ARCHITECTURE.md)
- [Guide de déploiement](./DEPLOYMENT.md)
- [Procédures d'incident](./INCIDENT_RESPONSE.md)

### Outils recommandés
- **Sécurité:** OWASP ZAP, Bandit, Safety
- **Performance:** Locust, k6, Apache Bench
- **Monitoring:** Prometheus, Grafana, Sentry
- **Tests:** pytest-xdist (parallèle), hypothesis (property-based)

---

## 🆘 Support

### En cas de problème critique
1. Vérifier [STATUS.md](./STATUS.md) pour incidents connus
2. Consulter logs: `tail -f logs/error.log`
3. Rollback si nécessaire: `git revert HEAD && deploy`
4. Escalader si >15min downtime

### Contacts
- **Tech Lead:** [À définir]
- **On-call:** [Rotation PagerDuty]
- **Slack:** #incidents-prod
