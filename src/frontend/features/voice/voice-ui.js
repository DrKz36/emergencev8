// src/frontend/features/voice/voice-ui.js

export class VoiceUI {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.recordButton = null;
    }

    init() {
        this.eventBus.on('ui:chat:ready', (payload) => this._attachButton(payload));
        this.setupEventListeners();
    }

    _attachButton(payload) {
        const chatInputContainer = payload.attachTo;
        if (!chatInputContainer) {
            console.error("VoiceUI: L'événement ui:chat:ready n'a pas fourni de conteneur valide.");
            return;
        }

        console.log("✅ VoiceUI: Conteneur du chat trouvé via event. Ajout du bouton vocal.");

        this.recordButton = document.createElement('button');
        this.recordButton.id = 'record-button';
        this.recordButton.className = 'record-button';
        this.recordButton.innerHTML = '🎙️'; // État initial
        this.recordButton.title = 'Démarrer/Arrêter l\'enregistrement vocal';

        chatInputContainer.prepend(this.recordButton);

        this.recordButton.addEventListener('click', () => {
            // L'UI ne fait qu'émettre un événement, elle n'a pas de logique d'état.
            this.eventBus.emit('voice:toggle-recording');
        });
    }

    // --- REFACTOR V10.4 : Mise à jour des écouteurs pour la machine à états ---
    setupEventListeners() {
        // 1. L'enregistrement commence
        this.eventBus.on('voice:recording-started', () => {
            if (this.recordButton) {
                this.recordButton.classList.add('is-recording');
                this.recordButton.classList.remove('is-processing');
                this.recordButton.innerHTML = '⏹️';
                this.recordButton.disabled = false; // Le bouton est activé pour pouvoir stopper
            }
        });

        // 2. L'enregistrement est arrêté, on attend le serveur
        this.eventBus.on('voice:processing-started', () => {
            if (this.recordButton) {
                this.recordButton.classList.remove('is-recording');
                this.recordButton.classList.add('is-processing');
                this.recordButton.innerHTML = '⏳';
                this.recordButton.disabled = true; // On désactive le bouton pour éviter les clics multiples
            }
        });
        
        // 3. L'interaction est complètement terminée (réponse jouée ou erreur)
        this.eventBus.on('voice:interaction-finished', () => {
            if (this.recordButton) {
                this.recordButton.classList.remove('is-recording', 'is-processing');
                this.recordButton.innerHTML = '🎙️'; // On revient à l'état initial
                this.recordButton.disabled = false; // On réactive le bouton pour la prochaine interaction
            }
        });

        // NOTE: 'voice:recording-stopped' est maintenant obsolète et remplacé par les deux ci-dessus.
    }
}