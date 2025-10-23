# PROMPT POUR SUITE AUDIT - Corrections Dashboard Admin

**Contexte :** Suite à l'audit complet du 2025-10-18, plusieurs problèmes critiques ont été identifiés dans le dashboard admin et le système de gestion des sessions. Ce prompt permet de poursuivre les corrections dans une nouvelle instance sans dépasser la fenêtre de contexte.

---

## 📋 CONTEXTE RAPIDE

### Problème Principal Identifié

**Confusion totale entre deux types de "sessions" :**

1. **Table `sessions`** = Threads de conversation/chat
   - Colonnes : `id`, `user_id`, `created_at`, `updated_at`, `session_data`, `summary`, etc.
   - Usage : Stocker les threads de conversation

2. **Table `auth_sessions`** = Sessions d'authentification JWT
   - Colonnes : `id`, `email`, `role`, `ip_address`, `issued_at`, `expires_at`, `revoked_at`, etc.
   - Usage : Stocker les sessions d'authentification JWT

**Le bordel actuel :**
- Dashboard admin endpoint `/admin/analytics/sessions` utilise la table `sessions` (threads)
- Auth admin endpoint `/api/auth/admin/sessions` utilise la table `auth_sessions` (JWT)
- **Résultat :** Deux vues "sessions" qui montrent des données complètement différentes !
- L'utilisateur admin est confus car il voit des threads déguisés en sessions d'auth

### Fichiers Concernés

**Backend :**
- `src/backend/features/dashboard/admin_service.py` (ligne 426-524) - Fonction `get_active_sessions()`
- `src/backend/features/dashboard/admin_router.py` (ligne 208-228) - Endpoint `/admin/analytics/sessions`
- `src/backend/features/auth/service.py` (ligne 1174-1183) - Fonction `list_sessions()`
- `src/backend/features/auth/router.py` (ligne 412-420) - Endpoint `/api/auth/admin/sessions`

**Frontend :**
- `src/frontend/features/admin/admin-dashboard.js` - Dashboard admin (onglet Analytics)
- `src/frontend/features/admin/auth-admin-module.js` - Module auth admin

**Documentation :**
- `docs/architecture/10-Components.md`
- `docs/architecture/30-Contracts.md`

---

## 🎯 TA MISSION

**Implémenter la Phase 1 du plan d'action :** Renommer endpoints et clarifier l'UI pour éliminer la confusion sessions/threads.

**Objectifs :**
1. ✅ Renommer `get_active_sessions()` → `get_active_threads()` (backend)
2. ✅ Renommer endpoint `/admin/analytics/sessions` → `/admin/analytics/threads` (backend)
3. ✅ Mettre à jour le frontend pour utiliser le nouvel endpoint
4. ✅ Clarifier l'UI : "Threads actifs" au lieu de "Sessions actives"
5. ✅ Tester en local
6. ✅ Mettre à jour AGENT_SYNC.md et docs/passation.md

---

## 📝 ÉTAPES DÉTAILLÉES

### Étape 1 : Backend - Renommer la fonction (15 min)

**Fichier :** `src/backend/features/dashboard/admin_service.py`

**Action :**
```python
# Ligne 426 - Renommer la fonction
async def get_active_threads(self) -> List[Dict[str, Any]]:  # ← Ancien nom: get_active_sessions
    """
    Get all active threads (conversations) across all users.
    Returns thread details including user, device, IP, and last activity.

    Note: This returns THREADS (conversations), not authentication sessions.
    For authentication sessions, use AuthService.list_sessions() instead.
    """
    try:
        # Get all threads (from 'sessions' table - legacy naming)
        query = """
            SELECT
                s.id,
                s.user_id,
                s.created_at,
                s.updated_at,
                s.metadata
            FROM sessions s
            WHERE s.user_id IS NOT NULL
            ORDER BY s.updated_at DESC
            LIMIT 100
        """
        # ... reste du code identique
```

**Renommer aussi l'appel dans admin_router.py :**

```python
# src/backend/features/dashboard/admin_router.py ligne 208-228

@router.get(
    "/admin/analytics/threads",  # ← Ancien: /admin/analytics/sessions
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get all active threads (admin only)",
    description="Returns all active conversation threads with details for monitoring and management.",
)
async def get_active_threads(  # ← Ancien nom: get_active_sessions
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
) -> Dict[str, Any]:
    """
    Get all active threads - admin only.
    Returns thread details including user, device info, IP, and last activity.

    Note: This endpoint returns THREADS (conversations), not authentication sessions.
    For authentication sessions, use /api/auth/admin/sessions instead.
    """
    logger.info("[Admin] Fetching active threads")
    threads = await admin_service.get_active_threads()  # ← Renommer l'appel
    logger.info(f"[Admin] Retrieved {len(threads)} active threads")
    return {
        "threads": threads,  # ← Renommer la clé (ancien: "sessions")
        "total": len(threads),
    }
```

**Vérifier les imports :** Aucun changement nécessaire.

---

### Étape 2 : Frontend - Mettre à jour l'appel API (10 min)

**Fichier :** `src/frontend/features/admin/admin-dashboard.js`

**Chercher la fonction `renderAnalyticsView()` et mettre à jour :**

```javascript
// Ligne ~680-720 (approximatif)
async renderAnalyticsView() {
    const sessionsContainer = this.container.querySelector('#analytics-sessions');
    const metricsContainer = this.container.querySelector('#analytics-metrics');

    // Charger les threads actifs (ancien: sessions)
    try {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/analytics/threads', {  // ← Ancien: /admin/analytics/sessions
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Admin API error: ${response.status}`);
        }

        const data = await response.json();
        const threads = data.threads || [];  // ← Ancien: data.sessions

        // Render threads list
        this.renderThreadsList(threads, sessionsContainer);  // ← Renommer la fonction aussi

    } catch (error) {
        console.error('[AdminDashboard] Error loading active threads:', error);
        this.showError('Impossible de charger les threads actifs');
    }

    // Charger les métriques système
    // ... reste du code
}
```

**Renommer aussi la fonction de rendu :**

```javascript
// Ancienne fonction: renderSessionsList
// Nouvelle fonction: renderThreadsList

renderThreadsList(threads, container) {  // ← Ancien: renderSessionsList(sessions, container)
    if (!threads || threads.length === 0) {
        container.innerHTML = `
            <div class="admin-empty">
                <p>Aucun thread actif</p>
            </div>
        `;
        return;
    }

    // Titre mis à jour
    const threadsHtml = `
        <h4>${getIcon('messageCircle', 'section-icon')} Threads Actifs (${threads.length})</h4>
        <div class="threads-table">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Thread ID</th>
                        <th>Utilisateur</th>
                        <th>Rôle</th>
                        <th>Créé</th>
                        <th>Dernière activité</th>
                        <th>Durée</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
                    ${threads.map(thread => `  <!-- Ancien: session -->
                        <tr>
                            <td><code>${thread.session_id || thread.id}</code></td>
                            <td>${thread.email}</td>
                            <td><span class="role-badge ${thread.role}">${thread.role}</span></td>
                            <td>${new Date(thread.created_at).toLocaleString('fr-FR')}</td>
                            <td>${new Date(thread.last_activity).toLocaleString('fr-FR')}</td>
                            <td>${thread.duration_minutes.toFixed(0)} min</td>
                            <td>
                                ${thread.is_active
                                    ? '<span class="status-badge active">Actif</span>'
                                    : '<span class="status-badge inactive">Inactif</span>'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = threadsHtml;
}
```

---

### Étape 3 : Frontend - Clarifier les labels UI (5 min)

**Fichier :** `src/frontend/features/admin/admin-dashboard.js`

**Mettre à jour les labels dans la fonction `render()` :**

```javascript
// Ligne ~100-105
<button class="admin-tab ${this.activeView === 'analytics' ? 'active' : ''}"
        data-view="analytics">
    <span class="tab-icon">${AdminIcons.activity}</span>
    <span class="tab-label">Analytics & Threads</span>  <!-- Ancien: Analytics -->
</button>
```

**Mettre à jour aussi la section Analytics :**

```javascript
// Dans renderAnalyticsView(), mettre à jour le titre de la section
sessionsContainer.innerHTML = `
    <h3>${getIcon('messageCircle', 'section-icon')} Threads de Conversation Actifs</h3>
    <p class="section-subtitle">
        Vue d'ensemble des threads de chat en cours.
        Pour les sessions d'authentification JWT, voir le module Auth Admin.
    </p>
    <!-- ... reste du contenu -->
`;
```

---

### Étape 4 : Ajouter un tooltip explicatif (5 min)

**Fichier :** `src/frontend/features/admin/admin-dashboard.js`

**Ajouter un tooltip pour clarifier :**

```javascript
// Dans renderAnalyticsView(), ajouter un bandeau informatif
const infoBanner = `
    <div class="info-banner">
        <div class="info-icon">${AdminIcons.info}</div>
        <div class="info-content">
            <strong>Note :</strong> Cette vue affiche les <strong>threads de conversation</strong> (table <code>sessions</code>).
            Pour consulter les <strong>sessions d'authentification JWT</strong> (table <code>auth_sessions</code>),
            utilisez le module <a href="#" data-module="auth-admin">Auth Admin</a>.
        </div>
    </div>
`;

sessionsContainer.insertAdjacentHTML('afterbegin', infoBanner);
```

**Ajouter le style CSS correspondant dans `admin-dashboard.css` :**

```css
.info-banner {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(59, 130, 246, 0.1);
    border-left: 3px solid #3b82f6;
    border-radius: 6px;
    margin-bottom: 20px;
    font-size: 0.9em;
}

.info-banner .info-icon {
    color: #3b82f6;
    flex-shrink: 0;
}

.info-banner .info-content {
    color: #cbd5e1;
}

.info-banner code {
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}

.info-banner a {
    color: #3b82f6;
    text-decoration: underline;
}

.info-banner a:hover {
    color: #60a5fa;
}
```

---

### Étape 5 : Tests (15 min)

**Actions :**

1. **Démarrer le backend local :**
   ```bash
   pwsh -File scripts/run-backend.ps1
   ```

2. **Ouvrir l'app dans le navigateur :**
   - Se connecter en tant qu'admin
   - Aller dans Admin → Analytics & Threads
   - Vérifier que la section affiche bien "Threads de Conversation Actifs"
   - Vérifier que le bandeau info est affiché
   - Vérifier que les données s'affichent correctement

3. **Tester l'endpoint directement :**
   ```bash
   # Récupérer un token admin
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"xxx"}'

   # Tester le nouvel endpoint
   curl -X GET http://localhost:8000/api/admin/analytics/threads \
     -H "Authorization: Bearer <token>"
   ```

4. **Vérifier les logs backend :**
   - Chercher `[Admin] Fetching active threads`
   - Vérifier qu'il n'y a pas d'erreur 404

5. **Tester le module Auth Admin :**
   - Aller dans Admin → Auth Admin
   - Vérifier que la section "Sessions actives" fonctionne toujours
   - Vérifier que les données affichées sont bien des sessions JWT

**Cas de test :**
- [ ] Dashboard admin charge sans erreur
- [ ] Onglet "Analytics & Threads" affiche le bon titre
- [ ] Bandeau info est visible et clair
- [ ] Données threads s'affichent correctement
- [ ] Pas d'erreur 404 dans la console
- [ ] Module Auth Admin fonctionne toujours

---

### Étape 6 : Documentation (10 min)

**Mettre à jour `docs/passation.md` :**

```markdown
## [2025-10-18 Session] — Agent: Claude Code (Sonnet 4.5) - Fix Confusion Sessions/Threads

### Fichiers modifiés
- `src/backend/features/dashboard/admin_service.py` - Renommé `get_active_sessions()` → `get_active_threads()`
- `src/backend/features/dashboard/admin_router.py` - Endpoint `/admin/analytics/threads` (ancien: sessions)
- `src/frontend/features/admin/admin-dashboard.js` - Mise à jour appels API + labels UI
- `src/frontend/features/admin/admin-dashboard.css` - Ajout styles bandeau info
- `docs/passation.md` - Cette entrée
- `AGENT_SYNC.md` - Mise à jour session

### Contexte
Suite à l'audit du 2025-10-18 (voir `AUDIT_COMPLET_2025-10-18.md`), correction du problème critique #1 :
Confusion entre deux types de "sessions" (threads de chat vs sessions d'authentification JWT).

**Problème identifié :**
- Table `sessions` = Threads de conversation
- Table `auth_sessions` = Sessions d'authentification JWT
- Dashboard admin utilisait la mauvaise table et les mauvais noms

**Solution implémentée :**
- Renommé fonction backend `get_active_sessions()` → `get_active_threads()`
- Renommé endpoint `/admin/analytics/sessions` → `/admin/analytics/threads`
- Clarifié labels UI : "Threads de Conversation Actifs"
- Ajouté bandeau informatif pour éviter la confusion
- Documenté clairement la différence dans les docstrings

### Tests
- ✅ Backend démarre sans erreur
- ✅ Endpoint `/admin/analytics/threads` répond correctement
- ✅ Frontend affiche les threads avec les bons labels
- ✅ Bandeau info visible et clair
- ✅ Module Auth Admin (sessions JWT) fonctionne toujours
- ✅ Aucune régression détectée

### Prochaines actions recommandées (Phase 2)
1. Améliorer `renderCostsChart()` (gestion null/undefined)
2. Standardiser format `user_id` (hash vs plain text)
3. Mettre à jour `docs/architecture/10-Components.md`
4. Créer ADR pour documenter la décision

### Blocages
Aucun.
```

**Mettre à jour `AGENT_SYNC.md` :**

Ajouter une section en haut du fichier :

```markdown
## 🔄 Dernière session (2025-10-18)

**Agent :** Claude Code (Sonnet 4.5)
**Durée :** 2h
**Commit :** `<hash du commit>`

**Résumé :**
- ✅ Fix confusion sessions/threads (problème critique #1)
- ✅ Renommage fonction backend + endpoint
- ✅ Clarification UI dashboard admin
- ✅ Tests complets
- ✅ Documentation mise à jour

**Fichiers modifiés :**
- Backend : admin_service.py, admin_router.py
- Frontend : admin-dashboard.js, admin-dashboard.css
- Docs : passation.md, AGENT_SYNC.md

**Prochaine étape :** Phase 2 (améliorer renderCostsChart)
```

---

## 🚀 COMMIT ET PUSH

**Une fois tous les tests passés :**

```bash
# Vérifier les changements
git status
git diff

# Ajouter les fichiers
git add src/backend/features/dashboard/admin_service.py
git add src/backend/features/dashboard/admin_router.py
git add src/frontend/features/admin/admin-dashboard.js
git add src/frontend/features/admin/admin-dashboard.css
git add docs/passation.md
git add AGENT_SYNC.md

# Créer le commit
git commit -m "fix(admin): rename sessions → threads to clarify dashboard analytics

PROBLÈME CRITIQUE RÉSOLU: Confusion entre threads et sessions d'auth

Avant:
- Dashboard admin endpoint: /admin/analytics/sessions
- Utilisait table 'sessions' (threads de chat)
- Labels UI: "Sessions actives"
- Confusion totale avec sessions JWT

Après:
- Dashboard admin endpoint: /admin/analytics/threads
- Utilise toujours table 'sessions' mais nom clarifié
- Labels UI: "Threads de Conversation Actifs"
- Bandeau info explicatif ajouté

Backend:
- Renommé get_active_sessions() → get_active_threads()
- Endpoint /admin/analytics/sessions → /admin/analytics/threads
- Docstrings mises à jour avec notes explicatives

Frontend:
- Appel API mis à jour vers nouveau endpoint
- Labels UI clarifiés (Threads au lieu de Sessions)
- Bandeau info ajouté pour éviter confusion
- Styles CSS pour bandeau info

Documentation:
- passation.md: Nouvelle entrée avec détails
- AGENT_SYNC.md: Session mise à jour

Tests:
- ✅ Backend démarre sans erreur
- ✅ Endpoint répond correctement
- ✅ Frontend affiche correctement
- ✅ Module Auth Admin (JWT sessions) toujours fonctionnel
- ✅ Aucune régression

Réf: AUDIT_COMPLET_2025-10-18.md (problème critique #1)
Phase: 1/4 (Immédiat)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push
```

**Les hooks Guardian vont s'exécuter automatiquement :**
- Pre-commit : Vérification intégrité
- Post-commit : Génération rapports
- Pre-push : Vérification production

---

## 📚 RESSOURCES

**Fichiers à consulter :**
- `AUDIT_COMPLET_2025-10-18.md` - Rapport complet de l'audit
- `docs/architecture/10-Components.md` - Architecture composants
- `docs/passation.md` - Journal inter-agents

**Endpoints concernés :**
- NOUVEAU : `GET /api/admin/analytics/threads` (dashboard admin)
- EXISTANT : `GET /api/auth/admin/sessions` (auth admin)

**Tables DB :**
- `sessions` - Threads de conversation/chat
- `auth_sessions` - Sessions d'authentification JWT

---

## ⚠️ IMPORTANT

**NE PAS confondre :**
- Dashboard admin (threads) ≠ Auth admin (sessions JWT)
- Table `sessions` ≠ Table `auth_sessions`
- Endpoint `/admin/analytics/threads` ≠ `/api/auth/admin/sessions`

**Garder cohérent :**
- Dashboard admin : toujours dire "threads"
- Auth admin : toujours dire "sessions" ou "sessions JWT"

---

## 🎯 CHECKLIST FINALE

Avant de marquer la tâche comme terminée :

- [ ] Backend renommé (fonction + endpoint)
- [ ] Frontend mis à jour (appel API + labels)
- [ ] Bandeau info ajouté et stylé
- [ ] Tests passent tous ✅
- [ ] Aucune erreur 404 dans les logs
- [ ] Module Auth Admin fonctionne toujours
- [ ] Documentation mise à jour (passation.md + AGENT_SYNC.md)
- [ ] Commit créé avec message détaillé
- [ ] Push effectué (hooks Guardian OK)

**Temps estimé total : 1h**

---

**🤖 Prompt généré par :** Claude Code (Sonnet 4.5)
**Date :** 2025-10-18
**Version :** 1.0
**Suivi :** AUDIT_COMPLET_2025-10-18.md - Phase 1 (Immédiat)

---

## 💡 POUR LA PROCHAINE INSTANCE

**Après avoir complété cette Phase 1, la Phase 2 consiste à :**

1. Améliorer `renderCostsChart()` (gestion null/undefined)
2. Standardiser format `user_id` (hash vs plain text)
3. Mettre à jour docs architecture

**Tout est documenté dans `AUDIT_COMPLET_2025-10-18.md` - Section "Plan d'Action Phase 2".**

**Bonne chance ! 🚀**
