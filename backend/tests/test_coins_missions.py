"""F45 (docs/coins.md §6, §7, §8, §11; quyết định nhiem-vu-va-quang-cao-mau): nhiệm vụ ngày và quảng cáo mẫu.

Ba nhiệm vụ mỗi ngày coin (giờ Việt Nam): `ad` (+5, tối đa 3 lần, quảng cáo mẫu 15 giây theo đồng hồ server),
`characters` (+10, 3 nhân vật khác nhau đã trả lời mình), `turns` (+5, 20 câu trả lời `send`/`retry`). Trần 30 coin/ngày
kiểm ở server trong cùng một `BEGIN IMMEDIATE` với việc ghi sổ.
"""
from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from lyris.analytics import events
from lyris.analytics.events import EventRejected
from lyris.auth import clock
from lyris.coins import holds, ledger, missions
from lyris.config import Settings, get_settings
from lyris.db.connection import connect
from lyris.llm.base import LLMError
from tests.coinutil import coin_env, names, settings, studio_chat_body
from tests.twoaccounts import card_body, parse_sse

AD_LIMIT = {"code": "ad_limit", "detail": "Hôm nay bạn đã xem đủ 3 quảng cáo."}
AD_NOT_FINISHED = {"code": "ad_not_finished", "detail": "Quảng cáo chưa xem xong."}
AD_EXPIRED = {"code": "ad_expired", "detail": "Lượt xem này đã hết hạn. Hãy xem lại."}


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class Clock:
    """Đồng hồ server giả (`lyris.auth.clock.now`)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, start: str) -> None:
        self.t = _at(start)
        monkeypatch.setattr(clock, "now", lambda: self.t)

    def set(self, text: str) -> None:
        self.t = _at(text)

    def add(self, seconds: float) -> None:
        self.t = self.t + timedelta(seconds=seconds)


def _err(resp: Any) -> dict[str, Any]:
    body = resp.json()
    return {"code": body.get("code"), "detail": body.get("detail")}


def _events(env: Any, name: str) -> list[dict[str, Any]]:
    return [json.loads(r[0]) for r in env.rows("SELECT props_json FROM analytics_events WHERE name = ? ORDER BY id", name)]


def _mission_rows(env: Any, who: str, day: str | None = None) -> list[Any]:
    rows = env.ledger(who, "mission")
    return [r for r in rows if day is None or r["coin_day"] == day]


def _by_id(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {m["id"]: m for m in body["missions"]}


async def _missions(client: Any) -> dict[str, Any]:
    resp = await client.get("/api/coins/missions")
    assert resp.status_code == 200, resp.text
    data: dict[str, Any] = resp.json()
    return data


async def _start(client: Any) -> int:
    resp = await client.post("/api/coins/ads/start")
    assert resp.status_code == 200, resp.text
    assert resp.json()["seconds"] == 15
    return int(resp.json()["ad_id"])


async def _watch_ad(client: Any, clk: Clock) -> dict[str, Any]:
    """Một lượt xem trọn vẹn: start, đợi 15 giây (đồng hồ giả), claim."""
    ad = await _start(client)
    clk.add(15)
    resp = await client.post(f"/api/coins/ads/{ad}/claim")
    assert resp.status_code == 200, resp.text
    data: dict[str, Any] = resp.json()
    return data


def _charged(env: Any, who: str, *, char_key: int | None, mode: str = "story", kind: str = "send") -> None:
    """Một câu trả lời đã trả coin (giữ chỗ `charged`), như `ChatService` ghi."""
    story_id = None if mode == "test" else 1
    with env.repo.transaction():
        conn = env.repo.conn
        hold_id = holds.open_hold(
            conn, env.ids[who], story_id=story_id, char_key=char_key, origin_card_id=None, mode=mode, kind=kind, amount=6
        )
        assert holds.charge_hold(conn, hold_id, message_id=None, story_id=story_id, card_id=char_key) is not None


# ---------------------------------------------------------------------------- danh sách, làm mới lúc 0:00 giờ Việt Nam


async def test_missions_list_and_reset_at_vietnam_midnight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch, "2026-11-14T16:58:00")  # 23:58 ngày 14/11 giờ Việt Nam
    async with coin_env(tmp_path, ("mai",)) as env:
        mai, owner = env.clients["mai"], env.clients["owner"]
        first = await _missions(mai)
        assert first["coin_day"] == "2026-11-14" and first["cap"] == 30 and first["earned_today"] == 0
        assert first["unlimited"] is False
        assert [(m["id"], m["target"], m["reward"]) for m in first["missions"]] == [
            ("ad", 3, 5), ("characters", 3, 10), ("turns", 20, 5)
        ]
        for m in first["missions"]:
            assert set(m) == {"id", "progress", "target", "reward", "claimed", "claimable", "remaining"}, m
            assert m["progress"] == 0 and m["claimed"] is False and m["claimable"] is False
        assert _by_id(first)["ad"]["remaining"] == 3

        # Chủ máy: không có nhiệm vụ.
        mine = await _missions(owner)
        assert mine["missions"] == [] and mine["unlimited"] is True
        refused = await owner.post("/api/coins/ads/start")
        assert refused.status_code == 409 and refused.json()["code"] == "no_missions", refused.text
        assert env.rows("SELECT COUNT(*) FROM coin_ad_views")[0][0] == 0

        # Trong ngày: một câu trả lời đã trả coin và một quảng cáo đã nhận.
        _charged(env, "mai", char_key=101)
        await _watch_ad(mai, clk)
        today = await _missions(mai)
        got = _by_id(today)
        assert today["earned_today"] == 5
        assert (got["ad"]["progress"], got["ad"]["remaining"]) == (1, 2)
        assert got["characters"]["progress"] == 1 and got["turns"]["progress"] == 1

        clk.set("2026-11-14T16:59:59")
        assert (await _missions(mai))["earned_today"] == 5  # còn là ngày 14/11
        clk.set("2026-11-14T17:00:00")  # 0:00 ngày 15/11 giờ Việt Nam
        fresh = await _missions(mai)
        assert fresh["coin_day"] == "2026-11-15" and fresh["earned_today"] == 0
        for m in fresh["missions"]:
            assert m["progress"] == 0 and m["claimed"] is False and m["claimable"] is False, m
        assert _by_id(fresh)["ad"]["remaining"] == 3


# ---------------------------------------------------------------------------- quảng cáo mẫu: 15 giây theo đồng hồ server


async def test_ad_claim_needs_15_server_seconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch, "2026-11-14T03:00:00")
    assert settings(tmp_path).ad_seconds == 15
    monkeypatch.setenv("LYRIS_AD_SECONDS", "2")
    monkeypatch.setenv("NORA_AD_SECONDS", "2")
    assert get_settings().ad_seconds == 15  # không biến môi trường nào đổi được 15 giây
    assert "ad_seconds" in Settings.__dataclass_fields__
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai, lan = env.clients["mai"], env.clients["lan"]
        start = 300
        ad = await _start(mai)
        clk.add(14)
        early = await mai.post(f"/api/coins/ads/{ad}/claim")
        assert early.status_code == 409 and _err(early) == AD_NOT_FINISHED, early.text
        assert env.balance("mai") == start and _mission_rows(env, "mai") == []
        clk.add(0.999)
        assert (await mai.post(f"/api/coins/ads/{ad}/claim")).status_code == 409  # 14,999 giây vẫn chưa đủ

        # Tài khoản khác: 404, không lộ là có, không cộng cho ai.
        for path in (f"/api/coins/ads/{ad}/claim", f"/api/coins/ads/{ad}/cancel"):
            other = await lan.post(path)
            assert other.status_code == 404, other.text
            assert "lan" not in other.text.lower() and "mai" not in other.text.lower()
        assert (await lan.post("/api/coins/ads/999999/claim")).status_code == 404

        clk.add(0.001)  # đúng 15 giây
        ok = await mai.post(f"/api/coins/ads/{ad}/claim")
        assert ok.status_code == 200, ok.text
        assert ok.json()["amount"] == 5 and ok.json()["wallet"]["balance"] == start + 5
        again = await mai.post(f"/api/coins/ads/{ad}/claim")
        assert again.status_code == 200 and again.json()["amount"] == 5
        assert env.balance("mai") == start + 5 and env.balance("lan") == 300
        rows = _mission_rows(env, "mai")
        assert [(r["delta"], r["mission"], r["idem_key"]) for r in rows] == [
            (5, "ad", f"mission:{env.ids['mai']}:2026-11-14:ad:1")
        ]
        # Huỷ một lượt đã nhận: không lỗi, không đổi gì.
        assert (await mai.post(f"/api/coins/ads/{ad}/cancel")).json() == {"ok": True}
        assert env.balance("mai") == start + 5


async def test_cancelled_or_expired_ad_cannot_be_claimed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch, "2026-11-14T03:00:00")
    async with coin_env(tmp_path, ("mai",)) as env:
        mai = env.clients["mai"]
        start = env.balance("mai")

        # "Đóng" trước khi nhận: cancel (gọi hai lần không lỗi); đủ 15 giây rồi vẫn không nhận được.
        closed = await _start(mai)
        clk.add(3)
        for _ in range(2):
            cancel = await mai.post(f"/api/coins/ads/{closed}/cancel")
            assert cancel.status_code == 200 and cancel.json() == {"ok": True}, cancel.text
        clk.add(20)
        late = await mai.post(f"/api/coins/ads/{closed}/claim")
        assert late.status_code == 409 and _err(late) == AD_EXPIRED, late.text

        # Quá 10 phút.
        stale = await _start(mai)
        clk.add(10 * 60 + 1)
        expired = await mai.post(f"/api/coins/ads/{stale}/claim")
        assert expired.status_code == 409 and _err(expired) == AD_EXPIRED, expired.text

        # Bắt đầu trước 0:00 giờ Việt Nam, nhận sau 0:00 (đủ 15 giây, chưa quá 10 phút).
        clk.set("2026-11-14T16:59:50")
        night = await _start(mai)
        clk.set("2026-11-14T17:00:06")
        crossed = await mai.post(f"/api/coins/ads/{night}/claim")
        assert crossed.status_code == 409 and _err(crossed) == AD_EXPIRED, crossed.text

        # `ads/start` lần hai huỷ lượt xem dở trước đó (tab khác).
        first = await _start(mai)
        second = await _start(mai)
        assert second != first
        clk.add(20)
        replaced = await mai.post(f"/api/coins/ads/{first}/claim")
        assert replaced.status_code == 409 and _err(replaced) == AD_EXPIRED, replaced.text
        row = env.rows("SELECT cancelled_at, claimed_at FROM coin_ad_views WHERE id = ?", first)[0]
        assert row["cancelled_at"] is not None and row["claimed_at"] is None
        assert env.balance("mai") == start and _mission_rows(env, "mai") == []
        assert env.rows(
            "SELECT COUNT(*) FROM coin_ad_views WHERE account_id = ? AND claimed_at IS NULL AND cancelled_at IS NULL",
            env.ids["mai"],
        )[0][0] == 1
        good = await mai.post(f"/api/coins/ads/{second}/claim")
        assert good.status_code == 200 and good.json()["amount"] == 5, good.text
        assert env.balance("mai") == start + 5 and len(_mission_rows(env, "mai")) == 1


async def test_ad_limit_3_per_day(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch, "2026-11-14T03:00:00")
    async with coin_env(tmp_path, ("mai",)) as env:
        mai = env.clients["mai"]
        start = env.balance("mai")
        for _ in range(3):
            await _watch_ad(mai, clk)
            clk.add(5)
        fourth = await mai.post("/api/coins/ads/start")
        assert fourth.status_code == 409 and _err(fourth) == AD_LIMIT, fourth.text
        assert env.rows("SELECT COUNT(*) FROM coin_ad_views WHERE account_id = ?", env.ids["mai"])[0][0] == 3
        ad = _by_id(await _missions(mai))["ad"]
        assert (ad["progress"], ad["remaining"], ad["claimed"]) == (3, 0, True)
        assert env.balance("mai") == start + 15
        assert [r["idem_key"].rsplit(":", 1)[1] for r in _mission_rows(env, "mai")] == ["1", "2", "3"]

        clk.set("2026-11-14T17:00:01")  # ngày coin mới
        assert _by_id(await _missions(mai))["ad"]["progress"] == 0
        data = await _watch_ad(mai, clk)
        assert data["amount"] == 5 and env.balance("mai") == start + 20
        assert _mission_rows(env, "mai")[-1]["idem_key"] == f"mission:{env.ids['mai']}:2026-11-15:ad:1"


# ---------------------------------------------------------------------------- "3 nhân vật khác nhau" và "Gửi 20 lượt"


async def _ok(resp: Any) -> dict[str, Any]:
    assert resp.status_code == 200, resp.text
    data: dict[str, Any] = resp.json()
    return data


async def test_characters_and_turns_progress_rules(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai",)) as env:
        mai, owner = env.clients["mai"], env.clients["owner"]
        persona = (await _ok(await mai.post("/api/personas", json={"name": "Mai", "gender": "female"})))["id"]
        x = (await _ok(await mai.post("/api/cards", json={"card": card_body("Hải Đăng")})))["id"]
        y = (await _ok(await mai.post("/api/cards", json={"card": card_body("Ngư Phủ")})))["id"]
        public = (await _ok(await owner.post("/api/cards", json={"card": card_body("Gió Bấc", visibility="public")})))["id"]

        async def story(card: int) -> dict[str, Any]:
            return await _ok(await mai.post("/api/stories", json={"card_id": card, "persona_id": persona}))

        async def send(story_id: int, text: str = "Chào.") -> Any:
            return await mai.post(f"/api/stories/{story_id}/messages", json={"content": text})

        async def progress() -> tuple[int, int]:
            got = _by_id(await _missions(mai))
            return got["characters"]["progress"], got["turns"]["progress"]

        s1, s2 = await story(x), await story(x)
        c1, c2 = await story(public), await story(public)
        assert c1["card_id"] != c2["card_id"] and public not in (c1["card_id"], c2["card_id"])  # hai bản sao

        # Hai story cùng một nhân vật: 1.
        for s in (s1, s2):
            assert names((await send(s["id"])).text)[-1] == "done"
        assert await progress() == (1, 2)
        # Hai bản sao của cùng một nhân vật công khai: 1.
        for s in (c1, c2):
            assert names((await send(s["id"])).text)[-1] == "done"
        assert await progress() == (2, 4)

        # Câu trả lời bị nhả (lỗi, không có chữ) không đếm.
        s3 = await story(y)
        env.fake.error = LLMError("model hỏng")
        assert names((await send(s3["id"])).text)[-1] == "error"
        env.fake.error = None
        assert await progress() == (2, 4)

        # "Tạo lại câu trả lời" không đếm cho "Gửi 20 lượt".
        sent = await send(s1["id"])
        reply_id = [d for n, d in parse_sse(sent.text) if n == "done"][0]["message"]["id"]
        assert await progress() == (2, 5)
        assert names((await mai.post(f"/api/messages/{reply_id}/regenerate")).text)[-1] == "done"
        assert await progress() == (2, 5)

        # Chat thử ở Studio (mode 'test') không đếm cho cả hai.
        assert names((await mai.post("/api/cards/test-chat", json=await studio_chat_body(mai))).text)[-1] == "done"
        assert await progress() == (2, 5)
        assert env.rows(
            "SELECT COUNT(*) FROM coin_holds WHERE account_id = ? AND status = 'charged' AND mode = 'test'", env.ids["mai"]
        )[0][0] == 1

        # Chưa đủ: 409 mission_not_done, không cộng.
        before = env.balance("mai")
        for mission in ("characters", "turns"):
            nope = await mai.post(f"/api/coins/missions/{mission}/claim")
            assert nope.status_code == 409 and nope.json()["code"] == "mission_not_done", nope.text
        assert env.balance("mai") == before and _mission_rows(env, "mai") == []
        assert (await mai.post("/api/coins/missions/ad/claim")).status_code in (404, 422)  # quảng cáo nhận trong hộp

        # "Trả lời" sau lỗi (retry) đếm cho cả hai: nhân vật thứ ba.
        assert names((await mai.post(f"/api/stories/{s3['id']}/reply")).text)[-1] == "done"
        assert await progress() == (3, 6)
        got = _by_id(await _missions(mai))
        assert got["characters"]["claimable"] is True and got["turns"]["claimable"] is False
        for i in range(14):
            assert names((await send(s2["id"], f"Lượt {i}.")).text)[-1] == "done"
        got = _by_id(await _missions(mai))
        assert got["turns"]["progress"] == 20 and got["turns"]["claimable"] is True
        assert got["characters"]["progress"] == 3  # không vượt target

        before = env.balance("mai")
        turns = await _ok(await mai.post("/api/coins/missions/turns/claim"))
        chars = await _ok(await mai.post("/api/coins/missions/characters/claim"))
        assert turns["amount"] == 5 and chars["amount"] == 10 and env.balance("mai") == before + 15
        got = _by_id(await _missions(mai))
        assert got["turns"]["claimed"] and got["characters"]["claimed"]
        assert not got["turns"]["claimable"] and not got["characters"]["claimable"]
        assert sorted(p["mission"] for p in _events(env, "mission_claimed")) == ["characters", "turns"]
        assert sorted((p["source"], p["amount"]) for p in _events(env, "coins_granted") if p["source"] != "signup") == [
            ("mission_characters", 10), ("mission_turns", 5)
        ]


# ---------------------------------------------------------------------------- nhận một lần, trần 30, đua nhau, sự kiện


def _race(fns: list[Any]) -> list[Any]:
    """Chạy các hàm cùng lúc trong các luồng riêng; trả kết quả hoặc ngoại lệ theo thứ tự."""
    barrier = threading.Barrier(len(fns))
    out: list[Any] = [None] * len(fns)

    def run(i: int) -> None:
        barrier.wait()
        try:
            out[i] = fns[i]()
        except Exception as exc:  # noqa: BLE001 - ghi lại để test kiểm
            out[i] = exc

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(fns))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    return out


async def test_claim_once_and_daily_cap_30(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clk = Clock(monkeypatch, "2026-11-14T03:00:00")
    async with coin_env(tmp_path, ("mai",)) as env:
        mai = env.clients["mai"]
        acc = env.ids["mai"]
        db = tmp_path / "lyris.db"
        for key in (1, 2, 3):
            _charged(env, "mai", char_key=key)
        for _ in range(17):
            _charged(env, "mai", char_key=1, kind="retry")

        # Hai tab cùng bấm "Nhận": một dòng sổ, cộng một lần.
        before = env.balance("mai")
        both = await asyncio.gather(
            mai.post("/api/coins/missions/characters/claim"), mai.post("/api/coins/missions/characters/claim")
        )
        assert [r.status_code for r in both] == [200, 200], [r.text for r in both]
        assert env.balance("mai") == before + 10
        assert len([r for r in _mission_rows(env, "mai") if r["mission"] == "characters"]) == 1

        # Hai luồng (hai kết nối) gọi post_mission song song: một dòng sổ.
        conns = [connect(db), connect(db)]
        try:
            results = _race([lambda c=c: missions.post_mission(c, acc, "turns") for c in conns])
        finally:
            for c in conns:
                c.close()
        assert all(isinstance(r, ledger.Entry) for r in results), results
        assert sorted(r.created for r in results) == [False, True]
        assert len([r for r in _mission_rows(env, "mai") if r["mission"] == "turns"]) == 1
        assert env.balance("mai") == before + 15

        # Đã nhận 2 quảng cáo; hai lượt xem khác nhau cùng nhận song song: chỉ một thành công, không bao giờ có lần thứ 4.
        await _watch_ad(mai, clk)
        await _watch_ad(mai, clk)
        assert env.balance("mai") == before + 25
        with env.repo.transaction():
            # Gỡ lưới an toàn "một lượt xem mở" để chứng minh việc đếm trong transaction tự đứng được.
            env.repo.conn.execute("DROP INDEX idx_coin_ad_open")
            stamp = clock.iso(clk.t - timedelta(seconds=20))
            ids = [
                int(env.repo.conn.execute(
                    "INSERT INTO coin_ad_views (account_id, coin_day, started_at) VALUES (?, '2026-11-14', ?)", (acc, stamp)
                ).lastrowid or 0)
                for _ in range(2)
            ]
        conns = [connect(db), connect(db)]
        try:
            results = _race([
                lambda c=c, ad=ad: missions.claim_ad(c, acc, ad, seconds=15) for c, ad in zip(conns, ids, strict=True)
            ])
        finally:
            for c in conns:
                c.close()
        wins = [r for r in results if not isinstance(r, Exception)]
        losses = [r for r in results if isinstance(r, missions.MissionRejected)]
        assert len(wins) == 1 and len(losses) == 1, results
        assert losses[0].code == "ad_limit"
        ads = [r for r in _mission_rows(env, "mai") if r["mission"] == "ad"]
        assert len(ads) == 3 and sorted(r["idem_key"] for r in ads) == [
            f"mission:{acc}:2026-11-14:ad:{n}" for n in (1, 2, 3)
        ]
        day_total = sum(r["delta"] for r in _mission_rows(env, "mai", "2026-11-14"))
        assert day_total == 30
        assert (await _missions(mai))["earned_today"] == 30

        # Ngày mới: một "nhiệm vụ giả" +10 đã ghi; 10 + 10 + 5 + 5 = 30, thứ gì thêm cũng 409 mission_cap.
        clk.set("2026-11-15T03:00:00")
        with env.repo.transaction():
            ledger.post(env.repo.conn, acc, 10, "mission", f"mission:{acc}:2026-11-15:fake", mission="turns")
        for key in (4, 5, 6):
            _charged(env, "mai", char_key=key)
        await _ok(await mai.post("/api/coins/missions/characters/claim"))
        await _watch_ad(mai, clk)
        await _watch_ad(mai, clk)
        third = await _start(mai)
        clk.add(15)
        capped = await mai.post(f"/api/coins/ads/{third}/claim")
        assert capped.status_code == 409 and capped.json()["code"] == "mission_cap", capped.text
        for _ in range(20):
            _charged(env, "mai", char_key=4)
        turns_capped = await mai.post("/api/coins/missions/turns/claim")
        assert turns_capped.status_code == 409 and turns_capped.json()["code"] == "mission_cap", turns_capped.text
        with pytest.raises(missions.MissionRejected) as raised:
            with env.repo.transaction():
                missions.post_mission(env.repo.conn, acc, "turns")
        assert raised.value.code == "mission_cap"
        day = sum(r["delta"] for r in _mission_rows(env, "mai", "2026-11-15"))
        assert day == 30
        view = await _missions(mai)
        assert view["earned_today"] == 30
        assert not any(m["claimable"] for m in view["missions"])
        for d in {r["coin_day"] for r in _mission_rows(env, "mai")}:
            assert sum(r["delta"] for r in _mission_rows(env, "mai", d)) <= 30

        # Sự kiện (§11): đúng luật events.py.
        assert events.EVENTS["ad_started"].sources == frozenset({"server"}) and events.EVENTS["ad_started"].props == {}
        assert events.EVENTS["mission_claimed"].sources == frozenset({"server"})
        assert events.EVENTS["mission_claimed"].required == {"mission"}
        assert events.EVENTS["missions_viewed"].sources == frozenset({"client"})
        assert events.validate("missions_viewed", {"from": "composer"}, source="client") == {"from": "composer"}
        for bad, source in (({"from": "chip"}, "client"), ({"from": "wallet"}, "server")):
            with pytest.raises(EventRejected):
                events.validate("missions_viewed", bad, source=source)
        with pytest.raises(EventRejected):
            events.validate("mission_claimed", {"mission": "bonus"}, source="server")
        started = _events(env, "ad_started")
        # Qua API: 5 lần "ads/start"; nhận được 4 quảng cáo và 2 lần "characters" (lần bấm thứ hai của tab kia, các lần
        # gọi thẳng post_mission/claim_ad trong luồng và các lần bị từ chối không ghi sự kiện).
        assert started and all(p == {} for p in started) and len(started) == 5
        claimed = _events(env, "mission_claimed")
        assert sorted(p["mission"] for p in claimed) == ["ad", "ad", "ad", "ad", "characters", "characters"]
        for p in claimed:
            assert events.validate("mission_claimed", p, source="server") == p
        granted = [p for p in _events(env, "coins_granted") if p["source"].startswith("mission_")]
        assert sorted((p["source"], p["amount"]) for p in granted) == sorted(
            [("mission_ad", 5)] * 4 + [("mission_characters", 10)] * 2
        )
