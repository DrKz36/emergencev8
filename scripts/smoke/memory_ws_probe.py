# /scripts/smoke/memory_ws_probe.py
# Minimal WS client (jwt subprotocol) pour piloter le chat et vérifier les signaux.
# CHANGELOG:
# - Supprime 'extra_headers' (incompatible avec ta version de 'websockets')
# - Envoie TOUJOURS le sous-protocole 'jwt' (+ token si dispo)
# - 'origin' conservé (ok avec websockets récents), safe à retirer si besoin

import asyncio, json, uuid, argparse, sys, os, time

try:
    import websockets
    from websockets.exceptions import InvalidStatus
except Exception as e:
    print("⚠️  'websockets' requis. Installe:  python -m pip install websockets")
    raise

def compute_ws_url(base: str) -> str:
    base = base.strip().rstrip("/")
    if base.startswith(("https://","http://")):
        scheme = "wss://" if base.startswith("https://") else "ws://"
        host = base.split("://",1)[1]
        return f"{scheme}{host}/ws/{uuid.uuid4()}"
    if base.startswith(("wss://","ws://")):
        return f"{base.rstrip('/')}/{uuid.uuid4()}"
    return f"ws://{base.strip('/')}/ws/{uuid.uuid4()}"

def compute_origin(base: str) -> str:
    if base.startswith("wss://"): return "https://" + base.split("://",1)[1]
    if base.startswith("ws://"):  return "http://"  + base.split("://",1)[1]
    if base.startswith(("https://","http://")): return base
    return "http://" + base

class Probe:
    def __init__(self, base, token=None, timeout=120):
        self.base = base
        self.ws_url = compute_ws_url(base)
        self.origin = compute_origin(base)
        self.token = token or os.environ.get("EMERGENCE_ID_TOKEN")
        self.timeout = int(timeout)
        self.events = []

    async def _connect(self):
        # Toujours proposer 'jwt'; ajouter le token si dispo (mimique du front). :contentReference[oaicite:2]{index=2}
        subprotocols = ["jwt"] + ([self.token] if self.token else [])
        print(f"[probe] connect → {self.ws_url}  (subprotocols={subprotocols}, origin={self.origin})")
        # NB: PAS d'extra_headers (incompatible sur ta version)
        return await websockets.connect(self.ws_url, subprotocols=subprotocols, origin=self.origin)

    async def _wait_stream_then_completed(self, ws):
        end_seen = False
        completed_seen = False
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
            data = json.loads(raw)
            t = data.get("type")
            p = data.get("payload", {})
            self.events.append((t, p))
            if t in ("ws:chat_stream_start","ws:chat_stream_chunk","ws:chat_stream_end","ws:analysis_status","ws:rag_status","ws:memory_banner"):
                print(f"[evt] {t} :: {p}")
            if t == "ws:chat_stream_end":
                end_seen = True
            if t == "ws:analysis_status" and str(p.get("status","")).lower() == "completed" and end_seen:
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
                        "ts": int(time.time() * 1000)
                    }
                }
                await ws.send(json.dumps(payload))
                ok = await self._wait_stream_then_completed(ws)
                print(f"[probe] stream completed={ok}")
                return ok
        except InvalidStatus as e:
            print(f"[probe][HANDSHAKE] HTTP {getattr(e, 'status_code', '?')} — sous-protocole/token/Origin peut être invalide. Détail: {e}")
            raise
        except Exception as e:
            print(f"[probe][ERROR] {e}")
            raise

    # --- Plans A→F ---
    async def test_A(self, agent):
        await self.run_once(agent, "Aujourd’hui je veux travailler sur la Roadmap V8 et corriger la latence.", use_rag=False)
        await self.run_once(agent, "Tu te rappelles ce que j’ai dit juste avant ?", use_rag=False)

    async def test_B(self, agent):
        await self.run_once(agent, "Le mot-code pour Anima est AURORA-8152. Je travaille depuis Genève.", use_rag=False)
        await self.run_once(agent, "Quel est le mot-code d’Anima ?", use_rag=False)

    async def test_C(self, agent):
        text = "Quel est ton mot-code ?" if agent == "anima" else "Quel est le mot-code d’Anima ?"
        await self.run_once(agent, text, use_rag=False)

    async def test_D(self, agent, text, use_rag):
        await self.run_once(agent, text or "Que contient le document RAG_TEST_A ?", use_rag=use_rag)

    async def test_E(self, agent, text):
        if agent == "anima":
            await self.run_once(agent, text or "Je préfère les réponses courtes.", use_rag=False)
        else:
            await self.run_once(agent, text or "Quelle longueur de réponse je préfère ?", use_rag=False)

    async def test_F(self, agent, text):
        before = len(self.events)
        await self.run_once(agent, text or "Ping test signaux.", use_rag=False)
        seq = [t for (t, _) in self.events[before:] if t.startswith("ws:chat_stream_") or t == "ws:analysis_status"]
        ok_start = "ws:chat_stream_start" in seq
        ok_end = "ws:chat_stream_end" in seq
        completed_count = sum(1 for t in seq if t == "ws:analysis_status")
        print(f"[probe:F] order-ok(start={ok_start}, end={ok_end}), completed_count={completed_count}")

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
    args = ap.parse_args()

    p = Probe(args.base, token=args.token, timeout=args.timeout)
    run = args.run.upper()

    if run == "A":   await p.test_A(args.agent)
    elif run == "B": await p.test_B(args.agent)
    elif run == "C": await p.test_C(args.agent)
    elif run == "D": await p.test_D(args.agent, args.text, args.use_rag)
    elif run == "E": await p.test_E(args.agent, args.text)
    elif run == "F": await p.test_F(args.agent, args.text)
    elif run == "ATOF":
        await p.test_A(args.agent); await p.test_B(args.agent); await p.test_C(args.agent)
        await p.test_D(args.agent, args.text, False); await p.test_D(args.agent, args.text, True)
        await p.test_E("anima", None); await p.test_E("neo", None); await p.test_F(args.agent, None)
    else:
        print(f"Run inconnu: {run}"); sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())
