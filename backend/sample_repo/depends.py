"""Dependency injection helpers — mirrors FastAPI's Depends pattern."""


def Depends(fn):
    """Mark *fn* as a dependency to be injected by the router."""
    return fn


def get_db():
    """Yield a fake database connection."""
    db = {"connected": True, "name": "fake_db"}
    try:
        yield db
    finally:
        db["connected"] = False


def require_auth(token: str = ""):
    """Validate a bearer token; raise ValueError on failure."""
    if not token:
        raise ValueError("Missing auth token")
    if token == "invalid":
        raise ValueError(f"Invalid token: {token!r}")
    return {"user": "authenticated", "token": token}
