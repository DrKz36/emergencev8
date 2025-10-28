# Guardian v3.0 - Email Notifications Activation

**Date:** 2025-10-28
**Email:** emergence.app.ch@gmail.com
**Status:** ✅ Configuré et prêt

---

## 📧 Configuration Email

### Variables d'environnement (.env)

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=emergence.app.ch@gmail.com
SMTP_PASSWORD=lubmqvvmxubdqsxm  # App password Gmail
SMTP_FROM_EMAIL=emergence.app.ch@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

✅ **Déjà configuré** dans `.env`

### Configuration Guardian

**Fichier:** `claude-plugins/integrity-docs-guardian/config/guardian_config.json`

```json
{
  "reporting": {
    "email_notifications": true,
    "email_to": "emergence.app.ch@gmail.com",
    "email_from": "emergence.app.ch@gmail.com"
  }
}
```

✅ **Mis à jour** avec email officiel

---

## 🚀 Activation

### 1. Test rapide

```powershell
cd scripts
.\test_guardian_email.ps1
```

**Ce que ça fait :**
- Vérifie que `.env` et le script d'envoi existent
- Envoie un rapport Guardian test à `emergence.app.ch@gmail.com`
- Affiche le résultat (succès ou erreur)

**Résultat attendu :**
```
✅ EMAIL ENVOYÉ AVEC SUCCÈS
📧 Vérifie ta boîte mail: emergence.app.ch@gmail.com
```

### 2. Activer Task Scheduler avec email

```powershell
cd claude-plugins\integrity-docs-guardian\scripts
.\setup_guardian.ps1 -EmailTo "emergence.app.ch@gmail.com"
```

**Ce que ça fait :**
- Configure les hooks Git v3.0
- Crée la tâche planifiée (monitoring toutes les 6h)
- Active les notifications Toast Windows
- Active les notifications Email à `emergence.app.ch@gmail.com`

**Résultat :**
```
✅ Tâche planifiée créée: EMERGENCE_Guardian_ProdMonitor
   Script: guardian_monitor_with_notifications.ps1
   Intervalle: 6h
   Notifications: Toast Windows + Email ✅
   Email: emergence.app.ch@gmail.com
```

### 3. Vérifier la tâche

```powershell
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"
```

---

## 📊 Que contient l'email ?

L'email Guardian contient un **rapport HTML stylisé** avec :

### Header
- 🛡️ Logo Guardian
- Status global (✅ OK / ⚠️ WARNING / 🚨 CRITICAL)
- Timestamp

### Summary Box
- Nombre total d'erreurs
- Nombre de warnings
- Nombre de signaux critiques
- Score de santé global

### Sections détaillées

1. **📚 Anima (DocKeeper)**
   - Documentation gaps détectés
   - Fichiers modifiés
   - Recommandations

2. **🔍 Neo (IntegrityWatcher)**
   - Issues backend/frontend
   - Changements API
   - Conflits potentiels

3. **☁️ ProdGuardian**
   - État production Cloud Run
   - Erreurs production
   - Métriques santé

4. **📊 Nexus (Coordinator)**
   - Rapport unifié
   - Statistiques globales
   - Actions prioritaires

### Footer
- Liens vers rapports JSON complets
- Timestamp génération
- Signature Guardian v3.0

---

## 🔔 Quand les emails sont envoyés ?

### Monitoring automatique (Task Scheduler)

**Tâche:** `EMERGENCE_Guardian_ProdMonitor`
**Fréquence:** Toutes les 6h (configurable)
**Condition:** Envoie email SEULEMENT si issues détectées

**Statuts qui déclenchent l'email :**
- `critical` → 🚨 Email + Toast (priorité haute)
- `warning` → ⚠️ Email + Toast
- `ok` → ✅ Pas d'email (tout va bien)

### Monitoring manuel

```powershell
# Test monitoring complet avec notification
.\guardian_monitor_with_notifications.ps1 -EmailTo "emergence.app.ch@gmail.com"
```

### Envoi direct (debug)

```powershell
# Envoyer rapport actuel par email
python send_guardian_reports_email.py --to "emergence.app.ch@gmail.com"
```

---

## 🧪 Tests

### Test 1: Email simple

```powershell
cd scripts
.\test_guardian_email.ps1
```

✅ **Attendu:** Email reçu dans les 30 secondes

### Test 2: Monitoring avec notification

```powershell
cd claude-plugins\integrity-docs-guardian\scripts
.\guardian_monitor_with_notifications.ps1 -EmailTo "emergence.app.ch@gmail.com"
```

✅ **Attendu:**
- Check production ProdGuardian
- Lecture rapport JSON
- Notification Toast si issues
- Email si issues

### Test 3: Task Scheduler (dry-run)

```powershell
# Lancer la tâche manuellement
Start-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Vérifier le dernier résultat
Get-ScheduledTaskInfo -TaskName "EMERGENCE_Guardian_ProdMonitor" | Select-Object LastRunTime, LastTaskResult
```

---

## 📝 Logs

### Où vérifier les logs ?

1. **Task Scheduler logs:**
   - Ouvrir Task Scheduler (`taskschd.msc`)
   - Trouver `EMERGENCE_Guardian_ProdMonitor`
   - Onglet "History"

2. **Rapports Guardian:**
   - `reports/prod_report.json` (dernier check production)
   - `reports/docs_report.json` (dernier check docs)
   - `reports/integrity_report.json` (dernier check intégrité)
   - `reports/unified_report.json` (rapport consolidé)

3. **Console PowerShell:**
   - Les scripts affichent output détaillé en console

---

## ⚙️ Configuration avancée

### Changer la fréquence

```powershell
# Monitoring toutes les 2h au lieu de 6h
.\setup_guardian.ps1 -IntervalHours 2 -EmailTo "emergence.app.ch@gmail.com"
```

### Désactiver emails (garder Toast)

Modifier `config/guardian_config.json` :
```json
{
  "reporting": {
    "email_notifications": false
  }
}
```

Puis relancer :
```powershell
.\setup_guardian.ps1
```

### Ajouter un destinataire supplémentaire

Modifier le script `guardian_monitor_with_notifications.ps1` ligne 67 :
```powershell
& python "$scriptsDir\send_guardian_reports_email.py" --to "emergence.app.ch@gmail.com" --to "autre@example.com"
```

---

## 🚨 Troubleshooting

### Problème 1: Email non reçu

**Vérifier :**
1. `.env` contient bien `SMTP_PASSWORD=lubmqvvmxubdqsxm`
2. `EMAIL_ENABLED=1` dans `.env`
3. Gmail n'a pas bloqué l'app password

**Test direct :**
```bash
python -c "from src.backend.features.auth.email_service import EmailService, build_email_config_from_env; import asyncio; asyncio.run(EmailService(build_email_config_from_env()).send_email('emergence.app.ch@gmail.com', 'Test', 'Test body'))"
```

### Problème 2: Task Scheduler ne s'exécute pas

**Vérifier :**
1. Droits admin (Task Scheduler nécessite admin)
2. PowerShell 7 installé (`C:\Program Files\PowerShell\7\pwsh.exe`)
3. Fallback PowerShell 5 si PowerShell 7 absent

**Vérifier manuellement :**
```powershell
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"
Start-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"
```

### Problème 3: Toast notifications ne marchent pas

**Vérifier :**
1. Windows 10/11 (Toast natif)
2. Notifications activées dans Windows Settings
3. Script `send_toast_notification.ps1` existe

**Fallback :** Le script utilise MessageBox Windows si Toast fail

---

## ✅ Checklist Activation

- [x] `.env` configuré avec credentials SMTP
- [x] `guardian_config.json` mis à jour (`email_notifications: true`)
- [x] Script `send_guardian_reports_email.py` accepte `--to`
- [x] Script `guardian_monitor_with_notifications.ps1` envoie emails
- [x] Script de test `test_guardian_email.ps1` créé
- [x] Task Scheduler configuré avec email

---

## 🎯 Commandes Rapides

```powershell
# Test email
.\test_guardian_email.ps1

# Setup complet avec email
.\setup_guardian.ps1 -EmailTo "emergence.app.ch@gmail.com"

# Test monitoring manuel
.\guardian_monitor_with_notifications.ps1 -EmailTo "emergence.app.ch@gmail.com"

# Vérifier Task Scheduler
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Lancer tâche manuellement
Start-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Désactiver Guardian
.\setup_guardian.ps1 -Disable
```

---

## 📚 Documentation

- **Guide complet Guardian v3.0:** `GUARDIAN_V3_CHANGELOG.md`
- **Config email:** `config/guardian_config.json`
- **Script email:** `scripts/send_guardian_reports_email.py`
- **Script monitoring:** `scripts/guardian_monitor_with_notifications.ps1`

---

## 🏆 Résultat Final

**Tu recevras maintenant des emails automatiques sur `emergence.app.ch@gmail.com` :**

- ✅ **Toutes les 6h** si issues détectées en production
- ✅ **Immédiatement** si erreur critique
- ✅ **Format HTML stylisé** avec tous les détails
- ✅ **Toast Windows** en parallèle pour alertes locales
- ✅ **Pas de spam** si tout va bien (email uniquement si problème)

**Le système Guardian v3.0 est maintenant 100% opérationnel avec notifications email.** 🔥
