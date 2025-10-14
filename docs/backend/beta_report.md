# Beta Report System - Documentation technique

**Module:** `backend.features.beta_report`
**Date:** 2025-10-13
**Version:** 1.0

---

## Vue d'ensemble

Le système de rapport beta permet aux testeurs de soumettre leurs retours sur la plateforme via un formulaire interactif. La solution utilise une approche **mailto** pour maximiser la fiabilité et la simplicité.

---

## Architecture

### Composants

```
beta_report.html (Frontend)
    ↓
    mailto: link
    ↓
Client email utilisateur
    ↓
gonzalefernando@gmail.com
```

### Approche initiale (abandonnée)

Une approche backend REST a été tentée mais abandonnée en raison de problèmes de routage complexes dans l'architecture FastAPI existante :

```
beta_report.html (Frontend)
    ↓
POST /api/beta-report (Backend)
    ↓
Email service (SendGrid/AWS SES)
    ↓
gonzalefernando@gmail.com
```

**Problèmes rencontrés:**
- Conflits de routage avec routers montés sur `/api`
- Erreurs 405 (Method Not Allowed) persistantes
- Cache Python (.pyc) compliquant le debugging
- Ordre de montage des routers impactant le fonctionnement

**Décision:** Abandon de l'approche backend au profit de mailto pour Beta 1.0.

---

## Frontend - beta_report.html

### Localisation
- **Fichier:** `beta_report.html` (racine du projet)
- **URL production:** https://emergence-app.ch/beta_report.html
- **Servi par:** Serveur web statique (Nginx/Apache) ou FastAPI static files

### Structure

Le formulaire est un fichier HTML standalone contenant :

1. **CSS inline** : Design moderne avec gradients et animations
2. **JavaScript vanilla** : Pas de dépendances externes
3. **55 checkboxes** : Organisées en 8 phases de test
4. **Champs texte** : Commentaires par phase + feedback général
5. **Barre de progression** : Mise à jour en temps réel

### Fonctionnement JavaScript

```javascript
// 1. Auto-détection navigateur/OS
const userAgent = navigator.userAgent;
// Parse et pré-remplit le champ "browserInfo"

// 2. Tracking progression
const checkboxes = document.querySelectorAll('input[type="checkbox"]');
checkboxes.forEach(checkbox => {
  checkbox.addEventListener('change', updateProgress);
});

// 3. Génération email
form.addEventListener('submit', function(e) {
  e.preventDefault();

  // Collecte données
  const data = collectFormData();

  // Construction corps email
  let emailBody = formatEmailBody(data);

  // Ouverture client email
  const subject = encodeURIComponent(`EMERGENCE Beta - ${email} (${%})`);
  const body = encodeURIComponent(emailBody);
  window.location.href = `mailto:gonzalefernando@gmail.com?subject=${subject}&body=${body}`;

  // Affichage message succès
  showSuccessMessage();
});
```

### Format email généré

```
EMERGENCE Beta 1.0 - Rapport de Test
========================================

Email: user@example.com
Navigateur/OS: Chrome 120 / Windows 11
Progression: 35/55 (64%)

Phase 1 (Auth & Onboarding): 5/5
  Commentaires: [commentaires utilisateur]

Phase 2 (Chat agents): 4/5
  Commentaires: [commentaires utilisateur]

...

BUGS:
[Description des bugs critiques]

SUGGESTIONS:
[Suggestions d'amélioration]

COMMENTAIRES:
[Commentaires libres]
```

### Limites mailto

⚠️ **Limitations connues:**

1. **Taille du corps** : Les clients email ont des limites variables (généralement ~2000 caractères dans l'URL)
2. **Formatage** : Le formatage peut varier selon le client email
3. **Caractères spéciaux** : Nécessitent `encodeURIComponent()`
4. **Pas de validation serveur** : L'email peut ne pas être envoyé
5. **Pas de confirmation** : Pas de tracking côté serveur

✅ **Avantages:**

1. **Toujours fonctionnel** : Pas de dépendance backend
2. **Debugging facile** : L'utilisateur voit le contenu
3. **Attachements possibles** : L'utilisateur peut ajouter des screenshots
4. **Universel** : Fonctionne sur tous les navigateurs/OS
5. **Simple** : Pas de configuration serveur nécessaire

---

## Backend - beta_report router (futur)

### Localisation
- **Module:** `src/backend/features/beta_report/`
- **Router:** `src/backend/features/beta_report/router.py`
- **Init:** `src/backend/features/beta_report/__init__.py`

### Statut
⚠️ **Non fonctionnel en Beta 1.0**

Le router existe dans le code mais n'est pas utilisé. Il a été préparé pour une future implémentation avec service email backend.

### Code router

```python
# src/backend/features/beta_report/router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

router = APIRouter(tags=["Beta"])

class BetaReportRequest(BaseModel):
    email: str
    browserInfo: str | None = None
    checklist: Dict[str, bool]
    completion: str
    completionPercentage: int
    comments1: str | None = None
    # ... autres champs
    bugs: str | None = None
    suggestions: str | None = None
    generalComments: str | None = None

@app.post("/beta-report")
async def submit_beta_report(report: BetaReportRequest):
    """
    Endpoint pour soumettre un rapport beta.

    TODO Beta 1.1:
    - Intégrer service email (SendGrid/AWS SES)
    - Sauvegarder en base de données
    - Envoyer notification admin
    """
    # Formater email
    email_body = format_beta_report_email(report)

    # Sauvegarder localement (temporaire)
    save_report_to_file(report)

    # TODO: Envoyer via service email
    # await email_service.send(...)

    return {
        "status": "success",
        "message": "Rapport reçu",
        "timestamp": datetime.now().isoformat()
    }
```

### Montage dans main.py

```python
# src/backend/main.py
from backend.features.beta_report.router import router as BETA_REPORT_ROUTER

def create_app():
    app = FastAPI()

    # Monter le router (NON FONCTIONNEL Beta 1.0)
    # _mount_router(BETA_REPORT_ROUTER, "/api")

    return app
```

### Problèmes rencontrés

1. **Routage 405:** L'endpoint retourne systématiquement 405 (Method Not Allowed)
2. **OpenAPI vide:** L'endpoint n'apparaît pas dans `/openapi.json`
3. **Cache Python:** Les modifications ne sont pas prises en compte malgré les redémarrages
4. **Conflits routers:** Plusieurs routers montés sur `/api` causent des conflits

### TODO Beta 1.1

Pour réactiver le backend router :

- [ ] Débugger les conflits de routage FastAPI
- [ ] Implémenter service email (SendGrid ou AWS SES)
- [ ] Ajouter sauvegarde base de données
- [ ] Créer table `beta_reports` dans SQLite
- [ ] Ajouter endpoint admin pour consulter les rapports
- [ ] Implémenter rate limiting (max 5 rapports/jour/user)
- [ ] Ajouter validation Pydantic stricte
- [ ] Tests unitaires et E2E

---

## Sauvegarde locale (implémentation actuelle)

### Format fichiers

Les rapports sont actuellement sauvegardés localement dans `data/beta_reports/` :

```
data/beta_reports/
├── report_20251013_143022_user_at_example_com.txt
├── report_20251013_143022_user_at_example_com.json
├── report_20251013_150045_test_at_test_com.txt
└── report_20251013_150045_test_at_test_com.json
```

**Format TXT:**
```
EMERGENCE Beta 1.0 - Rapport de Test
=====================================
[contenu formaté lisible]
```

**Format JSON:**
```json
{
  "email": "user@example.com",
  "browserInfo": "Chrome 120 / Windows 11",
  "checklist": {
    "test1_1": true,
    "test1_2": true,
    ...
  },
  "completion": "35/55",
  "completionPercentage": 64,
  "comments1": "...",
  ...
}
```

### Accès aux rapports

⚠️ En Beta 1.0, les rapports locaux ne sont accessibles que via :
1. SSH sur le serveur de production
2. Accès filesystem local en développement

TODO Beta 1.1: Créer interface admin pour consulter les rapports.

---

## Intégration future avec service email

### Option 1: SendGrid

```python
import sendgrid
from sendgrid.helpers.mail import Mail

async def send_beta_report_email(report: BetaReportRequest):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

    message = Mail(
        from_email='noreply@emergence-app.ch',
        to_emails='gonzalefernando@gmail.com',
        subject=f'EMERGENCE Beta - {report.email} ({report.completionPercentage}%)',
        html_content=format_beta_report_html(report)
    )

    response = await sg.send(message)
    return response.status_code == 202
```

### Option 2: AWS SES

```python
import boto3

async def send_beta_report_email(report: BetaReportRequest):
    ses = boto3.client('ses', region_name='eu-west-1')

    response = ses.send_email(
        Source='noreply@emergence-app.ch',
        Destination={'ToAddresses': ['gonzalefernando@gmail.com']},
        Message={
            'Subject': {'Data': f'EMERGENCE Beta - {report.email}'},
            'Body': {'Html': {'Data': format_beta_report_html(report)}}
        }
    )

    return response['ResponseMetadata']['HTTPStatusCode'] == 200
```

### Configuration requise

```python
# .env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
# ou
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=eu-west-1
```

---

## Tests

### Tests manuels

1. Ouvrir https://emergence-app.ch/beta_report.html
2. Remplir email (obligatoire)
3. Cocher quelques tests
4. Ajouter commentaires
5. Soumettre
6. Vérifier que le client email s'ouvre
7. Vérifier le contenu de l'email
8. Envoyer l'email
9. Vérifier réception sur gonzalefernando@gmail.com

### Tests automatisés (TODO)

```python
# tests/backend/features/test_beta_report.py
import pytest
from fastapi.testclient import TestClient

def test_submit_beta_report_valid(client: TestClient):
    """Test soumission rapport valide"""
    report = {
        "email": "test@test.com",
        "checklist": {"test1_1": True},
        "completion": "1/55",
        "completionPercentage": 2
    }

    response = client.post("/api/beta-report", json=report)

    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_submit_beta_report_invalid_email(client: TestClient):
    """Test email invalide"""
    report = {
        "email": "invalid-email",
        "checklist": {},
        "completion": "0/55",
        "completionPercentage": 0
    }

    response = client.post("/api/beta-report", json=report)

    assert response.status_code == 422  # Validation error
```

---

## Métriques

### Métriques à collecter (Beta 1.1)

- Nombre de rapports soumis
- Taux de complétion moyen
- Bugs les plus reportés
- Suggestions les plus fréquentes
- Temps moyen de remplissage du formulaire
- Taux d'abandon par phase
- Navigateurs/OS utilisés

### Dashboard admin (Beta 1.1)

Créer interface admin pour :
- Lister tous les rapports
- Filtrer par date/email/complétion
- Voir statistiques agrégées
- Exporter en CSV/JSON
- Marquer rapports comme "traités"

---

## Sécurité

### Considérations

✅ **Actuellement (mailto):**
- Pas d'injection possible (encode URI)
- Pas de données sensibles transmises
- Client email gère la sécurité

⚠️ **Future implémentation backend:**
- [ ] Rate limiting (max 5 rapports/jour/user)
- [ ] Validation stricte Pydantic
- [ ] Sanitization des champs texte
- [ ] Protection CSRF
- [ ] Authentication requise (JWT)
- [ ] Logging des soumissions
- [ ] Détection spam/abuse

---

## Maintenance

### Checklist de maintenance

- [ ] Vérifier que beta_report.html est accessible
- [ ] Monitorer emails reçus vs rapports attendus
- [ ] Analyser rapports régulièrement
- [ ] Mettre à jour la checklist si nouvelles features
- [ ] Archiver rapports après traitement
- [ ] Répondre aux testeurs avec feedback

### Logs

En attendant le backend, les logs sont :
- Emails reçus sur gonzalefernando@gmail.com
- Fichiers dans `data/beta_reports/` (si backend activé)

---

**Dernière mise à jour:** 2025-10-14
**Maintenu par:** Équipe EMERGENCE
**Statut:** Beta 1.0 - Mailto actif, Backend en préparation

---

## Changelog

### 2025-10-14
- ✅ Ajout module d'invitations beta via interface admin
- ✅ Endpoint `/api/admin/allowlist/emails` pour récupérer la liste des emails
- ✅ Endpoint `/api/admin/beta-invitations/send` pour envoyer invitations
- ✅ Interface web `beta_invitations.html` pour gestion manuelle
- ✅ Service email pleinement fonctionnel avec templates HTML
- ✅ Documentation beta complète (START_HERE.md, guides, etc.)

### 2025-10-13
- Création du module beta_report
- Implémentation formulaire HTML avec mailto
- Documentation initiale
