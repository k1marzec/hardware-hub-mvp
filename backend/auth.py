"""Real, cryptographically-signed session tokens + role-based access control
dependencies for FastAPI endpoints.

This replaces the previous placeholder ("mock-token-{email}") which was not
a real token at all - just a predictable, unsigned string that nothing ever
verified server-side. Every admin-only and self-scoped endpoint in main.py
now depends on `get_current_user` / `require_admin` from this module, so a
request without a valid, signed token (or a non-admin token hitting an
admin-only route) is rejected before any handler code runs.
"""

import os
import secrets

from fastapi import Depends, Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

import models
from database import get_db

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    # Dev-friendly fallback so `uvicorn main:app --reload` still boots with
    # zero setup - but a random key means every process restart invalidates
    # every existing session (everyone gets logged out), and this must NEVER
    # be relied on in production. Set SESSION_SECRET_KEY in backend/.env
    # (any long random string) to get stable, persistent sessions.
    SESSION_SECRET_KEY = secrets.token_hex(32)
    print(
        "[auth] WARNING: SESSION_SECRET_KEY is not set in backend/.env - using "
        "a random, in-memory-only key for this process. All logins will be "
        "invalidated on the next restart. Set SESSION_SECRET_KEY for stable, "
        "production-ready sessions."
    )

_serializer = URLSafeTimedSerializer(SESSION_SECRET_KEY, salt="hardware-hub-session")
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours


def create_session_token(user_id: int) -> str:
    """Issues a signed, tamper-proof session token for the given user id.

    Unlike the old `f"mock-token-{email}"` placeholder, this cannot be
    forged or predicted without knowing SESSION_SECRET_KEY: `itsdangerous`
    HMAC-signs the payload, so any modification (e.g. changing the user id
    to impersonate someone else) invalidates the signature.
    """
    return _serializer.dumps({"uid": user_id})


def get_current_user(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> models.User:
    """Resolves the caller's `User` row from a signed `Authorization: Bearer
    <token>` header.

    Raises 401 if the header is missing/malformed, the signature is
    invalid or expired, or the token no longer maps to a real user (e.g.
    the account was deleted after the token was issued).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    try:
        data = _serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user = db.query(models.User).filter(models.User.id == data.get("uid")).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency for admin-only endpoints.

    403s an authenticated-but-non-admin user (as opposed to 401, which
    means "not logged in / invalid token at all") - the caller is a known,
    valid user, just not authorized for this specific action.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
