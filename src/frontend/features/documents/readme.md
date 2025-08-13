# Module: Documents

**Version:** 1.0 (V8.0 Architecture)
**Responsable:** `documents.js`, `documents-ui.js`

## Rôle

Ce module fournit l'interface et la logique permettant à l'utilisateur d'uploader des fichiers (`.pdf`, `.txt`, `.docx`) sur le serveur. Le backend se charge ensuite de parser, stocker et vectoriser ces documents pour les rendre accessibles aux agents IA dans le cadre du RAG (Retrieval-Augmented Generation).

## Architecture

-   **`documents.js`**: Contient la classe `DocumentsModule` qui gère la logique d'appel à l'API pour l'upload. Il communique avec le reste de l'application via l'eventBus.
-   **`documents-ui.js`**: Contient la classe `DocumentsUI` responsable de la manipulation du DOM. Elle affiche le bouton d'upload, la liste des fichiers et notifie `DocumentsModule` des actions de l'utilisateur.
-   **`documents.css`**: Contient les styles CSS isolés pour ce module.

## Événements Émis

-   `documents:upload_requested` : Émis par l'UI quand l'utilisateur veut uploader un fichier.
-   `documents:upload_started`: Émis par le module logique au début du processus.
-   `documents:upload_succeeded`: Émis par le module logique en cas de succès.
-   `documents:upload_failed`: Émis par le module logique en cas d'échec.