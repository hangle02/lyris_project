"""Phase 4 end-to-end (docs/phase4.md §6.6, §7, §14.1): ChatService thật + FakeLLM, qua HTTP.

- Lượt gợi ra mục -> lore_hits (fresh), snapshot lore_used; lượt sau -> carried.
- Mục chỉ người chơi biết KHÔNG BAO GIỜ tới model, nhưng mở khoá cho người chơi (/lore audience player).
- Test lộ toàn bộ trên luc-bac-uyen: gửi lần lượt mọi khoá của mọi mục.
- Rollback: regenerate / lật variant / xoá lượt; lượt bị ngắt ghi hit một lần.
- Sửa sổ thế giới hẹn prefill lại đúng story của card đó.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.db.repo import ANY_ACCOUNT, Repo
from lyris.llm.fake import FakeLLM
from lyris.lore.parse import META_SPOILER_TERMS
from lyris.lore.select import LORE_SCAN_DEPTH, LORE_TOKEN_LIMIT
from lyris.models import PromptLore
from tests.test_phase3_e2e import make_settings, repo_of
from tests.authutil import owner_client

WORLDS = Path(__file__).resolve().parents[2] / "worlds"
REPLY = "Hắn im lặng một lúc rồi gật đầu.\n\n[Thought: Lại chuyện này.]"


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM(replies=[REPLY])


@pytest.fixture
async def app(tmp_path: Path, llm: FakeLLM) -> AsyncIterator[FastAPI]:
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


async def ok(resp: httpx.Response) -> Any:
    assert resp.status_code == 200, resp.text
    return resp.json()


def done_of(body: str) -> dict[str, Any]:
    for block in body.split("\n\n"):
        lines = block.strip().split("\n")
        if lines and lines[0] == "event: done":
            return dict(json.loads(lines[1][len("data: ") :])["message"])
    raise AssertionError(body)


async def send(client: httpx.AsyncClient, sid: int, text: str) -> dict[str, Any]:
    resp = await client.post(f"/api/stories/{sid}/messages", json={"content": text})
    assert resp.status_code == 200, resp.text
    return done_of(resp.text)


async def luc_story(client: httpx.AsyncClient) -> tuple[int, int]:
    """(card_id, story_id): card luc-bac-uyen đã nhập world.md, story với persona đầu tiên."""
    draft = await ok(await client.post("/api/cards/import", content=(WORLDS / "luc-bac-uyen" / "card.json").read_bytes()))
    card = await ok(await client.post("/api/cards", json={"card": draft["card"]}))
    text = (WORLDS / "luc-bac-uyen" / "world.md").read_text(encoding="utf-8")
    await ok(await client.post(f"/api/cards/{card['id']}/lore/import", json={"text": text}))
    pid = (await client.get("/api/personas")).json()[0]["id"]
    story = await ok(await client.post("/api/stories", json={"card_id": card["id"], "persona_id": pid}))
    return card["id"], story["id"]


def d_block(content: str) -> str:
    if not content.startswith("[Thông tin thế giới"):
        return ""
    return content.split("[Hết thông tin thế giới.]")[0]


def hits(repo: Repo, message_id: int) -> list[tuple[int, str]]:
    rows = repo.conn.execute(
        "SELECT entry_id, slot FROM lore_hits WHERE message_id = ? ORDER BY entry_id", (message_id,)
    ).fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def entry_id(repo: Repo, card_id: int, title: str) -> int:
    return next(e.id for e in repo.list_lore(card_id) if e.title == title)  # type: ignore[return-value]


# ---------------------------------------------------------------------------- luồng chính


async def test_fresh_then_carried_snapshot_and_unlocked(client: httpx.AsyncClient, app: FastAPI, llm: FakeLLM) -> None:
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    betrothal = entry_id(repo, cid, "Hôn ước Lục - Ôn")
    first = await send(client, sid, "Hôn ước giữa hai nhà là chuyện thế nào?")
    last = llm.calls[-1]["messages"][-1].content
    assert "- Hôn ước Lục - Ôn: Năm 1979" in d_block(last)
    assert "Hôn ước Lục - Ôn" not in llm.calls[-1]["messages"][0].content  # không bao giờ trong system
    assert (betrothal, "fresh") in hits(repo, first["id"])
    snap = repo.get_message(first["id"], account_id=ANY_ACCOUNT).prompt_snapshot
    assert snap is not None and any(u["entry_id"] == betrothal and u["slot"] == "fresh" for u in snap["lore_used"])
    assert "lore_unsent" in snap and snap["token_estimate"]["D"] > 0

    second = await send(client, sid, "Ừ.")
    assert (betrothal, "carried") in hits(repo, second["id"])
    assert "- Hôn ước Lục - Ôn: Năm 1979" in d_block(llm.calls[-1]["messages"][-1].content)

    story_lore = await ok(await client.get(f"/api/stories/{sid}/lore"))
    assert story_lore["available"] is True and story_lore["can_edit"] is True and story_lore["card_id"] == cid
    row = next(e for e in story_lore["entries"] if e["entry_id"] == betrothal)
    assert row["audience"] == "everyone" and row["turns"] == 2 and row["first_turn"] < row["last_turn"]
    assert "{{user}}" not in row["content"] and "Lâm Vãn" in row["content"]  # đã thay tên persona
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert "Hôn ước Lục - Ôn" in extras["lore_tags"] and extras["lore_available"] is True
    assert extras["lore_count"] == len(story_lore["entries"])


async def test_player_only_entry_never_reaches_model_but_unlocks(client: httpx.AsyncClient, app: FastAPI, llm: FakeLLM) -> None:
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    secret = next(e for e in repo.list_lore(cid) if e.title == "Hứa Tri Ý và đêm mười bảy tháng ba")
    person = next(e for e in repo.list_lore(cid) if e.title == "Hứa Tri Ý")
    msg = await send(client, sid, "Hứa Tri Ý là ai vậy? Đêm mười bảy tháng ba có gì?")
    sent = "\n".join(m.content for c in llm.calls for m in c["messages"])
    assert "chín giờ bốn mươi tối mười bảy tháng ba" not in sent
    assert "nữ chính của nguyên tác" not in sent and "Vẽ màu nước rất đẹp" not in sent
    assert (secret.id, "unsent") in hits(repo, msg["id"]) and (person.id, "unsent") in hits(repo, msg["id"])
    snap = repo.get_message(msg["id"], account_id=ANY_ACCOUNT)
    assert snap.prompt_snapshot is not None and secret.id in snap.prompt_snapshot["lore_unsent"]
    assert all(u["entry_id"] != secret.id for u in snap.prompt_snapshot["lore_used"])
    story_lore = await ok(await client.get(f"/api/stories/{sid}/lore"))
    by = {e["entry_id"]: e for e in story_lore["entries"]}
    assert by[secret.id]["audience"] == "player" and by[person.id]["audience"] == "player"
    assert all(e["audience"] != "others" for e in story_lore["entries"])
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    assert secret.title in extras["lore_tags"]


async def test_full_leak_sweep_every_key_of_every_entry(client: httpx.AsyncClient, app: FastAPI, llm: FakeLLM) -> None:
    """§6.1: gửi lần lượt mọi khoá của mọi mục như lời người chơi. Khối D gửi cho model không bao giờ chứa nội
    dung của một mục chỉ người chơi biết hay một từ META_SPOILER_TERMS; cả prompt không chứa nội dung mục đó."""
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    all_entries = repo.list_lore(cid)
    secrets = [e for e in all_entries if e.known_by == ["{{user}}"]]
    assert len(secrets) == 10
    snippets = []
    for e in secrets:
        sentences = [s.strip() for s in e.content.replace("\n", " ").split(". ") if len(s.strip()) > 25]
        snippets += [s.replace("{{user}}", "Lâm Vãn")[:60] for s in sentences]
    keys = [k for e in all_entries for k in e.keys]
    assert len(keys) > 100
    blocks = 0
    for i, key in enumerate(keys):
        before = len(llm.calls)
        await send(client, sid, f"Lượt {i}: {key}?")
        call = llm.calls[before]
        d = d_block(call["messages"][-1].content)
        blocks += bool(d)
        for term in META_SPOILER_TERMS:
            assert term not in d.casefold(), (key, term, d)
        prompt = "\n".join(m.content for m in call["messages"])
        for snippet in snippets:
            assert snippet not in prompt, (key, snippet)
    assert blocks > len(keys) // 2


async def test_matched_but_no_room_is_not_unlocked(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = repo_of(app)
    card_id = (await client.get("/api/cards")).json()[0]["id"]
    long = "Một câu dài về chuyện cũ của tiệm sách. " * 12
    ids = []
    for i in range(6):
        created = await ok(await client.post(f"/api/cards/{card_id}/lore", json={"title": f"Chuyện {i}", "keys": ["tiệm sách"], "content": long}))
        ids.append(created["id"])
    pid = (await client.get("/api/personas")).json()[0]["id"]
    story = await ok(await client.post("/api/stories", json={"card_id": card_id, "persona_id": pid}))
    msg = await send(client, story["id"], "Kể chuyện tiệm sách đi.")
    rows = dict(hits(repo, msg["id"]))
    sent = [i for i in ids if rows.get(i) == "fresh"]
    unsent = [i for i in ids if rows.get(i) == "unsent"]
    assert sent and unsent and len(sent) + len(unsent) == 6
    story_lore = await ok(await client.get(f"/api/stories/{story['id']}/lore"))
    assert sorted(e["entry_id"] for e in story_lore["entries"]) == sorted(sent)
    extras = await ok(await client.get(f"/api/stories/{story['id']}/extras"))
    assert len(extras["lore_tags"]) == len(sent) and extras["lore_count"] == len(sent)


async def test_character_entry_counts_in_lore_count_not_tags(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    await send(client, sid, "Kể về câu nói đêm mưa đi, và hôn ước nữa.")
    extras = await ok(await client.get(f"/api/stories/{sid}/extras"))
    story_lore = await ok(await client.get(f"/api/stories/{sid}/lore"))
    private = [e for e in story_lore["entries"] if e["audience"] == "character"]
    assert [e["title"] for e in private] == ["Câu nói đêm mưa"]
    assert "Câu nói đêm mưa" not in extras["lore_tags"]
    assert extras["lore_count"] == len(story_lore["entries"]) == len(extras["lore_tags"]) + 1
    assert entry_id(repo, cid, "Câu nói đêm mưa") == private[0]["entry_id"]


# ---------------------------------------------------------------------------- rollback


async def test_regenerate_flip_delete_and_entry_removal(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    first = await send(client, sid, "Kể chuyện cái nhẫn sapphire đi.")
    ring = entry_id(repo, cid, "Chiếc nhẫn sapphire")
    titles = lambda body: [e["title"] for e in body["entries"]]  # noqa: E731
    assert "Chiếc nhẫn sapphire" in titles(await ok(await client.get(f"/api/stories/{sid}/lore")))

    # Sổ thế giới đổi giữa chừng (tắt mục nhẫn, thêm mục mới cùng khoá): variant mới có hit riêng.
    await ok(await client.patch(f"/api/cards/{cid}/lore/{ring}", json={"enabled": False}))
    new = await ok(await client.post(f"/api/cards/{cid}/lore", json={"title": "Nhẫn mới", "keys": ["sapphire"]}))
    resp = await client.post(f"/api/messages/{first['id']}/regenerate")
    regen = done_of(resp.text)
    assert regen["variant_index"] == 1 and (new["id"], "fresh") in hits(repo, regen["id"])
    assert all(e != ring for e, _ in hits(repo, regen["id"]))
    now = titles(await ok(await client.get(f"/api/stories/{sid}/lore")))
    assert "Nhẫn mới" in now and "Chiếc nhẫn sapphire" not in now

    # Lật lại variant cũ: hit của nó active trở lại.
    await ok(await client.post(f"/api/messages/{regen['id']}/variant", json={"variant_index": 0}))
    now = titles(await ok(await client.get(f"/api/stories/{sid}/lore")))
    assert "Chiếc nhẫn sapphire" in now and "Nhẫn mới" not in now
    # Mục bị tắt: không gợi nữa, nhưng hit cũ vẫn hiện (đã từng mở).

    # Xoá mục từ file: bia mộ, biến mất khỏi danh sách đã mở ngay.
    await ok(await client.delete(f"/api/cards/{cid}/lore/{ring}"))
    assert "Chiếc nhẫn sapphire" not in titles(await ok(await client.get(f"/api/stories/{sid}/lore")))

    # Xoá từ lượt: hit đi theo CASCADE.
    second = await send(client, sid, "Hôn ước thì sao?")
    assert hits(repo, second["id"])
    user_turn = repo.get_message(second["id"], account_id=ANY_ACCOUNT).turn_index - 1
    user_msg = next(m for m in repo.active_messages(sid) if m.turn_index == user_turn)
    await ok(await client.delete(f"/api/messages/{user_msg.id}"))
    assert hits(repo, second["id"]) == []
    assert repo.conn.execute("SELECT COUNT(*) FROM lore_hits WHERE message_id = ?", (second["id"],)).fetchone()[0] == 0


async def test_aborted_turn_records_hits_once(tmp_path: Path) -> None:
    llm = FakeLLM(replies=["Hắn nói chậm rãi từng chữ, kể rất dài về chuyện cũ. " * 10], chunk_size=5, delay=0.002)
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            cid, sid = await luc_story(client)
            repo = repo_of(application)
            gen = application.state.chat.send(sid, "Hôn ước là sao?")
            async for event in gen:
                if event.name == "delta":
                    break
            await gen.aclose()
            msg = repo.active_messages(sid)[-1]
            assert msg.role == "assistant" and msg.gen_stats is not None and msg.gen_stats.aborted
            betrothal = entry_id(repo, cid, "Hôn ước Lục - Ôn")
            assert (betrothal, "fresh") in hits(repo, msg.id)  # type: ignore[arg-type]
            assert msg.id is not None
            before = len(hits(repo, msg.id))
            lore = PromptLore(unsent_ids=[betrothal])
            application.state.lore.record_hits(sid, msg.id, lore)  # ghi lại: UNIQUE, không nhân đôi
            assert len(hits(repo, msg.id)) == before


async def test_scan_depth_through_real_history(client: httpx.AsyncClient, app: FastAPI) -> None:
    repo = repo_of(app)
    cid, sid = await luc_story(client)
    betrothal = entry_id(repo, cid, "Hôn ước Lục - Ôn")
    m1 = await send(client, sid, "Hôn ước ấy à?")  # P₀
    m2 = await send(client, sid, "Ừ.")  # P₋₁ của lượt sau
    m3 = await send(client, sid, "Thế à.")  # P₋₂: lượt nhắc hôn ước giờ cách 2 cặp lượt
    m4 = await send(client, sid, "Rồi sao nữa.")  # P₋₃: đã ra khỏi độ sâu quét
    assert LORE_SCAN_DEPTH == 4
    assert (betrothal, "fresh") in hits(repo, m1["id"])
    assert (betrothal, "carried") in hits(repo, m2["id"])
    assert (betrothal, "carried") in hits(repo, m3["id"])
    assert all(e != betrothal for e, _ in hits(repo, m4["id"]))


# ---------------------------------------------------------------------------- prefill hẹn lại khi sửa sổ


async def test_lore_changed_reschedules_prefill_only_for_that_card(seeded_repo: Repo) -> None:
    from lyris.studio.stories import create_story_for
    from tests.test_jobs import drain, make_env, until

    env = make_env(seeded_repo, prefill=True)
    sid = env.sid  # story seed (card đầu tiên)
    card, persona = env.repo.list_cards(account_id=ANY_ACCOUNT)[0], env.repo.list_personas(account_id=ANY_ACCOUNT)[0]
    assert card.id is not None and persona.id is not None and env.repo.get_story(sid, account_id=ANY_ACCOUNT).card_id == card.id
    other_card = env.repo.create_card(card.model_copy(update={"id": None}), account_id=env.repo.owner_id())
    assert other_card.id is not None
    other = create_story_for(env.repo, other_card.id, persona.id, model_name="m", account_id=env.repo.owner_id())
    await drain(env.chat.send(sid, '"Chào cậu."'))
    await env.worker.run_until_idle()

    # Đang chờ prefill story khác card: sửa sổ của card này không đụng tới.
    env.worker._prefill_due = other.id
    assert env.queue.lore_changed(card.id) == [sid]
    assert env.worker._prefill_due == other.id

    # Prefill đang chạy của story thuộc card: huỷ rồi hẹn lại.
    env.worker._prefill_due = None
    env.llm.delay = 0.05
    task = asyncio.create_task(env.worker.prefill(sid))
    await until(lambda: env.worker._prefill_task is not None)
    env.queue.lore_changed(card.id)
    assert await task is False
    assert env.worker._prefill_due == sid
    # Card không có story: không báo ai.
    lonely = env.repo.create_card(card.model_copy(update={"id": None}), account_id=env.repo.owner_id())
    assert lonely.id is not None and env.queue.lore_changed(lonely.id) == []


async def test_lore_service_on_change_is_wired_to_queue(client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    monkeypatch.setattr(app.state.jobs, "lore_changed", lambda card_id: seen.append(card_id) or [])
    app.state.lore.on_change = app.state.jobs.lore_changed
    card_id = (await client.get("/api/cards")).json()[0]["id"]
    created = await ok(await client.post(f"/api/cards/{card_id}/lore", json={"title": "A", "keys": ["aa bb"]}))
    await ok(await client.patch(f"/api/cards/{card_id}/lore/{created['id']}", json={"enabled": False}))
    await ok(await client.delete(f"/api/cards/{card_id}/lore/{created['id']}"))
    assert seen == [card_id, card_id, card_id]


async def test_prefill_with_lore_card_matches_and_uses_reserve(client: httpx.AsyncClient, app: FastAPI, llm: FakeLLM) -> None:
    """Prefill (mặc định) của story có sổ thế giới: đúng `messages[:-1]` của lượt thật sau đó."""
    repo = repo_of(app)
    _, sid = await luc_story(client)
    await send(client, sid, "Hôn ước là sao?")
    prefix = app.state.state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
    assert prefix is not None and prefix.open_last is False
    await send(client, sid, "Kể tiếp đi")
    assert llm.calls[-1]["messages"][:-1] == prefix.messages


async def test_lore_change_while_worker_idle_reschedules_prefill_and_summary(seeded_repo: Repo) -> None:
    """Review: prefill đã chạy xong (worker rảnh), người chơi sang Studio thêm mục thế giới đầu tiên (dự phòng
    D 0 -> 520, cửa sổ lượt sau dịch). Worker phải hẹn prefill lại cho story đang chơi, phần đầu gửi trước
    phải khớp prompt thật của lượt sau, và tóm tắt cho mốc mới được xếp ngay."""
    from lyris.chat.service import ChatService
    from lyris.jobs.queue import JobQueue
    from lyris.jobs.worker import Worker
    from lyris.llm.fake import FakeLLM
    from lyris.lore.service import LoreService
    from lyris.models import LoreEntryIn
    from lyris.prompt.builder import PromptBudget
    from lyris.state.service import ModelCatalog, StateService
    from tests.test_jobs import FakeEmbedder, FakeExtractor, FakeSummarizer, drain
    from tests.test_phase3b_e2e import long_reply

    repo = seeded_repo
    budget = PromptBudget(num_ctx=8192)
    llm = FakeLLM(replies=[long_reply(n) * 3 for n in range(80)])
    lore = LoreService(repo)
    state = StateService(repo, llm, catalog=ModelCatalog(None), budget=budget, lore=lore)
    queue = JobQueue(repo, state)
    lore.on_change = queue.lore_changed
    worker = Worker(repo, queue, state, llm, extractor=FakeExtractor(), summarizer=FakeSummarizer(),
                    embedder=FakeEmbedder(), poll_interval=0.05, budget=budget, prefill=True)
    chat = ChatService(repo, llm, budget=budget, state=state, jobs=queue, lore=lore)
    sid = repo.list_stories(account_id=ANY_ACCOUNT)[0].id
    assert sid is not None
    card_id = repo.get_story(sid, account_id=ANY_ACCOUNT).card_id
    turn = "Kể tiếp đi mà, kể thêm chút nữa thôi. " * 3

    class Reserve520:
        def prompt_lore(self, *a: Any) -> PromptLore:
            return PromptLore(reserve_tokens=LORE_TOKEN_LIMIT)

        def reserve_for(self, card_id: int) -> int:
            return LORE_TOKEN_LIMIT

    for _ in range(40):
        await drain(chat.send(sid, turn))
        await worker.run_until_idle()
        assert await worker.prefill(sid)  # như _loop: prefill chạy xong, worker rảnh
        worker._prefill_due = None
        before = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
        real_lore, state.lore = state.lore, Reserve520()  # type: ignore[assignment]
        flipped = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
        state.lore = real_lore
        assert before is not None and flipped is not None
        if flipped.messages != before.messages:
            break
    else:
        pytest.fail("dự phòng D chưa bao giờ làm cửa sổ dịch")

    lore.create(card_id, LoreEntryIn(title="Hôn ước", keys=["hôn ước"], content="Hai nhà hứa gả con."), account_id=ANY_ACCOUNT)
    assert worker._prefill_due == sid
    assert repo.has_pending_jobs(sid, kinds=("summarize",))
    await worker.run_until_idle()
    assert await worker.prefill(sid)
    prefix = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
    assert prefix is not None and prefix.messages != before.messages
    await drain(chat.send(sid, turn))
    real = [c for c in llm.calls if c.get("raw") is not True][-1]["messages"]
    assert [m.model_dump() if hasattr(m, "model_dump") else m for m in prefix.messages] == [
        m.model_dump() if hasattr(m, "model_dump") else m for m in real[:-1]
    ]


async def test_lore_change_does_not_steal_a_pending_prefill_of_another_story(seeded_repo: Repo) -> None:
    from tests.test_jobs import drain, make_env

    env = make_env(seeded_repo, prefill=True)
    await drain(env.chat.send(env.sid, '"Chào cậu."'))
    await env.worker.run_until_idle()
    card_id = env.repo.get_story(env.sid, account_id=ANY_ACCOUNT).card_id
    env.worker._prefill_due = None
    env.queue.lore_changed(card_id)
    assert env.worker._prefill_due == env.sid  # rảnh: hẹn lại story đang chơi
    env.worker._prefill_due = 999
    env.queue.lore_changed(card_id)
    assert env.worker._prefill_due == 999
