# Guardian Reports - Envoi automatique par Email

## Vue d'ensemble

Le système Guardian peut maintenant envoyer automatiquement des rapports par email aux administrateurs après chaque exécution. Cette fonctionnalité permet de recevoir un résumé complet de tous les rapports Guardian (production, intégrité, documentation, etc.) directement dans votre boîte mail.

## Configuration requise

### 1. Variables d'environnement SMTP

Ajoutez les variables suivantes dans votre fichier `.env` à la racine du projet:

```env
# Configuration Email
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-application
SMTP_FROM_EMAIL=votre-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE Guardian
SMTP_USE_TLS=1
```

### 2. Configuration Gmail (recommandé)

Si vous utilisez Gmail:

1. Allez sur https://myaccount.google.com/apppasswords
2. Créez un "mot de passe d'application" pour "Mail"
3. Utilisez ce mot de passe (16 caractères) dans `SMTP_PASSWORD`
4. **Ne pas utiliser votre mot de passe Gmail principal**

### 3. Autres fournisseurs SMTP

**Outlook/Office365:**
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=1
```

**Amazon SES:**
```env
SMTP_HOST=email-smtp.eu-west-1.amazonaws.com
SMTP_PORT=587
SMTP_USE_TLS=1
```

## Utilisation

### Envoi manuel des rapports

Pour envoyer manuellement les rapports Guardian par email:

```bash
python claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py
```

### Envoi automatique avec orchestration

Les rapports sont automatiquement envoyés à la fin de chaque orchestration Guardian:

**Auto Orchestrator** (simple):
```bash
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Master Orchestrator** (complet):
```bash
python claude-plugins/integrity-docs-guardian/scripts/master_orchestrator.py
```

Les deux orchestrateurs envoient maintenant automatiquement les rapports par email à la fin de leur exécution.

## Contenu du rapport email

Le rapport email contient:

### 1. Statut Global
- Badge de statut: ✅ OK, ⚠️ WARNING, 🚨 CRITICAL
- Date et heure de génération

### 2. Rapports individuels
Chaque rapport Guardian est inclus avec:
- **Production Guardian** (prod_report.json)
- **Intégrité Neo** (integrity_report.json)
- **Documentation Anima** (docs_report.json)
- **Rapport Unifié Nexus** (unified_report.json)
- **Rapport Global Master** (global_report.json)
- **Orchestration** (orchestration_report.json)

### 3. Détails par rapport
Pour chaque rapport:
- Statut (OK/WARNING/CRITICAL)
- Statistiques (erreurs, warnings, problèmes)
- Recommandations prioritaires (top 3)
- Timestamp du dernier scan

### 4. Format
- **HTML stylisé** avec thème ÉMERGENCE (dégradés bleu/noir)
- **Version texte** pour compatibilité
- Design responsive et lisible

## Destinataires

**Par défaut, seul l'administrateur reçoit les rapports:**
- Email admin: `gonzalefernando@gmail.com`

Pour modifier le destinataire, éditez le fichier:
```python
# claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py
ADMIN_EMAIL = "votre-email@example.com"
```

**Important:** Les rapports ne sont envoyés qu'aux administrateurs, pas aux membres utilisateurs de la plateforme.

## Personnalisation

### Modifier les rapports inclus

Éditez le fichier `send_guardian_reports_email.py`:

```python
report_files = [
    'global_report.json',
    'prod_report.json',
    'integrity_report.json',
    'docs_report.json',
    'unified_report.json',
    'orchestration_report.json'
]
```

### Modifier le template HTML

Les templates HTML sont générés dans la fonction `generate_html_report()`. Vous pouvez:
- Modifier les couleurs (variables CSS dans le style)
- Ajouter/retirer des sections
- Changer la structure du rapport

### Ajouter plusieurs destinataires

Pour envoyer à plusieurs admins, modifiez:

```python
ADMIN_EMAILS = [
    "admin1@example.com",
    "admin2@example.com"
]

# Dans send_guardian_reports():
for admin_email in ADMIN_EMAILS:
    success = await email_service.send_custom_email(
        to_email=admin_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )
```

## Troubleshooting

### Erreur "Service email non activé"

**Cause:** Variables d'environnement manquantes ou `EMAIL_ENABLED=0`

**Solution:**
1. Vérifiez que `.env` contient toutes les variables SMTP
2. Vérifiez que `EMAIL_ENABLED=1`
3. Redémarrez le terminal/script après modification du `.env`

### Erreur "SMTP Authentication Failed"

**Cause:** Mauvais identifiants SMTP

**Solution Gmail:**
1. Utilisez un "mot de passe d'application" (pas le mot de passe Gmail)
2. Activez l'authentification à 2 facteurs sur votre compte Google
3. Générez un nouveau mot de passe d'application

**Solution Outlook:**
1. Vérifiez que l'authentification SMTP est activée dans les paramètres
2. Utilisez le mot de passe complet du compte

### Erreur "Connection timeout"

**Cause:** Problème réseau ou firewall

**Solution:**
1. Vérifiez votre connexion internet
2. Vérifiez que le port 587 (TLS) ou 465 (SSL) n'est pas bloqué
3. Essayez avec un autre fournisseur SMTP

### Email non reçu

**Vérifications:**
1. Vérifiez les **spam/courrier indésirable**
2. Vérifiez l'adresse email du destinataire
3. Vérifiez les logs du script: `claude-plugins/integrity-docs-guardian/reports/orchestrator.log`

## Exemple d'exécution

```bash
$ python claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py

📧 Préparation de l'envoi des rapports Guardian...
  ✅ global_report.json chargé
  ✅ prod_report.json chargé
  ✅ integrity_report.json chargé
  ✅ docs_report.json chargé
  ✅ unified_report.json chargé
  ✅ orchestration_report.json chargé

📤 Envoi du rapport à: gonzalefernando@gmail.com
✅ Rapport Guardian envoyé avec succès à gonzalefernando@gmail.com
```

## Automatisation avancée

### Avec le scheduler Guardian

Le scheduler Guardian peut exécuter automatiquement l'orchestration (et donc l'envoi d'email) à intervalles réguliers:

```bash
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

Configuration dans `guardian_config.json`:
```json
{
  "agents": {
    "prodguardian": {
      "enabled": true,
      "triggers": ["scheduled"],
      "schedule_interval_hours": 6
    }
  }
}
```

### Avec un cron job (Linux/Mac)

```bash
# Exécuter l'orchestration + email toutes les 6 heures
0 */6 * * * cd /path/to/emergenceV8 && python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

### Avec Windows Task Scheduler

1. Ouvrez "Planificateur de tâches"
2. Créez une nouvelle tâche
3. Action: Démarrer un programme
4. Programme: `python.exe`
5. Arguments: `claude-plugins\integrity-docs-guardian\scripts\auto_orchestrator.py`
6. Répertoire: `C:\dev\emergenceV8`
7. Déclencheur: Répéter toutes les 6 heures

## Sécurité

### Bonnes pratiques

1. **Ne jamais commit** le fichier `.env` dans Git
2. **Utiliser des mots de passe d'application** (pas les mots de passe principaux)
3. **Restreindre les destinataires** aux administrateurs uniquement
4. **Chiffrer les emails** si possible (TLS/SSL)
5. **Surveiller les logs** pour détecter les envois anormaux

### Permissions

Les rapports Guardian peuvent contenir des informations sensibles:
- Logs de production
- Erreurs système
- Configuration interne
- Métriques d'utilisation

**Assurez-vous que seuls les administrateurs reçoivent ces rapports.**

## Logs

Les logs d'envoi d'email sont disponibles dans:
```
claude-plugins/integrity-docs-guardian/reports/orchestrator.log
```

Format:
```
2025-10-17 08:30:15 [INFO] Sending email report to administrators...
2025-10-17 08:30:17 [INFO] ✅ Email report sent successfully to administrators
```

## Support

Pour toute question ou problème:
- **Email:** gonzalefernando@gmail.com
- **Logs:** Consultez `orchestrator.log` pour les détails
- **Documentation:** Consultez les docs ÉMERGENCE dans `docs/`

---

**Version:** 1.0.0
**Dernière mise à jour:** 17 octobre 2025
**Auteur:** ÉMERGENCE Guardian System
