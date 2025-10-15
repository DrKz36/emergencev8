"""
Script d'injection de messages de test pour validation Phase 3 - Groupement thématique
Injecte 25 messages (5 thèmes x 5 messages) avec timestamps simulés
"""

import sys
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DB_PATH = Path("src/backend/data/db/emergence_v7.db")
USER_ID = "test_user_local"
SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"
THREAD_ID = f"test_thread_{uuid.uuid4().hex[:8]}"

# Chargement du payload
with open("memory_injection_payload.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

messages = payload["messages"]

print(f"🧠 Injection de {len(messages)} messages de test dans ÉMERGENCE")
print(f"   Database: {DB_PATH}")
print(f"   User ID: {USER_ID}")
print(f"   Session ID: {SESSION_ID}")
print(f"   Thread ID: {THREAD_ID}")
print()

# Connexion SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Créer session et thread
print("📦 Création de la session et du thread...")

cursor.execute("""
    INSERT OR IGNORE INTO sessions (id, user_id, created_at, updated_at)
    VALUES (?, ?, datetime('now'), datetime('now'))
""", (SESSION_ID, USER_ID))

cursor.execute("""
    INSERT OR IGNORE INTO threads (
        id, session_id, user_id, type, title, archived,
        created_at, updated_at, last_message_at
    )
    VALUES (?, ?, ?, 'chat', 'Test Mémoire Phase 3 - Groupement Thématique', 0,
            datetime('now'), datetime('now'), datetime('now'))
""", (THREAD_ID, SESSION_ID, USER_ID))

conn.commit()
print(f"   ✅ Session créée: {SESSION_ID}")
print(f"   ✅ Thread créé: {THREAD_ID}")
print()

# Injecter les messages
print("💉 Injection des messages...")
injected_count = 0

for msg in messages:
    msg_id = f"msg_{uuid.uuid4().hex}"
    timestamp_iso = msg["timestamp"]
    content = msg["content"]

    # Convertir le timestamp au format attendu
    try:
        dt = datetime.fromisoformat(timestamp_iso)
        created_at = dt.isoformat()
    except Exception as e:
        print(f"   ⚠️  Erreur parsing timestamp {timestamp_iso}: {e}")
        created_at = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO messages (
            id, thread_id, role, content, created_at,
            tokens, meta, agent_id, session_id, user_id
        )
        VALUES (?, ?, 'user', ?, ?, 0, '{}', NULL, ?, ?)
    """, (msg_id, THREAD_ID, content, created_at, SESSION_ID, USER_ID))

    injected_count += 1

    # Log condensé
    preview = content[:60] + "..." if len(content) > 60 else content
    print(f"   [{injected_count:02d}/25] {timestamp_iso} | {preview}")

conn.commit()
conn.close()

print()
print(f"✅ {injected_count} messages injectés avec succès !")
print()
print("🌱 Prochaine étape : déclencher la consolidation mémoire")
print(f"   Commande: curl -X POST http://127.0.0.1:8000/api/memory/tend-garden \\")
print(f"             -H 'Content-Type: application/json' \\")
print(f"             -d '{{\"thread_id\": \"{THREAD_ID}\", \"session_id\": \"{SESSION_ID}\"}}'")
print()
print("📊 Validation : vérifier le groupement thématique avec")
print("   GET /api/memory/concepts/search?q=docker")
print("   GET /api/memory/search/unified?q=philosophie")
