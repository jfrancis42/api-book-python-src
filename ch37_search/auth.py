"""Authentication dependency (Chapter 32)."""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

# In production, load from database. Token -> username.
VALID_TOKENS: dict[str, str] = {
    "test-token-octocat": "octocat",
    "test-token-hubot": "hubot",
}


def get_current_user(authorization: str | None = Security(API_KEY_HEADER)) -> str:
    """Require a valid Bearer token. Returns the authenticated username."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    username = VALID_TOKENS.get(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def get_optional_user(authorization: str | None = Security(API_KEY_HEADER)) -> str | None:
    """Return the authenticated username, or None if unauthenticated."""
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return VALID_TOKENS.get(token)
