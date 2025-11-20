# Documents - Maintenance 2025-11-20

- **Fallback parsing** : les imports PyMuPDF/PyPDF2/python-docx sont maintenant chargés paresseusement avec gestion explicite des dépendances absentes (le service ne tombe plus si une lib n’est pas installée).
- **Comportement** : aucun changement fonctionnel attendu sur l’UI Documents, le fallback PyPDF2 reste la voie de secours pour les environnements sans PyMuPDF.

Fichiers concernés :
- `src/backend/features/documents/parser.py`
