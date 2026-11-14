"""F42 (docs/coins.md): tiện ích chung cho test coin — app với LLM giả, chủ máy + thành viên, đọc ví/sổ/giữ chỗ."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.coins import ledger
from lyris.config import Settings
from lyris.db.repo import Repo
from lyris.llm.fake import FakeLLM
from lyris.seed import load_seed_card
from tests.authutil import add_member, client_for, ensure_owner_password, repo_of
from tests.twoaccounts import parse_sse

REPLY = "Lạc Dương khẽ cười, kéo ghế ngồi xuống cạnh cô.\n\n\"Lại đến rồi à, ngồi đi.\"\n\n[Thought: Lại đến rồi.]"


def settings(tmp_path: Path, *, coins: bool = True, slots: int = 2) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="chat-model:test",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
        chat_slots=slots,
        coins_enabled=coins,
    )


@dataclass
class CoinEnv:
    app: FastAPI
    fake: FakeLLM
    ids: dict[str, int]
    clients: dict[str, httpx.AsyncClient] = field(default_factory=dict)

    @property
    def repo(self) -> Repo:
        return repo_of(self.app)

    def balance(self, who: str) -> int:
        with self.repo.locked() as conn:
            return ledger.balance(conn, self.ids[who])

    def rows(self, sql: str, *params: Any) -> list[Any]:
        with self.repo.locked() as conn:
            return conn.execute(sql, params).fetchall()

    def ledger(self, who: str, kind: str | None = None) -> list[Any]:
        sql = "SELECT * FROM coin_ledger WHERE account_id = ?"
        params: list[Any] = [self.ids[who]]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        return self.rows(sql + " ORDER BY id", *params)

    def holds(self, who: str) -> list[Any]:
        return self.rows("SELECT * FROM coin_holds WHERE account_id = ? ORDER BY id", self.ids[who])

    def set_balance(self, who: str, target: int) -> None:
        """Đưa số dư về `target` bằng một dòng `admin_adjust` (như chủ máy trừ/cộng tay)."""
        current = self.balance(who)
        if current == target:
            return
        with self.repo.transaction():
            ledger.post(
                self.repo.conn, self.ids[who], target - current, "admin_adjust",
                f"adjust:test:{who}:{len(self.ledger(who))}", actor_id=self.ids["owner"], reason="test",
            )


@asynccontextmanager
async def coin_env(
    tmp_path: Path, members: tuple[str, ...] = ("mai",), *, coins: bool = True, slots: int = 2, fake: FakeLLM | None = None
) -> AsyncIterator[CoinEnv]:
    fake = fake or FakeLLM(replies=[REPLY])
    app = create_app(settings(tmp_path, coins=coins, slots=slots), fake)
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        ids = {"owner": ensure_owner_password(repo)}
        for name in members:
            ids[name] = add_member(repo, name, name.title())
        env = CoinEnv(app=app, fake=fake, ids=ids)
        env.clients = {name: client_for(app, ids[name]) for name in ids}
        try:
            yield env
        finally:
            for c in env.clients.values():
                await c.aclose()


async def new_story(client: httpx.AsyncClient, mode: str = "story") -> int:
    resp = await client.post("/api/stories")
    assert resp.status_code == 200, resp.text
    story_id = int(resp.json()["id"])
    if mode != "story":
        patched = await client.patch(f"/api/stories/{story_id}", json={"mode": mode})
        assert patched.status_code == 200, patched.text
    return story_id


def names(body: str) -> list[str]:
    return [n for n, _ in parse_sse(body)]


async def studio_chat_body(client: httpx.AsyncClient) -> dict[str, Any]:
    persona = (await client.get("/api/personas")).json()
    if not persona:
        made = await client.post("/api/personas", json={"name": "Người chơi", "gender": "female"})
        assert made.status_code == 200, made.text
        persona = [made.json()]
    return {
        "card": load_seed_card().model_dump(),
        "persona_id": persona[0]["id"],
        "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}},
        "messages": [{"role": "user", "content": "Chào anh."}],
    }


async def until(cond: Callable[[], bool], tries: int = 600) -> None:
    for _ in range(tries):
        if cond():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("điều kiện không bao giờ đúng")


__all__ = ["REPLY", "CoinEnv", "coin_env", "names", "new_story", "settings", "studio_chat_body", "until"]
