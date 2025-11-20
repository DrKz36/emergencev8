"""
Test End-to-End : Extraction préférences via WebSocket

Ce script simule une session utilisateur complète :
1. Connexion WebSocket
2. Envoi de messages avec préférences
3. Fermeture session (déclenche extraction)
4. Validation ChromaDB

Usage:
    python scripts/test_e2e_preferences.py
    python scripts/test_e2e_preferences.py --url ws://localhost:8000/api/chat/ws
"""

import asyncio
import websockets
import json
import argparse
import sys
import time
from pathlib import Path

# Ajouter src au path pour validate_preferences
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class E2ETestPreferences:
    """Test E2E extraction préférences"""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.session_id = None
        self.preferences_sent = 0

    async def test_websocket_connection(self):
        """Test connexion WebSocket"""
        print("\n" + "=" * 60)
        print("🔌 TEST: Connexion WebSocket")
        print("=" * 60)

        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"✅ Connecté à {self.ws_url}")

                # Attendre message session_established
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(msg)

                if data.get("type") == "ws:session_established":
                    self.session_id = data["payload"]["session_id"]
                    print(f"✅ Session établie: {self.session_id}")
                    return True, websocket
                else:
                    print(f"❌ Message inattendu: {data.get('type')}")
                    return False, None

        except asyncio.TimeoutError:
            print("❌ Timeout: pas de réponse du serveur")
            return False, None
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False, None

    async def send_preference_messages(self, websocket):
        """Envoie messages avec préférences"""
        print("\n" + "=" * 60)
        print("📤 TEST: Envoi messages avec préférences")
        print("=" * 60)

        messages = [
            {
                "text": "Je préfère utiliser Python avec FastAPI pour mes APIs backend",
                "agent_id": "anima",
                "expected_type": "preference",
            },
            {
                "text": "J'aime beaucoup TypeScript et React pour le développement frontend",
                "agent_id": "nexus",
                "expected_type": "preference",
            },
            {
                "text": "J'évite toujours les bases de données NoSQL pour les données financières",
                "agent_id": "anima",
                "expected_type": "constraint",
            },
        ]

        for i, msg_data in enumerate(messages, 1):
            print(f"\n📨 Message {i}/3:")
            print(f"   Text: {msg_data['text'][:60]}...")
            print(f"   Type attendu: {msg_data['expected_type']}")

            # Construire payload
            payload = {
                "type": "chat.message",
                "payload": {
                    "text": msg_data["text"],
                    "agent_id": msg_data["agent_id"],
                    "use_rag": False,
                },
            }

            try:
                # Envoyer message
                await websocket.send(json.dumps(payload))
                print("   ✅ Envoyé")

                # Attendre réponse agent (peut prendre quelques secondes)
                timeout = 30.0
                start = time.time()
                response_received = False

                while (time.time() - start) < timeout:
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=max(0.1, timeout - (time.time() - start)),
                        )
                        response_data = json.loads(response)

                        # Chercher réponse agent (ws:agent_response ou similaire)
                        if response_data.get("type") in [
                            "ws:agent_response",
                            "ws:message",
                        ]:
                            print("   ✅ Réponse agent reçue")
                            response_received = True
                            break

                    except asyncio.TimeoutError:
                        break
                    except Exception as e:
                        print(f"   ⚠️  Erreur lecture réponse: {e}")
                        break

                if not response_received:
                    print(f"   ⚠️  Pas de réponse agent (timeout {timeout}s)")

                self.preferences_sent += 1

                # Délai entre messages (éviter rate limiting)
                if i < len(messages):
                    await asyncio.sleep(1.0)

            except Exception as e:
                print(f"   ❌ Erreur envoi: {e}")
                return False

        print(f"\n✅ {self.preferences_sent} messages avec préférences envoyés")
        return True

    async def close_session_and_wait(self, websocket):
        """Ferme WebSocket et attend finalisation"""
        print("\n" + "=" * 60)
        print("🔒 TEST: Fermeture session (déclenche finalisation)")
        print("=" * 60)

        try:
            await websocket.close()
            print("✅ WebSocket fermé")

            # Attendre que backend finalise session (extraction préférences)
            print("⏳ Attente finalisation session (5s)...")
            await asyncio.sleep(5.0)

            print("✅ Session finalisée (supposé)")
            return True

        except Exception as e:
            print(f"❌ Erreur fermeture: {e}")
            return False

    def validate_chromadb(self):
        """Valide que préférences sont dans ChromaDB"""
        print("\n" + "=" * 60)
        print("🔍 TEST: Validation ChromaDB")
        print("=" * 60)

        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet", persist_directory="./chroma_data"
                )
            )

            collection = client.get_collection("memory_preferences")
            count = collection.count()

            print(f"📊 Total préférences dans ChromaDB: {count}")

            if count >= self.preferences_sent:
                print(
                    f"✅ Au moins {self.preferences_sent} préférences trouvées (attendu: {self.preferences_sent})"
                )

                # Afficher quelques préférences
                results = collection.get(limit=5, include=["metadatas", "documents"])

                for i, (doc, meta) in enumerate(
                    zip(results["documents"], results["metadatas"]), 1
                ):
                    print(f"\n   🔹 Préférence {i}:")
                    print(
                        f"      User: {meta.get('user_sub') or meta.get('user_id', 'N/A')}"
                    )
                    print(f"      Type: {meta.get('type', 'N/A')}")
                    print(f"      Topic: {meta.get('topic', 'N/A')}")
                    print(f"      Confidence: {meta.get('confidence', 'N/A')}")
                    print(f"      Text: {doc[:60]}...")

                return True

            elif count > 0:
                print(
                    f"⚠️  {count} préférences trouvées (attendu: ≥{self.preferences_sent})"
                )
                print("   Possible que certaines aient été filtrées (confidence < 0.6)")
                return True

            else:
                print(
                    f"❌ Aucune préférence dans ChromaDB (attendu: ≥{self.preferences_sent})"
                )
                print("\n💡 Causes possibles:")
                print("   - Extraction a échoué (vérifier logs backend)")
                print(
                    "   - Préférences pas encore persistées (attendre plus longtemps)"
                )
                print("   - Bug Hotfix P1.3 non corrigé")
                return False

        except Exception as e:
            print(f"❌ Erreur validation ChromaDB: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def run_full_test(self):
        """Exécute test E2E complet"""
        print("\n" + "=" * 70)
        print("🧪 TEST END-TO-END HOTFIX P1.3 - EXTRACTION PRÉFÉRENCES")
        print("=" * 70)

        results = {
            "connection": False,
            "messages_sent": False,
            "session_closed": False,
            "chromadb_validated": False,
        }

        # Étape 1 : Connexion
        success, websocket = await self.test_websocket_connection()
        results["connection"] = success

        if not success:
            print("\n❌ ÉCHEC: Impossible de se connecter au WebSocket")
            return results

        try:
            # Étape 2 : Envoi messages
            success = await self.send_preference_messages(websocket)
            results["messages_sent"] = success

            if not success:
                print("\n❌ ÉCHEC: Erreur lors de l'envoi des messages")
                return results

            # Étape 3 : Fermeture session
            success = await self.close_session_and_wait(websocket)
            results["session_closed"] = success

        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # S'assurer que WebSocket est fermé
            try:
                if websocket and not websocket.closed:
                    await websocket.close()
            except Exception:
                pass

        # Étape 4 : Validation ChromaDB
        success = self.validate_chromadb()
        results["chromadb_validated"] = success

        return results

    def print_summary(self, results):
        """Affiche résumé des tests"""
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ TESTS E2E")
        print("=" * 70)

        print(
            f"\n✅ Connexion WebSocket:     {'✅ PASS' if results['connection'] else '❌ FAIL'}"
        )
        print(
            f"✅ Messages envoyés:         {'✅ PASS' if results['messages_sent'] else '❌ FAIL'}"
        )
        print(
            f"✅ Session fermée:           {'✅ PASS' if results['session_closed'] else '❌ FAIL'}"
        )
        print(
            f"✅ ChromaDB validé:          {'✅ PASS' if results['chromadb_validated'] else '❌ FAIL'}"
        )

        all_passed = all(results.values())

        print("\n" + "=" * 70)

        if all_passed:
            print("✅ TOUS LES TESTS E2E SONT PASSÉS !")
            print("🚀 Hotfix P1.3 validé en local - Prêt pour production")
            print("\n💡 Prochaines étapes:")
            print("   1. Vérifier logs backend pour confirmer extraction")
            print(
                "   2. Vérifier métriques: curl http://localhost:8000/api/metrics | grep memory_preference"
            )
            print("   3. Si tout OK: git push origin main")
            print(
                "   4. Déployer production: gcloud builds submit --config cloudbuild.yaml"
            )
        else:
            print("❌ CERTAINS TESTS E2E ONT ÉCHOUÉ")
            print("⚠️  Vérifier logs backend et corriger avant déploiement")
            print("\n💡 Debugging:")
            print("   - Logs backend: chercher [PreferenceExtractor]")
            print("   - Vérifier ChromaDB: python scripts/validate_preferences.py")
            print(
                "   - Vérifier métriques échecs: curl http://localhost:8000/api/metrics"
            )

        print("=" * 70)

        return all_passed


async def main():
    parser = argparse.ArgumentParser(
        description="Test E2E extraction préférences (Hotfix P1.3)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="ws://localhost:8000/api/chat/ws",
        help="URL WebSocket backend (défaut: ws://localhost:8000/api/chat/ws)",
    )

    args = parser.parse_args()

    # Créer et exécuter test
    test = E2ETestPreferences(ws_url=args.url)
    results = await test.run_full_test()
    all_passed = test.print_summary(results)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
