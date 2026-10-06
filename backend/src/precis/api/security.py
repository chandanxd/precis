"""
JWT authentication, input sanitization, prompt injection detection, and rate limiting.
"""

import html
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import ClassVar

import jwt
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

# Development fallback; production deployments must provide PRECIS_SECRET.
SECRET_KEY = os.getenv("PRECIS_SECRET", "precis-local-dev-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

security_scheme = HTTPBearer(auto_error=False)

# Maximum input lengths
MAX_DOCUMENT_LENGTH = 100_000  # 100K characters
MAX_QUERY_LENGTH = 2_000  # 2K characters

# Prompt injection patterns (basic detection)
_INJECTION_PATTERNS = [
    r"(ignore|disregard)\s+(all\s+)?(previous|above)?\s*instructions?",
    r"disregard\s+(all\s+)?above",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",
    r"<\s*script",
]

_injection_regex = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def generate_token(subject: str = "local_user") -> str:
    """Generate a JWT token for API access."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def validate_token(token: str) -> dict:
    """Validate a JWT token. Returns the payload or raises HTTPException(401)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT on protected routes."""

    # Routes that don't require authentication
    PUBLIC_ROUTES: ClassVar[set[str]] = {
        "/api/health",
        "/api/auth/token",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public routes and WebSocket
        if path in self.PUBLIC_ROUTES or path.startswith("/ws"):
            return await call_next(request)

        # Allow OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            validate_token(token)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        return await call_next(request)


def sanitize_text(text: str, max_length: int) -> str:
    """
    Sanitize input text:
    1. Strip HTML tags
    2. Unescape HTML entities
    3. Normalize whitespace
    4. Enforce length limit
    """
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Enforce length
    if len(text) > max_length:
        raise ValueError(
            f"Input exceeds the maximum length of {max_length} characters."
        )
    return text


def sanitize_document(text: str) -> str:
    """Sanitize document text for ingestion."""
    return sanitize_text(text, MAX_DOCUMENT_LENGTH)


def sanitize_query(query: str) -> str:
    """Sanitize query text."""
    return sanitize_text(query, MAX_QUERY_LENGTH)


def check_injection(text: str) -> bool:
    """Check if text contains prompt injection patterns. Returns True if suspicious."""
    if not text:
        return False
    return bool(_injection_regex.search(text))


class RateLimiter:
    """Simple in-memory thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if the client is within rate limits."""
        now = time.time()
        with self._lock:
            # Clean old entries for current client
            active = [
                t for t in self._requests[client_id] if now - t < self.window
            ]
            if len(active) >= self.max_requests:
                self._requests[client_id] = active
                return False

            active.append(now)
            self._requests[client_id] = active

            # Prevent unbounded memory growth by pruning stale client entries
            if len(self._requests) > 100:
                dead_clients = [
                    cid
                    for cid, timestamps in self._requests.items()
                    if not timestamps or now - timestamps[-1] >= self.window
                ]
                for cid in dead_clients:
                    del self._requests[cid]

            return True

    def remaining(self, client_id: str) -> int:
        """Return remaining requests in current window."""
        now = time.time()
        with self._lock:
            recent = [t for t in self._requests[client_id] if now - t < self.window]
            return max(0, self.max_requests - len(recent))


# Global rate limiter for query endpoint
query_limiter = RateLimiter(max_requests=10, window_seconds=60)
