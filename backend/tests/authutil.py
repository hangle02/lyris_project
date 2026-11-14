"""Phase 4b: tiện ích đăng nhập cho test (docs/auth.md §8.1).

Mọi `/api` (trừ 4 route mở của `/api/auth`) cần đăng nhập, và mọi request ghi cần `X-Lyris: 1`. Các test cũ
dùng `owner_client(app)` thay cho `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), ...)`: chủ máy
được đặt sẵn mật khẩu `OWNER_PASSWORD` (hash tính một lần cho cả lượt test) và một phiên cấp thẳng trong DB,
nên không tốn thêm lần scrypt nào cho mỗi test.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx
from fastapi import FastAPI

from lyris.auth import clock, passwords, store
from lyris.auth.net import SESSION_COOKIE
from lyris.db.repo import Repo, new_uid

OWNER_PASSWORD = "mật khẩu chủ máy"
MEMBER_PASSWORD = "mật khẩu thành viên"
CSRF_HEADERS = {"X-Lyris": "1"}


@lru_cache(maxsize=4)
def _hash(password: str) -> passwords.PasswordHash:
    return passwords.hash_password_sync(password)


def repo_of(app: FastAPI) -> Repo:
    repo: Repo = app.state.repo
    return repo


def ensure_owner_password(repo: Repo, password: str = OWNER_PASSWORD) -> int:
    """Chủ máy chưa có mật khẩu thì đặt `password` (bỏ qua màn thiết lập). Trả id chủ máy."""
    owner = repo.owner_account()
    assert owner.id is not None
    with repo.transaction():
        row = store.account_by_id(repo.conn, owner.id)
        assert row is not None
        if row.password is None:
            store.write_password(repo.conn, owner.id, _hash(password), clock.now(), temporary=False)
            store.delete_setup(repo.conn)
    return owner.id


def add_member(repo: Repo, handle: str, display_name: str = "Thành viên", password: str = MEMBER_PASSWORD) -> int:
    """Thêm thành viên có mật khẩu (chèn thẳng vào DB, không qua mã mời)."""
    owner_id = ensure_owner_password(repo)
    with repo.transaction():
        account_id = store.insert_member(
            repo.conn, uid=new_uid(), handle=handle, display_name=display_name, invited_by=owner_id
        )
        store.write_password(repo.conn, account_id, _hash(password), clock.now(), temporary=False)
    return account_id


def session_token(repo: Repo, account_id: int) -> str:
    """Cấp thẳng một phiên trong DB (như vừa đăng nhập) và trả token cho cookie."""
    with repo.transaction():
        token, _ = store.insert_session(repo.conn, account_id, now=clock.now(), label="test", ip="127.0.0.1")
    return token


def client_for(app: FastAPI, account_id: int | None, *, base_url: str = "http://test", **kwargs: Any) -> httpx.AsyncClient:
    """Client đã đăng nhập tài khoản `account_id` (None: không đăng nhập), luôn gửi `X-Lyris: 1`."""
    repo = repo_of(app)
    ensure_owner_password(repo)
    cookies = {SESSION_COOKIE: session_token(repo, account_id)} if account_id is not None else {}
    headers = {**CSRF_HEADERS, **kwargs.pop("headers", {})}
    transport = kwargs.pop("transport", None) or httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url=base_url, cookies=cookies, headers=headers, **kwargs)


def owner_client(app: FastAPI, *, base_url: str = "http://test", **kwargs: Any) -> httpx.AsyncClient:
    """Client đã đăng nhập chủ máy (cho các test viết trước Phase 4b)."""
    owner_id = ensure_owner_password(repo_of(app))
    return client_for(app, owner_id, base_url=base_url, **kwargs)


def anon_client(app: FastAPI, *, base_url: str = "http://test", **kwargs: Any) -> httpx.AsyncClient:
    """Client chưa đăng nhập (vẫn gửi `X-Lyris`, trừ khi test ghi đè headers)."""
    headers = {**CSRF_HEADERS, **kwargs.pop("headers", {})}
    transport = kwargs.pop("transport", None) or httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url=base_url, headers=headers, **kwargs)


__all__ = [
    "CSRF_HEADERS",
    "MEMBER_PASSWORD",
    "OWNER_PASSWORD",
    "add_member",
    "anon_client",
    "client_for",
    "ensure_owner_password",
    "owner_client",
    "session_token",
]


def owner_asgi_headers(app: FastAPI) -> list[tuple[bytes, bytes]]:
    """Header thô cho test gọi thẳng ASGI (scope tự dựng): cookie phiên chủ máy và `X-Lyris`."""
    owner_id = ensure_owner_password(repo_of(app))
    token = session_token(repo_of(app), owner_id)
    return [(b"x-lyris", b"1"), (b"cookie", f"{SESSION_COOKIE}={token}".encode())]
