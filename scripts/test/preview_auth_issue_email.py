"""
Preview the authentication issue email template
Shows both HTML and text versions
"""

import sys
import io

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Email variables
to_email = "gonzalefernando@gmail.com"
base_url = "https://emergence-app.ch"
reset_url = f"{base_url}/reset-password.html"
report_url = f"{base_url}/beta_report.html"

subject = "🔧 ÉMERGENCE Beta - Résolution des problèmes d'authentification"

print("=" * 80)
print("APERÇU DE L'EMAIL - NOTIFICATION PROBLÈME D'AUTHENTIFICATION")
print("=" * 80)
print()
print("📧 DE : ÉMERGENCE <gonzalefernando@gmail.com>")
print(f"📧 À : {to_email}")
print(f"📋 SUJET : {subject}")
print()
print("=" * 80)
print("VERSION TEXTE (pour preview - le HTML sera envoyé)")
print("=" * 80)
print()

text_body = f"""
🔧 ÉMERGENCE V8 - Résolution des problèmes d'authentification

Bonjour cher beta-testeur,

Nous vous écrivons pour vous informer d'un problème d'authentification qui a affecté
certains utilisateurs de la beta ÉMERGENCE V8.

✅ BONNE NOUVELLE : Le problème a été identifié et résolu !

🔐 ACTION REQUISE

Pour garantir la sécurité de votre compte et éviter tout problème de connexion, nous
vous recommandons fortement de réinitialiser votre mot de passe.

Accédez à la page de réinitialisation :
{reset_url}

📝 ÉTAPES RECOMMANDÉES

1. Cliquez sur le lien ci-dessus pour accéder à la page de réinitialisation
2. Saisissez votre adresse email ({to_email})
3. Vérifiez votre boîte mail pour le lien de réinitialisation
4. Créez un nouveau mot de passe sécurisé
5. Reconnectez-vous à ÉMERGENCE

⚠️ SI VOUS N'AVEZ PAS DE PROBLÈMES DE CONNEXION

Vous n'êtes pas obligé de réinitialiser votre mot de passe, mais nous vous
encourageons à le faire par précaution.

📋 FORMULAIRE DE BETA-TEST

Que vous ayez rencontré ou non des problèmes, votre feedback est essentiel pour
améliorer ÉMERGENCE. Merci de prendre quelques minutes pour remplir le formulaire :

{report_url}

🎯 Votre feedback nous aide à :
- Identifier les bugs et points de friction
- Comprendre ce qui n'est pas clair ou intuitif
- Prioriser les améliorations importantes
- Créer une meilleure expérience utilisateur

🙏 MERCI POUR VOTRE PATIENCE

Nous nous excusons pour les désagréments causés par ce problème d'authentification.
Votre participation active au programme beta est inestimable.

Toute l'équipe vous remercie !

L'équipe d'Émergence
FG, Claude et Codex

---
BESOIN D'AIDE ?
Email : gonzalefernando@gmail.com
Formulaire : {report_url}

Cet email a été envoyé automatiquement par ÉMERGENCE.
Merci de ne pas répondre à cet email.
"""

print(text_body)
print()
print("=" * 80)
print("ÉLÉMENTS CLÉS INCLUS")
print("=" * 80)
print()
print("✅ Explication du problème d'authentification")
print("✅ Annonce que c'est résolu")
print("✅ Invitation à réinitialiser le mot de passe")
print(f"✅ Lien direct : {reset_url}")
print("✅ Instructions étape par étape")
print("✅ Note pour ceux sans problème")
print("✅ Rappel du formulaire beta_report.html")
print(f"✅ Lien formulaire : {report_url}")
print("✅ Arguments sur l'importance du feedback")
print("✅ Design HTML avec logo ÉMERGENCE (sera envoyé)")
print()
print("=" * 80)
print()
