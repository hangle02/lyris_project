"""F44 (docs/coins.md §5.1): ai là "người chơi" của nhân vật công khai.

Người chơi của nhân vật công khai X = tài khoản không phải người tạo X, không phải chủ máy, có story chơi bằng bản sao của
X, với ít nhất 3 câu trả lời đã trả coin (giữ chỗ `charged`) cộng dồn, ở ít nhất 2 ngày coin khác nhau.

F44 làm lại (2026-11-14 22:15): thưởng mốc 10/50/100 người chơi bị thay hẳn bằng thưởng theo bảng xếp hạng "Nhân vật
hot" và thưởng công khai lần đầu; test của luật mới ở `test_creator_rank.py` và `test_hot_board.py`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from lyris.auth import clock
from lyris.coins import creator
from lyris.llm.base import LLMError
from tests.coinutil import coin_env
from tests.twoaccounts import card_body

DAY1 = "2026-11-14T03:00:00"  # 10:00 ngày 14/11 giờ Việt Nam
NAME = "Hạ Vy"


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class Clock:
    """Đồng hồ server giả (`lyris.auth.clock.now`)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, start: str = DAY1) -> None:
        self.t = _at(start)
        monkeypatch.setattr(clock, "now", lambda: self.t)

    def days(self, n: int) -> None:
        self.t = self.t + timedelta(days=n)


def _players(n: int) -> tuple[str, ...]:
    return tuple(f"choi{i:02d}" for i in range(1, n + 1))


async def _ok(resp: Any) -> Any:
    assert resp.status_code == 200, (resp.request.method, str(resp.request.url), resp.status_code, resp.text)
    return resp.json()


async def _public_card(client: Any, name: str = NAME, *, visibility: str = "public") -> int:
    body = await _ok(await client.post("/api/cards", json={"card": card_body(name, visibility=visibility)}))
    assert body["visibility"] == visibility
    return int(body["id"])


async def _play(env: Any, who: str, card_id: int) -> int:
    """`who` bắt đầu một story với nhân vật `card_id` (công khai của người khác: bản sao). Trả id story."""
    client = env.clients[who]
    personas = await _ok(await client.get("/api/personas"))
    if not personas:
        await _ok(await client.post("/api/personas", json={"name": who.title(), "gender": "female"}))
    story = await _ok(await client.post("/api/stories", json={"card_id": card_id}))
    return int(story["id"])


def _reply(env: Any, who: str, story_id: int) -> bool:
    """Một câu trả lời có chữ: giữ chỗ rồi trừ, đúng đường `ChatService` gọi `CoinService`. False: không bị tính coin."""
    coins = env.app.state.coins
    story = env.repo.get_story(story_id, account_id=env.ids[who])
    hold = coins.hold(env.ids[who], story=story, mode="story", kind="send")
    if hold is None:
        return False
    assert coins.charge(hold, None)
    return True


def _released(env: Any, who: str, story_id: int, reason: str) -> None:
    coins = env.app.state.coins
    story = env.repo.get_story(story_id, account_id=env.ids[who])
    hold = coins.hold(env.ids[who], story=story, mode="story", kind="send")
    assert hold is not None
    assert coins.release(hold, reason)


async def _send(env: Any, who: str, story_id: int) -> None:
    """Một lượt gửi qua API thật (LLM giả): câu trả lời có chữ được lưu và trừ 6 coin."""
    resp = await env.clients[who].post(f"/api/stories/{story_id}/messages", json={"content": "Chào."})
    assert resp.status_code == 200, resp.text
    assert "event: done" in resp.text, resp.text[-300:]


def _player_rows(env: Any, card_id: int) -> list[tuple[int, int | None]]:
    return [(int(r[0]), r[1]) for r in env.rows(
        "SELECT player_id, creator_id FROM creator_players WHERE card_id = ? ORDER BY player_id", card_id
    )]


def _milestone_rows(env: Any, who: str) -> list[Any]:
    return env.ledger(who, "creator_milestone")


async def _qualify(env: Any, clk: Clock, players: tuple[str, ...], stories: dict[str, int]) -> None:
    """Mỗi người chơi: 2 câu trả lời hôm nay, 1 câu ngày coin sau (đồng hồ +1 ngày)."""
    for who in players:
        _reply(env, who, stories[who])
        _reply(env, who, stories[who])
    clk.days(1)
    for who in players:
        _reply(env, who, stories[who])


# ---------------------------------------------------------------------------- ai là người chơi


async def test_player_counts_after_3_charged_replies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan", "minh")) as env:
        x = await _public_card(env.clients["havy"])
        lan = await _play(env, "lan", x)
        copy = env.rows("SELECT card_id FROM stories WHERE id = ?", lan)[0][0]
        assert copy != x
        assert env.rows("SELECT story_copy, origin_card_id FROM character_cards WHERE id = ?", copy)[0][:] == (1, x)

        # 2 câu trả lời đã trả coin (qua API thật): chưa phải người chơi.
        await _send(env, "lan", lan)
        await _send(env, "lan", lan)
        charged = env.rows("SELECT origin_card_id, status FROM coin_holds WHERE account_id = ? ORDER BY id", env.ids["lan"])
        assert [tuple(r) for r in charged] == [(x, "charged"), (x, "charged")]
        assert _player_rows(env, x) == []
        # Câu thứ 3 cùng ngày coin: vẫn chưa.
        await _send(env, "lan", lan)
        assert _player_rows(env, x) == []
        # Một câu ở ngày coin sau: đúng một dòng (X, lan, người tạo X).
        clk.days(1)
        await _send(env, "lan", lan)
        assert _player_rows(env, x) == [(env.ids["lan"], env.ids["havy"])]
        # Câu tiếp theo không thêm dòng.
        await _send(env, "lan", lan)
        assert _player_rows(env, x) == [(env.ids["lan"], env.ids["havy"])]

        # 3 câu chia ở hai story bản sao khác nhau của X: cộng dồn.
        clk.days(1)
        first = await _play(env, "minh", x)
        second = await _play(env, "minh", x)
        copies = {r[0] for r in env.rows("SELECT card_id FROM stories WHERE id IN (?, ?)", first, second)}
        assert len(copies) == 2  # hai bản sao khác nhau của X
        await _send(env, "minh", first)
        _reply(env, "minh", second)
        assert len(_player_rows(env, x)) == 1
        clk.days(1)
        _reply(env, "minh", second)
        assert _player_rows(env, x) == sorted([(env.ids["lan"], env.ids["havy"]), (env.ids["minh"], env.ids["havy"])])
        # Không ai đủ 10: chưa có thưởng.
        assert _milestone_rows(env, "havy") == []


async def test_creator_owner_and_released_replies_never_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch)
    async with coin_env(tmp_path, ("havy", "lan")) as env:
        x = await _public_card(env.clients["havy"])

        # Người tạo chơi chính X (không có bản sao) và một bản sao của chính X: không bao giờ được tính.
        own = await _play(env, "havy", x)
        assert env.rows("SELECT card_id FROM stories WHERE id = ?", own)[0][0] == x
        # App không cho người tạo chụp bản sao của chính mình (`copy_public_card` từ chối), nên dựng thẳng trong DB
        # tạm: một story bản sao của X (lan bắt đầu) được chuyển sang tài khoản người tạo.
        self_story = await _play(env, "lan", x)
        persona = env.rows("SELECT persona_id FROM stories WHERE id = ?", own)[0][0]
        with env.repo.transaction():
            conn = env.repo.conn
            copy_id = conn.execute("SELECT card_id FROM stories WHERE id = ?", (self_story,)).fetchone()[0]
            conn.execute("UPDATE character_cards SET account_id = ? WHERE id = ?", (env.ids["havy"], copy_id))
            conn.execute(
                "UPDATE stories SET account_id = ?, persona_id = ? WHERE id = ?", (env.ids["havy"], persona, self_story)
            )
        # Chủ máy chơi X (bản sao): chủ máy không bị tính coin, không có giữ chỗ.
        owner_story = await _play(env, "owner", x)
        # Thành viên khác: câu trả lời bị nhả (lỗi, rỗng) qua API thật và qua dịch vụ.
        lan = await _play(env, "lan", x)
        env.fake.error = LLMError("máy lỗi")
        failed = await env.clients["lan"].post(f"/api/stories/{lan}/messages", json={"content": "Chào."})
        assert failed.status_code == 200 and "event: error" in failed.text
        env.fake.error = None

        for day in range(3):
            if day:
                clk.days(1)
            for _ in range(2):
                assert _reply(env, "havy", own)
                assert _reply(env, "havy", self_story)
                assert not _reply(env, "owner", owner_story)
                _released(env, "lan", lan, "error")
                _released(env, "lan", lan, "empty")
        # Một giữ chỗ `charged` của chủ máy với origin X (không có đường nào tạo ra, nhưng luật vẫn chặn).
        with env.repo.transaction():
            conn = env.repo.conn
            for day in ("2026-11-14", "2026-11-15", "2026-11-16"):
                hid = conn.execute(
                    "INSERT INTO coin_holds (account_id, story_id, char_key, origin_card_id, mode, kind, amount, status,"
                    " coin_day, created_at) VALUES (?, ?, ?, ?, 'story', 'send', 6, 'charged', ?, ?)",
                    (env.ids["owner"], owner_story, x, x, day, clock.iso(clock.now())),
                ).lastrowid
                assert hid is not None
                assert creator.note_charged(conn, hid) == []
            # Đủ 3 câu ở 3 ngày coin: chỉ luật "không phải chủ máy" loại tài khoản này.
            assert creator.qualifies(conn, x, env.ids["owner"])
            assert creator.qualifies(conn, x, env.ids["havy"])  # người tạo cũng đủ số câu, bị loại vì là người tạo

        assert env.holds("owner") and all(h["account_id"] == env.ids["owner"] for h in env.holds("owner"))
        statuses = {h["status"] for h in env.holds("lan")}
        assert statuses == {"released"}
        assert {h["origin_card_id"] for h in env.holds("havy")} == {None, x}  # bản sao của chính mình vẫn có origin
        assert _player_rows(env, x) == []

        # Đối chứng: lan có 3 câu trả lời ĐÃ trả coin ở 2 ngày coin thì được tính ngay.
        _reply(env, "lan", lan)
        _reply(env, "lan", lan)
        clk.days(1)
        _reply(env, "lan", lan)
        assert _player_rows(env, x) == [(env.ids["lan"], env.ids["havy"])]
