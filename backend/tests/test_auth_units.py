"""Phase 4b (docs/auth.md §1.3, §3.1, §3.3, §3.7): hàm thuần của lyris.auth — mã, mật khẩu (scrypt thật),
IP thật sau proxy, so Origin/Host, nhãn thiết bị, cookie."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from lyris.auth import codes, passwords
from lyris.auth.middleware import csrf_ok, same_origin
from lyris.auth.net import clear_cookie_header, client_ip, device_label, request_is_secure, set_cookie_header
from lyris.config import REPO_ROOT

CASES_FILE = REPO_ROOT / "frontend" / "src" / "lib" / "inviteCode.cases.json"


# ---------------------------------------------------------------------------- mã


def test_shared_code_cases() -> None:
    """Cùng bảng ca thử với frontend (lib/inviteCode)."""
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 10
    for case in cases:
        assert codes.normalize_code(case["input"]) == case["expected"], case


def test_random_codes() -> None:
    seen = {codes.random_code() for _ in range(200)}
    assert len(seen) == 200
    for code in seen:
        assert len(code) == 12 and set(code) <= set(codes.CROCKFORD)
        assert not set(code) & set("ILOU")
        assert codes.normalize_code(codes.format_invite(code)) == code
        assert codes.normalize_code(codes.group(code)) == code
    assert codes.format_invite("7KQ2M9XD4TPA") == "LYR-7KQ2-M9XD-4TPA"
    assert codes.code_hint("7KQ2M9XD4TPA") == "4TPA"
    assert len(codes.code_hash("7KQ2M9XD4TPA")) == 32


def test_temporary_password_shape() -> None:
    for _ in range(50):
        temp = codes.temporary_password()
        groups = temp.split("-")
        assert len(groups) == 3 and all(len(g) == 4 for g in groups)
        assert set(temp.replace("-", "")) <= set(codes.TEMP_ALPHABET)
        assert not set(temp) & set("0o1liI")
        passwords.check_rules(temp, handle="mai")  # mật khẩu tạm qua được luật thường


# ---------------------------------------------------------------------------- mật khẩu


@pytest.mark.parametrize(
    ("password", "handle", "message"),
    [
        ("ngắn", None, passwords.TOO_SHORT),
        ("x" * 129, None, passwords.TOO_LONG),
        ("12345678", None, passwords.TOO_COMMON),
        ("MatKhau123", None, passwords.TOO_COMMON),
        ("anhyeuem", None, passwords.TOO_COMMON),
        ("hoa_mai.2026", "hoa_mai.2026", passwords.SAME_AS_HANDLE),
        ("@Hoa_Mai.2026", "hoa_mai.2026", passwords.SAME_AS_HANDLE),
    ],
)
def test_password_rules(password: str, handle: str | None, message: str) -> None:
    with pytest.raises(passwords.PasswordRuleError) as err:
        passwords.check_rules(password, handle=handle)
    assert str(err.value) == message
    assert password not in str(err.value) or password == "ngắn"


def test_password_rules_accept_unicode_and_spaces() -> None:
    nfd = unicodedata.normalize("NFD", "  trăng  sáng  ")
    value = passwords.check_rules(nfd, handle="ban")
    assert value == unicodedata.normalize("NFC", nfd)  # NFC, không cắt khoảng trắng
    assert passwords.check_rules("a" * 128, handle=None) == "a" * 128
    with pytest.raises(passwords.PasswordRuleError, match="khác mật khẩu cũ"):
        passwords.check_rules("mật khẩu mới", handle=None, current=unicodedata.normalize("NFD", "mật khẩu mới"))


def test_common_password_list_size() -> None:
    common = passwords.common_passwords()
    assert 180 <= len(common) <= 260
    assert {"matkhau123", "anhyeuem", "12345678"} <= common


def test_real_scrypt_hash_and_verify() -> None:
    hashed = passwords.hash_password_sync(unicodedata.normalize("NFD", "Mật khẩu"))
    assert (hashed.n, hashed.r, hashed.p) == (2**17, 8, 1) and hashed.current_params()
    assert len(hashed.salt) == 16 and len(hashed.digest) == 32
    assert passwords.verify_password_sync(unicodedata.normalize("NFC", "Mật khẩu"), hashed)
    assert not passwords.verify_password_sync("Mật khẩu ", hashed)
    assert not passwords.verify_password_sync("Mật khẩu", None)
    other = passwords.hash_password_sync("Mật khẩu")
    assert other.salt != hashed.salt and other.digest != hashed.digest
    old = passwords.hash_password_sync("Mật khẩu", n=2**14)
    assert not old.current_params() and passwords.verify_password_sync("Mật khẩu", old)


def test_verify_without_account_still_hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(passwords, "_scrypt", lambda pw, salt, n, r, p: calls.append(n) or b"\0" * 32)
    assert passwords.verify_password_sync("gì cũng được", None) is False  # digest giả toàn 0 vẫn không khớp
    assert calls == [passwords.SCRYPT_N]


async def test_hashing_runs_off_the_event_loop() -> None:
    import threading

    seen: list[str] = []
    original = passwords._scrypt

    def spy(*args: Any) -> bytes:
        seen.append(threading.current_thread().name)
        return original(*args)

    passwords._scrypt = spy  # type: ignore[assignment]
    try:
        hashed = await passwords.hash_password("một mật khẩu dài")
        assert await passwords.verify_password("một mật khẩu dài", hashed)
    finally:
        passwords._scrypt = original  # type: ignore[assignment]
    assert seen and all(name != threading.main_thread().name for name in seen)


# ---------------------------------------------------------------------------- IP, HTTPS


class _App:
    class state:  # noqa: N801
        settings = None


def make_request(peer: str | None, headers: dict[str, str] | list[tuple[str, str]] | None = None, scheme: str = "http") -> Request:
    items = headers.items() if isinstance(headers, dict) else (headers or [])
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/x",
        "scheme": scheme,
        "headers": [(k.lower().encode(), v.encode()) for k, v in items],
        "client": (peer, 1234) if peer else None,
        "server": ("test", 80),
        "app": _App,
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.parametrize(
    ("peer", "xff", "expected"),
    [
        ("127.0.0.1", "1.2.3.4,192.168.1.9", "192.168.1.9"),
        ("127.0.0.1", "1.2.3.4, 127.0.0.1", "127.0.0.1"),  # không phải 1.2.3.4
        ("127.0.0.1", "127.0.0.1,127.0.0.1", "127.0.0.1"),
        ("127.0.0.1", "::ffff:192.168.1.7", "192.168.1.7"),
        ("::1", "10.0.0.5", "10.0.0.5"),
        ("::ffff:127.0.0.1", "10.0.0.6", "10.0.0.6"),
        ("127.0.0.1", None, "127.0.0.1"),
        ("127.0.0.1", "", "127.0.0.1"),
        ("192.168.1.20", "1.2.3.4", "192.168.1.20"),  # peer không phải 127.0.0.1: bỏ qua header
        ("192.168.1.20", "127.0.0.1", "192.168.1.20"),
        ("::ffff:192.168.1.21", None, "192.168.1.21"),
    ],
)
def test_client_ip(peer: str, xff: str | None, expected: str) -> None:
    headers = {"X-Forwarded-For": xff} if xff is not None else {}
    assert client_ip(make_request(peer, headers)) == expected


def test_client_ip_uses_last_of_repeated_headers() -> None:
    req = make_request("127.0.0.1", [("X-Forwarded-For", "1.1.1.1"), ("X-Forwarded-For", "2.2.2.2, 192.168.1.4")])
    assert client_ip(req) == "192.168.1.4"


@pytest.mark.parametrize(
    ("peer", "proto", "scheme", "secure"),
    [
        ("127.0.0.1", "https", "http", True),
        ("127.0.0.1", "https,http", "http", False),  # phần tử đầu do client tự gửi
        ("127.0.0.1", "http,https", "http", True),
        ("192.168.1.20", "https", "http", False),
        ("127.0.0.1", None, "https", True),
        ("127.0.0.1", None, "http", False),
    ],
)
def test_request_is_secure(peer: str, proto: str | None, scheme: str, secure: bool) -> None:
    headers = {"X-Forwarded-Proto": proto} if proto else {}
    assert request_is_secure(make_request(peer, headers, scheme)) is secure


# ---------------------------------------------------------------------------- CSRF


@pytest.mark.parametrize(
    ("origin", "host", "ok"),
    [
        ("http://localhost:5173", "localhost:5173", True),
        ("http://LOCALHOST:5173", "localhost:5173", True),
        ("http://192.168.1.5:5173", "192.168.1.5:5173", True),
        ("http://192.168.1.5:8080", "192.168.1.5:5173", False),
        ("http://example.com", "example.com:80", True),
        ("https://mac.tail1234.ts.net", "mac.tail1234.ts.net", True),
        ("https://mac.tail1234.ts.net", "mac.tail1234.ts.net:80", False),
        ("http://[::1]:5173", "[::1]:5173", True),
        ("null", "localhost:5173", False),
        ("file://", "localhost:5173", False),
        ("http://evil.example", "localhost:5173", False),
    ],
)
def test_same_origin(origin: str, host: str, ok: bool) -> None:
    assert same_origin(origin, host) is ok


def test_csrf_ok_rules() -> None:
    def h(**kw: str) -> Headers:
        return Headers({k.replace("_", "-"): v for k, v in kw.items()})

    assert csrf_ok("GET", h())
    assert csrf_ok("HEAD", h()) and csrf_ok("OPTIONS", h())
    assert not csrf_ok("POST", h(host="test"))
    assert csrf_ok("POST", h(host="test", x_lyris="1"))
    assert not csrf_ok("DELETE", h(host="test", x_lyris="true"))
    assert not csrf_ok("PUT", h(host="test", x_lyris="1", origin="http://other"))
    assert not csrf_ok("PATCH", h(host="test", x_lyris="1", sec_fetch_site="cross-site"))
    assert csrf_ok("PATCH", h(host="test", x_lyris="1", sec_fetch_site="same-site"))


# ---------------------------------------------------------------------------- cookie, thiết bị


def test_cookie_headers() -> None:
    assert set_cookie_header("lyris_session", "abc", max_age=60, secure=False) == (
        "lyris_session=abc; Path=/; Max-Age=60; HttpOnly; SameSite=Lax"
    )
    assert set_cookie_header("__Host-lyris_session", "abc", max_age=60, secure=True).endswith("; Secure")
    assert clear_cookie_header("__Host-lyris_device") == "__Host-lyris_device=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"


@pytest.mark.parametrize(
    ("ua", "label"),
    [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1", "Safari · iPhone"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0 Safari/537.36", "Chrome · Mac"),
        ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) CriOS/120 Mobile Safari/604.1", "Chrome · iPad"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36 Edg/130.0", "Edge · Windows"),
        ("Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0", "Firefox · Linux"),
        ("Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile Safari/537.36", "Chrome · Android"),
        ("curl/8.0", ""),
        (None, ""),
    ],
)
def test_device_label(ua: str | None, label: str) -> None:
    assert device_label(ua) == label


def test_no_extra_dependencies() -> None:
    """§0: không cài thêm thư viện băm mật khẩu."""
    source = "\n".join(p.read_text(encoding="utf-8") for p in (Path(passwords.__file__).parent).glob("*.py"))
    for name in ("argon2", "bcrypt", "passlib", "itsdangerous"):
        assert f"import {name}" not in source
