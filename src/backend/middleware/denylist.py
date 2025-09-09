# -*- coding: utf-8 -*-
"""
DenylistMiddleware — bloque l’accès aux chemins sensibles avant tout fallback.
Raison: empêcher l’exposition de /.git/* (doit retourner 403, cf. mémo v5).
"""

import re
from typing import Callable, Awaitable
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.responses import PlainTextResponse

_DENY_PATTERNS = [
    re.compile(r"^/\.git(?:/|$)"),
]

class DenylistMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        for pat in _DENY_PATTERNS:
            if pat.match(path):
                resp = PlainTextResponse("Forbidden", status_code=403)
                return await resp(scope, receive, send)

        return await self.app(scope, receive, send)
