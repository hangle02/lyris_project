"""Phase 3b end-to-end qua HTTP và ChatService thật (docs/phase3.md §10), với LLM giả có kịch bản.

- Gợi ý theo yêu cầu: POST /suggestions -> /extras có gợi ý -> người chơi gửi -> gợi ý biến mất (và worker
  trích xuất lượt mới không tự sinh lại gợi ý).
- Dòng thời gian sau vài lượt (kể cả lời mở đầu, lượt 0), đúng dạng JSON mà frontend đọc (types.ts TimelineEntry).
- Cửa sổ lịch sử cắt theo khúc qua đường chat thật: điểm bắt đầu đứng yên qua nhiều lượt, system (A+B+C)
  giữ nguyên từng byte khi cửa sổ chưa dịch, và tóm tắt cho khúc vừa rơi đã sẵn khi cửa sổ dịch.

Không gọi Ollama thật.
"""
from __future__ import annotations

from lyris.db.repo import ANY_ACCOUNT

import statistics
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from lyris.api.app import create_app
from lyris.models import EMOTION_KEYS
from tests.test_phase3_e2e import (
    EXTRACTIONS,
    REPLY_FOREHEAD,
    REPLY_LIBRARY,
    REPLY_TEA,
    ScriptedLLM,
    done_message,
    extras,
    first_story,
    make_settings,
    ok,
    repo_of,
    send,
    worker_of,
)
from tests.authutil import owner_client


@pytest.fixture
def llm() -> ScriptedLLM:
    return ScriptedLLM([REPLY_TEA, REPLY_LIBRARY, REPLY_FOREHEAD])


@pytest.fixture
async def app(tmp_path: Path, llm: ScriptedLLM) -> AsyncIterator[FastAPI]:
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with owner_client(app, base_url="http://test") as c:
        yield c


def suggestion_calls(llm: ScriptedLLM) -> list[dict[str, Any]]:
    return [c for c in llm.json_calls() if "suggestions" in c["schema"].get("properties", {})]


# ---------------------------------------------------------------------------- gợi ý: xin -> hiện -> gửi -> mất


async def test_suggestions_requested_shown_then_gone_after_send(
    app: FastAPI, client: httpx.AsyncClient, llm: ScriptedLLM
) -> None:
    sid = await first_story(client)
    await send(client, sid, "Đi uống trà sữa không?")
    await worker_of(app).run_until_idle()
    # Không có gợi ý tự động sau một lượt (extraction không còn sinh gợi ý).
    assert (await extras(client, sid))["suggestions"] == []
    assert suggestion_calls(llm) == []
    extract_schemas = [c["schema"] for c in llm.json_calls()]
    assert extract_schemas and all("suggestions" not in s.get("properties", {}) for s in extract_schemas)

    first = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert set(first) == {"items"} and 1 <= len(first["items"]) <= 3
    assert all(isinstance(s, str) and s for s in first["items"])
    assert (await extras(client, sid))["suggestions"] == first["items"]

    # "Gợi ý khác": thay gợi ý cũ, prompt nhắc tránh các gợi ý trước.
    second = await ok(await client.post(f"/api/stories/{sid}/suggestions"))
    assert second["items"] != first["items"]
    assert (await extras(client, sid))["suggestions"] == second["items"]
    last_prompt = "\n".join(m.content for m in suggestion_calls(llm)[-1]["messages"])
    assert all(item in last_prompt for item in first["items"])

    # Người chơi trả lời (bằng chính một gợi ý): gợi ý biến mất, kể cả sau khi worker trích xuất lượt mới.
    await send(client, sid, second["items"][0])
    assert (await extras(client, sid))["suggestions"] == []
    await worker_of(app).run_until_idle()
    data = await extras(client, sid)
    assert data["suggestions"] == [] and data["pending"] is False
    assert len(suggestion_calls(llm)) == 2  # không bao giờ tự gọi


async def test_suggestions_survive_reextract_but_not_edit(app: FastAPI, client: httpx.AsyncClient) -> None:
    sid = await first_story(client)
    reply = await send(client, sid, "Đi uống trà sữa không?")
    items = (await ok(await client.post(f"/api/stories/{sid}/suggestions")))["items"]
    # Worker trích xuất lượt đó sau khi đã có gợi ý: gợi ý vẫn còn.
    await worker_of(app).run_until_idle()
    assert (await extras(client, sid))["suggestions"] == items
    # Sửa câu trả lời của nhân vật: gợi ý cũ không còn khớp nên bị xoá.
    resp = await client.patch(f"/api/messages/{reply['id']}", json={"content": reply["raw_content"] + " Ừm."})
    assert resp.status_code == 200, resp.text
    assert (await extras(client, sid))["suggestions"] == []


# ---------------------------------------------------------------------------- dòng thời gian


async def test_timeline_after_several_turns(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = await first_story(client)
    greeting = repo_of(app).active_messages(sid)[0]
    assert greeting.turn_index == 0
    # Kịch bản cho lời mở đầu: model trả cả delta và fact, nhưng lượt 0 chỉ được giữ cảnh + ký ức.
    monkeypatch.setitem(EXTRACTIONS, greeting.visible_content[:40], {
        "relationship_delta": {"affection": 5, "trust": 5, "attraction": 0, "obsession": 0, "fear": 0, "aversion": 0},
        "location": "Cổng trường",
        "time": "Chiều tan học",
        "memory": {"text": "Lâm Vãn gặp Lạc Dương ở cổng trường.", "importance": 2},
        "facts": [{"subject": "Lạc Dương", "text": "Lạc Dương học cùng trường"}],
    })
    sent = [
        await send(client, sid, "Đi uống trà sữa không?"),
        await send(client, sid, "Mưa to quá, đi đâu đây?"),
        await send(client, sid, "Ngon quá trời!"),
    ]
    # Story seed tạo lúc khởi động với LLM giả không tự xếp lời mở đầu: chỉ lượt 0 chưa được ghi nhớ
    # (3 lượt vừa gửi đã có job). "Đọc lại story" xếp nó.
    before = await extras(client, sid)
    assert before["unprocessed_turns"] == 1
    await ok(await client.post(f"/api/stories/{sid}/state/rebuild"))
    await worker_of(app).run_until_idle()
    assert (await extras(client, sid))["unprocessed_turns"] == 0

    timeline = await ok(await client.get(f"/api/stories/{sid}/timeline"))
    keys = {"turn_index", "message_id", "mode", "created_at", "memory", "facts", "delta", "scene"}
    assert all(set(e) == keys for e in timeline)
    turns = [e["turn_index"] for e in timeline]
    assert turns == sorted(turns) and turns[-3:] == [m["turn_index"] for m in sent]
    by_turn = {e["turn_index"]: e for e in timeline}
    # Mỗi mục trỏ đúng message của nhân vật ở lượt đó (để giao diện nhảy tới).
    for msg in sent:
        assert by_turn[msg["turn_index"]]["message_id"] == msg["id"]
        assert by_turn[msg["turn_index"]]["mode"] == "story"

    tea, library, forehead = (by_turn[m["turn_index"]] for m in sent)
    # Chỉ giữ 2 thay đổi lớn nhất (affection 3, trust 2; bỏ attraction 1), theo thứ tự EMOTION_KEYS.
    assert tea["delta"] == {"affection": 3, "trust": 2}
    assert list(library["delta"]) == ["fear", "aversion"] and library["delta"] == {"fear": 1, "aversion": 2}
    # Ba giá trị 2, 2, 1: giữ hai số 2 (affection, attraction).
    assert forehead["delta"] == {"affection": 2, "attraction": 2}
    for e in timeline:
        assert all(k in EMOTION_KEYS and v != 0 for k, v in e["delta"].items())
    assert tea["scene"] == {"location": "Quán trà sữa đầu ngõ", "time": "Chiều tan học"}
    assert library["scene"] == {"location": "Thư viện trường", "time": None}
    assert forehead["scene"] is None  # "không đổi" -> không có cảnh mới
    assert tea["memory"].startswith("Lạc Dương mời Lâm Vãn")
    assert tea["facts"] == ["Lâm Vãn mê trà sữa trân châu đường đen từ hồi cấp hai"]
    assert library["facts"] == []

    # Lượt 0 có cảnh + ký ức, không bao giờ có delta hay fact (dù model có trả).
    opening = by_turn[0]
    assert opening["delta"] == {} and opening["facts"] == []
    assert opening["memory"] == "Lâm Vãn gặp Lạc Dương ở cổng trường."
    assert opening["scene"] == {"location": "Cổng trường", "time": "Chiều tan học"}

    # Làm lại lượt cuối: variant mới chưa có state nên mục cũ rời dòng thời gian; trích xuất xong thì mục
    # trỏ tới message mới.
    regen = await client.post(f"/api/messages/{sent[-1]['id']}/regenerate")
    assert regen.status_code == 200, regen.text
    new_id = done_message(regen.text)["id"]
    ids = {e["message_id"] for e in await ok(await client.get(f"/api/stories/{sid}/timeline"))}
    assert sent[-1]["id"] not in ids
    await worker_of(app).run_until_idle()
    after = {e["turn_index"]: e for e in await ok(await client.get(f"/api/stories/{sid}/timeline"))}
    assert after[sent[-1]["turn_index"]]["message_id"] == new_id


# ---------------------------------------------------------------------------- cửa sổ theo khúc qua ChatService


def long_reply(n: int) -> str:
    return (
        f"Lạc Dương khẽ cười ở lượt R{n}, kéo ghế ngồi xuống cạnh Lâm Vãn. "
        + "Anh kể chuyện tiệm sách cũ, chuyện mưa dầm và con mèo mướp hay nằm trên bậu cửa. " * 6
        + f'\n\n"Cậu nghe tiếp không, lượt R{n}?"'
    )


async def test_window_start_stable_through_chat_service(tmp_path: Path) -> None:
    llm = ScriptedLLM([long_reply(n) for n in range(1, 41)])
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            sid = await first_story(client)
            repo = repo_of(application)
            seq: list[tuple[int, str, list[Any]]] = []  # (lượt đầu cửa sổ, system, messages)
            uppers: list[int | None] = []
            summarized: list[bool] = []  # có job tóm tắt được xếp sau lượt này không
            for t in range(30):
                before = len([j for j in repo.list_jobs(sid) if j.kind == "summarize"])
                done = await send(client, sid, f"*Tớ chống cằm nghe.* Lượt P{t}, kể tiếp đi mà, kể thêm chút nữa thôi.")
                # Worker chạy giữa các lượt như ngoài đời (trích xuất + tóm tắt trước khúc sắp rơi).
                await worker_of(application).run_until_idle()
                summarized.append(len([j for j in repo.list_jobs(sid) if j.kind == "summarize"]) > before)
                snapshot = repo.get_message(done["id"], account_id=ANY_ACCOUNT).prompt_snapshot
                assert snapshot is not None
                start = snapshot["window_start_turn"]
                messages = llm.chat_calls()[-1]["messages"]
                seq.append((start, messages[0].content, messages))
                uppers.append(snapshot.get("summary_upto_turn"))

    starts = [s for s, _, _ in seq]
    assert starts == sorted(starts), "cửa sổ không bao giờ lùi"
    moves = [i for i in range(1, len(starts)) if starts[i] != starts[i - 1]]
    assert len(moves) >= 2, f"story phải đủ dài để cửa sổ dịch vài lần: {starts}"
    # Mỗi lần dịch bỏ cả một khúc (nhiều hơn một lượt người chơi + nhân vật).
    assert all(starts[i] - starts[i - 1] > 2 for i in moves)
    # Giữa hai lần dịch, cửa sổ đứng yên ít nhất 2 lượt liên tiếp.
    edges = [0, *moves, len(starts)]
    runs = [b - a for a, b in zip(edges, edges[1:], strict=False)]
    assert all(r >= 2 for r in runs[1:-1]), runs

    for i in range(1, len(seq)):
        (s0, sys0, m0), (s1, sys1, m1) = seq[i - 1], seq[i]
        if s0 == s1:
            # Cửa sổ không dịch: system (A+B+C) giữ nguyên từng byte và prompt lượt trước (trừ ghi chú F ở
            # message cuối) là tiền tố của prompt lượt này, nên Ollama dùng lại KV cache.
            assert sys1 == sys0, f"system đổi ở lượt {i} dù cửa sổ đứng yên"
            head = m0[:-1]
            assert m1[: len(head)] == head

    # Khi cửa sổ đã cắt, khối C dùng đúng tóm tắt phủ tới ngay trước cửa sổ (worker chuẩn bị sẵn).
    for (start, system, _), upto in zip(seq, uppers, strict=True):
        if start > 0:
            assert upto == start - 1, (start, upto)
            assert "Tóm tắt chuyện cũ" in system

    # Gọi model tóm tắt đẩy prompt chat ra khỏi cache: chỉ được làm ngay trước lượt cửa sổ dịch (lượt đó vốn
    # phải đọc lại prompt), không bao giờ ngay sau một lần dịch hay khi cửa sổ còn đứng yên lượt sau.
    assert any(summarized)
    for i, queued in enumerate(summarized[:-1]):
        if queued:
            assert starts[i + 1] != starts[i], (i, starts, summarized)
    assert not any(summarized[i] for i in moves), (moves, summarized)


async def test_prefill_prefix_is_exactly_the_next_prompt_head(tmp_path: Path) -> None:
    # §10.6: phần worker gửi trước (prefill) phải trùng từng message với prompt thật của lượt sau, trừ message
    # cuối (lượt người chơi + ghi chú F), kể cả ở lượt cửa sổ dịch. Lệch một byte là Ollama đọc lại từ đó.
    llm = ScriptedLLM([long_reply(n) for n in range(1, 41)])
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            sid = await first_story(client)
            repo = repo_of(application)
            state = application.state.state
            assert worker_of(application).prefill_enabled is False  # LLM tiêm vào: không prefill
            starts: list[int] = []
            matched = 0
            prefix = None
            for t in range(30):
                done = await send(client, sid, f"*Tớ chống cằm nghe.* Lượt P{t}, kể tiếp đi mà, kể thêm chút nữa thôi.")
                messages = llm.chat_calls()[-1]["messages"]
                if prefix is not None:
                    assert messages[:-1] == prefix.messages, f"lượt {t}: prefill lệch prompt thật"
                    matched += 1
                await worker_of(application).run_until_idle()
                starts.append(repo.get_message(done["id"], account_id=ANY_ACCOUNT).prompt_snapshot["window_start_turn"])
                prefix = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
                assert prefix is not None and prefix.messages[-1].role == "assistant"
                assert prefix.options["num_predict"] == 1 and prefix.options["num_ctx"] == 8192
    assert matched == 29
    assert len(set(starts)) >= 3, f"phải có lượt cửa sổ dịch: {starts}"


def player_turn(t: int, chars: int) -> str:
    text = f"*Tớ chống cằm nghe.* Lượt P{t}. " + "Kể tiếp đi mà, kể thêm chút nữa thôi. " * 20
    return text[:chars]


@pytest.mark.parametrize(
    "lengths",
    [
        pytest.param(lambda t: 80, id="same-length"),  # đoán cũ (dài nhất + 120) lệch ở 3/3 lượt dịch
        pytest.param(lambda t: 400 if t % 4 == 3 else 30, id="mostly-short"),  # đoán cũ lệch ở các lượt ngắn
    ],
)
async def test_prefill_prefix_matches_when_player_writes_a_typical_turn(tmp_path: Path, lengths: Any) -> None:
    # §10.6: phần đầu gửi trước đoán lượt người chơi dài bằng trung vị 5 lượt gần đây (không cộng dư). Lượt
    # người chơi dài đúng như vậy thì phần đầu phải trùng prompt thật, kể cả ở lượt cửa sổ dịch. Chỉ lượt dài
    # khác thường rơi đúng mốc dịch mới được phép lệch.
    llm = ScriptedLLM([long_reply(n) for n in range(1, 61)])
    application = create_app(make_settings(tmp_path), llm)
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            sid = await first_story(client)
            repo = repo_of(application)
            state = application.state.state
            sent: list[int] = []
            starts: list[int] = []
            typical_shifts = 0
            prefix = None
            for t in range(45):
                text = player_turn(t, lengths(t))
                done = await send(client, sid, text)
                messages = llm.chat_calls()[-1]["messages"]
                starts.append(repo.get_message(done["id"], account_id=ANY_ACCOUNT).prompt_snapshot["window_start_turn"])
                if prefix is not None and len(text) == statistics.median_low(sent[-5:]):
                    assert messages[:-1] == prefix.messages, f"lượt {t}: prefill lệch prompt thật"
                    if starts[-1] != starts[-2]:
                        typical_shifts += 1
                sent.append(len(text))
                await worker_of(application).run_until_idle()
                prefix = state.next_prompt_prefix(repo.get_story(sid, account_id=ANY_ACCOUNT))
                assert prefix is not None
    assert len(set(starts)) >= 4, f"phải có nhiều lượt cửa sổ dịch: {starts}"
    assert typical_shifts >= 2, "phải kiểm tra được lượt cửa sổ dịch với lượt người chơi bình thường"


async def test_mode_switch_keeps_summary_right_before_window(tmp_path: Path) -> None:
    """Đổi Story <-> DM giữa chừng: mốc khúc giống nhau ở hai chế độ, nên khi cửa sổ đã cắt thì khối C luôn
    là tóm tắt phủ tới ngay trước cửa sổ (không có lượt nào nằm ngoài cả cửa sổ lẫn tóm tắt)."""
    llm = ScriptedLLM([long_reply(n) for n in range(1, 41)])
    application = create_app(make_settings(tmp_path), llm)
    checked = 0
    async with application.router.lifespan_context(application):
        async with owner_client(application, base_url="http://test") as client:
            sid = await first_story(client)
            repo = repo_of(application)
            for t in range(32):
                mode = "story" if (t // 5) % 2 == 0 else "dm"
                await ok(await client.patch(f"/api/stories/{sid}", json={"mode": mode}))
                # Đổi chế độ xếp tóm tắt trước nếu cửa sổ sắp dịch ở chế độ mới; worker chạy lúc người chơi gõ.
                await worker_of(application).run_until_idle()
                done = await send(client, sid, f"*Tớ chống cằm nghe.* Lượt P{t}, kể tiếp đi mà, kể thêm chút nữa thôi.")
                await worker_of(application).run_until_idle()
                snapshot = repo.get_message(done["id"], account_id=ANY_ACCOUNT).prompt_snapshot
                assert snapshot is not None
                if snapshot["dropped_turns"] > 0:
                    checked += 1
                    assert snapshot.get("summary_upto_turn") == snapshot["window_start_turn"] - 1, (t, mode, snapshot)
    assert checked >= 5


# ---------------------------------------------------------------------------- câu lỗi: backend <-> frontend


def test_plain_error_messages_match_frontend_contract() -> None:
    """Mọi câu lỗi dễ hiểu của server phải có trong danh sách frontend kiểm tra là "không kỹ thuật"
    (frontend/src/lib/friendlyError.test.ts), để client không diễn đạt lại chúng thêm lần nữa."""
    import re

    from lyris.chat import service as chat_service
    from lyris.llm import errors

    test_file = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "friendlyError.test.ts"
    source = test_file.read_text(encoding="utf-8")
    block = source.split("const server = [", 1)[1].split("];", 1)[0]
    frontend = set(re.findall(r'"([^"]+)"', block))
    backend = {
        *errors._BY_KIND.values(),
        *errors._MISSING_MODEL.values(),
        *errors._FALLBACK.values(),
        errors.EMPTY_REPLY,
        errors.EMPTY_PREVIEW,
        errors.SAVE_FAILED,
        errors.UNEXPECTED,
        chat_service.BUSY_DETAIL,
        chat_service.SUGGEST_BUSY_DETAIL,
        chat_service.NO_REPLY_TO_SUGGEST,
    }
    assert backend <= frontend, sorted(backend - frontend)
    for text in backend:
        assert not re.search(r"ollama|\bmodel\b", text, re.IGNORECASE), text
