# Multi-stage build pour Chat/LLM Service
# Optimisé pour OpenAI, Anthropic, Google Generative AI + RAG + Memory

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY infra/cloud-run/chat-requirements.txt .
RUN pip install --no-cache-dir --user -r chat-requirements.txt

# ======= Production Stage =======
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create data directories
RUN mkdir -p /app/data /app/data/chroma

# Copy application code
COPY src/backend /app/backend
COPY src/shared /app/shared
COPY prompts /app/prompts

# Copy only Chat Service specific modules
# - features/chat (main service)
# - features/memory (vector, gardener, concept_recall, proactive_hints)
# - features/debate (optional, used by chat service)
# - core (session_manager, cost_tracker, websocket, database, config)
# - shared (models, config, dependencies)

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/api/health', timeout=5)"

# Run Chat Service
# Note: Utilise le même point d'entrée que l'app principale,
# mais seuls les endpoints /api/chat/* et /ws/chat/* sont exposés
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
