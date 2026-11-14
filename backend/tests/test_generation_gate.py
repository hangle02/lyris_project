"""Phase 4b (docs/auth.md §5): dùng chung một model cho nhiều tài khoản.

- `GenerationGate`: tối đa `LYRIS_CHAT_SLOTS` lượt sinh cùng lúc, mỗi tài khoản 1, xếp hàng vào trước ra trước,
  chờ quá 120 giây thì bỏ;
- qua API: tài khoản đang sinh ở story 1 gửi ở story 2 -> 409; hai tài khoản chạy song song; người thứ ba nhận
  `waiting` rồi `start` theo thứ tự đến; quá hạn chờ thì sự kiện lỗi, tin người chơi đã lưu;
- hàng việc nền xen kẽ theo tài khoản (§5.3).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.chat.gate import WAIT_TIMEOUT_DETAIL, AccountBusy, GateTimeout, GenerationGate
from lyris.config import Settings, get_settings
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.models import CharacterCard, Persona
from lyris.seed import load_seed_card
from lyris.studio.stories import create_story_for
from tests.authutil import add_member, client_for, ensure_owner_password, repo_of
from tests.twoaccounts import parse_sse

REPLY = "Lạc Dương khẽ cười, kéo ghế ngồi xuống cạnh cô.\n\n[Thought: Lại đến rồi.]"


# ---------------------------------------------------------------------------- GenerationGate


async def test_gate_limits_slots_and_accounts() -> None:
    gate = GenerationGate(2)
    a = gate.reserve(1, "Lạc Dương vẫn đang trả lời bạn ở story khác.")
    b = gate.reserve(2)
    assert a.ready and b.ready and gate.active == 2
    with pytest.raises(AccountBusy, match="Lạc Dương vẫn đang trả lời"):
        gate.reserve(1)  # mỗi tài khoản một lượt, không xếp hàng
    c = gate.reserve(3)
    d = gate.reserve(4)
    assert not c.ready and not d.ready and gate.queued == 2
    order: list[int] = []

    async def run(ticket: Any, who: int) -> None:
        await ticket.wait()
        order.append(who)

    tasks = [asyncio.create_task(run(c, 3)), asyncio.create_task(run(d, 4))]
    await asyncio.sleep(0)
    b.release()  # slot chuyển cho người đến trước
    await asyncio.sleep(0.01)
    assert order == [3] and gate.active == 2 and gate.queued == 1
    a.release()
    await asyncio.gather(*tasks)
    assert order == [3, 4]
    c.release()
    d.release()
    d.release()  # trả hai lần không sao
    assert gate.active == 0 and gate.queued == 0
    assert gate.reserve(1).ready  # tài khoản 1 sinh lại được


async def test_gate_timeout_and_cancel_leave_no_trace() -> None:
    gate = GenerationGate(1, wait_timeout=0.05)
    first = gate.reserve(1)
    late = gate.reserve(2)
    with pytest.raises(GateTimeout):
        await late.wait()
    assert gate.queued == 0 and gate.active == 1 and gate.holder(2) is None
    waiting = gate.reserve(3)
    task = asyncio.create_task(waiting.wait())
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert gate.queued == 0 and gate.holder(3) is None
    first.release()
    assert gate.active == 0
    nxt = gate.reserve(4)
    assert nxt.ready


def test_chat_slots_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LYRIS_CHAT_SLOTS", raising=False)
    monkeypatch.delenv("NORA_CHAT_SLOTS", raising=False)
    assert get_settings().chat_slots == 2
    monkeypatch.setenv("LYRIS_CHAT_SLOTS", "1")
    assert get_settings().chat_slots == 1
    monkeypatch.setenv("LYRIS_CHAT_SLOTS", "0")
    with pytest.raises(ValueError, match="LYRIS_CHAT_SLOTS"):
        get_settings()


# ---------------------------------------------------------------------------- qua API


def _settings(tmp_path: Path, slots: int) -> Settings:
    return Settings(
        db_path=tmp_path / "lyris.db",
        ollama_url="http://127.0.0.1:9",
        chat_model="chat-model:test",
        num_ctx=8192,
        avatars_dir=tmp_path / "avatars",
        chat_slots=slots,
    )


class Env:
    def __init__(self, app: FastAPI, fake: FakeLLM, clients: dict[str, httpx.AsyncClient]) -> None:
        self.app = app
        self.fake = fake
        self.clients = clients

    @property
    def gate(self) -> GenerationGate:
        gate: GenerationGate = self.app.state.gate
        return gate


async def _env(tmp_path: Path, slots: int, names: tuple[str, ...]) -> AsyncIterator[Env]:
    fake = FakeLLM(replies=[REPLY])
    app = create_app(_settings(tmp_path, slots), fake)
    async with app.router.lifespan_context(app):
        repo = repo_of(app)
        ids = {"owner": ensure_owner_password(repo)}
        for name in names:
            if name != "owner":
                ids[name] = add_member(repo, name, name.title())
        clients = {name: client_for(app, ids[name]) for name in names}
        try:
            yield Env(app, fake, clients)
        finally:
            for c in clients.values():
                await c.aclose()


async def _story(client: httpx.AsyncClient) -> int:
    resp = await client.post("/api/stories")
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


async def _until(cond: Callable[[], bool]) -> None:
    for _ in range(400):
        if cond():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("điều kiện không bao giờ đúng")


def _names(body: str) -> list[str]:
    out: list[str] = []
    for name, _ in parse_sse(body):
        if name == "delta" and out and out[-1] == "delta*":
            continue
        out.append("delta*" if name == "delta" else name)
    return out


async def test_same_account_second_story_is_409(tmp_path: Path) -> None:
    async for env in _env(tmp_path, 2, ("owner",)):
        a = env.clients["owner"]
        one, two = await _story(a), await _story(a)
        env.fake.delay = 0.02
        first = asyncio.create_task(a.post(f"/api/stories/{one}/messages", json={"content": "Chào."}))
        await _until(lambda: env.gate.active == 1)
        busy = await a.post(f"/api/stories/{two}/messages", json={"content": "Còn mình?"})
        assert busy.status_code == 409
        assert busy.json()["detail"] == "Lạc Dương vẫn đang trả lời bạn ở story khác. Đợi xong rồi gửi tiếp nhé."
        assert (await a.post(f"/api/stories/{two}/suggestions")).status_code == 409
        body = {
            "card": load_seed_card().model_dump(),
            "persona_id": (await a.get("/api/personas")).json()[0]["id"],
            "settings": {"narration_pronouns": {"character": "anh", "player": "cô"}},
            "messages": [{"role": "user", "content": "Chào."}],
        }
        chat_test = await a.post("/api/cards/test-chat", json=body)
        assert chat_test.status_code == 409 and "Lạc Dương vẫn đang trả lời" in chat_test.json()["detail"]
        draft = await a.post("/api/cards/draft", json={"idea": "Một người lạ", "language": "vi"})
        assert draft.status_code == 409
        assert draft.json()["detail"] == "Lạc Dương vẫn đang trả lời bạn ở story khác. Đợi xong rồi gửi tiếp nhé."
        resp = await first
        assert _names(resp.text) == ["user_message", "start", "delta*", "done"]
        env.fake.delay = 0.0
        assert _names((await a.post(f"/api/stories/{two}/messages", json={"content": "Giờ thì sao?"})).text)[-1] == "done"
        assert env.gate.active == 0


async def test_two_accounts_stream_in_parallel(tmp_path: Path) -> None:
    async for env in _env(tmp_path, 2, ("owner", "mai")):
        a, b = env.clients["owner"], env.clients["mai"]
        sa, sb = await _story(a), await _story(b)
        env.fake.delay = 0.02
        ta = asyncio.create_task(a.post(f"/api/stories/{sa}/messages", json={"content": "A đây."}))
        tb = asyncio.create_task(b.post(f"/api/stories/{sb}/messages", json={"content": "B đây."}))
        await _until(lambda: env.gate.active == 2)
        assert env.gate.queued == 0
        ra, rb = await asyncio.gather(ta, tb)
        assert _names(ra.text) == _names(rb.text) == ["user_message", "start", "delta*", "done"]


async def test_third_waits_then_starts_in_arrival_order(tmp_path: Path) -> None:
    async for env in _env(tmp_path, 1, ("owner", "mai", "lan")):
        a, b, c = env.clients["owner"], env.clients["mai"], env.clients["lan"]
        sa, sb, sc = await _story(a), await _story(b), await _story(c)
        env.fake.delay = 0.02
        ta = asyncio.create_task(a.post(f"/api/stories/{sa}/messages", json={"content": "Lượt của A."}))
        await _until(lambda: env.gate.active == 1)
        tb = asyncio.create_task(b.post(f"/api/stories/{sb}/messages", json={"content": "Lượt của B."}))
        await _until(lambda: env.gate.queued == 1)
        tc = asyncio.create_task(c.post(f"/api/stories/{sc}/messages", json={"content": "Lượt của C."}))
        await _until(lambda: env.gate.queued == 2)
        ra, rb, rc = await asyncio.gather(ta, tb, tc)
        assert _names(ra.text) == ["user_message", "start", "delta*", "done"]
        assert _names(rb.text) == ["user_message", "waiting", "start", "delta*", "done"]
        assert _names(rc.text) == ["user_message", "waiting", "start", "delta*", "done"]
        assert parse_sse(rb.text)[1] == ("waiting", {})
        order = [
            next(who for who in "ABC" if any(f"Lượt của {who}." in m.content for m in call["messages"]))
            for call in env.fake.calls
        ]
        assert order == ["A", "B", "C"]


async def test_wait_timeout_keeps_the_player_message(tmp_path: Path) -> None:
    async for env in _env(tmp_path, 1, ("owner", "mai")):
        a, b = env.clients["owner"], env.clients["mai"]
        sa, sb = await _story(a), await _story(b)
        env.gate.wait_timeout = 0.05
        env.fake.delay = 0.05
        ta = asyncio.create_task(a.post(f"/api/stories/{sa}/messages", json={"content": "Dài dòng."}))
        await _until(lambda: env.gate.active == 1)
        rb = await b.post(f"/api/stories/{sb}/messages", json={"content": "Tin của Mai."})
        events = parse_sse(rb.text)
        assert [n for n, _ in events] == ["user_message", "waiting", "error"]
        assert events[-1][1] == {"detail": WAIT_TIMEOUT_DETAIL, "technical": None}
        msgs = (await b.get(f"/api/stories/{sb}/messages")).json()
        assert msgs[-1]["role"] == "user" and msgs[-1]["raw_content"] == "Tin của Mai."
        await ta
        env.fake.delay = 0.0
        retry = await b.post(f"/api/stories/{sb}/reply")  # nút "Thử lại"
        assert _names(retry.text) == ["start", "delta*", "done"]
        assert env.gate.active == 0 and env.gate.queued == 0


# ---------------------------------------------------------------------------- hàng việc nền (§5.3)


def _account_story(repo: Repo, account_id: int) -> int:
    card = repo.create_card(load_seed_card(), account_id=account_id)
    persona = repo.create_persona(Persona(name="P", gender="female"), account_id=account_id)
    assert card.id is not None and persona.id is not None
    story = create_story_for(repo, card.id, persona.id, model_name="m", account_id=account_id)
    assert story.id is not None
    return story.id


def _queue(repo: Repo, story_id: int, n: int) -> list[int]:
    ids = []
    with repo.transaction():
        for _ in range(n):
            cur = repo.conn.execute(
                "INSERT INTO jobs (story_id, message_id, kind, status, attempts, created_at, updated_at)"
                " VALUES (?, NULL, 'embed', 'queued', 0, '2026-11-14T00:00:00Z', '2026-11-14T00:00:00Z')",
                (story_id,),
            )
            ids.append(int(cur.lastrowid or 0))
    return ids


def test_jobs_interleave_by_account(repo: Repo) -> None:
    owner = repo.owner_id()
    member = repo.create_account("mai", "Mai").id
    assert member is not None
    sa, sb = _account_story(repo, owner), _account_story(repo, member)
    a_jobs = _queue(repo, sa, 10)
    b_jobs = _queue(repo, sb, 1)
    claimed = []
    while (job := repo.claim_next_job()) is not None:
        claimed.append(job.id)
        repo.finish_job(job.id, "done")
    assert claimed[:3] == [a_jobs[0], b_jobs[0], a_jobs[1]]  # job của B chạy thứ hai
    assert sorted(claimed) == sorted(a_jobs + b_jobs)
    # Chỉ một tài khoản có việc: vẫn FIFO.
    more = _queue(repo, sa, 3)
    got = []
    while (job := repo.claim_next_job()) is not None:
        got.append(job.id)
        repo.finish_job(job.id, "done")
    assert got == more


def test_repo_refuses_missing_account(repo: Repo) -> None:
    """§4.2: hàm của Repo bắt buộc `account_id`; None không còn nghĩa "mọi tài khoản"."""
    owner = repo.owner_id()
    card = repo.create_card(load_seed_card(), account_id=owner)
    assert card.id is not None
    with pytest.raises(TypeError):
        repo.get_card(card.id)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        repo.get_card(card.id, account_id=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repo.list_stories(account_id=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repo.create_card(CharacterCard.model_validate(load_seed_card().model_dump()))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        repo.create_persona(Persona(name="X", gender="male"), account_id=ANY_ACCOUNT)  # type: ignore[arg-type]
    assert repo.get_card(card.id, account_id=ANY_ACCOUNT).id == card.id
