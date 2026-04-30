"""Shared FastAPI dependencies."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Cookie, Header, HTTPException, status

COOKIE_NAME = "tc_session"


def api_token_auth(*, token_hash: str):
    """Build a dependency that compares either Authorization: Bearer <token>
    or Cookie tc_session=<token> against a sha256 hash. Header takes precedence."""

    expected = token_hash.lower()

    def _verify(token: str) -> bool:
        got = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(got, expected)

    def _dep(
        authorization: str | None = Header(default=None),
        tc_session: str | None = Cookie(default=None),
    ) -> None:
        if authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):]
            if _verify(token):
                return
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        if tc_session and _verify(tc_session):
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid credentials")

    return _dep
