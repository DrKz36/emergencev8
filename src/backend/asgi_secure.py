from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp
import re

from backend.main import app as fastapi_app  # ne modifie pas backend.main

DENY_PATTERNS = [
    re.compile(r"^/\.git(?:/|$)", re.IGNORECASE),
    re.compile(r"^/\.env(?:$|\.|/)", re.IGNORECASE),
    re.compile(r"^/\.dockerignore$", re.IGNORECASE),
    re.compile(r"^/Dockerfile$", re.IGNORECASE),
    re.compile(r"^/secrets?(?:$|/)", re.IGNORECASE),
    re.compile(r"^/config(?:$|/|\.)", re.IGNORECASE),
]

class DenySensitiveMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        for pat in DENY_PATTERNS:
            if pat.search(path):
                return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)

fastapi_app.add_middleware(DenySensitiveMiddleware)
app: ASGIApp = fastapi_app
