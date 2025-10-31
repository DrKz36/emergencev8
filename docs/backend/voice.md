# Voice Feature - TTS/STT avec ElevenLabs & Whisper

## Vue d'ensemble

Le module Voice offre des capacités de synthèse vocale (TTS) et de reconnaissance vocale (STT) pour permettre aux utilisateurs d'interagir vocalement avec les agents.

**Version:** beta-3.3.16
**Date:** 2025-10-31
**Status:** ✅ TTS opérationnel | 🚧 STT/WebSocket prévu pour v3.4+

## Architecture

### Backend (`src/backend/features/voice/`)

```
voice/
├── models.py          # Pydantic models (VoiceServiceConfig, TTSRequest)
├── service.py         # VoiceService (synthesize_speech, transcribe_audio)
└── router.py          # REST + WebSocket endpoints
```

### Services

#### VoiceService (`service.py`)

**Responsabilités:**
- Synthèse vocale (TTS) via ElevenLabs API
- Transcription audio (STT) via OpenAI Whisper
- Gestion des streams audio (chunked streaming)
- Intégration avec ChatService pour interactions vocales complètes

**Méthodes principales:**

```python
async def synthesize_speech(self, text: str) -> AsyncGenerator[bytes, None]:
    """
    Génère un flux audio MP3 à partir de texte avec ElevenLabs.

    Args:
        text: Texte à synthétiser

    Yields:
        Chunks audio MP3 (bytes)

    Raises:
        HTTPException: Si génération échoue
    """

async def transcribe_audio(self, audio_data: bytes) -> str:
    """
    Transcrit audio vers texte avec OpenAI Whisper.

    Args:
        audio_data: Données audio (webm/opus)

    Returns:
        Texte transcrit

    Raises:
        HTTPException: Si transcription échoue
    """
```

**Configuration (.env):**

```env
# ElevenLabs TTS
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=ohItIVrXTBI80RrUECOD  # Voix française naturelle
ELEVENLABS_MODEL_ID=eleven_multilingual_v2

# OpenAI Whisper STT
OPENAI_API_KEY=sk-proj-...
WHISPER_MODEL=whisper-1  # Optionnel (défaut: whisper-1)
```

### Endpoints

#### REST - TTS (Opérationnel)

**`POST /api/voice/tts`**

Génère un flux audio MP3 à partir de texte.

**Request:**
```json
{
  "text": "Bonjour, je suis Anima !"
}
```

**Response:**
- Status: 200
- Content-Type: `audio/mpeg`
- Content-Disposition: `inline`
- Body: Stream MP3 (chunked)

**Erreurs:**
- 400: Texte vide
- 503: VoiceService indisponible
- 500: Erreur génération TTS

**Exemple cURL:**
```bash
curl -X POST https://emergence-app.run.app/api/voice/tts \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test de synthèse vocale"}' \
  --output test.mp3
```

#### WebSocket - Interaction vocale (Prévu v3.4+)

**`WS /api/voice/ws/{agent_name}?session_id=<uuid>`**

Interaction vocale bi-directionnelle avec un agent.

**Flow:**
1. Client envoie audio (webm/opus bytes)
2. Serveur transcrit via Whisper
3. Serveur génère réponse LLM via ChatService
4. Serveur synthétise via ElevenLabs
5. Serveur stream audio MP3 au client

**Messages serveur:**
```json
{ "type": "text", "data": "Réponse LLM" }
{ "type": "audio", "data": <bytes MP3> }
{ "type": "error", "data": "Message d'erreur" }
```

**Note:** WebSocket vocal non encore utilisé par l'UI frontend.

## Frontend

### UI Chat (`src/frontend/features/chat/chat-ui.js`)

**Fonctionnalités:**
- ✅ Bouton "Écouter" sur chaque message d'agent (icône speaker)
- ✅ Appel API `/api/voice/tts` avec texte du message
- ✅ Player audio HTML5 flottant (bas droite)
- ✅ Contrôles natifs (play/pause/volume/timeline)
- ✅ Cleanup automatique URLs blob après lecture

**Implémentation:**

```javascript
async _handleListenMessage(button) {
  const text = this._decodeHTML(button.getAttribute('data-message'));
  const response = await apiClient.post('/api/voice/tts', { text });
  const blob = await response.blob();
  const audioUrl = URL.createObjectURL(blob);

  let audio = document.getElementById('chat-audio-player');
  if (!audio) {
    audio = document.createElement('audio');
    audio.id = 'chat-audio-player';
    audio.controls = true;
    audio.style.cssText = 'position: fixed; bottom: 80px; right: 20px; ...';
    document.body.appendChild(audio);
  }

  audio.src = audioUrl;
  audio.play();
}
```

## Provider ElevenLabs

### Caractéristiques

- **Model:** `eleven_multilingual_v2`
- **Voice ID:** `ohItIVrXTBI80RrUECOD` (voix française naturelle)
- **Format audio:** MP3, bitrate 128kbps
- **Latency:** ~500-1000ms (streaming)
- **Qualité:** Voix naturelle supérieure aux TTS standards (Google, AWS Polly)

### Limites

- **Quota:** 10,000 caractères/mois (plan free) / 100,000 caractères/mois (plan starter)
- **Rate limit:** 2 requêtes/seconde
- **Max text length:** 5000 caractères par requête

### Coûts (Référence)

- **Plan Free:** $0 pour 10k chars/mois
- **Plan Starter:** $5/mois pour 100k chars
- **Plan Creator:** $22/mois pour 500k chars
- **Entreprise:** Custom pricing

## Tests

### Tests Backend

```bash
# Tests unitaires VoiceService
pytest tests/backend/features/test_voice_service.py -v

# Tests d'intégration endpoints
pytest tests/backend/features/test_voice_router.py -v
```

### Tests manuels

**TTS via cURL:**
```bash
# Obtenir JWT token
export JWT_TOKEN=$(curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}' \
  | jq -r '.token')

# Tester TTS
curl -X POST http://localhost:8080/api/voice/tts \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, ceci est un test de synthèse vocale"}' \
  --output test.mp3

# Lire l'audio
mpv test.mp3  # ou vlc, ffplay, etc.
```

**TTS via UI:**
1. Ouvrir module Dialogue
2. Envoyer message à un agent
3. Cliquer bouton "Écouter" (icône speaker)
4. Player audio apparaît en bas à droite
5. Audio se joue automatiquement

## Roadmap

### Version actuelle (beta-3.3.16)
- ✅ TTS REST endpoint opérationnel
- ✅ Bouton "Écouter" sur messages agents
- ✅ Player audio flottant
- ✅ Configuration ElevenLabs centralisée

### v3.4 - Voice Interaction Complète
- 🚧 WebSocket vocal bi-directionnel
- 🚧 UI microphone + enregistrement audio
- 🚧 Transcription STT Whisper en temps réel
- 🚧 Conversation vocale complète (mains libres)

### v3.5 - Voice Avancée
- 🔮 Voix personnalisées par agent (multi-voice)
- 🔮 Voice cloning pour voix custom
- 🔮 Support langues multiples (détection auto)
- 🔮 Mode conversation continue (VAD - Voice Activity Detection)

## Dépendances

**Backend Python:**
```python
httpx>=0.27.0  # Client HTTP async pour appels ElevenLabs/OpenAI
openai>=1.0.0  # SDK OpenAI (Whisper STT)
```

**APIs externes:**
- ElevenLabs API (TTS)
- OpenAI API (Whisper STT)

## Troubleshooting

### Erreur: VoiceService indisponible (503)

**Cause:** Clés API manquantes dans `.env`

**Solution:**
```bash
# Vérifier .env contient:
ELEVENLABS_API_KEY=sk_...
OPENAI_API_KEY=sk-proj-...
```

### Erreur: Audio ne se joue pas

**Cause 1:** Autoplay bloqué par navigateur

**Solution:** Cliquer manuellement sur play dans le player audio

**Cause 2:** Format audio incompatible

**Solution:** Vérifier que le navigateur supporte MP3 (tous modernes le supportent)

### Erreur: Rate limit ElevenLabs (429)

**Cause:** Trop de requêtes TTS en peu de temps (>2/sec)

**Solution:**
- Implémenter throttling côté client
- Upgrader plan ElevenLabs si usage élevé

## Sécurité

### Points d'attention

- ✅ **Auth JWT requise** - Tous les endpoints voice nécessitent authentification
- ✅ **Validation input** - Texte validé (max 5000 chars, pas de texte vide)
- ✅ **Rate limiting** - Respecte limites ElevenLabs (2 req/sec)
- ✅ **Pas de secrets exposés** - Clés API uniquement côté backend
- ⚠️ **Pas de sanitization audio** - Audio généré non filtré (confiance ElevenLabs)

### Recommandations

1. **Monitoring usage** - Logger les requêtes TTS pour détecter abus
2. **Rate limiting custom** - Ajouter rate limit applicatif (ex: 10 TTS/min par user)
3. **Quotas utilisateurs** - Limiter caractères TTS/jour par utilisateur
4. **Audit logs** - Logger tous les appels voice pour traçabilité

## Références

- [ElevenLabs API Documentation](https://elevenlabs.io/docs/api-reference/text-to-speech)
- [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [Architecture ÉMERGENCE - Contrats API](./architecture/30-Contracts.md#6-voice-api-endpoints)
- [Architecture ÉMERGENCE - Composants Backend](./architecture/10-Components.md)
