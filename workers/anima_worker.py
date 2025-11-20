"""
Anima Worker - Cloud Run Service (Pub/Sub Push subscriber)
Agent Anthropic Claude exécuté de manière asynchrone
"""

import logging
import json
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Header
from anthropic import AsyncAnthropic
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.core.database.manager_postgres import PostgreSQLManager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Anima Worker", version="1.0.0")

# Database manager (PostgreSQL)
db = PostgreSQLManager(
    host=os.getenv("CLOUD_SQL_HOST"),
    unix_socket=os.getenv("CLOUD_SQL_UNIX_SOCKET"),  # Cloud SQL Proxy
    database=os.getenv("CLOUD_SQL_DATABASE", "emergence"),
    user=os.getenv("CLOUD_SQL_USER", "emergence-app"),
    password=os.getenv("DB_PASSWORD"),
    min_size=1,
    max_size=5,
)

# Anthropic client
anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@app.on_event("startup")
async def startup():
    """Connect to database on startup"""
    logger.info("Anima Worker starting up...")
    await db.connect()
    logger.info(f"Connected to PostgreSQL: {await db.get_version()}")


@app.on_event("shutdown")
async def shutdown():
    """Disconnect from database on shutdown"""
    logger.info("Anima Worker shutting down...")
    await db.disconnect()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "worker": "anima", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check with DB status"""
    db_healthy = await db.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "ok" if db_healthy else "error",
        "worker": "anima",
    }


@app.post("/process")
async def process_message(
    request: Request, authorization: Optional[str] = Header(None)
):
    """
    Endpoint appelé par Pub/Sub (push subscription).

    Payload Pub/Sub:
    {
        "message": {
            "data": "<base64_encoded_json>",
            "messageId": "...",
            "publishTime": "..."
        },
        "subscription": "..."
    }
    """
    # Vérifier authentification Pub/Sub (OIDC token)
    # Note: En prod, vérifier le token JWT avec service account

    try:
        # Parse Pub/Sub message
        body = await request.json()
        message = body.get("message", {})

        # Decode base64 data
        import base64

        data_b64 = message.get("data", "")
        data_json = base64.b64decode(data_b64).decode("utf-8")
        task_data = json.loads(data_json)

        logger.info(f"Received task: message_id={task_data.get('message_id')}")

        # Process task
        result = await process_agent_task(task_data)

        # Acknowledge message (return 200)
        return {
            "status": "processed",
            "message_id": task_data.get("message_id"),
            "result_id": result.get("result_id"),
        }

    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        # Return 200 pour éviter retry infini (message va en DLQ après max attempts)
        raise HTTPException(status_code=500, detail=str(e))


async def process_agent_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite tâche agent Anima.

    Task data structure:
    {
        "message_id": "uuid",
        "session_id": "uuid",
        "user_id": "email",
        "messages": [{"role": "user", "content": "..."}],
        "model": "claude-3-haiku",
        "max_tokens": 1024,
        "temperature": 0.7,
        "system_prompt": "...",
        "metadata": {...}
    }
    """
    message_id = task_data.get("message_id")
    session_id = task_data.get("session_id")
    user_id = task_data.get("user_id")
    messages = task_data.get("messages", [])
    model = task_data.get("model", "claude-3-haiku-20240307")
    max_tokens = task_data.get("max_tokens", 1024)
    temperature = task_data.get("temperature", 0.7)
    system_prompt = task_data.get("system_prompt", "")

    logger.info(f"Processing Anima task: message_id={message_id}, model={model}")

    try:
        # Call Anthropic API
        response = await anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt if system_prompt else None,
            messages=messages,
        )

        # Extract response
        assistant_text = response.content[0].text
        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens

        # Calculate cost (prix Claude Haiku au 2025)
        cost_usd = calculate_cost(model, tokens_input, tokens_output)

        # Store response in database
        result_id = await store_agent_response(
            message_id=message_id,
            session_id=session_id,
            user_id=user_id,
            agent_id="anima",
            provider="anthropic",
            model=model,
            content=assistant_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            metadata=task_data.get("metadata", {}),
        )

        logger.info(
            f"Anima response stored: result_id={result_id}, cost=${cost_usd:.4f}"
        )

        # TODO: Notify orchestrator via callback (WebSocket ou autre mécanisme)
        await notify_orchestrator(session_id, result_id, assistant_text)

        return {
            "result_id": result_id,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        logger.error(f"Anima API call failed: {e}", exc_info=True)
        # Store error in database
        await store_agent_error(message_id, session_id, str(e))
        raise


def calculate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    """
    Calcule coût Anthropic (prix 2025).

    Tarifs Claude Haiku (exemple):
    - Input: $0.25 / 1M tokens
    - Output: $1.25 / 1M tokens
    """
    # Prix par modèle (USD par 1M tokens)
    PRICING = {
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    }

    prices = PRICING.get(model, PRICING["claude-3-haiku-20240307"])
    cost_input = (tokens_input / 1_000_000) * prices["input"]
    cost_output = (tokens_output / 1_000_000) * prices["output"]

    return cost_input + cost_output


async def store_agent_response(
    message_id: str,
    session_id: str,
    user_id: str,
    agent_id: str,
    provider: str,
    model: str,
    content: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    metadata: Dict[str, Any],
) -> str:
    """Stocke réponse agent dans PostgreSQL"""
    # Insert message
    query_message = """
    INSERT INTO messages (session_id, role, content, agent_id, model, provider, tokens_input, tokens_output, cost_usd, metadata)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    RETURNING id
    """

    result_id = await db.fetch_val(
        query_message,
        session_id,
        "assistant",
        content,
        agent_id,
        model,
        provider,
        tokens_input,
        tokens_output,
        cost_usd,
        json.dumps(metadata),
    )

    # Insert cost tracking
    query_cost = """
    INSERT INTO costs (user_id, session_id, message_id, agent_id, provider, model, tokens_input, tokens_output, cost_usd)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """

    await db.execute(
        query_cost,
        user_id,
        session_id,
        str(result_id),
        agent_id,
        provider,
        model,
        tokens_input,
        tokens_output,
        cost_usd,
    )

    return str(result_id)


async def store_agent_error(message_id: str, session_id: str, error: str):
    """Stocke erreur agent"""
    query = """
    INSERT INTO messages (session_id, role, content, agent_id, metadata)
    VALUES ($1, $2, $3, $4, $5)
    """

    await db.execute(
        query,
        session_id,
        "error",
        f"Agent error: {error}",
        "anima",
        json.dumps({"error": error, "original_message_id": message_id}),
    )


async def notify_orchestrator(session_id: str, result_id: str, content: str):
    """
    Notifie orchestrator que la réponse est prête.

    Options:
    1. WebSocket direct (si orchestrator maintient connexions)
    2. Pub/Sub reverse (topic pour orchestrator)
    3. Redis Pub/Sub
    4. Polling par orchestrator

    Pour l'instant: log uniquement (orchestrator poll la DB)
    """
    logger.info(f"Response ready for session {session_id}: result_id={result_id}")
    # TODO: Implémenter notification réelle


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
