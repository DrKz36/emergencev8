#!/bin/bash
# Script pour révoquer toutes les sessions actives
# Usage: ./revoke_all_sessions.sh YOUR_ADMIN_ID_TOKEN

if [ -z "$1" ]; then
    echo "Usage: $0 YOUR_ADMIN_ID_TOKEN"
    echo ""
    echo "Pour obtenir ton token:"
    echo "1. Connecte-toi sur https://emergence-app.ch"
    echo "2. Ouvre la console développeur (F12)"
    echo "3. Va dans Application > Cookies"
    echo "4. Copie la valeur de 'id_token'"
    exit 1
fi

TOKEN="$1"
BASE_URL="https://emergence-app-47nct44nma-ew.a.run.app"

echo "🔍 Récupération des sessions actives..."
SESSIONS=$(curl -s -X GET "$BASE_URL/api/admin/sessions" \
    -H "Cookie: id_token=$TOKEN" \
    -H "Content-Type: application/json")

echo "$SESSIONS" | python -m json.tool 2>/dev/null || echo "$SESSIONS"

# Extraire les IDs et révoquer
echo ""
echo "🗑️  Révocation des sessions..."
echo "$SESSIONS" | python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'items' in data:
        for session in data['items']:
            print(session.get('id', 'unknown'))
except:
    pass
" | while read session_id; do
    if [ ! -z "$session_id" ]; then
        echo "  - Révocation de $session_id..."
        curl -s -X POST "$BASE_URL/api/admin/sessions/revoke" \
            -H "Cookie: id_token=$TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"session_id\": \"$session_id\"}"
        echo ""
    fi
done

echo "✅ Terminé!"
