"""Middleware ASGI cho `/api` (docs/auth.md §3.2, §3.3).

1. Chặn CSRF cho mọi method ghi (khác GET/HEAD/OPTIONS): bắt buộc `X-Lyris: 1`; có `Origin` thì host:port
   phải bằng header `Host`; `Sec-Fetch-Site: cross-site` thì từ chối. Sai: 403 `code = "csrf"`.
2. Response chưa tự đặt `Cache-Control` thì thêm `no-store` (JSON của `/api`, kể cả `auth/me`).
3. Gửi các `Set-Cookie` mà dependency/route đã hẹn trong `request.state` (gia hạn phiên, xoá cookie khi
   phiên hết hạn) — kể cả khi route trả `FileResponse`/stream, hay khi dependency raise lỗi.

ASGI thuần (không `BaseHTTPMiddleware`) để không đụng tới stream SSE.
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders

from lyris.auth import errors

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
COOKIE_STATE_KEY = "lyris_set_cookies"
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _host_port(netloc: str, scheme: str) -> tuple[str, int | None] | None:
    try:
        parts = urlsplit(f"//{netloc}")
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if not host:
        return None
    return host, port if port is not None else _DEFAULT_PORTS.get(scheme)


def same_origin(origin: str, host_header: str) -> bool:
    """host:port của `Origin` bằng header `Host` (cổng mặc định theo scheme của Origin)."""
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    scheme = parsed.scheme.lower()
    if scheme not in _DEFAULT_PORTS or not parsed.netloc:
        return False
    a = _host_port(parsed.netloc, scheme)
    b = _host_port(host_header, scheme)
    return a is not None and a == b


def csrf_ok(method: str, headers: Headers) -> bool:
    if method.upper() in SAFE_METHODS:
        return True
    if headers.get("x-lyris") != "1":
        return False
    origin = headers.get("origin")
    if origin is not None and not same_origin(origin, headers.get("host", "")):
        return False
    return headers.get("sec-fetch-site", "").lower() != "cross-site"


class AuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not str(scope.get("path", "")).startswith("/api"):
            await self.app(scope, receive, send)
            return
        if not csrf_ok(str(scope.get("method", "GET")), Headers(scope=scope)):
            error = errors.AuthError(403, errors.CSRF, "csrf")
            body = json.dumps(error.payload(), ensure_ascii=False).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        state = scope.setdefault("state", {})

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if "cache-control" not in headers:
                    headers["Cache-Control"] = "no-store"
                for value in state.get(COOKIE_STATE_KEY, ()):
                    headers.append("set-cookie", value)
            await send(message)

        await self.app(scope, receive, send_wrapper)


__all__ = ["COOKIE_STATE_KEY", "AuthMiddleware", "csrf_ok", "same_origin"]
