"""IP thật sau proxy, HTTPS, nhãn thiết bị, cookie (docs/auth.md §3.2, §3.7).

`client_ip`: uvicorn chạy với `--no-proxy-headers`. Peer TCP là 127.0.0.1/::1 (Vite trên chính Mac) và
có `X-Forwarded-For` thì lấy phần tử CUỐI (phần Vite vừa nối vào, là địa chỉ thật của kết nối tới Vite);
không thì lấy peer. Client tự gửi `X-Forwarded-For` chỉ đổi được các phần tử phía trước.
"""
from __future__ import annotations

import hashlib
import re

from starlette.requests import Request

from lyris.config import Settings

SESSION_COOKIE = "lyris_session"
DEVICE_COOKIE = "lyris_device"
SECURE_PREFIX = "__Host-"
DEVICE_MAX_AGE = 365 * 24 * 3600
_LOOPBACK = {"127.0.0.1", "::1"}
_TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_\-]{20,100}$")


def _bare(ip: str) -> str:
    ip = ip.strip()
    if ip.lower().startswith("::ffff:") and "." in ip:
        return ip[7:]
    return ip


def peer_ip(request: Request) -> str:
    return _bare(request.client.host) if request.client and request.client.host else ""


def _last_forwarded(request: Request, header: str) -> str | None:
    values = request.headers.getlist(header)
    if not values:
        return None
    parts = [p.strip() for p in ",".join(values).split(",")]
    last = parts[-1] if parts else ""
    return last or None


def client_ip(request: Request) -> str:
    """IP dùng cho giới hạn thử sai và ghi log (§3.7)."""
    peer = peer_ip(request)
    if peer in _LOOPBACK:
        forwarded = _last_forwarded(request, "x-forwarded-for")
        if forwarded:
            return _bare(forwarded)[:64]
    return peer[:64]


def request_is_secure(request: Request) -> bool:
    """Cookie có `Secure` (và tên `__Host-`) không.

    Có khi: `LYRIS_COOKIE_SECURE=1`; request tới thẳng uvicorn bằng HTTPS; hoặc peer là 127.0.0.1 và phần tử
    CUỐI của `X-Forwarded-Proto` là `https`. Không đọc phần tử đầu: điện thoại trên Wi-Fi tự gửi được
    `X-Forwarded-Proto: https`, Vite nối `http` vào sau.
    """
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if settings is not None and settings.cookie_secure:
        return True
    if request.url.scheme == "https":
        return True
    if peer_ip(request) in _LOOPBACK:
        return (_last_forwarded(request, "x-forwarded-proto") or "").lower() == "https"
    return False


def cookie_name(base: str, secure: bool) -> str:
    return SECURE_PREFIX + base if secure else base


def read_cookie(request: Request, base: str) -> tuple[str, str] | None:
    """(tên cookie, giá trị) của cookie `base` hoặc `__Host-base`; giá trị sai dạng coi như không có."""
    for name in (SECURE_PREFIX + base, base):
        value = request.cookies.get(name)
        if value and _TOKEN_SHAPE.fullmatch(value):
            return name, value
    return None


def cookie_names_present(request: Request, base: str) -> list[str]:
    return [name for name in (SECURE_PREFIX + base, base) if name in request.cookies]


def set_cookie_header(name: str, value: str, *, max_age: int, secure: bool) -> str:
    """Giá trị header `Set-Cookie` (HttpOnly, SameSite=Lax, Path=/, không Domain)."""
    parts = [f"{name}={value}", "Path=/", f"Max-Age={max(0, int(max_age))}", "HttpOnly", "SameSite=Lax"]
    if secure or name.startswith(SECURE_PREFIX):
        parts.append("Secure")
    return "; ".join(parts)


def clear_cookie_header(name: str) -> str:
    return set_cookie_header(name, "", max_age=0, secure=name.startswith(SECURE_PREFIX))


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


_BROWSERS = (
    ("Edg/", "Edge"),
    ("EdgiOS", "Edge"),
    ("OPR/", "Opera"),
    ("FxiOS", "Firefox"),
    ("Firefox/", "Firefox"),
    ("CriOS", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)
_SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Macintosh", "Mac"),
    ("Mac OS X", "Mac"),
    ("Windows", "Windows"),
    ("CrOS", "ChromeOS"),
    ("Linux", "Linux"),
)


def device_label(user_agent: str | None) -> str:
    """"Safari · iPhone" rút gọn từ User-Agent, tối đa 60 ký tự; không nhận ra thì rỗng."""
    ua = user_agent or ""
    browser = next((name for key, name in _BROWSERS if key in ua), "")
    system = next((name for key, name in _SYSTEMS if key in ua), "")
    label = " · ".join(x for x in (browser, system) if x)
    return label[:60]


__all__ = [
    "DEVICE_COOKIE",
    "DEVICE_MAX_AGE",
    "SESSION_COOKIE",
    "clear_cookie_header",
    "client_ip",
    "cookie_name",
    "cookie_names_present",
    "device_label",
    "peer_ip",
    "read_cookie",
    "request_is_secure",
    "set_cookie_header",
    "token_hash",
]
