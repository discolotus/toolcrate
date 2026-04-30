"""Shared FastAPI dependencies."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Header, HTTPException, status


def api_token_auth(*, token_hash: str):
    """Build a dependency that compares Authorization: Bearer <token> against a sha256 hash."""

    expected = token_hash.lower()

    def _dep(authorization: str | None = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        token = authorization[len("Bearer "):]
        got = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(got, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    return _dep
