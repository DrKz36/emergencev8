#!/usr/bin/env python3
"""
Benchmark de rétention mémoire - Agent ÉMERGENCE
=================================================

Test la capacité de rétention de contexte des agents Neo, Anima, Nexus
à trois jalons temporels : T+1h, T+24h, T+7j

Usage:
    # Pour Neo
    AGENT_NAME=Neo python scripts/memory_probe.py

    # Pour Anima
    AGENT_NAME=Anima python scripts/memory_probe.py

    # Pour Nexus
    AGENT_NAME=Nexus python scripts/memory_probe.py

Variables d'environnement:
    AGENT_NAME      : Neo | Anima | Nexus (défaut: Neo)
    SESSION_ID      : ID de session (défaut: session-{agent})
    BACKEND_URL     : URL backend (défaut: http://localhost:8000)
    JWT_TOKEN       : Token JWT pour auth (défaut: demo-token)

Sortie:
    Fichier CSV : memory_results_{agent}.csv
"""

import os
import time
import csv
import datetime as dt
import yaml
import httpx
from pathlib import Path
from typing import List, Dict

# Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "Neo")
SESSION_ID = os.getenv(
    "SESSION_ID",
    f"session-{AGENT_NAME.lower()}-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
JWT_TOKEN = os.getenv("JWT_TOKEN", "demo-token")

# Chemins
ROOT_DIR = Path(__file__).parent.parent
RESULTS_CSV = ROOT_DIR / f"memory_results_{AGENT_NAME.lower()}.csv"
GROUND_TRUTH_PATH = ROOT_DIR / "prompts" / "ground_truth.yml"

# Délais de test (nom, secondes)
# Pour tests rapides, utiliser des délais courts (ex: 60s, 120s, 180s)
# Pour production, utiliser les vrais délais (3600, 86400, 604800)
DELTAS = [("T+1h", 3600), ("T+1d", 86400), ("T+1w", 604800)]

# Mode debug (délais raccourcis)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
if DEBUG_MODE:
    print("⚠️  MODE DEBUG: Délais raccourcis pour tests rapides")
    DELTAS = [("T+1min", 60), ("T+2min", 120), ("T+3min", 180)]


def call_agent(message: str) -> str:
    """Appelle l'API /api/chat pour envoyer un message à l'agent."""
    url = f"{BACKEND_URL}/api/chat"
    payload = {
        "agent": AGENT_NAME.lower(),
        "message": message,
        "session_id": SESSION_ID,
    }
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json().get("response", "")
    except httpx.HTTPStatusError as e:
        print(f"❌ Erreur HTTP {e.response.status_code}: {e.response.text}")
        return ""
    except httpx.RequestError as e:
        print(f"❌ Erreur de connexion: {e}")
        return ""
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return ""


def normalize(text: str) -> str:
    """Normalise une chaîne pour comparaison (minuscules, espaces simplifiés)."""
    return " ".join(text.lower().split())


def score(ground_truth: str, prediction: str) -> float:
    """
    Calcule un score de similarité entre vérité terrain et prédiction.

    Returns:
        1.0 si correspondance exacte
        0.5 si la vérité est contenue dans la prédiction
        0.0 sinon
    """
    gt = normalize(ground_truth)
    pred = normalize(prediction)

    if gt == pred:
        return 1.0
    if gt and gt in pred:
        return 0.5
    return 0.0


def ensure_csv():
    """Crée le fichier CSV avec headers si nécessaire."""
    if not RESULTS_CSV.exists():
        RESULTS_CSV.write_text(
            "timestamp_utc,agent,session,tick,fact_id,score,truth,prediction\n",
            encoding="utf-8",
        )


def log_result(tick: str, fact_id: str, score_val: float, truth: str, prediction: str):
    """Enregistre un résultat dans le CSV."""
    ensure_csv()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            [
                dt.datetime.utcnow().isoformat(),
                AGENT_NAME,
                SESSION_ID,
                tick,
                fact_id,
                f"{score_val:.2f}",
                truth,
                prediction,
            ]
        )


def inject_context(facts: List[Dict]):
    """Injecte le contexte initial dans la mémoire de l'agent."""
    ctx_lines = [f"- {fact['prompt']}" for fact in facts]
    ctx = "\n".join(ctx_lines)

    message = f"""Mémorise ces informations pour la suite de notre conversation :

{ctx}

Ces informations sont importantes et je vais te les redemander plus tard.
Confirme-moi que tu les as bien mémorisées."""

    response = call_agent(message)
    print(f"✅ Contexte injecté. Réponse agent: {response[:100]}...")


def ask_recall(tick: str, facts: List[Dict]):
    """Teste le rappel des faits à un instant donné."""
    print(f"\n📝 Test de rappel à {tick}")
    for fact in facts:
        question = f"Peux-tu rappeler la valeur associée à : {fact['prompt']} (réponds uniquement avec la valeur, rien d'autre)"
        pred = call_agent(question)

        score_val = score(fact["answer"], pred)
        log_result(tick, fact["id"], score_val, fact["answer"], pred)

        # Affichage résultat
        emoji = "✅" if score_val >= 0.5 else "❌"
        print(
            f"  {emoji} {fact['id']}: score={score_val:.2f} | attendu='{fact['answer']}' | obtenu='{pred[:50]}'"
        )


def run():
    """Exécute le benchmark complet."""
    print("=" * 80)
    print(f"🧠 BENCHMARK DE RÉTENTION MÉMOIRE - Agent {AGENT_NAME}")
    print("=" * 80)
    print(f"Session ID : {SESSION_ID}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Résultats  : {RESULTS_CSV}")
    print()

    # Chargement des faits
    if not GROUND_TRUTH_PATH.exists():
        print(f"❌ Fichier ground truth introuvable: {GROUND_TRUTH_PATH}")
        return

    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        facts = yaml.safe_load(f)["facts"]

    print(f"📚 {len(facts)} faits chargés depuis ground_truth.yml")

    # Injection du contexte
    print(f"\n🔄 Injection du contexte initial dans {AGENT_NAME}...")
    inject_context(facts)

    # Planification des tests
    t0 = time.time()
    schedule = [(label, t0 + seconds) for label, seconds in DELTAS]

    print("\n⏰ Tests planifiés:")
    for label, when in schedule:
        dt_when = dt.datetime.fromtimestamp(when)
        print(f"  - {label}: {dt_when.strftime('%Y-%m-%d %H:%M:%S')}")

    # Boucle de tests
    while schedule:
        label, when = schedule[0]
        now = time.time()

        if now >= when:
            print(
                f"\n🚀 Exécution test {label} (planifié à {dt.datetime.fromtimestamp(when).strftime('%H:%M:%S')})"
            )
            ask_recall(label, facts)
            schedule.pop(0)
        else:
            # Attente
            remaining = int(when - now)
            if remaining > 60:
                print(
                    f"⏳ Attente {remaining // 60}min {remaining % 60}s avant prochain test ({label})...",
                    end="\r",
                )
            time.sleep(min(30, remaining))

    print("\n" + "=" * 80)
    print(f"✅ Benchmark terminé pour {AGENT_NAME}")
    print(f"📊 Résultats sauvegardés dans : {RESULTS_CSV}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
