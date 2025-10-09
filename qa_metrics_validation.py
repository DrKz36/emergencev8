"""
QA Validation - Métriques Prometheus Phase 3
Envoie des requêtes réelles pour incrémenter les compteurs
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "https://emergence-app-47nct44nma-ew.a.run.app"
METRICS_URL = f"{BASE_URL}/api/metrics"


async def get_metric_value(metric_name: str) -> float:
    """Récupère la valeur actuelle d'une métrique"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(METRICS_URL)
        for line in response.text.split('\n'):
            if line.startswith(metric_name) and not line.startswith('#'):
                # Format: metric_name{labels} value
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return float(parts[-1])
                    except ValueError:
                        continue
    return 0.0


async def dev_login() -> dict:
    """Login en mode dev pour obtenir un token"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/api/auth/dev/login")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[WARNING] Login failed: {response.status_code}")
            print(f"[DEBUG] Response: {response.text[:200]}")
            return {}


async def send_chat_message(token: str, message: str) -> dict:
    """Envoie un message chat pour déclencher analyse mémoire"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/chat/send",
            headers=headers,
            json={"message": message, "session_id": "qa_test_session"}
        )
        return response.json() if response.status_code == 200 else {}


async def trigger_memory_analysis(token: str) -> bool:
    """Déclenche une analyse mémoire explicite"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/memory/analyze",
                headers=headers,
                json={"session_id": "qa_test_session"}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[WARNING] Memory analysis endpoint error: {e}")
            return False


async def main():
    print("=" * 60)
    print("QA VALIDATION - MÉTRIQUES PROMETHEUS PHASE 3")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}\n")

    # 1. État initial des métriques
    print("[METRICS] État initial des métriques:")
    initial_memory = await get_metric_value("memory_analysis_success_total")
    initial_concept = await get_metric_value("concept_recall_detections_total")
    initial_cache_hits = await get_metric_value("memory_analysis_cache_hits_total")

    print(f"  - memory_analysis_success_total: {initial_memory}")
    print(f"  - concept_recall_detections_total: {initial_concept}")
    print(f"  - memory_analysis_cache_hits_total: {initial_cache_hits}\n")

    # 2. Login dev
    print("[AUTH] Login mode dev...")
    auth_data = await dev_login()
    if not auth_data or "token" not in auth_data:
        print("[ERROR] Échec login - arrêt QA")
        return

    token = auth_data["token"]
    print(f"[OK] Token obtenu (user: {auth_data.get('email', 'N/A')})\n")

    # 3. Envoyer messages pour déclencher métriques
    print("[CHAT] Envoi de messages pour déclencher analyse mémoire...")
    messages = [
        "Quelle est l'architecture d'Emergence?",
        "Explique-moi le système de métriques Prometheus",
        "Comment fonctionne le concept recall?"
    ]

    for i, msg in enumerate(messages, 1):
        print(f"  [{i}/{len(messages)}] {msg[:50]}...")
        result = await send_chat_message(token, msg)
        await asyncio.sleep(2)  # Pause entre messages

    print("[OK] Messages envoyés\n")

    # 4. Déclencher analyse explicite si endpoint existe
    print("[MEMORY] Tentative déclenchement analyse mémoire...")
    await trigger_memory_analysis(token)
    await asyncio.sleep(3)
    print("[OK] Analyse déclenchée\n")

    # 5. Vérifier incrémentation
    print("[METRICS] État final des métriques:")
    final_memory = await get_metric_value("memory_analysis_success_total")
    final_concept = await get_metric_value("concept_recall_detections_total")
    final_cache_hits = await get_metric_value("memory_analysis_cache_hits_total")

    print(f"  - memory_analysis_success_total: {final_memory} (Delta {final_memory - initial_memory})")
    print(f"  - concept_recall_detections_total: {final_concept} (Delta {final_concept - initial_concept})")
    print(f"  - memory_analysis_cache_hits_total: {final_cache_hits} (Delta {final_cache_hits - initial_cache_hits})\n")

    # 6. Résultat
    print("=" * 60)
    if final_memory > initial_memory or final_concept > initial_concept:
        print("[SUCCESS] QA RÉUSSIE - Les métriques s'incrémentent correctement")
    else:
        print("[WARNING] QA PARTIELLE - Les métriques n'ont pas bougé")
        print("   Vérifier logs Cloud Run pour diagnostiquer")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
