"""
Script de diagnostic pour vérifier les données du cockpit.
Analyse la base de données pour valider que les coûts, messages, tokens, etc. sont correctement enregistrés.
"""

import sqlite3
from pathlib import Path

# Trouver le fichier de base de données
DB_PATH = Path(__file__).parent / "instance" / "emergence.db"

if not DB_PATH.exists():
    print(f"❌ Base de données introuvable: {DB_PATH}")
    print("\n💡 Suggestions:")
    print("  1. Vérifiez que le backend a été démarré au moins une fois")
    print("  2. Vérifiez le chemin: instance/emergence.db")
    print("  3. Le fichier se crée automatiquement au premier démarrage")
    exit(1)

print(f"✅ Base de données trouvée: {DB_PATH}")
print("=" * 70)
print("📊 DIAGNOSTIC COCKPIT - ANALYSE DES DONNÉES")
print("=" * 70)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ============================================================================
# 1. MESSAGES
# ============================================================================
print("\n📧 MESSAGES")
print("-" * 70)

try:
    cursor.execute("SELECT COUNT(*) as total FROM messages")
    total_messages = cursor.fetchone()["total"]
    print(f"Total messages: {total_messages}")

    if total_messages > 0:
        # Par période
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE datetime(created_at) >= datetime('now', 'localtime', 'start of day')) as today,
                COUNT(*) FILTER (WHERE datetime(created_at) >= datetime('now', 'localtime', '-7 days')) as week,
                COUNT(*) FILTER (WHERE datetime(created_at) >= datetime('now', 'localtime', '-30 days')) as month
            FROM messages
        """)
        row = cursor.fetchone()
        print(f"  Aujourd'hui: {row['today']}")
        print(f"  Cette semaine (7j): {row['week']}")
        print(f"  Ce mois (30j): {row['month']}")

        # Message le plus récent
        cursor.execute("SELECT created_at FROM messages ORDER BY created_at DESC LIMIT 1")
        last_msg = cursor.fetchone()
        print(f"  Dernier message: {last_msg['created_at']}")
    else:
        print("  ⚠️ Aucun message dans la base de données")
        print("  💡 Créez une conversation pour voir des données")

except sqlite3.OperationalError as e:
    print(f"  ❌ Erreur: {e}")
    print("  💡 La table 'messages' n'existe peut-être pas encore")

# ============================================================================
# 2. COÛTS
# ============================================================================
print("\n💰 COÛTS")
print("-" * 70)

try:
    cursor.execute("SELECT COUNT(*) as total FROM costs")
    total_costs = cursor.fetchone()["total"]
    print(f"Total entrées de coûts: {total_costs}")

    if total_costs > 0:
        # Total des coûts
        cursor.execute("SELECT SUM(total_cost) as sum FROM costs")
        total_sum = cursor.fetchone()["sum"] or 0
        print(f"Coût total cumulé: ${total_sum:.6f}")

        # Par modèle
        print("\n  Coûts par modèle:")
        cursor.execute("""
            SELECT
                model,
                COUNT(*) as count,
                SUM(total_cost) as cost,
                SUM(input_tokens) as input_tok,
                SUM(output_tokens) as output_tok
            FROM costs
            GROUP BY model
            ORDER BY cost DESC
        """)
        for row in cursor.fetchall():
            model = row["model"]
            count = row["count"]
            cost = row["cost"] or 0
            input_tok = row["input_tok"] or 0
            output_tok = row["output_tok"] or 0
            print(f"    {model}: {count} requêtes, ${cost:.6f}, {input_tok:,} in, {output_tok:,} out")

        # DIAGNOSTIC GEMINI
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                SUM(total_cost) as cost,
                SUM(input_tokens) as input_tok,
                SUM(output_tokens) as output_tok
            FROM costs
            WHERE model LIKE '%gemini%'
        """)
        gemini = cursor.fetchone()
        if gemini and gemini["count"] > 0:
            print("\n  🔥 GEMINI (diagnostic Gap #1):")
            print(f"    Requêtes: {gemini['count']}")
            print(f"    Coût total: ${gemini['cost'] or 0:.6f}")
            print(f"    Tokens: {gemini['input_tok'] or 0:,} in, {gemini['output_tok'] or 0:,} out")

            if (gemini["cost"] or 0) == 0:
                print(f"    ⚠️ WARNING: Coûts Gemini à $0.00 avec {gemini['count']} requêtes!")
                print("    💡 Vérifiez que le fix Gap #1 est bien appliqué")
            elif (gemini["input_tok"] or 0) == 0 and (gemini["output_tok"] or 0) == 0:
                print(f"    ⚠️ WARNING: Tokens Gemini à 0 avec {gemini['count']} requêtes!")
                print("    💡 count_tokens() ne fonctionne peut-être pas")
            else:
                print("    ✅ OK: Gemini semble correctement tracké")

        # Par période
        print("\n  Coûts par période:")
        cursor.execute("""
            SELECT
                SUM(CASE WHEN datetime(timestamp) >= datetime('now', 'localtime', 'start of day') THEN total_cost ELSE 0 END) as today,
                SUM(CASE WHEN datetime(timestamp) >= datetime('now', 'localtime', '-7 days') THEN total_cost ELSE 0 END) as week,
                SUM(CASE WHEN datetime(timestamp) >= datetime('now', 'localtime', '-30 days') THEN total_cost ELSE 0 END) as month
            FROM costs
        """)
        periods = cursor.fetchone()
        print(f"    Aujourd'hui: ${periods['today'] or 0:.6f}")
        print(f"    Cette semaine (7j): ${periods['week'] or 0:.6f}")
        print(f"    Ce mois (30j): ${periods['month'] or 0:.6f}")

        # Coût moyen par requête
        avg_cost = total_sum / total_costs
        print(f"\n  Coût moyen par requête: ${avg_cost:.6f}")

        # Dernière entrée
        cursor.execute("SELECT timestamp, model, total_cost FROM costs ORDER BY timestamp DESC LIMIT 1")
        last_cost = cursor.fetchone()
        print(f"  Dernière entrée: {last_cost['timestamp']} - {last_cost['model']} (${last_cost['total_cost']:.6f})")

    else:
        print("  ⚠️ Aucun coût enregistré")
        print("  💡 Les coûts sont enregistrés après chaque requête LLM")

except sqlite3.OperationalError as e:
    print(f"  ❌ Erreur: {e}")
    print("  💡 La table 'costs' n'existe peut-être pas encore")

# ============================================================================
# 3. SESSIONS
# ============================================================================
print("\n🧵 SESSIONS")
print("-" * 70)

try:
    cursor.execute("SELECT COUNT(*) as total FROM sessions")
    total_sessions = cursor.fetchone()["total"]
    print(f"Total sessions: {total_sessions}")

    if total_sessions > 0:
        cursor.execute("""
            SELECT COUNT(*) as active
            FROM sessions
            WHERE archived = 0 OR archived IS NULL
        """)
        active = cursor.fetchone()["active"]
        print(f"  Sessions actives: {active}")
        print(f"  Sessions archivées: {total_sessions - active}")

        # Dernière session
        cursor.execute("SELECT id, created_at FROM sessions ORDER BY created_at DESC LIMIT 1")
        last_session = cursor.fetchone()
        print(f"  Dernière session: {last_session['id']} ({last_session['created_at']})")

except sqlite3.OperationalError as e:
    print(f"  ❌ Erreur: {e}")

# ============================================================================
# 4. DOCUMENTS
# ============================================================================
print("\n📄 DOCUMENTS")
print("-" * 70)

try:
    cursor.execute("SELECT COUNT(*) as total FROM documents")
    total_docs = cursor.fetchone()["total"]
    print(f"Total documents: {total_docs}")

    if total_docs > 0:
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM documents
            GROUP BY type
            ORDER BY count DESC
        """)
        print("  Par type:")
        for row in cursor.fetchall():
            print(f"    {row['type']}: {row['count']}")

except sqlite3.OperationalError as e:
    print(f"  ❌ Erreur: {e}")

# ============================================================================
# 5. TOKENS (calcul depuis costs)
# ============================================================================
print("\n🪙 TOKENS")
print("-" * 70)

try:
    cursor.execute("""
        SELECT
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output
        FROM costs
    """)
    tokens = cursor.fetchone()
    total_input = tokens["total_input"] or 0
    total_output = tokens["total_output"] or 0
    total_tokens = total_input + total_output

    print(f"Total tokens: {total_tokens:,}")
    print(f"  Input: {total_input:,}")
    print(f"  Output: {total_output:,}")

    if total_costs > 0:
        avg_tokens = total_tokens / total_costs
        print(f"  Moyenne par message: {avg_tokens:.0f}")

except sqlite3.OperationalError as e:
    print(f"  ❌ Erreur: {e}")

# ============================================================================
# 6. RÉSUMÉ & RECOMMANDATIONS
# ============================================================================
print("\n" + "=" * 70)
print("📋 RÉSUMÉ & RECOMMANDATIONS")
print("=" * 70)

issues = []
warnings = []
successes = []

if total_messages == 0:
    warnings.append("Aucun message → Créez une conversation pour tester")
else:
    successes.append(f"{total_messages} messages enregistrés")

if total_costs == 0:
    issues.append("Aucun coût enregistré → Vérifiez que record_cost() est appelé")
else:
    successes.append(f"{total_costs} coûts enregistrés (${total_sum:.6f} total)")

    # Check Gemini
    if gemini and gemini["count"] > 0:
        if (gemini["cost"] or 0) == 0:
            issues.append("🔥 CRITIQUE: Coûts Gemini = $0.00 → Gap #1 NON corrigé")
        else:
            successes.append(f"✅ Gemini correctement tracké (${gemini['cost']:.6f})")

if total_sessions == 0:
    warnings.append("Aucune session → Normal si première utilisation")
else:
    successes.append(f"{total_sessions} sessions ({active} actives)")

print("\n✅ Succès:")
for s in successes:
    print(f"  • {s}")

if warnings:
    print("\n⚠️ Avertissements:")
    for w in warnings:
        print(f"  • {w}")

if issues:
    print("\n🔴 Problèmes:")
    for i in issues:
        print(f"  • {i}")
else:
    if total_messages > 0 and total_costs > 0:
        print("\n🎉 TOUT SEMBLE FONCTIONNEL!")
        print("   Le cockpit devrait afficher des données correctes.")

print("\n" + "=" * 70)
print("Pour tester le cockpit:")
print("  1. Démarrez le backend: python -m uvicorn src.backend.main:app --reload")
print("  2. Ouvrez l'application frontend")
print("  3. Allez dans le cockpit (menu ou /cockpit)")
print("  4. Les valeurs affichées devraient correspondre aux chiffres ci-dessus")
print("=" * 70)

conn.close()
