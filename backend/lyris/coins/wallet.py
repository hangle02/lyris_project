"""`CoinService`: ví, giữ chỗ/trừ/nhả khi chat, quà đăng nhập, lịch sử (docs/coins.md §1–§3, §7, §10.5).

App luôn dựng một `CoinService` (`lyris/api/app.py`). `enabled=False` (`LYRIS_COINS=0`) hoặc chủ máy thì `hold` trả
None: không giữ chỗ, không trừ. `ChatService` dựng không có `coins` (None) thì không tính coin (test cũ).

Sự kiện số liệu (§11) đi qua `track(name, props)` do route đưa vào (đã chốt ngữ cảnh request); `charge`/`release`
dùng `track` đã gắn vào giữ chỗ. Không bao giờ có chữ tự do trong thuộc tính.
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from lyris.auth import clock as auth_clock
from lyris.coins import creator as creator_mod
from lyris.coins import hot as hot_mod
from lyris.coins import holds as holds_mod
from lyris.coins import ledger, topup
from lyris.coins import missions as missions_mod
from lyris.coins import packs as packs_mod
from lyris.coins.clock import coin_day
from lyris.coins.errors import (
    ADJUST_OWNER_DETAIL,
    DAILY_GRANT,
    PRICE_PER_REPLY,
    AdjustRejected,
    CoinsRequired,
    adjust_too_large_detail,
)
from lyris.db.repo import NotFound, Repo
from lyris.models import Story

logger = logging.getLogger("lyris.coins")

# (tên sự kiện, thuộc tính) → ghi số liệu. None = không ghi.
CoinTrack = Callable[[str, Mapping[str, Any]], None]

HISTORY_PAGE = 30
HISTORY_MAX = 100
ADJUST_MAX = 10_000

# §10.5: chữ của lịch sử (server dựng `label`).
LABEL_SIGNUP = "Quà tạo tài khoản"
LABEL_BACKFILL = "Quà mở ví"
LABEL_DAILY = "Đăng nhập hôm nay"
LABEL_TEST_CHAT = "Chat thử ở Studio"
LABEL_TOPUP = "Nạp bằng mã"
LABEL_MISSION = {
    "ad": "Nhiệm vụ: Xem quảng cáo",
    "characters": "Nhiệm vụ: Trò chuyện với 3 nhân vật khác nhau",
    "turns": "Nhiệm vụ: Gửi 20 lượt",
}
FALLBACK_NAME = "nhân vật"


def chat_label(name: str) -> str:
    return f"Câu trả lời của {name}"


def adjust_label(reason: str | None) -> str:
    return f"Người quản lý điều chỉnh: {reason}" if reason else "Người quản lý điều chỉnh"


def milestone_label(name: str, milestone: int) -> str:
    """Nhãn dòng thưởng mốc cũ (`milestone:`), giữ trong lịch sử từ khi F44 làm lại."""
    return f"{name} đạt {milestone} người chơi"


def amount_bucket(delta: int) -> str:
    """Nhóm số coin của `coins_adjusted` (§11): không ghi số chính xác."""
    size = abs(delta)
    return "1_50" if size <= 50 else "51_300" if size <= 300 else "301_plus"


@dataclass
class Hold:
    """Một giữ chỗ đang mở cho một lượt sinh. `settled`: đã trừ hoặc đã nhả."""

    id: int
    account_id: int
    mode: str
    kind: str
    amount: int
    story_id: int | None
    card_id: int | None
    track: CoinTrack | None = field(default=None, repr=False)
    settled: bool = False
    charged: bool = False


def _emit(track: CoinTrack | None, name: str, props: Mapping[str, Any]) -> None:
    if track is None:
        return
    try:
        track(name, props)
    except Exception:  # số liệu không bao giờ làm hỏng lượt chat
        logger.warning("Không ghi được sự kiện %s", name)


class CoinService:
    def __init__(self, repo: Repo, *, enabled: bool = True, ad_seconds: int = missions_mod.AD_SECONDS) -> None:
        self.repo = repo
        self.enabled = enabled
        self.price = PRICE_PER_REPLY
        self.ad_seconds = ad_seconds
        # F44: sự kiện của người tạo (thưởng mốc) ghi tách khỏi request của người chơi (`Tracker.emit_detached`).
        # app gắn sau khi dựng Tracker; None (test, script) thì không ghi.
        self.tracker: Any = None
        # Giữ chỗ mà một lượt sinh của TIẾN TRÌNH NÀY còn đang dùng (bỏ ra khi trừ hay nhả xong, dù thành công hay
        # lỗi). Một giữ chỗ `held` của tài khoản không có ở đây là mồ côi (nhả lỗi, transaction lưu bị cuộn lại):
        # `hold()` nhả nó (lý do `error`) thay vì 409 mãi tới khi khởi động lại. Cổng sinh đã bảo đảm mỗi tài khoản
        # chỉ một lượt sinh trong tiến trình (app chạy một tiến trình; giữ chỗ của lần chạy trước nhả trong lifespan).
        self._live: set[int] = set()

    # ------------------------------------------------------------------ ai bị tính coin

    def _role(self, conn: sqlite3.Connection, account_id: int) -> str | None:
        row = conn.execute("SELECT role FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return None if row is None else str(row[0])

    def is_owner(self, account_id: int) -> bool:
        with self.repo.locked() as conn:
            return self._role(conn, account_id) == "owner"

    def charges(self, account_id: int) -> bool:
        """Tài khoản này có bị tính coin không (coin bật và là thành viên)."""
        return self.enabled and not self.is_owner(account_id)

    # ------------------------------------------------------------------ giữ chỗ / trừ / nhả

    def _card_refs(self, conn: sqlite3.Connection, card_id: int) -> tuple[int, int | None]:
        """(char_key, origin_card_id): bản sao nhân vật công khai đếm theo nhân vật gốc."""
        row = conn.execute("SELECT story_copy, origin_card_id FROM character_cards WHERE id = ?", (card_id,)).fetchone()
        if row is not None and row[0] and row[1] is not None:
            return int(row[1]), int(row[1])
        return card_id, None

    def hold(
        self,
        account_id: int,
        *,
        story: Story | None,
        mode: str,
        kind: str,
        track: CoinTrack | None = None,
    ) -> Hold | None:
        """Giữ chỗ `price` coin trước khi sinh. None khi coin tắt hoặc là chủ máy.
        `CoinsRequired` (402) khi số dùng được < giá; `HoldBusy` khi đã có giữ chỗ mở."""
        if not self.enabled:
            return None
        story_id = story.id if story is not None else None
        card_id = story.card_id if story is not None else None
        try:
            with self.repo.transaction():
                conn = self.repo.conn
                if self._role(conn, account_id) != "member":
                    return None
                char_key: int | None = None
                origin: int | None = None
                if card_id is not None:
                    char_key, origin = self._card_refs(conn, card_id)
                self._release_orphans(conn, account_id)
                hold_id = holds_mod.open_hold(
                    conn, account_id, story_id=story_id, char_key=char_key, origin_card_id=origin,
                    mode=mode, kind=kind, amount=self.price,
                )
        except CoinsRequired:
            _emit(track, "coins_insufficient", {"mode": mode, "kind": kind})
            raise
        self._live.add(hold_id)
        return Hold(
            id=hold_id, account_id=account_id, mode=mode, kind=kind, amount=self.price,
            story_id=story_id, card_id=card_id, track=track,
        )

    def _release_orphans(self, conn: sqlite3.Connection, account_id: int) -> None:
        """Nhả (lý do `error`) giữ chỗ `held` của tài khoản mà không lượt sinh nào của tiến trình này còn dùng."""
        rows = conn.execute(
            "SELECT id FROM coin_holds WHERE account_id = ? AND status = 'held'", (account_id,)
        ).fetchall()
        for row in rows:
            hold_id = int(row[0])
            if hold_id in self._live:
                continue
            if holds_mod.release_hold(conn, hold_id, "error"):
                logger.warning("Nhả giữ chỗ coin mồ côi %s của tài khoản %s", hold_id, account_id)

    def charge(self, hold: Hold, message_id: int | None) -> bool:
        """Trừ giữ chỗ (câu trả lời có chữ đã/đang được lưu). Gọi bên trong transaction lưu câu trả lời.
        Không bao giờ raise: lỗi thì log, câu trả lời vẫn được lưu. True nếu đã trừ."""
        if hold.settled:
            return hold.charged
        try:
            with self.repo.transaction():
                entry = holds_mod.charge_hold(
                    self.repo.conn, hold.id, message_id=message_id, story_id=hold.story_id, card_id=hold.card_id
                )
                if entry is not None:
                    self._note_player(hold.id)
        except Exception:
            logger.exception("Không trừ được giữ chỗ coin %s (câu trả lời vẫn được lưu)", hold.id)
            return False
        finally:
            self._live.discard(hold.id)
        hold.settled = True
        if entry is None:
            logger.error("Giữ chỗ coin %s không còn 'held' lúc trừ: không trừ, câu trả lời vẫn được lưu", hold.id)
            return False
        hold.charged = True
        _emit(hold.track, "coins_spent", {"mode": hold.mode, "kind": hold.kind})
        return True

    # ------------------------------------------------------------------ người chơi, bảng Nhân vật hot, thưởng (F44, F46)

    def _note_player(self, hold_id: int) -> list[int]:
        """Ghi người chơi sau một lần trừ (cùng transaction, SAVEPOINT riêng). Lỗi ở đây không bao giờ làm mất lần
        trừ hay câu trả lời: chỉ phần F44 bị cuộn lại."""
        try:
            return creator_mod.note_charged(self.repo.conn, hold_id)
        except Exception:
            logger.exception("Không ghi được người chơi sau giữ chỗ %s", hold_id)
            return []

    def _emit_refresh(self, result: hot_mod.Refresh | None, payments: list[hot_mod.Payment] | None = None) -> None:
        """Sự kiện của người tạo (bậc xếp hạng, thưởng): ghi tách khỏi request (`Tracker.emit_detached`), không tên
        nhân vật. Không bao giờ raise."""
        tracker = self.tracker
        if tracker is None:
            return
        from lyris.analytics.tracker import TrackContext

        reached = result.reached if result is not None else []
        paid = list(result.payments if result is not None else []) + list(payments or [])
        try:
            for r in reached:
                ctx = TrackContext(account_id=r.creator_id, anon_id="")
                tracker.emit_detached(ctx, "creator_rank_reached", {"tier": r.tier, "paid": r.paid})
            for p in paid:
                ctx = TrackContext(account_id=p.account_id, anon_id="")
                tracker.emit_detached(ctx, "coins_granted", {"source": p.source, "amount": p.amount})
        except Exception:  # số liệu không bao giờ làm hỏng việc trả thưởng
            logger.warning("Không ghi được sự kiện thưởng sáng tác")

    def refresh_hot(self, *, force: bool = False) -> hot_mod.Refresh | None:
        """Tính lại bảng "Nhân vật hot" khi đã cũ hơn 60 phút (`force`: tính ngay) và trả thưởng xếp hạng / công khai
        lần đầu trong cùng transaction (coin tắt: chỉ tính bảng, thưởng chờ). Không bao giờ raise: lỗi chỉ ghi log,
        bảng cũ giữ nguyên, lần sau tính lại. Bảng còn mới thì chỉ đọc (không mở transaction ghi, không giữ khoá ghi
        của SQLite): mỗi lần mở Khám phá hay checkin không chặn việc ghi khác."""
        try:
            if not force:
                with self.repo.locked() as conn:
                    if not hot_mod.is_stale(conn, auth_clock.now()):
                        return None
            with self.repo.transaction():
                conn = self.repo.conn
                if force:
                    result: hot_mod.Refresh | None = hot_mod.compute(conn, coins=self.enabled)
                else:
                    result = hot_mod.refresh_if_stale(conn, coins=self.enabled)
        except Exception:
            logger.exception("Không tính được bảng Nhân vật hot")
            return None
        self._emit_refresh(result)
        return result

    def first_public(self, account_id: int) -> list[hot_mod.Payment]:
        """Thưởng công khai lần đầu của một tài khoản (checkin). Không bao giờ raise."""
        if not self.enabled:
            return []
        try:
            with self.repo.transaction():
                paid = hot_mod.first_public_check(self.repo.conn, coins=True, account_id=account_id)
        except Exception:
            logger.exception("Không trả được thưởng công khai lần đầu của tài khoản %s", account_id)
            return []
        self._emit_refresh(None, paid)
        return paid

    def hot_board(self, limit: int = hot_mod.BOARD_SIZE) -> dict[str, Any]:
        """`GET /api/explore/hot`: tính lại nếu đã cũ (không bao giờ raise), rồi đọc bảng mới nhất."""
        self.refresh_hot()
        with self.repo.locked() as conn:
            return hot_mod.board(conn, limit)

    def creator_progress(self, card_id: int, *, owner: bool) -> dict[str, int | None]:
        """`creator` của `GET /api/cards/{id}` (chủ nhân vật công khai). Chủ máy / coin tắt: `next_reward` None."""
        with self.repo.locked() as conn:
            return hot_mod.progress(conn, card_id, rewards=self.enabled and not owner)

    def release(self, hold: Hold, reason: str, *, force: bool = False) -> bool:
        """Nhả giữ chỗ (không có chữ được lưu). Không bao giờ raise. True nếu vừa nhả.
        `force`: không tin cờ `settled` trong bộ nhớ (transaction lưu câu trả lời bị cuộn lại SAU khi `charge` đã
        đánh dấu): nhả theo DB, chỉ khi giữ chỗ còn `held`."""
        if hold.settled and not force:
            return False
        try:
            with self.repo.transaction():
                done = holds_mod.release_hold(self.repo.conn, hold.id, reason)
        except Exception:
            logger.exception("Không nhả được giữ chỗ coin %s", hold.id)
            return False
        finally:
            self._live.discard(hold.id)
        hold.settled = True
        if done:
            hold.charged = False
        if done:
            _emit(hold.track, "coins_released", {"kind": hold.kind, "reason": reason})
        return done

    def release_stale(self) -> list[tuple[int, str]]:
        """Nhả mọi giữ chỗ còn `held` (lý do `restart`). CHỈ gọi trong `lifespan` của app, trước khi nhận request:
        CLI, `migrate()`, script hay test mở DB không bao giờ gọi (app có thể đang sinh)."""
        with self.repo.transaction():
            return holds_mod.release_open_holds(self.repo.conn, "restart")

    # ------------------------------------------------------------------ ví

    def wallet(self, account_id: int) -> dict[str, Any]:
        with self.repo.transaction():
            conn = self.repo.conn
            owner = self._role(conn, account_id) == "owner"
            if owner:
                return {
                    "balance": 0, "available": 0, "unlimited": True, "price_per_reply": self.price,
                    "enabled": self.enabled,
                }
            ledger.ensure_wallet(conn, account_id)
            bal = ledger.balance(conn, account_id)
            available = max(0, bal - ledger.held(conn, account_id))
        return {
            "balance": bal, "available": available, "unlimited": False, "price_per_reply": self.price,
            "enabled": self.enabled,
        }

    def checkin(self, account_id: int, *, track: CoinTrack | None = None) -> dict[str, Any]:
        """Quà đăng nhập trong ngày (+60, `daily:<id>:<ngày coin>`), một lần mỗi ngày coin (§3.4).
        Chủ máy và coin tắt: không có quà."""
        day = coin_day()
        granted = False
        today = 0
        if self.charges(account_id):
            with self.repo.transaction():
                entry = ledger.post(
                    self.repo.conn, account_id, DAILY_GRANT, "daily_login", f"daily:{account_id}:{day}"
                )
            granted = entry.created
            today = DAILY_GRANT
            if granted:
                _emit(track, "coins_granted", {"source": "daily", "amount": DAILY_GRANT})
        # F46 (§5.2): mỗi lần mở app, bảng "Nhân vật hot" được tính lại nếu đã cũ hơn 60 phút (thưởng xếp hạng được trả
        # dù không ai mở bảng); F44 (§5.5): thưởng công khai lần đầu của chính tài khoản này.
        self.refresh_hot()
        if self.charges(account_id):
            self.first_public(account_id)
        return {
            "granted": granted,
            "amount": DAILY_GRANT if granted else 0,
            "today": today,
            "coin_day": day,
            "wallet": self.wallet(account_id),
        }

    # ------------------------------------------------------------------ chủ máy cộng/trừ tay (§4.4)

    def adjust(
        self,
        account_id: int,
        delta: int,
        reason: str,
        request_id: str,
        *,
        actor_id: int,
        track: CoinTrack | None = None,
    ) -> dict[str, Any]:
        """Chủ máy cộng/trừ coin có lý do. Trừ tối đa số coin dùng được (số dư − giữ chỗ), kiểm và ghi trong một
        transaction; cùng `request_id` cùng nội dung thì trả kết quả cũ (khác: `IdemConflict`)."""
        if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or abs(delta) > ADJUST_MAX:
            raise ValueError("delta phải là số nguyên khác 0, từ -10.000 tới 10.000")
        key = f"adjust:{request_id}"
        with self.repo.transaction():
            conn = self.repo.conn
            role = self._role(conn, account_id)
            if role is None:
                raise NotFound("Không tìm thấy tài khoản.")
            if role == "owner":
                raise AdjustRejected("adjust_owner", ADJUST_OWNER_DETAIL)
            replay = conn.execute("SELECT 1 FROM coin_ledger WHERE idem_key = ?", (key,)).fetchone() is not None
            if not replay and delta < 0:
                ledger.ensure_wallet(conn, account_id)
                available = ledger.balance(conn, account_id) - ledger.held(conn, account_id)
                if -delta > available:
                    raise AdjustRejected("adjust_too_large", adjust_too_large_detail(available))
            entry = ledger.post(conn, account_id, delta, "admin_adjust", key, actor_id=actor_id, reason=reason)
        if entry.created:
            _emit(track, "coins_adjusted", {"direction": "up" if delta > 0 else "down", "amount_bucket": amount_bucket(delta)})
        wallet = self.wallet(account_id)
        return {"balance": wallet["balance"], "available": wallet["available"]}

    # ------------------------------------------------------------------ nạp coin, chế độ thử (F43, §4)

    def packs(self) -> dict[str, Any]:
        return {
            "test_mode": packs_mod.TEST_MODE,
            "packs": [{"id": p.id, "coins": p.coins, "bonus": p.bonus, "price_vnd": p.price_vnd} for p in packs_mod.PACKS],
            "contact": packs_mod.CONTACT,
        }

    def create_code(
        self,
        actor_id: int,
        *,
        amount: int | None,
        pack_id: str | None,
        note: str,
        days: int,
        track: CoinTrack | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Chủ máy tạo mã nạp: một gói (`pack_id`) HOẶC một số coin (`amount`). Mã đầy đủ chỉ trả về lần này."""
        if (pack_id is None) == (amount is None):
            raise ValueError("chọn một gói hoặc nhập số coin")
        if pack_id is not None:
            found = packs_mod.pack(pack_id)
            if found is None:
                raise ValueError("gói không hợp lệ")
            amount = found.coins
        assert amount is not None
        now = auth_clock.now()
        with self.repo.transaction():
            item, code = topup.create_code(
                self.repo.conn, actor_id=actor_id, amount=amount, pack_id=pack_id, note=note, days=days, now=now
            )
        _emit(track, "topup_code_created", {"pack": pack_id or "custom", "expires_days": days})
        logger.info("Chủ máy tạo mã nạp số %d (…%s, %d coin)", item["id"], item["hint"], item["amount"])
        return item, code

    def list_codes(self) -> list[dict[str, Any]]:
        with self.repo.locked() as conn:
            return topup.list_codes(conn, auth_clock.now())

    def revoke_code(self, code_id: int) -> dict[str, Any]:
        with self.repo.transaction():
            return topup.revoke_code(self.repo.conn, code_id, auth_clock.now())

    def redeem(self, account_id: int, raw: str | None, *, track: CoinTrack | None = None) -> dict[str, Any]:
        """Thành viên nhập mã nạp. Chủ máy: 422 `topup_code_owner` (mã không bị dùng). Sai/hết hạn/đã dùng/đã huỷ:
        cùng 422 `topup_code_invalid`; 10 lần sai trong 60 phút: 429 `rate_limited` (kể cả mã đúng)."""
        with self.repo.transaction():
            conn = self.repo.conn
            if self._role(conn, account_id) == "owner":
                raise topup.owner_rejected()
            outcome = topup.redeem(conn, account_id, raw, auth_clock.now())
        if not outcome.ok:
            _emit(track, "topup_code_failed", {"reason": outcome.reason})
            raise topup.rate_limited() if outcome.reason == "rate_limited" else topup.invalid()
        _emit(track, "coins_granted", {"source": "topup_code", "amount": outcome.amount})
        _emit(track, "topup_code_redeemed", {"pack": outcome.pack})
        return {"amount": outcome.amount, "wallet": self.wallet(account_id)}

    def admin_log(self) -> dict[str, Any]:
        with self.repo.locked() as conn:
            return topup.admin_log(conn, auth_clock.now())

    # ------------------------------------------------------------------ nhiệm vụ ngày, quảng cáo mẫu (F45, §6)

    def _member_missions(self, conn: sqlite3.Connection, account_id: int) -> None:
        """Chủ máy và coin tắt: không có nhiệm vụ (409 `no_missions`)."""
        if not self.enabled or self._role(conn, account_id) != "member":
            raise missions_mod.MissionRejected("no_missions", missions_mod.NO_MISSIONS_DETAIL)

    def missions(self, account_id: int) -> dict[str, Any]:
        """`GET /api/coins/missions`. Chủ máy / coin tắt: `missions: []` (`unlimited` cho chủ máy)."""
        with self.repo.transaction():
            conn = self.repo.conn
            owner = self._role(conn, account_id) == "owner"
            if owner or not self.enabled:
                data: dict[str, Any] = {
                    "coin_day": coin_day(), "earned_today": 0, "cap": missions_mod.DAILY_CAP, "missions": [],
                }
            else:
                ledger.ensure_wallet(conn, account_id)
                data = missions_mod.view(conn, account_id)
        data["unlimited"] = owner
        data["enabled"] = self.enabled
        return data

    def _granted(self, track: CoinTrack | None, mission: str, amount: int) -> None:
        _emit(track, "coins_granted", {"source": f"mission_{mission}", "amount": amount})
        _emit(track, "mission_claimed", {"mission": mission})

    def claim_mission(self, account_id: int, mission: str, *, track: CoinTrack | None = None) -> dict[str, Any]:
        """Nhận thưởng `characters` / `turns` (nút "Nhận"). Bấm hai lần: dòng cũ, không cộng thêm."""
        with self.repo.transaction():
            conn = self.repo.conn
            self._member_missions(conn, account_id)
            entry = missions_mod.post_mission(conn, account_id, mission)
        if entry.created:
            self._granted(track, mission, entry.delta)
        return {"amount": entry.delta, "wallet": self.wallet(account_id)}

    def start_ad(self, account_id: int, *, track: CoinTrack | None = None) -> dict[str, Any]:
        with self.repo.transaction():
            conn = self.repo.conn
            self._member_missions(conn, account_id)
            out = missions_mod.start_ad(conn, account_id, seconds=self.ad_seconds)
        _emit(track, "ad_started", {})
        return out

    def claim_ad(self, account_id: int, ad_id: int, *, track: CoinTrack | None = None) -> dict[str, Any]:
        with self.repo.transaction():
            conn = self.repo.conn
            self._member_missions(conn, account_id)
            amount, created = missions_mod.claim_ad(conn, account_id, ad_id, seconds=self.ad_seconds)
        if created:
            self._granted(track, "ad", amount)
        return {"amount": amount, "wallet": self.wallet(account_id)}

    def cancel_ad(self, account_id: int, ad_id: int) -> dict[str, Any]:
        with self.repo.transaction():
            missions_mod.cancel_ad(self.repo.conn, account_id, ad_id)
        return {"ok": True}

    # ------------------------------------------------------------------ lịch sử

    def history(self, account_id: int, *, before: int | None = None, limit: int = HISTORY_PAGE) -> dict[str, Any]:
        """Dòng sổ của CHÍNH tài khoản này, mới trước, `limit` dòng mỗi trang (`next` = id để xem thêm)."""
        limit = max(1, min(limit, HISTORY_MAX))
        with self.repo.locked() as conn:
            params: list[Any] = [account_id]
            where = "account_id = ?"
            if before is not None:
                where += " AND id < ?"
                params.append(before)
            rows = conn.execute(
                "SELECT id, delta, kind, created_at, balance_after, story_id, card_id, mission, milestone, reason,"
                f" coin_day, idem_key FROM coin_ledger WHERE {where} ORDER BY id DESC LIMIT ?",
                (*params, limit + 1),
            ).fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            items = [history_item(conn, r, account_id) for r in rows]
        return {"items": items, "next": items[-1]["id"] if more and items else None}


def _name_of(conn: sqlite3.Connection, account_id: int, story_id: int | None, card_id: int | None) -> str:
    """Tên nhân vật của một dòng sổ, CHỈ từ story/card của chính tài khoản đó: SQLite dùng lại id story/card đã
    xoá (không AUTOINCREMENT), nên không lọc tài khoản thì lịch sử ví lộ tên nhân vật riêng tư của người khác."""
    if story_id is not None:
        row = conn.execute(
            "SELECT c.name FROM stories s JOIN character_cards c ON c.id = s.card_id"
            " WHERE s.id = ? AND s.account_id = ? AND c.account_id = ?",
            (story_id, account_id, account_id),
        ).fetchone()
        if row is not None and str(row[0]).strip():
            return str(row[0]).strip()
    if card_id is not None:
        row = conn.execute(
            "SELECT name FROM character_cards WHERE id = ? AND account_id = ?", (card_id, account_id)
        ).fetchone()
        if row is not None and str(row[0]).strip():
            return str(row[0]).strip()
    return FALLBACK_NAME


def history_item(conn: sqlite3.Connection, r: sqlite3.Row, account_id: int) -> dict[str, Any]:
    """Một dòng lịch sử ví với `label` tiếng Việt (§10.5). `r`: dòng `coin_ledger` (id, delta, kind, created_at,
    balance_after, story_id, card_id, mission, milestone, reason, coin_day, idem_key) của tài khoản `account_id`."""
    kind = str(r["kind"])
    name: str | None = None
    story_id = r["story_id"]
    if kind == "signup_grant":
        label = LABEL_SIGNUP
    elif kind == "backfill_grant":
        label = LABEL_BACKFILL
    elif kind == "daily_login":
        label = LABEL_DAILY
    elif kind == "chat":
        if story_id is None:
            label = LABEL_TEST_CHAT
        else:
            name = _name_of(conn, account_id, story_id, r["card_id"])
            label = chat_label(name)
    elif kind == "mission":
        label = LABEL_MISSION.get(str(r["mission"]), "Nhiệm vụ")
    elif kind == "creator_milestone":
        # Thưởng sáng tác: loại theo tiền tố idem_key (`rank:`, `first_public:`, dòng cũ `milestone:`; §5.7).
        key = str(r["idem_key"]) if "idem_key" in r.keys() and r["idem_key"] is not None else ""
        if key.startswith(hot_mod.FIRST_PUBLIC_PREFIX):
            label = hot_mod.reward_label(key, FALLBACK_NAME, None)
        else:
            name = _name_of(conn, account_id, None, r["card_id"])
            label = hot_mod.reward_label(key, name, r["milestone"])
    elif kind == "topup_code":
        label = LABEL_TOPUP
    else:
        label = adjust_label(r["reason"])
    item: dict[str, Any] = {
        "id": int(r["id"]),
        "delta": int(r["delta"]),
        "kind": kind,
        "label": label,
        "created_at": str(r["created_at"]),
        "balance_after": int(r["balance_after"]),
        "coin_day": str(r["coin_day"]),
        "story_id": story_id,
    }
    if name is not None:
        item["name"] = name
    return item


def emit_restart_releases(tracker: Any, released: list[tuple[int, str]]) -> None:
    """`coins_released reason=restart` cho từng giữ chỗ nhả lúc khởi động: không có request nên dùng
    `Tracker.emit_detached` (không gắn thiết bị/lượt; vẫn tôn trọng tài khoản đã tắt chia sẻ)."""
    if tracker is None:
        return
    from lyris.analytics.tracker import TrackContext

    for account_id, kind in released:
        tracker.emit_detached(
            TrackContext(account_id=account_id, anon_id=""), "coins_released", {"kind": kind, "reason": "restart"}
        )


__all__ = [
    "ADJUST_MAX",
    "CoinService",
    "CoinTrack",
    "HISTORY_PAGE",
    "Hold",
    "adjust_label",
    "chat_label",
    "history_item",
    "emit_restart_releases",
    "milestone_label",
]
