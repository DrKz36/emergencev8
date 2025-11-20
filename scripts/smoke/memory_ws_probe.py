# /scripts/smoke/memory_ws_probe.py
# Minimal WS client (jwt subprotocol) pour piloter le chat et vérifier les signaux.
# CHANGELOG:
# - Supprime 'extra_headers' (incompatible avec ta version de 'websockets')
# - Envoie TOUJOURS le sous-protocole 'jwt' (+ token si dispo)
# - 'origin' conservé (ok avec websockets récents), safe à retirer si besoin

import asyncio
import json
import os
import sys
import time
import uuid

try:
    import websockets
    from websockets.exceptions import InvalidStatus
except Exception:
    print("⚠️  'websockets' requis. Installe:  python -m pip install websockets")
    raise


def compute_ws_url(base: str, session_id: str | None = None) -> str:
    base = base.strip().rstrip("/")
    sid = (session_id or "").strip() or str(uuid.uuid4())
    if base.startswith(("https://", "http://")):
        scheme = "wss://" if base.startswith("https://") else "ws://"
        host = base.split("://", 1)[1]
        return f"{scheme}{host}/ws/{sid}"
    if base.startswith(("wss://", "ws://")):
        return f"{base.rstrip('/')}/{sid}"
    return f"ws://{base.strip('/')}/ws/{sid}"


def compute_origin(base: str) -> str:
    if base.startswith("wss://"):
        return "https://" + base.split("://", 1)[1]
    if base.startswith("ws://"):
        return "http://" + base.split("://", 1)[1]
    if base.startswith(("https://", "http://")):
        return base
    return "http://" + base


class Probe:
    def __init__(self, base, token=None, timeout=120, session_id=None):
        self.base = base
        self.session_id = (session_id or "").strip() or str(uuid.uuid4())
        self.ws_url = compute_ws_url(base, self.session_id)
        self.origin = compute_origin(base)
        self.token = token or os.environ.get("EMERGENCE_ID_TOKEN")
        self.timeout = int(timeout)
        self.events = []

    async def _connect(self):
        # Toujours proposer 'jwt'; ajouter le token si dispo (mimique du front). :contentReference[oaicite:2]{index=2}
        subprotocols = ["jwt"] + ([self.token] if self.token else [])
        print(
            f"[probe] connect → {self.ws_url}  (session_id={self.session_id}, subprotocols={subprotocols}, origin={self.origin})"
        )
        # NB: PAS d'extra_headers (incompatible sur ta version)
        return await websockets.connect(
            self.ws_url,
            subprotocols=subprotocols,
            origin=self.origin,
        )

    async def _wait_stream_then_completed(self, ws):
        end_seen = False
        completed_seen = False
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
            data = json.loads(raw)
            event_type = data.get("type")
            payload = data.get("payload", {})
            self.events.append((event_type, payload))
            if event_type in (
                "ws:chat_stream_start",
                "ws:chat_stream_chunk",
                "ws:chat_stream_end",
                "ws:analysis_status",
                "ws:rag_status",
                "ws:memory_banner",
            ):
                print(f"[evt] {event_type} :: {payload}")
            if event_type == "ws:chat_stream_end":
                end_seen = True
            if (
                event_type == "ws:analysis_status"
                and str(payload.get("status", "")).lower() == "completed"
                and end_seen
            ):
                completed_seen = True
                break
        return completed_seen

    async def run_once(self, agent_id, text, use_rag=False):
        try:
            async with await self._connect() as ws:
                print(f"[probe] opened. agreed_subprotocol={ws.subprotocol}")
                payload = {
                    "type": "chat.message",
                    "payload": {
                        "text": text,
                        "agent_id": agent_id,
                        "use_rag": bool(use_rag),
                        "msg_uid": str(uuid.uuid4()),
                        "ts": int(time.time() * 1000),
                    },
                }
                await ws.send(json.dumps(payload))
                completed = await self._wait_stream_then_completed(ws)
                print(f"[probe] stream completed={completed}")
                return completed
        except InvalidStatus as exc:
            status = getattr(exc, "status_code", "?")
            print(
                f"[probe][HANDSHAKE] HTTP {status} - sous-protocole/token/Origin peut être invalide. Détail: {exc}"
            )
            raise
        except Exception as exc:
            print(f"[probe][ERROR] {exc}")
            raise

    # --- Plans A→F ---
    async def test_A(self, agent):
        await self.run_once(
            agent,
            "Aujourd'hui je veux travailler sur la Roadmap V8 et corriger la latence.",
            use_rag=False,
        )
        await self.run_once(
            agent,
            "Tu te rappelles ce que j'ai dit juste avant ?",
            use_rag=False,
        )

    async def test_B(self, agent):
        await self.run_once(
            agent,
            "Le mot-code pour Anima est AURORA-8152. Je travaille depuis Genève.",
            use_rag=False,
        )
        await self.run_once(
            agent,
            "Quel est le mot-code d'Anima ?",
            use_rag=False,
        )

    async def test_C(self, agent):
        text = (
            "Quel est ton mot-code ?"
            if agent == "anima"
            else "Quel est le mot-code d'Anima ?"
        )
        await self.run_once(agent, text, use_rag=False)

    async def test_D(self, agent, text, use_rag):
        await self.run_once(
            agent,
            text or "Que contient le document RAG_TEST_A ?",
            use_rag=use_rag,
        )

    async def test_E(self, agent, text):
        if agent == "anima":
            await self.run_once(
                agent,
                text or "Je préfère les réponses courtes.",
                use_rag=False,
            )
        else:
            await self.run_once(
                agent,
                text or "Quelle longueur de réponse je préfère ?",
                use_rag=False,
            )

    async def test_F(self, agent, text):
        before = len(self.events)
        await self.run_once(agent, text or "Ping test signaux.", use_rag=False)
        recent_types = [
            event_type
            for (event_type, _payload) in self.events[before:]
            if event_type.startswith("ws:chat_stream_")
            or event_type == "ws:analysis_status"
        ]
        ok_start = "ws:chat_stream_start" in recent_types
        ok_end = "ws:chat_stream_end" in recent_types
        completed_count = sum(
            1 for event_type in recent_types if event_type == "ws:analysis_status"
        )
        print(
            f"[probe:F] order-ok(start={ok_start}, end={ok_end}), completed_count={completed_count}"
        )


async def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--id-token", dest="token", default=None)
    ap.add_argument("--run", default="A")
    ap.add_argument("--agent", default="neo")
    ap.add_argument("--text", default=None)
    ap.add_argument("--use-rag", action="store_true")
    ap.add_argument("--timeout", default="120")
    ap.add_argument("--session-id", dest="session_id", default=None)
    args = ap.parse_args()

    probe = Probe(
        args.base, token=args.token, timeout=args.timeout, session_id=args.session_id
    )
    print(f"[probe] using session_id={probe.session_id}")
    run = args.run.upper()

    if run == "A":
        await probe.test_A(args.agent)
    elif run == "B":
        await probe.test_B(args.agent)
    elif run == "C":
        await probe.test_C(args.agent)
    elif run == "D":
        await probe.test_D(args.agent, args.text, args.use_rag)
    elif run == "E":
        await probe.test_E(args.agent, args.text)
    elif run == "F":
        await probe.test_F(args.agent, args.text)
    elif run == "ATOF":
        await probe.test_A(args.agent)
        await probe.test_B(args.agent)
        await probe.test_C(args.agent)
        await probe.test_D(args.agent, args.text, False)
        await probe.test_D(args.agent, args.text, True)
        await probe.test_E("anima", None)
        await probe.test_E("neo", None)
        await probe.test_F(args.agent, None)
    else:
        print(f"Run inconnu: {run}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
