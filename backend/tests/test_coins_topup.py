"""F43 (docs/coins.md §4, §7, §11): nạp coin ở chế độ thử — gói giá, mã nạp (chủ máy tạo, thành viên dùng), giới hạn
thử mã sai, chủ máy cộng/trừ coin có lý do, nhật ký coin của chủ máy."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from lyris.analytics import events
from lyris.auth import clock, codes
from lyris.coins import ledger
from lyris.config import REPO_ROOT
from tests.coinutil import coin_env, names, new_story

COINS_DOC = REPO_ROOT / "docs" / "coins.md"
TRACKING_PLAN = REPO_ROOT / "docs" / "tracking-plan.md"
INVALID = {"detail": "Mã nạp không đúng hoặc đã hết hạn.", "code": "topup_code_invalid"}
F43_EVENTS = {"topup_code_redeemed", "topup_code_failed", "topup_code_created", "coins_adjusted"}


def _events(env: Any, name: str) -> list[dict[str, Any]]:
    return [json.loads(r[0]) for r in env.rows("SELECT props_json FROM analytics_events WHERE name = ? ORDER BY id", name)]


async def _make_code(env: Any, **body: Any) -> dict[str, Any]:
    body.setdefault("note", "")
    body.setdefault("expires_days", 7)
    resp = await env.clients["owner"].post("/api/admin/coins/codes", json=body)
    assert resp.status_code == 200, resp.text
    data: dict[str, Any] = resp.json()
    return data


def _iphone(code: str) -> str:
    """Như người dùng gõ trên iPhone: chữ thường, gạch ngang thành dấu U+2010, có khoảng trắng."""
    norm = codes.normalize_code(code)
    assert norm is not None
    return f"  {norm[:4].lower()}\u2010{norm[4:8].lower()} \u2010 {norm[8:].lower()} "


# ---------------------------------------------------------------------------- gói, tập route


async def test_packs_are_test_mode_with_vnd_prices(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        for who in ("mai", "owner"):
            resp = await env.clients[who].get("/api/coins/packs")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["test_mode"] is True
            assert data["contact"] is None  # chế độ thử: không có kênh liên hệ để mua (quyết định nap-coin-che-do-thu)
            packs = data["packs"]
            assert [p["id"] for p in packs] == ["p100", "p550", "p1200", "p2500"]
            assert [p["coins"] for p in packs] == [100, 550, 1200, 2500]
            assert [p["price_vnd"] for p in packs] == [10000, 50000, 100000, 200000]
            assert [p["bonus"] for p in packs] == [0, 50, 200, 500]
            assert all(set(p) == {"id", "coins", "bonus", "price_vnd"} for p in packs)


def _norm_path(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path.replace("\\|", "|"))


def _documented_routes() -> set[tuple[str, str]]:
    """Cột đầu của bảng §7 docs/coins.md: `METHOD /api/...` (tham số đường dẫn chuẩn hoá thành `{}`)."""
    doc = COINS_DOC.read_text(encoding="utf-8")
    section = doc.split("## 7. API", 1)[1].split("\n## ", 1)[0]
    table = section.split("Tập route có tiền tố", 1)[0]
    out: set[tuple[str, str]] = set()
    for line in table.splitlines():
        m = re.match(r"^\|\s*`(GET|POST|PUT|PATCH|DELETE) (/api/[^`\s?]+)", line)
        if m:
            out.add((m.group(1), _norm_path(m.group(2))))
    return out


# Route của F45 (nhiệm vụ ngày, quảng cáo mẫu): phải có trong §7 và trong app (F45 đã có).
F45_ROUTES = {
    ("GET", "/api/coins/missions"),
    ("POST", "/api/coins/missions/{}/claim"),
    ("POST", "/api/coins/ads/start"),
    ("POST", "/api/coins/ads/{}/claim"),
    ("POST", "/api/coins/ads/{}/cancel"),
}


async def test_coin_routes_are_exactly_the_documented_list(tmp_path: Path) -> None:
    documented = _documented_routes()
    assert len(documented) == 15, sorted(documented)  # 15 dòng của bảng §7 (missions claim gộp {characters|turns})
    assert F45_ROUTES <= documented
    expected = documented  # F45 đã có: so khớp tuyệt đối, không route nào thiếu hay thừa
    async with coin_env(tmp_path) as env:
        paths = env.app.openapi()["paths"]
        app_routes: set[tuple[str, str]] = set()
        for path, ops in paths.items():
            for method in ops:
                key = (method.upper(), _norm_path(path))
                if path.startswith(("/api/coins/", "/api/admin/coins/")) or key == ("POST", "/api/admin/accounts/{}/coins"):
                    app_routes.add(key)
    assert app_routes == expected, (sorted(app_routes - expected), sorted(expected - app_routes))
    # Không route nào nhận thẻ, ví điện tử hay thanh toán.
    assert not any(re.search(r"pay|card|momo|vnpay|stripe|checkout|bank", p) for _, p in app_routes)


# ---------------------------------------------------------------------------- mã nạp: chủ máy tạo


async def test_owner_creates_code_shown_once_hash_stored(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        made = await _make_code(env, pack_id="p100", note="cho Mai", expires_days=7)
        norm = codes.normalize_code(made["code"])
        assert norm is not None and len(norm) == 12
        item = made["item"]
        assert item["amount"] == 100 and item["pack_id"] == "p100" and item["note"] == "cho Mai"
        assert item["hint"] == norm[-4:] and item["status"] == "active" and item["used_by_handle"] is None
        rows = env.rows("SELECT * FROM coin_topup_codes")
        assert len(rows) == 1
        row = rows[0]
        assert bytes(row["code_hash"]) == codes.code_hash(norm) and row["code_hint"] == norm[-4:]
        # Mã đầy đủ không nằm ở cột nào của DB.
        for value in tuple(row):
            if isinstance(value, str):
                assert norm not in value.upper().replace("-", "")
        # Hạn 7 ngày.
        assert clock.parse(row["expires_at"]) - clock.parse(row["created_at"]) == timedelta(days=7)
        custom = await _make_code(env, amount=250, note="bù lỗi", expires_days=1)
        assert custom["item"]["amount"] == 250 and custom["item"]["pack_id"] is None
        listed = await env.clients["owner"].get("/api/admin/coins/codes")
        assert listed.status_code == 200
        text = listed.text
        for full in (made["code"], custom["code"]):
            n = codes.normalize_code(full)
            assert n is not None
            assert n not in text.upper().replace("-", "") and full not in text
        assert [i["id"] for i in listed.json()] == [custom["item"]["id"], made["item"]["id"]]  # mới trước
        assert all("code" not in i for i in listed.json())
        # Dữ liệu sai: cả gói lẫn số coin, không có gì, số coin ngoài 1–10.000, hạn lạ, ghi chú quá 60 ký tự.
        owner = env.clients["owner"]
        for body in (
            {"pack_id": "p100", "amount": 100}, {}, {"amount": 0}, {"amount": 10_001}, {"pack_id": "p999"},
            {"amount": 5, "expires_days": 3}, {"amount": 5, "note": "x" * 61},
        ):
            resp = await owner.post("/api/admin/coins/codes", json=body)
            assert resp.status_code == 422, (body, resp.text)
        assert len(env.rows("SELECT id FROM coin_topup_codes")) == 2
        assert _events(env, "topup_code_created") == [
            {"expires_days": 7, "pack": "p100"}, {"expires_days": 1, "pack": "custom"},
        ]


async def test_at_most_50_active_codes(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        owner = env.clients["owner"]
        made = [await _make_code(env, amount=10) for _ in range(50)]
        resp = await owner.post("/api/admin/coins/codes", json={"amount": 10, "expires_days": 7})
        assert resp.status_code == 422
        assert resp.json()["code"] == "topup_code_limit"
        assert resp.json()["detail"] == "Đã có 50 mã nạp còn hiệu lực. Huỷ bớt mã cũ rồi tạo mã mới."
        revoked = await owner.post(f"/api/admin/coins/codes/{made[0]['item']['id']}/revoke")
        assert revoked.status_code == 200 and revoked.json()["status"] == "revoked"
        await _make_code(env, amount=10)
        # Mã đã dùng hay hết hạn không còn tính là "còn hiệu lực".
        assert (await owner.post("/api/admin/coins/codes", json={"amount": 10})).status_code == 422
        assert (await env.clients["mai"].post("/api/coins/redeem", json={"code": made[1]["code"]})).status_code == 200
        await _make_code(env, amount=10)
        with env.repo.transaction():
            env.repo.conn.execute(
                "UPDATE coin_topup_codes SET expires_at = ? WHERE id = ?",
                (clock.iso(clock.now() - timedelta(seconds=1)), made[2]["item"]["id"]),
            )
        await _make_code(env, amount=10)
        assert (await owner.post("/api/admin/coins/codes", json={"amount": 10})).status_code == 422
        # Huỷ mã đã dùng: 409, mã vẫn "đã dùng".
        used = await owner.post(f"/api/admin/coins/codes/{made[1]['item']['id']}/revoke")
        assert used.status_code == 409
        assert (await owner.post("/api/admin/coins/codes/999999/revoke")).status_code == 404


async def test_member_gets_403_on_admin_coin_routes(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        made = await _make_code(env, amount=10)
        mai = env.clients["mai"]
        calls = [
            ("GET", "/api/admin/coins/codes", None),
            ("POST", "/api/admin/coins/codes", {"amount": 10, "expires_days": 7}),
            ("POST", f"/api/admin/coins/codes/{made['item']['id']}/revoke", None),
            ("GET", "/api/admin/coins/log", None),
            ("POST", f"/api/admin/accounts/{env.ids['mai']}/coins", {"delta": 50, "reason": "tự cộng", "request_id": "member-0001"}),
        ]
        # Mọi route /api/admin/coins/* của app đều có trong danh sách trên.
        admin_paths = {
            (m.upper(), re.sub(r"\{[^}]*\}", "{}", p))
            for p, ops in env.app.openapi()["paths"].items()
            if p.startswith("/api/admin/coins/")
            for m in ops
        }
        listed = {(m, re.sub(r"/\d+", "/{}", u)) for m, u, _ in calls}
        assert admin_paths <= listed, admin_paths - listed
        for method, url, body in calls:
            resp = await mai.request(method, url, json=body)
            assert resp.status_code == 403, (url, resp.text)
            assert resp.json()["code"] == "owner_only"
        assert env.balance("mai") == 300
        assert len(env.rows("SELECT id FROM coin_topup_codes")) == 1


# ---------------------------------------------------------------------------- mã nạp: thành viên dùng


async def test_redeem_once_same_error_for_used_expired_revoked_unknown(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai, lan, owner = env.clients["mai"], env.clients["lan"], env.clients["owner"]
        good = await _make_code(env, pack_id="p550", note="quà")
        expired = await _make_code(env, amount=40)
        revoked = await _make_code(env, amount=30)
        with env.repo.transaction():
            env.repo.conn.execute(
                "UPDATE coin_topup_codes SET expires_at = ? WHERE id = ?",
                (clock.iso(clock.now() - timedelta(minutes=1)), expired["item"]["id"]),
            )
        assert (await owner.post(f"/api/admin/coins/codes/{revoked['item']['id']}/revoke")).status_code == 200
        resp = await mai.post("/api/coins/redeem", json={"code": _iphone(good["code"])})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["amount"] == 550 and data["wallet"]["balance"] == 850 and data["wallet"]["available"] == 850
        assert env.balance("mai") == 850
        rows = env.ledger("mai", "topup_code")
        assert len(rows) == 1
        assert rows[0]["delta"] == 550 and rows[0]["idem_key"] == f"topup:{good['item']['id']}"
        assert rows[0]["code_id"] == good["item"]["id"] and rows[0]["actor_id"] == env.ids["owner"]
        history = (await mai.get("/api/coins/history")).json()["items"]
        assert history[0]["label"] == "Nạp bằng mã" and history[0]["delta"] == 550
        # Dùng lại (cả người khác), hết hạn, đã huỷ, không có thật, sai dạng: cùng một câu.
        unknown = codes.group(codes.random_code())
        for client, code in (
            (mai, good["code"]), (lan, good["code"]), (lan, expired["code"]), (lan, revoked["code"]),
            (lan, unknown), (lan, "abc"), (lan, ""),
        ):
            resp = await client.post("/api/coins/redeem", json={"code": code})
            assert resp.status_code == 422, (code, resp.text)
            body = resp.json()
            assert {k: body.get(k) for k in INVALID} == INVALID, body
        assert env.balance("mai") == 850 and env.balance("lan") == 300
        assert len(env.rows("SELECT id FROM coin_ledger WHERE kind = 'topup_code'")) == 1
        listed = {i["id"]: i for i in (await owner.get("/api/admin/coins/codes")).json()}
        assert listed[good["item"]["id"]]["status"] == "used" and listed[good["item"]["id"]]["used_by_handle"] == "mai"
        assert listed[expired["item"]["id"]]["status"] == "expired"
        assert listed[revoked["item"]["id"]]["status"] == "revoked"
        assert _events(env, "topup_code_redeemed") == [{"pack": "p550"}]
        assert {"source": "topup_code", "amount": 550} in _events(env, "coins_granted")
        assert [e["reason"] for e in _events(env, "topup_code_failed")] == [
            "used", "used", "expired", "revoked", "invalid", "invalid", "invalid",
        ]


async def test_concurrent_redeem_credits_one_account(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan", "binh")) as env:
        for _ in range(3):
            made = await _make_code(env, amount=100)
            before = {w: env.balance(w) for w in ("mai", "lan", "binh")}
            results = await asyncio.gather(
                *(env.clients[w].post("/api/coins/redeem", json={"code": made["code"]}) for w in ("mai", "lan", "binh"))
            )
            assert sorted(r.status_code for r in results) == [200, 422, 422]
            after = {w: env.balance(w) for w in ("mai", "lan", "binh")}
            gained = {w: after[w] - before[w] for w in after}
            assert sorted(gained.values()) == [0, 0, 100]
            rows = env.rows("SELECT account_id FROM coin_ledger WHERE idem_key = ?", f"topup:{made['item']['id']}")
            assert len(rows) == 1
            code_row = env.rows("SELECT used_by FROM coin_topup_codes WHERE id = ?", made["item"]["id"])[0]
            assert code_row["used_by"] == rows[0]["account_id"]


async def test_redeem_rate_limited_after_10_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        now = {"t": clock.now()}
        monkeypatch.setattr(clock, "now", lambda: now["t"])
        mai = env.clients["mai"]
        good = await _make_code(env, amount=70)
        # Dòng thử mã cũ: 31 ngày (bị xoá khi ghi lần thử mới) và 29 ngày (còn giữ).
        with env.repo.transaction():
            for days in (31, 29):
                env.repo.conn.execute(
                    "INSERT INTO coin_code_attempts (account_id, ok, created_at) VALUES (?, 0, ?)",
                    (env.ids["mai"], clock.iso(now["t"] - timedelta(days=days))),
                )
        for i in range(10):
            resp = await mai.post("/api/coins/redeem", json={"code": codes.random_code()})
            assert resp.status_code == 422, (i, resp.text)
            now["t"] += timedelta(minutes=1)
        attempts = env.rows("SELECT created_at FROM coin_code_attempts WHERE account_id = ?", env.ids["mai"])
        assert len(attempts) == 11  # 10 lần mới + dòng 29 ngày; dòng 31 ngày đã bị xoá
        assert min(clock.parse(a[0]) for a in attempts) > now["t"] - timedelta(days=30)
        # Lần thứ 11 trong 60 phút: 429, kể cả mã đúng; mã vẫn còn hiệu lực.
        resp = await mai.post("/api/coins/redeem", json={"code": good["code"]})
        assert resp.status_code == 429, resp.text
        assert resp.json()["code"] == "rate_limited"
        assert resp.json()["detail"] == "Bạn đã thử sai nhiều lần. Hãy đợi một lúc rồi thử lại."
        assert env.balance("mai") == 300
        status = {i["id"]: i["status"] for i in (await env.clients["owner"].get("/api/admin/coins/codes")).json()}
        assert status[good["item"]["id"]] == "active"
        # Giới hạn theo tài khoản: Lan vẫn thử được.
        assert (await env.clients["lan"].post("/api/coins/redeem", json={"code": codes.random_code()})).status_code == 422
        # Lần sai đầu tiên ra khỏi cửa sổ 60 phút: thử lại được.
        now["t"] += timedelta(minutes=52)
        resp = await mai.post("/api/coins/redeem", json={"code": good["code"]})
        assert resp.status_code == 200, resp.text
        assert env.balance("mai") == 370
        assert _events(env, "topup_code_failed")[10] == {"reason": "rate_limited"}


async def test_owner_cannot_redeem_code(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        made = await _make_code(env, amount=60)
        resp = await env.clients["owner"].post("/api/coins/redeem", json={"code": made["code"]})
        assert resp.status_code == 422
        assert resp.json() == {"detail": "Tài khoản quản lý không cần nạp coin.", "code": "topup_code_owner"}
        assert env.rows("SELECT used_at, used_by FROM coin_topup_codes")[0][0] is None
        assert env.rows("SELECT COUNT(*) FROM coin_ledger WHERE account_id = ?", env.ids["owner"])[0][0] == 0
        assert env.rows("SELECT COUNT(*) FROM coin_code_attempts")[0][0] == 0
        listed = (await env.clients["owner"].get("/api/admin/coins/codes")).json()
        assert listed[0]["status"] == "active"
        # Mã vẫn dùng được cho thành viên.
        assert (await env.clients["mai"].post("/api/coins/redeem", json={"code": made["code"]})).status_code == 200
        assert env.balance("mai") == 360


# ---------------------------------------------------------------------------- chủ máy cộng/trừ tay


async def test_owner_adjust_requires_reason_and_never_negative(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        owner = env.clients["owner"]
        url = f"/api/admin/accounts/{env.ids['mai']}/coins"
        for body in (
            {"delta": 20, "request_id": "req-noreason-1"},
            {"delta": 20, "reason": "ab", "request_id": "req-short-001"},
            {"delta": 20, "reason": "  a  ", "request_id": "req-short-002"},
            {"delta": 20, "reason": "x" * 121, "request_id": "req-long-0001"},
            {"delta": 0, "reason": "không đổi", "request_id": "req-zero-0001"},
            {"delta": 10_001, "reason": "quá nhiều", "request_id": "req-big-00001"},
        ):
            resp = await owner.post(url, json=body)
            assert resp.status_code == 422, (body, resp.text)
        assert env.balance("mai") == 300
        too_much = await owner.post(url, json={"delta": -301, "reason": "thu lại", "request_id": "req-minus-001"})
        assert too_much.status_code == 422
        assert too_much.json() == {"detail": "Không trừ được quá số coin dùng được (300 coin).", "code": "adjust_too_large"}
        ok = await owner.post(url, json={"delta": 20, "reason": "thử bot", "request_id": "req-plus-0001"})
        assert ok.status_code == 200 and ok.json() == {"balance": 320, "available": 320}
        again = await owner.post(url, json={"delta": 20, "reason": "thử bot", "request_id": "req-plus-0001"})
        assert again.status_code == 200 and again.json()["balance"] == 320
        rows = env.ledger("mai", "admin_adjust")
        assert len(rows) == 1
        assert rows[0]["actor_id"] == env.ids["owner"] and rows[0]["reason"] == "thử bot" and rows[0]["delta"] == 20
        conflict = await owner.post(url, json={"delta": 25, "reason": "thử bot", "request_id": "req-plus-0001"})
        assert conflict.status_code == 409 and conflict.json()["code"] == "idem_conflict"
        other = await owner.post(
            f"/api/admin/accounts/{env.ids['lan']}/coins", json={"delta": 20, "reason": "thử bot", "request_id": "req-plus-0001"}
        )
        assert other.status_code == 409 and other.json()["code"] == "idem_conflict"
        down = await owner.post(url, json={"delta": -320, "reason": "thu hết", "request_id": "req-minus-002"})
        assert down.status_code == 200 and down.json() == {"balance": 0, "available": 0}
        to_owner = await owner.post(
            f"/api/admin/accounts/{env.ids['owner']}/coins", json={"delta": 5, "reason": "tự cộng", "request_id": "req-owner-001"}
        )
        assert to_owner.status_code == 422
        assert (await owner.post("/api/admin/accounts/999999/coins", json={"delta": 5, "reason": "ai đó", "request_id": "req-none-0001"})).status_code == 404
        # Thành viên thấy lý do trong lịch sử; hàng thành viên ở Quản lý có số coin (chủ máy: null).
        labels = [i["label"] for i in (await env.clients["mai"].get("/api/coins/history")).json()["items"]]
        assert labels[:2] == ["Người quản lý điều chỉnh: thu hết", "Người quản lý điều chỉnh: thử bot"]
        accounts = {a["handle"]: a for a in (await owner.get("/api/admin/accounts")).json()}
        assert accounts["mai"]["coin_balance"] == 0 and accounts["lan"]["coin_balance"] == 300
        assert accounts[next(h for h, a in accounts.items() if a["role"] == "owner")]["coin_balance"] is None
        assert _events(env, "coins_adjusted") == [
            {"amount_bucket": "1_50", "direction": "up"}, {"amount_bucket": "301_plus", "direction": "down"},
        ]


async def test_adjust_during_open_hold_keeps_reply_and_charge(tmp_path: Path) -> None:
    async with coin_env(tmp_path) as env:
        mai, owner = env.clients["mai"], env.clients["owner"]
        story = await new_story(mai)
        env.set_balance("mai", 10)
        env.fake.delay = 0.03
        task = asyncio.create_task(mai.post(f"/api/stories/{story}/messages", json={"content": "Kể tiếp đi."}))
        await until_held(env)
        url = f"/api/admin/accounts/{env.ids['mai']}/coins"
        five = await owner.post(url, json={"delta": -5, "reason": "thu lại", "request_id": "hold-minus-5"})
        assert five.status_code == 422
        assert five.json() == {"detail": "Không trừ được quá số coin dùng được (4 coin).", "code": "adjust_too_large"}
        four = await owner.post(url, json={"delta": -4, "reason": "thu lại", "request_id": "hold-minus-4"})
        assert four.status_code == 200 and four.json() == {"balance": 6, "available": 0}
        resp = await task
        env.fake.delay = 0.0
        assert names(resp.text)[-1] == "done"
        assert env.balance("mai") == 0
        chat = env.ledger("mai", "chat")
        assert len(chat) == 1 and chat[0]["delta"] == -6
        assert len(env.rows("SELECT id FROM messages WHERE story_id = ? AND role = 'assistant'", story)) == 2  # + lời chào


async def until_held(env: Any) -> None:
    for _ in range(600):
        if any(h["status"] == "held" for h in env.holds("mai")):
            return
        await asyncio.sleep(0.005)
    raise AssertionError("không thấy giữ chỗ")


# ---------------------------------------------------------------------------- nhật ký của chủ máy


async def test_admin_coin_log_has_no_story_content(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai, owner = env.clients["mai"], env.clients["owner"]
        story = await new_story(mai)
        secret = "Bí mật riêng của Mai ở hồ sen"
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": secret})).text)[-1] == "done"
        card_id = env.repo.get_story(story, account_id=env.ids["mai"]).card_id
        card_name = env.repo.get_card(card_id, account_id=env.ids["mai"]).name
        made = await _make_code(env, pack_id="p100", note="quà sinh nhật")
        assert (await mai.post("/api/coins/redeem", json={"code": made["code"]})).status_code == 200
        url = f"/api/admin/accounts/{env.ids['lan']}/coins"
        assert (await owner.post(url, json={"delta": -7, "reason": "thu lại lạm dụng", "request_id": "log-adjust-1"})).status_code == 200
        with env.repo.transaction():
            ledger.post(
                env.repo.conn, env.ids["mai"], 100, "creator_milestone", f"milestone:{card_id}:10",
                card_id=card_id, milestone=10,
            )
            # Cũ hơn 30 ngày: có trong nhật ký nhưng không vào tổng 30 ngày.
            ledger.post(
                env.repo.conn, env.ids["lan"], 9, "admin_adjust", "adjust:old-1", actor_id=env.ids["owner"], reason="cũ",
                now=clock.now() - timedelta(days=31),
            )
        resp = await owner.get("/api/admin/coins/log")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        items = data["items"]
        # Mới trước (theo thứ tự ghi sổ); quà tạo tài khoản, câu trả lời không có trong nhật ký.
        assert [(i["kind"], i["delta"]) for i in items] == [
            ("admin_adjust", 9), ("creator_milestone", 100), ("admin_adjust", -7), ("topup_code", 100),
        ]
        by_kind = {(i["kind"], i["delta"]): i for i in items}
        assert by_kind[("topup_code", 100)]["handle"] == "mai" and by_kind[("topup_code", 100)]["note"] == "quà sinh nhật"
        assert by_kind[("admin_adjust", -7)]["handle"] == "lan" and by_kind[("admin_adjust", -7)]["reason"] == "thu lại lạm dụng"
        assert by_kind[("creator_milestone", 100)]["handle"] == "mai" and by_kind[("creator_milestone", 100)]["milestone"] == 10
        # Không story, nhân vật hay nội dung tin nhắn.
        text = resp.text
        assert secret not in text and card_name not in text
        for item in items:
            assert not {"story_id", "card_id", "hold_id", "name", "content"} & set(item), item
        # Tổng 30 ngày: phát (quà tạo tài khoản 2 × 300 + mốc 100), nạp bằng mã 100, tiêu 6.
        assert data["totals"] == {"days": 30, "granted": 700, "topped_up": 100, "spent": 6}
        # 50 dòng mới nhất, chỉ ba loại.
        with env.repo.transaction():
            for i in range(60):
                ledger.post(env.repo.conn, env.ids["lan"], 1, "admin_adjust", f"adjust:bulk-{i}", actor_id=env.ids["owner"], reason=f"đợt {i}")
            ledger.post(env.repo.conn, env.ids["lan"], 5, "mission", "mission:x", mission="ad")
        items = (await owner.get("/api/admin/coins/log")).json()["items"]
        assert len(items) == 50 and items[0]["reason"] == "đợt 59" and items[-1]["reason"] == "đợt 10"
        assert {i["kind"] for i in items} == {"admin_adjust"}
        ids = [i["id"] for i in items]
        assert ids == sorted(ids, reverse=True)
        # Sự kiện của F43 đúng luật events.py, có trong tracking-plan.md §4.
        doc = TRACKING_PLAN.read_text(encoding="utf-8").split("## 4.", 1)[1].split("\n## ", 1)[0]
        for name in F43_EVENTS:
            spec = events.EVENTS[name]
            assert spec.sources == frozenset({"server"}), name
            assert all(isinstance(r, (events.Choice, events.IntChoice)) for r in spec.props.values()), name
            assert re.search(rf"^\|\s*`{name}`\s*\|\s*S\s*\|", doc, flags=re.M), name
        for name, props in (
            ("topup_code_redeemed", {"pack": "custom"}), ("topup_code_failed", {"reason": "rate_limited"}),
            ("topup_code_created", {"pack": "p2500", "expires_days": 30}),
            ("coins_adjusted", {"direction": "down", "amount_bucket": "51_300"}),
        ):
            assert events.validate(name, props, source="server") == props
        for name, props in (
            ("topup_code_failed", {"reason": "wrong_code"}), ("topup_code_created", {"pack": "p100", "expires_days": 3}),
            ("coins_adjusted", {"direction": "up", "amount_bucket": "1_50", "reason": "x"}),
        ):
            with pytest.raises(events.EventRejected):
                events.validate(name, props, source="server")
        for name in ("topup_viewed", "topup_pack_selected"):
            assert events.EVENTS[name].sources == frozenset({"client"})
            assert re.search(rf"^\|\s*`{name}`\s*\|\s*C\s*\|", doc, flags=re.M), name
        recorded = {r[0] for r in env.rows("SELECT name FROM analytics_events")}
        assert {"topup_code_created", "topup_code_redeemed", "coins_adjusted"} <= recorded
