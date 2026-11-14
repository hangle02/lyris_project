"""F42 (docs/coins.md §7, §10.5, §11, §12): lịch sử ví, sự kiện số liệu của coin, xuất/xoá dữ liệu, Điều khoản."""
from __future__ import annotations

import re
from pathlib import Path

from lyris.analytics import events
from lyris.auth import store
from lyris.coins import ledger
from lyris.compliance import account_data, legal
from lyris.config import REPO_ROOT
from lyris.llm.base import LLMError
from tests.authutil import MEMBER_PASSWORD, anon_client
from tests.coinutil import coin_env, names, new_story, studio_chat_body
from tests.test_api_studio import card_body

TRACKING_PLAN = REPO_ROOT / "docs" / "tracking-plan.md"
TRACK_TS = REPO_ROOT / "frontend" / "src" / "lib" / "track.ts"
COIN_EVENTS = {"coins_spent", "coins_released", "coins_insufficient", "coins_granted", "wallet_viewed"}
COIN_TABLES = (
    "coin_wallets", "coin_ledger", "coin_holds", "coin_code_attempts", "coin_ad_views", "creator_players",
)


async def test_history_is_own_paged_and_labelled(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai, lan = env.clients["mai"], env.clients["lan"]
        story = await new_story(mai)
        name = env.repo.get_story(story, account_id=env.ids["mai"]).card_id
        card_name = env.repo.get_card(name, account_id=env.ids["mai"]).name
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào."})).text)[-1] == "done"
        assert names((await mai.post("/api/cards/test-chat", json=await studio_chat_body(mai))).text)[-1] == "done"
        assert (await mai.post("/api/coins/checkin")).json()["granted"] is True
        conn = env.repo.conn
        acc = env.ids["mai"]
        with env.repo.transaction():
            ledger.post(conn, acc, 5, "mission", "m:ad", mission="ad")
            ledger.post(conn, acc, 10, "mission", "m:ch", mission="characters")
            ledger.post(conn, acc, 5, "mission", "m:tu", mission="turns")
            ledger.post(conn, acc, 100, "creator_milestone", "milestone:x:10", card_id=name, milestone=10)
            ledger.post(conn, acc, 550, "topup_code", "topup:1", code_id=1)
            ledger.post(conn, acc, -3, "admin_adjust", "adjust:1", actor_id=env.ids["owner"], reason="bù lỗi máy")
            ledger.post(conn, env.ids["lan"], 7, "mission", "m:lan", mission="ad")
        first = (await mai.get("/api/coins/history")).json()
        labels = [i["label"] for i in first["items"]]
        assert labels == [
            "Người quản lý điều chỉnh: bù lỗi máy", "Nạp bằng mã", f"{card_name} đạt 10 người chơi",
            "Nhiệm vụ: Gửi 20 lượt", "Nhiệm vụ: Trò chuyện với 3 nhân vật khác nhau", "Nhiệm vụ: Xem quảng cáo",
            "Đăng nhập hôm nay", "Chat thử ở Studio", f"Câu trả lời của {card_name}", "Quà tạo tài khoản",
        ]
        assert first["next"] is None
        chat_item = first["items"][-2]
        assert chat_item["delta"] == -6 and chat_item["story_id"] == story and chat_item["name"] == card_name
        assert {"id", "delta", "kind", "label", "created_at", "balance_after"} <= set(chat_item)
        # Chỉ của mình: Lan không thấy dòng nào của Mai và ngược lại.
        lan_items = (await lan.get("/api/coins/history")).json()["items"]
        assert [i["label"] for i in lan_items] == ["Nhiệm vụ: Xem quảng cáo", "Quà tạo tài khoản"]
        assert all(i["delta"] != 7 for i in first["items"])
        # 30 dòng mỗi trang.
        with env.repo.transaction():
            for i in range(35):
                ledger.post(conn, acc, 1, "mission", f"m:bulk:{i}", mission="ad")
        page1 = (await mai.get("/api/coins/history")).json()
        assert len(page1["items"]) == 30 and page1["next"] == page1["items"][-1]["id"]
        page2 = (await mai.get(f"/api/coins/history?before={page1['next']}")).json()
        assert len(page2["items"]) == 15 and page2["next"] is None
        ids = [i["id"] for i in page1["items"] + page2["items"]]
        assert ids == sorted(ids, reverse=True) and len(set(ids)) == 45
        # Chủ máy: lịch sử rỗng, không lỗi.
        assert (await env.clients["owner"].get("/api/coins/history")).json() == {"items": [], "next": None}


async def test_history_label_never_shows_other_accounts_card_name(tmp_path: Path) -> None:
    """id story/card được dùng lại sau khi xoá (SQLite không AUTOINCREMENT): lịch sử ví và file xuất của Mai không
    bao giờ hiện tên nhân vật riêng tư của Lan; dòng thưởng mốc trỏ card id của người khác cũng vậy."""
    secret = "Bí mật riêng của Lan"
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai, lan = env.clients["mai"], env.clients["lan"]
        story = await new_story(mai)
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào anh."})).text)[-1] == "done"
        assert (await mai.delete(f"/api/stories/{story}")).status_code == 200
        body = await studio_chat_body(lan)
        made = await lan.post("/api/cards", json={"card": card_body(name=secret)})
        assert made.status_code == 200, made.text
        lan_card = made.json()["id"]
        lan_story = await lan.post("/api/stories", json={"card_id": lan_card, "persona_id": body["persona_id"]})
        assert lan_story.status_code == 200, lan_story.text
        assert lan_story.json()["id"] == story  # id story của Mai được dùng lại cho story của Lan
        with env.repo.transaction():
            ledger.post(
                env.repo.conn, env.ids["mai"], 100, "creator_milestone", "milestone:test:10",
                card_id=lan_card, milestone=10,
            )
        items = (await mai.get("/api/coins/history")).json()["items"]
        labels = [i["label"] for i in items]
        assert all("Lan" not in label for label in labels), labels
        assert "nhân vật đạt 10 người chơi" in labels, labels  # card id của Lan: không lấy tên
        assert all(i.get("name") != secret for i in items), items
        exported = (await mai.get("/api/account/export")).json()
        assert all("Lan" not in r["label"] for r in exported["coins"]["ledger"]), exported["coins"]["ledger"]
        # Lan vẫn thấy tên nhân vật của chính mình.
        own = (await lan.post(f"/api/stories/{lan_story.json()['id']}/messages", json={"content": "Chào."})).text
        assert names(own)[-1] == "done"
        assert (await lan.get("/api/coins/history")).json()["items"][0]["label"].endswith(secret)


async def test_coin_events_follow_the_strict_schema(tmp_path: Path) -> None:
    assert COIN_EVENTS <= set(events.EVENTS)
    for name in COIN_EVENTS:
        spec = events.EVENTS[name]
        for rule in spec.props.values():
            assert isinstance(rule, (events.Choice, events.Flag, events.Count, events.IntChoice)), name
    assert events.EVENTS["wallet_viewed"].sources == frozenset({"client"})
    assert all(events.EVENTS[n].sources == frozenset({"server"}) for n in COIN_EVENTS - {"wallet_viewed"})
    source = events.EVENTS["coins_granted"].props["source"]
    assert isinstance(source, events.Choice) and "backfill" not in source.values
    assert {"signup", "daily"} <= source.values
    reason = events.EVENTS["coins_released"].props["reason"]
    assert isinstance(reason, events.Choice)
    assert reason.values == {"error", "empty", "cancelled", "queue_timeout", "save_failed", "invalid", "restart"}
    doc = TRACKING_PLAN.read_text(encoding="utf-8")
    section4 = doc.split("## 4.", 1)[1].split("\n## ", 1)[0]
    for name in COIN_EVENTS:
        assert re.search(rf"^\|\s*`{name}`\s*\|", section4, flags=re.M), name
    ts = TRACK_TS.read_text(encoding="utf-8")
    client_block = ts.split("export const CLIENT_EVENTS", 1)[1].split("} as const", 1)[0]
    assert re.search(r"^\s*wallet_viewed:", client_block, flags=re.M)
    # Ghi đúng chỗ: tạo tài khoản, quà đăng nhập, trừ, nhả, hết coin.
    async with coin_env(tmp_path, ("mai",)) as env:
        invite = await env.clients["owner"].post("/api/admin/invites", json={"note": "moi"})
        body = {
            "invite_code": invite.json()["code"], "handle": "moi", "display_name": "Mới", "password": MEMBER_PASSWORD,
            "accept_terms": True, "terms_version": legal.LEGAL_VERSION,
        }
        async with anon_client(env.app) as c:
            assert (await c.post("/api/auth/signup", json=body)).status_code == 200
        mai = env.clients["mai"]
        await mai.post("/api/coins/checkin")
        story = await new_story(mai)
        await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào."})
        env.fake.error = LLMError("hỏng")
        await mai.post(f"/api/stories/{story}/messages", json={"content": "Nữa."})
        env.fake.error = None
        env.set_balance("mai", 0)
        assert (await mai.post(f"/api/stories/{story}/reply")).status_code == 402
        got = env.rows("SELECT name, props_json FROM analytics_events WHERE name LIKE 'coins_%' ORDER BY id")
        assert [tuple(r) for r in got] == [
            ("coins_granted", '{"amount":300,"source":"signup"}'),
            ("coins_granted", '{"amount":60,"source":"daily"}'),
            ("coins_spent", '{"kind":"send","mode":"story"}'),
            ("coins_released", '{"kind":"send","reason":"error"}'),
            ("coins_insufficient", '{"kind":"retry","mode":"story"}'),
        ]


async def test_export_has_coins_and_delete_removes_coin_rows(tmp_path: Path) -> None:
    async with coin_env(tmp_path, ("mai", "lan")) as env:
        mai = env.clients["mai"]
        story = await new_story(mai)
        assert names((await mai.post(f"/api/stories/{story}/messages", json={"content": "Chào."})).text)[-1] == "done"
        exported = (await mai.get("/api/account/export")).json()
        assert exported["coins"]["balance"] == 294
        ledger_rows = exported["coins"]["ledger"]
        assert [(r["kind"], r["delta"]) for r in ledger_rows] == [("signup_grant", 300), ("chat", -6)]
        assert {"created_at", "balance_after", "label"} <= set(ledger_rows[0])
        # Lan là actor_id của một dòng sổ của Mai: xoá Lan được, dòng đó còn, actor_id thành NULL.
        mai_id, lan_id = env.ids["mai"], env.ids["lan"]
        with env.repo.transaction():
            row = ledger.post(env.repo.conn, mai_id, 3, "admin_adjust", "adjust:actor", actor_id=lan_id, reason="thử")
        account_data.delete_account(env.repo, lan_id)
        kept = env.rows("SELECT actor_id, delta FROM coin_ledger WHERE id = ?", row.id)
        assert [tuple(r) for r in kept] == [(None, 3)]
        # Mai cũng có mặt ở các bảng coin còn lại: mã nạp (người tạo / người dùng), người chơi và mốc của nhân vật.
        mai_card = env.rows("SELECT card_id FROM stories WHERE id = ?", story)[0][0]
        with env.repo.transaction():
            code = env.repo.conn.execute(
                "INSERT INTO coin_topup_codes (code_hash, code_hint, amount, created_by, created_at, expires_at,"
                " used_by, used_at) VALUES (x'00ff', 'ABCD', 100, ?, '2026-11-14T00:00:00.000Z',"
                " '2026-12-14T00:00:00.000Z', ?, '2026-11-14T01:00:00.000Z')",
                (mai_id, mai_id),
            ).lastrowid
            env.repo.conn.execute(
                "INSERT INTO creator_players (card_id, player_id, creator_id, qualified_at)"
                " VALUES (?, ?, ?, '2026-11-14T00:00:00.000Z')",
                (mai_card, mai_id, mai_id),
            )
            env.repo.conn.execute(
                "INSERT INTO creator_milestones (card_id, milestone, creator_id, outcome, reached_at)"
                " VALUES (?, 10, ?, 'paid', '2026-11-14T00:00:00.000Z')",
                (mai_card, mai_id),
            )
            # F44 làm lại: bậc xếp hạng và thưởng công khai lần đầu (docs/coins.md §2.2).
            env.repo.conn.execute(
                "INSERT INTO creator_rank_tiers (card_id, tier, creator_id, rank, outcome, reached_at)"
                " VALUES (?, 10, ?, 3, 'waiting', '2026-11-14T00:00:00.000Z')",
                (mai_card, mai_id),
            )
            env.repo.conn.execute(
                "INSERT INTO creator_first_public (account_id, card_id, ledger_id, paid_at)"
                " VALUES (?, ?, 1, '2026-11-14T00:00:00.000Z')",
                (mai_id, mai_card),
            )
        # Xoá Mai: không còn dòng nào của Mai trong mọi bảng coin.
        account_data.delete_account(env.repo, mai_id)
        for table in COIN_TABLES:
            column = "player_id" if table == "creator_players" else "account_id"
            assert env.rows(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", mai_id)[0][0] == 0, table
        for table in ("creator_players", "creator_milestones", "creator_rank_tiers"):
            assert env.rows(f"SELECT COUNT(*) FROM {table} WHERE creator_id = ?", mai_id)[0][0] == 0, table
        assert env.rows("SELECT COUNT(*) FROM creator_first_public WHERE account_id = ?", mai_id)[0][0] == 0
        # Mã nạp còn (chủ máy cần nhật ký), nhưng không còn trỏ tới Mai.
        assert [tuple(r) for r in env.rows("SELECT created_by, used_by FROM coin_topup_codes WHERE id = ?", code)] == [
            (None, None)
        ]
        with env.repo.locked() as conn:
            assert store.account_by_id(conn, mai_id) is None


def _heading_section(text: str, title: str) -> str:
    """Nội dung dưới tiêu đề Markdown (##/###) kết thúc bằng `title`, tới tiêu đề cùng cấp hoặc cao hơn kế tiếp."""
    match = re.search(rf"^(#{{2,3}}) [^\n]*\b{title}\s*$", text, flags=re.M)
    if match is None:
        return ""
    level = len(match.group(1))
    rest = text[match.end():]
    nxt = re.search(rf"^#{{2,{level}}} ", rest, flags=re.M)
    return rest[: nxt.start()] if nxt else rest


async def test_terms_have_coin_section_and_version_bumped(tmp_path: Path) -> None:
    terms = (REPO_ROOT / "docs" / "legal" / "terms.md").read_text(encoding="utf-8")
    privacy = (REPO_ROOT / "docs" / "legal" / "privacy.md").read_text(encoding="utf-8")
    vi, en = terms.split("## English", 1)
    vi_coin = _heading_section(vi, "Coin")
    en_coin = _heading_section(en, "Coins")
    assert vi_coin.strip() and en_coin.strip()
    for phrase in (
        "không phải tiền", "không đổi ra tiền", "không chuyển", "mất", "chế độ thử", "chưa bán coin",
        "mã nạp", "được tặng, không bán", "đặt lại về 0", "30 ngày",
    ):
        assert phrase in vi_coin.lower(), phrase
    for phrase in (
        "not money", "cannot be exchanged for money", "cannot be transferred", "lost", "test mode", "does not sell coins",
        "top-up codes", "given, never sold", "reset to 0", "30 days",
    ):
        assert phrase in en_coin.lower(), phrase
    pvi, pen = privacy.split("## English", 1)
    assert "sổ coin" in pvi.lower() and "coin ledger" in pen.lower()
    assert legal.LEGAL_VERSION != "2026-11-15"
    assert legal.LEGAL_VERSION in terms and legal.LEGAL_VERSION in privacy
    # Tài khoản đã đồng ý bản cũ (kể cả chủ máy) được hỏi lại một lần.
    async with coin_env(tmp_path, ("mai",)) as env:
        with env.repo.transaction():
            env.repo.conn.execute("UPDATE accounts SET privacy_version = '2026-11-15', terms_accepted_at = '2026-11-14T00:00:00.000Z'")
        for who in ("owner", "mai"):
            me = (await env.clients[who].get("/api/auth/me")).json()
            assert me["account"]["terms_required"] is True, who
            done = await env.clients[who].post("/api/account/terms", json={"accept_terms": True, "version": legal.LEGAL_VERSION})
            assert done.status_code == 200, done.text
            assert (await env.clients[who].get("/api/auth/me")).json()["account"]["terms_required"] is False
