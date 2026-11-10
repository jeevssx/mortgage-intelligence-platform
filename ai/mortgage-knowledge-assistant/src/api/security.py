"""Optional M6 JWT check. If JWT_SECRET is unset, every request is allowed (local-only use).

If set, it must be the SAME shared secret as mortgage-service/servicing-service — this service
only validates, it never issues tokens (see docs/security/security-controls.md).
"""

from __future__ import annotations

import jwt
from fastapi import Request

from src.config import Settings
from src.utils.errors import UnauthorizedError

_ALGORITHM = "HS256"


def require_auth(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if not settings.jwt_secret:
        return  # Auth not configured — local/dev use only, documented in README.

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Bearer token")
    token = header[len("Bearer ") :]
    try:
        jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Missing or invalid Bearer token") from exc
