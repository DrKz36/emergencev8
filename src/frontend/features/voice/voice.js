// src/frontend/features/voice/voice.js

export class VoiceModule {
    constructor(eventBus, stateManager) {
        this.eventBus = eventBus;
        this.stateManager = stateManager;

        this.state = 'IDLE'; // 'IDLE', 'RECORDING', 'PROCESSING', 'PLAYING'
        this.mediaRecorder = null;
        this.websocket = null;
        this.audioChunks = [];
        this.audioPlayer = null;
    }

    init() {
        this.registerEvents();
    }

    registerEvents() {
        this.eventBus.on('voice:toggle-recording', () => this.handleToggle());
    }

    handleToggle() {
        switch (this.state) {
            case 'IDLE':
                this.startRecording();
                break;
            case 'RECORDING':
                this.stopRecordingAndProcess();
                break;
            case 'PROCESSING':
            case 'PLAYING':
                console.log(`Action ignorée, état actuel: ${this.state}`);
                break;
        }
    }

    async startRecording() {
        const agentName = this.stateManager.get('chat.currentAgentId') || 'anima';
        const sessionId = this.stateManager.get('websocket.sessionId');

        if (!sessionId) {
            console.error("Impossible de démarrer le vocal : ID de session manquant.");
            this.eventBus.emit('notification:show', { message: "La connexion principale n'est pas établie.", type: 'error' });
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.state = 'RECORDING';
            this.eventBus.emit('voice:recording-started');
            console.log(`[STATE: ${this.state}] Enregistrement démarré pour: ${agentName}`);

            const wsUrl = `ws://localhost:8000/ws/voice/${agentName}?session_id=${sessionId}`;
            this.websocket = new WebSocket(wsUrl);
            this.audioChunks = [];

            this.websocket.onopen = () => {
                console.log("WebSocket vocal connecté.");
                this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0 && this.websocket?.readyState === WebSocket.OPEN) {
                        this.websocket.send(event.data);
                    }
                };
                this.mediaRecorder.start(1000);
            };

            this.websocket.onmessage = (event) => this.handleServerMessage(event);
            this.websocket.onerror = (error) => this.handleWebSocketError(error);
            this.websocket.onclose = () => this.handleWebSocketClose();

        } catch (error) {
            console.error("Erreur au démarrage de l'enregistrement:", error);
            this.eventBus.emit('notification:show', { message: "Impossible d'accéder au microphone.", type: 'error' });
            this.state = 'IDLE';
        }
    }

    stopRecordingAndProcess() {
        if (!this.mediaRecorder) return;
        
        this.state = 'PROCESSING';
        this.eventBus.emit('voice:processing-started');
        console.log(`[STATE: ${this.state}] Enregistrement arrêté, en attente du serveur.`);

        if (this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        this.mediaRecorder = null;
        
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({ type: 'audio_stream_end' }));
            console.log("Signal de fin de flux audio envoyé au serveur.");
        }
    }

    handleServerMessage(event) {
        if (this.state === 'PROCESSING' && event.data instanceof Blob) {
            this.state = 'PLAYING';
            console.log(`[STATE: ${this.state}] Début de la lecture.`);
            this.eventBus.emit('voice:playing-started');
        }

        if (event.data instanceof Blob) {
            this.audioChunks.push(event.data);
        } else if (typeof event.data === 'string') {
            try {
                const msg = JSON.parse(event.data);
                
                if (msg.type === "voice:text_response") {
                    console.log("Réponse textuelle reçue, émission vers le chat.");
                    const agentId = this.stateManager.get('chat.currentAgentId');
                    const messagePayload = {
                        message: {
                            agent_id: agentId,
                            content: msg.payload,
                            timestamp: new Date().toISOString()
                        }
                    };
                    this.eventBus.emit('chat:response', messagePayload);
                }
                else if (msg.type === "voice:stream_end") {
                    console.log("Le serveur a terminé de streamer. Lecture finale.");
                    this._playReceivedAudio();
                    if (this.websocket?.readyState === WebSocket.OPEN) {
                        this.websocket.close();
                    }
                }
            } catch (e) {
                console.error("Message non-JSON reçu:", event.data);
            }
        }
    }

    _playReceivedAudio() {
        if (this.audioChunks.length === 0) {
            this.resetState();
            return;
        };

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/mpeg' });
        const audioUrl = URL.createObjectURL(audioBlob);
        this.audioPlayer = new Audio(audioUrl);
        this.audioPlayer.play().catch(e => console.error("Erreur de lecture audio:", e));

        this.audioChunks = [];

        this.audioPlayer.onended = () => {
            URL.revokeObjectURL(audioUrl);
            this.audioPlayer = null;
            this.resetState();
        };
    }
    
    handleWebSocketError(error) {
        console.error("Erreur WebSocket vocal:", error);
        this.resetState();
    }

    handleWebSocketClose() {
        console.log("WebSocket vocal déconnecté.");
        // --- FIX V10.7 : On retire l'appel `resetState` immédiat qui cause la race condition ---
        // Le reset est maintenant géré uniquement par l'événement `onended` de l'audio.
        if(this.state !== 'IDLE') {
             this._playReceivedAudio();
        }
    }
    
    resetState() {
        console.log("Réinitialisation de l'état vocal à IDLE.");
        this.state = 'IDLE';
        
        if(this.mediaRecorder) {
            if(this.mediaRecorder.state === 'recording') this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.mediaRecorder = null;
        }
        if(this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer = null;
        }
        if(this.websocket) {
            if(this.websocket.readyState === WebSocket.OPEN) this.websocket.close();
            this.websocket = null;
        }

        this.audioChunks = [];
        this.eventBus.emit('voice:interaction-finished');
    }
}