"""Truy cập dữ liệu: card, persona, story, message, feedback, lịch sử sửa.

Một kết nối sqlite3 dùng chung; mọi method khoá bằng một threading.RLock. Thao tác nhiều câu
lệnh chạy trong transaction tường minh (xem `Repo.transaction`).
"""
from __future__ import annotations

import functools
import itertools
import json
import secrets
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Concatenate, Literal, ParamSpec, TypeVar

from lyris.models import (
    Account,
    AccountUpdate,
    AddressTerms,
    AppSettings,
    CharacterCard,
    GenStats,
    LoreEntry,
    LoreSlot,
    MemoryItem,
    MemoryKind,
    Message,
    NarrationPronouns,
    Persona,
    Rating,
    RelationshipValues,
    Story,
)
from lyris.coins.hot import sync_public_since
from lyris.state.fold import (
    EVENT_KINDS,
    EXTRACTION_KINDS,
    MESSAGE_STATE_KINDS,
    EventKind,
    StateEvent,
    initial_relationship,
)

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"



class _AnyAccount:
    """Kiểu của hằng `ANY_ACCOUNT` (một đối tượng duy nhất)."""

    __slots__ = ()
    _instance: _AnyAccount | None = None

    def __new__(cls) -> _AnyAccount:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "ANY_ACCOUNT"

    def __reduce__(self) -> str:
        return "ANY_ACCOUNT"


# Lọc theo chủ sở hữu (Phase 2c, siết lại ở Phase 4b, docs/auth.md §4.2). Mọi hàm của Repo có tham số
# `account_id` đều BẮT BUỘC truyền (keyword, không có mặc định):
# - một id tài khoản (int): chỉ bản ghi của tài khoản đó; của tài khoản khác coi như không có (NotFound);
# - `ANY_ACCOUNT`: không lọc. Chỉ dùng ở việc nền không có request (worker, prompt builder, state, script),
#   không bao giờ ở route.
# `None` không còn nghĩa "mọi tài khoản" (trước Phase 4b) và bị từ chối (TypeError), để quên truyền không
# thành rò rỉ khi có hai tài khoản.
ANY_ACCOUNT = _AnyAccount()
AccountScope = int | _AnyAccount


def account_int(account_id: object) -> int:
    """`account_id` phải là id tài khoản thật (int, không phải bool/None/ANY_ACCOUNT)."""
    if isinstance(account_id, bool) or not isinstance(account_id, int):
        raise TypeError(f"account_id phải là id tài khoản (int), không phải {account_id!r}")
    return account_id


def _scope(account_id: object, column: str = "account_id") -> tuple[str, tuple[Any, ...]]:
    """Mệnh đề WHERE lọc theo chủ sở hữu: `ANY_ACCOUNT` = không lọc; id = đúng tài khoản đó."""
    if account_id is ANY_ACCOUNT:
        return "1 = 1", ()
    return f"{column} = ?", (account_int(account_id),)


# Account chủ máy mặc định (migration 0005 cũng tạo đúng account này). Không lấy thông tin cá nhân nào.
DEFAULT_ACCOUNT_HANDLE = "ban"
DEFAULT_ACCOUNT_NAME = "Bạn"

AccountImage = Literal["avatar", "banner"]


def new_uid() -> str:
    """Mã toàn cầu của account/persona/card/story: 32 ký tự hex ngẫu nhiên, không đổi."""
    return secrets.token_hex(16)

STORY_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {
        "title",
        "scenario",
        "mode",
        "language",
        "relationship_type",
        "pov",
        "thought_style",
        "narration_pronouns",
        "model_name",
        "scene_summary",
        "show_thoughts",  # Phase 4 (B): chỉ là cách hiển thị
    }
)
# Đổi riêng các trường này không tính là "hoạt động" của story: không đổi stories.updated_at (hub xếp story theo
# hoạt động gần nhất; bật/tắt một công tắc hiển thị không được đẩy story lên đầu).
STORY_DISPLAY_FIELDS: frozenset[str] = frozenset({"show_thoughts"})

_MESSAGE_SELECT = """
SELECT m.*,
       f.rating AS rating,
       (SELECT COUNT(*) FROM messages v
         WHERE v.story_id = m.story_id AND v.turn_index = m.turn_index) AS variant_count
  FROM messages m
  LEFT JOIN feedback f ON f.message_id = m.id
"""

# Thời điểm hoạt động gần nhất của story `s` (dùng trong SELECT ... FROM stories s).
_STORY_ACTIVITY = (
    "MAX(s.updated_at, COALESCE((SELECT MAX(m.created_at) FROM messages m WHERE m.story_id = s.id), ''))"
)

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class StoryRow:
    """Một dòng của `Repo.story_rows`: story + dữ liệu phụ cho danh sách story."""

    story: Story
    card_name: str
    card_role: str
    card_avatar: str | None
    persona_name: str
    updated_at: str | None
    last_visible: str | None
    last_role: str | None
    last_mode: str | None


JobKind = Literal["extract", "summarize", "embed"]
JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]
JOB_KINDS: tuple[JobKind, ...] = ("extract", "summarize", "embed")


@dataclass(frozen=True)
class Job:
    """Một dòng bảng `jobs` (hàng đợi việc nền, lyris/jobs/)."""

    id: int
    story_id: int
    message_id: int | None
    kind: JobKind
    status: JobStatus
    attempts: int
    error: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class NewMemory:
    """Ký ức/fact chuẩn bị ghi (story, message, lượt lấy từ message)."""

    kind: MemoryKind
    text: str
    subject: str | None = None
    importance: int = 3


class NotFound(LookupError):
    """Không tìm thấy bản ghi theo id."""


# Phase 4b (docs/auth.md §4.3, §7.4): card công khai vừa bị ẩn/xoá đúng lúc người khác bắt đầu story.
NO_LONGER_SHARED = "Nhân vật này không còn được chia sẻ."


@dataclass(frozen=True)
class CardOrigin:
    """Phase 4b (§4.3): card là bản sao (`story_copy`) của card công khai nào, của ai, chụp lúc nào."""

    story_copy: bool
    origin_card_id: int | None = None
    origin_account_id: int | None = None
    origin_updated_at: str | None = None


def _without_template_marker(extensions: dict[str, Any]) -> dict[str, Any]:
    """`extensions` của bản sao: không dấu mẫu `lyris.template` (§4.3), không `v2.character_book` (sổ thế
    giới đã chép thành mục riêng)."""
    from lyris.lore.book import without_book

    out = without_book(dict(extensions))
    lyris = out.get("lyris")
    if isinstance(lyris, dict) and "template" in lyris:
        rest = {k: v for k, v in lyris.items() if k != "template"}
        if rest:
            out["lyris"] = rest
        else:
            del out["lyris"]
    return out


class HandleTaken(ValueError):
    """@handle đã có account khác dùng (không phân biệt hoa thường)."""

    def __init__(self, handle: str) -> None:
        self.handle = handle
        super().__init__(f"@{handle} đã có người dùng. Hãy chọn handle khác.")


class InUse(ValueError):
    """Card/persona đang được story dùng; chỉ xoá được khi gọi lại với `with_stories=True`."""

    def __init__(self, count: int, message: str | None = None) -> None:
        self.count = count
        super().__init__(message or f"Có {count} story đang dùng")


def _locked(fn: Callable[Concatenate[Repo, P], R]) -> Callable[Concatenate[Repo, P], R]:
    @functools.wraps(fn)
    def wrapper(self: Repo, *args: P.args, **kwargs: P.kwargs) -> R:
        with self._lock:
            return fn(self, *args, **kwargs)

    return wrapper


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _row_to_card(row: sqlite3.Row) -> CharacterCard:
    return CharacterCard(
        id=row["id"],
        uid=row["uid"],
        visibility=row["visibility"],
        name=row["name"],
        role=row["role"],
        gender=row["gender"],
        language=row["language"],
        description=row["description"],
        personality=row["personality"],
        appearance=row["appearance"],
        background=row["background"],
        goals=row["goals"],
        secrets=row["secrets"],
        speech_style=row["speech_style"],
        style_profile=row["style_profile"],
        address_terms=AddressTerms.model_validate_json(row["address_terms_json"]),
        greeting=row["greeting"],
        example_dialogues=row["example_dialogues"],
        tags=json.loads(row["tags_json"]),
        scenario=row["scenario"],
        alternate_greetings=json.loads(row["alternate_greetings_json"]),
        creator_notes=row["creator_notes"],
        avatar=row["avatar"],
        extensions=json.loads(row["extensions_json"]),
    )


def _card_columns(card: CharacterCard) -> dict[str, Any]:
    """Các cột nội dung của card (không gồm id, uid, account_id, avatar, created_at/updated_at)."""
    return {
        "visibility": card.visibility,
        "name": card.name,
        "role": card.role,
        "gender": card.gender,
        "language": card.language,
        "description": card.description,
        "personality": card.personality,
        "appearance": card.appearance,
        "background": card.background,
        "goals": card.goals,
        "secrets": card.secrets,
        "speech_style": card.speech_style,
        "style_profile": card.style_profile,
        "address_terms_json": _dumps(card.address_terms.model_dump(mode="json")),
        "greeting": card.greeting,
        "example_dialogues": card.example_dialogues,
        "tags_json": _dumps(card.tags),
        "scenario": card.scenario,
        "alternate_greetings_json": _dumps(card.alternate_greetings),
        "creator_notes": card.creator_notes,
        "extensions_json": _dumps(card.extensions),
    }


def _row_to_persona(row: sqlite3.Row) -> Persona:
    return Persona(
        id=row["id"],
        uid=row["uid"],
        name=row["name"],
        gender=row["gender"],
        description=row["description"],
        avatar=row["avatar"],
    )


def _row_to_story(row: sqlite3.Row) -> Story:
    return Story(
        id=row["id"],
        uid=row["uid"],
        card_id=row["card_id"],
        persona_id=row["persona_id"],
        title=row["title"],
        scenario=row["scenario"],
        language=row["language"],
        mode=row["mode"],
        relationship_type=row["relationship_type"],
        pov=row["pov"],
        thought_style=row["thought_style"],
        narration_pronouns=NarrationPronouns.model_validate_json(row["narration_pronouns_json"]),
        model_name=row["model_name"],
        scene_summary=row["scene_summary"],
        created_at=row["created_at"],
        # Phase 4: đọc phòng thủ (DB chưa áp migration 0007 thì coi như bật, không làm hỏng route story).
        show_thoughts=bool(row["show_thoughts"]) if "show_thoughts" in row.keys() else True,
    )


def _row_to_account(row: sqlite3.Row) -> Account:
    keys = row.keys()
    # Phase 4b (0008): vai trò, trạng thái, chờ đổi mật khẩu. Đọc phòng thủ để Repo còn mở được DB cũ (test
    # migration dựng DB version 6/7).
    auth = {
        "role": row["role"],
        "status": row["status"],
        "must_change_password": bool(row["must_change_password"]),
    } if "role" in keys else {}
    return Account(
        **auth,
        id=row["id"],
        uid=row["uid"],
        handle=row["handle"],
        display_name=row["display_name"],
        bio=row["bio"],
        avatar=row["avatar"],
        banner=row["banner"],
        profile_completed=bool(row["profile_completed"]),
        created_at=row["created_at"],
    )


def _row_to_message(row: sqlite3.Row) -> Message:
    snapshot = row["prompt_snapshot_json"]
    stats = row["gen_stats_json"]
    return Message(
        id=row["id"],
        story_id=row["story_id"],
        turn_index=row["turn_index"],
        variant_index=row["variant_index"],
        is_active=bool(row["is_active"]),
        role=row["role"],
        mode=row["mode"],
        raw_content=row["raw_content"],
        visible_content=row["visible_content"],
        thought=row["thought"],
        directive=row["directive"],
        model_output=row["model_output"],
        prompt_snapshot=json.loads(snapshot) if snapshot is not None else None,
        model_name=row["model_name"],
        gen_stats=GenStats.model_validate_json(stats) if stats is not None else None,
        rating=row["rating"],
        variant_count=row["variant_count"],
        created_at=row["created_at"],
        edited_at=row["edited_at"],
    )


def _row_to_memory(row: sqlite3.Row) -> MemoryItem:
    return MemoryItem(
        id=row["id"],
        story_id=row["story_id"],
        message_id=row["message_id"],
        turn_index=row["turn_index"],
        kind=row["kind"],
        text=row["text"],
        subject=row["subject"],
        importance=row["importance"],
        created_at=row["created_at"],
    )


def _row_to_event(row: sqlite3.Row) -> StateEvent | None:
    try:
        payload = json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return StateEvent(
        id=row["id"],
        story_id=row["story_id"],
        message_id=row["message_id"],
        turn_index=row["turn_index"],
        kind=row["kind"],
        payload=payload,
        created_at=row["created_at"],
    )


def _json_or(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
    return value if isinstance(value, type(default)) else default


def _row_to_lore(row: sqlite3.Row) -> LoreEntry:
    return LoreEntry(
        id=row["id"],
        card_id=row["card_id"],
        slug=row["slug"],
        title=row["title"],
        category=row["category"],
        keys=[k for k in _json_or(row["keys_json"], []) if isinstance(k, str)],
        known_by=[k for k in _json_or(row["known_by_json"], ["*"]) if isinstance(k, str)] or ["*"],
        content=row["content"],
        source=row["source"],
        edited=bool(row["edited"]),
        enabled=bool(row["enabled"]),
        priority=row["priority"],
        position=row["position"],
        extra=_json_or(row["extra_json"], {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@dataclass(frozen=True)
class LoreHitRow:
    """Một mục đã mở khoá trong story (gộp các lượt active đã gợi ra nó), `Repo.unlocked_lore`."""

    entry: LoreEntry
    first_turn: int
    last_turn: int
    turns: int
    sent: bool  # đã từng thật sự vào prompt (slot carried/fresh)


# Cột lore_entries ghi được qua `Repo.update_lore`.
LORE_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"title", "category", "keys", "known_by", "content", "source", "edited", "removed", "enabled", "priority",
     "position", "extra", "slug"}
)


def _lore_columns(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, value in fields.items():
        if name == "keys":
            out["keys_json"] = _dumps(list(value))
        elif name == "known_by":
            out["known_by_json"] = _dumps(list(value))
        elif name == "extra":
            out["extra_json"] = _dumps(value) if value else None
        elif name in ("edited", "removed", "enabled"):
            out[name] = 1 if value else 0
        else:
            out[name] = value
    return out


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        story_id=row["story_id"],
        message_id=row["message_id"],
        kind=row["kind"],
        status=row["status"],
        attempts=row["attempts"],
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def fts_match_expression(terms: list[str]) -> str | None:
    """Biểu thức MATCH an toàn cho FTS5: mỗi term/cụm từ đặt trong ngoặc kép, nối bằng OR.

    Dấu ngoặc kép trong term được nhân đôi (cú pháp chuỗi của FTS5), nên không có toán tử nào lọt vào.
    Term rỗng bị bỏ; không còn term nào -> None.
    """
    quoted: list[str] = []
    for term in terms:
        if not isinstance(term, str):
            continue
        cleaned = " ".join(term.split())
        if not cleaned:
            continue
        phrase = '"' + cleaned.replace('"', '""') + '"'
        if phrase not in quoted:
            quoted.append(phrase)
    return " OR ".join(quoted) if quoted else None


# Message active: event/ký ức của variant không active bị bỏ qua khi đọc.
_ACTIVE_JOIN = "JOIN messages m ON m.id = {alias}.message_id AND m.is_active = 1"


def _message_columns(msg: Message) -> dict[str, Any]:
    """Các cột nội dung của message (không gồm story/turn/variant/active)."""
    return {
        "role": msg.role,
        "mode": msg.mode,
        "raw_content": msg.raw_content,
        "visible_content": msg.visible_content,
        "thought": msg.thought,
        "directive": msg.directive,
        "model_output": msg.model_output,
        "prompt_snapshot_json": _dumps(msg.prompt_snapshot) if msg.prompt_snapshot is not None else None,
        "model_name": msg.model_name,
        "gen_stats_json": _dumps(msg.gen_stats.model_dump(mode="json")) if msg.gen_stats is not None else None,
    }


class Repo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._savepoints = itertools.count(1)
        self._has_copy_columns = False  # cache: character_cards.story_copy đã có (0008) thì không mất nữa
        # Phase 4b (§4.3): file avatar của bản sao vừa bị dọn (`_drop_orphan_copies`), chờ caller xoá sau commit.
        self._orphan_avatars: list[str] = []
        # Phase 4b (§5.3): tài khoản của job vừa lấy ra chạy, để lấy job xen kẽ theo tài khoản.
        self._last_job_account: int | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    # ------------------------------------------------------------------ transaction

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Transaction tường minh, giữ khoá suốt thời gian chạy; lồng nhau dùng SAVEPOINT."""
        with self._lock:
            conn = self._conn
            if conn.in_transaction:
                name = f"lyris_sp_{next(self._savepoints)}"
                conn.execute(f"SAVEPOINT {name}")
                try:
                    yield
                except BaseException:
                    conn.execute(f"ROLLBACK TO {name}")
                    conn.execute(f"RELEASE {name}")
                    raise
                conn.execute(f"RELEASE {name}")
            else:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    yield
                except BaseException:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    raise
                conn.execute("COMMIT")

    def _insert(self, table: str, values: dict[str, Any]) -> int:
        cols = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        cur = self._conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))
        rowid = cur.lastrowid
        assert rowid is not None
        return rowid

    def _exists(self, table: str, row_id: int, account_id: AccountScope = ANY_ACCOUNT, *, extra: str = "") -> bool:
        """Có bản ghi `row_id` thuộc `account_id` (`ANY_ACCOUNT`: của ai cũng được; bảng có account_id)."""
        where, params = _scope(account_id)
        sql = f"SELECT 1 FROM {table} WHERE id = ? AND {where}{extra}"
        return self._conn.execute(sql, (row_id, *params)).fetchone() is not None

    def _require_story(self, story_id: int, account_id: AccountScope = ANY_ACCOUNT) -> None:
        if not self._exists("stories", story_id, account_id):
            raise NotFound(f"Không tìm thấy story {story_id}")

    def _require_card(self, card_id: int, account_id: AccountScope = ANY_ACCOUNT, *, copies: bool = True) -> None:
        if not self._exists("character_cards", card_id, account_id, extra="" if copies else f" AND {self._no_copy()}"):
            raise NotFound(f"Không tìm thấy nhân vật {card_id}")

    def _require_persona(self, persona_id: int, account_id: AccountScope = ANY_ACCOUNT) -> None:
        if not self._exists("personas", persona_id, account_id):
            raise NotFound(f"Không tìm thấy persona {persona_id}")

    def _copies_supported(self) -> bool:
        """DB đã có cột bản sao của card (migration 0008). Test dựng DB version cũ vẫn dùng được Repo."""
        if not self._has_copy_columns:
            self._has_copy_columns = any(
                r[1] == "story_copy" for r in self._conn.execute("PRAGMA table_info(character_cards)")
            )
        return self._has_copy_columns

    def _no_copy(self, alias: str = "") -> str:
        """Điều kiện "không phải bản sao" (`story_copy = 0`); DB trước 0008 thì luôn đúng."""
        return f"{alias}story_copy = 0" if self._copies_supported() else "1 = 1"

    def owner_id(self) -> int:
        """Id tài khoản chủ máy (tạo tài khoản mặc định nếu DB chưa có tài khoản nào)."""
        with self._lock:
            return self._owner_row_id()

    def _has_attempts(self) -> bool:
        """DB đã có bảng `auth_attempts` (migration 0008, Phase 4b)."""
        row = self._conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'auth_attempts'")
        return row.fetchone() is not None

    def _has_roles(self) -> bool:
        """DB đã có cột `accounts.role` (migration 0008, Phase 4b)."""
        return any(r[1] == "role" for r in self._conn.execute("PRAGMA table_info(accounts)"))

    def _owner_row_id(self) -> int:
        """Id tài khoản chủ máy: `role = 'owner'` (Phase 4b); DB cũ chưa có vai trò thì id nhỏ nhất."""
        has_roles = self._has_roles()
        sql = "SELECT id FROM accounts WHERE role = 'owner'" if has_roles else "SELECT MIN(id) FROM accounts"
        row = self._conn.execute(sql).fetchone()
        if row is not None and row[0] is not None:
            return int(row[0])
        values: dict[str, Any] = {
            "uid": new_uid(), "handle": DEFAULT_ACCOUNT_HANDLE, "display_name": DEFAULT_ACCOUNT_NAME
        }
        if has_roles:
            values.update(role="owner", training_opt_in=1)
        with self.transaction():
            return self._insert("accounts", values)

    # ------------------------------------------------------------------ accounts

    @_locked
    def owner_account(self) -> Account:
        """Account chủ máy (`role = 'owner'`; tạo account mặc định nếu DB chưa có account nào)."""
        return self.get_account(self._owner_row_id())

    @contextmanager
    def locked(self) -> Iterator[sqlite3.Connection]:
        """Giữ khoá của Repo để đọc vài câu liền nhau (không mở transaction). Phase 4b: lyris.auth dùng
        khi đọc; không bao giờ băm mật khẩu trong lúc giữ khoá này (docs/auth.md §3.1)."""
        with self._lock:
            yield self._conn

    @_locked
    def get_account(self, account_id: int) -> Account:
        row = self._conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy tài khoản {account_id}")
        return _row_to_account(row)

    @_locked
    def find_account_by_handle(self, handle: str) -> Account | None:
        """Account có @handle này (không phân biệt hoa thường); None nếu không có."""
        row = self._conn.execute("SELECT * FROM accounts WHERE handle = ?", (handle,)).fetchone()
        return None if row is None else _row_to_account(row)

    @_locked
    def create_account(
        self, handle: str, display_name: str, *, bio: str = "", profile_completed: bool = False
    ) -> Account:
        """Thêm account (uid mới). Handle trùng -> HandleTaken. Không kiểm tra luật handle (việc của caller)."""
        try:
            with self.transaction():
                account_id = self._insert(
                    "accounts",
                    {
                        "uid": new_uid(),
                        "handle": handle,
                        "display_name": display_name,
                        "bio": bio,
                        "profile_completed": int(profile_completed),
                    },
                )
        except sqlite3.IntegrityError as exc:
            raise HandleTaken(handle) from exc
        return self.get_account(account_id)

    @_locked
    def handle_taken(self, handle: str, *, exclude_account_id: int | None = None) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM accounts WHERE handle = ? AND (? IS NULL OR id != ?)",
            (handle, exclude_account_id, exclude_account_id),
        ).fetchone()
        return row is not None

    @_locked
    def update_account(self, account_id: int, update: AccountUpdate) -> Account:
        """Lưu tên hiển thị, handle, giới thiệu; đặt `profile_completed = 1`. uid không bao giờ đổi.

        Handle trùng account khác -> HandleTaken.
        """
        try:
            with self.transaction():
                old = self._conn.execute("SELECT handle FROM accounts WHERE id = ?", (account_id,)).fetchone()
                if old is None:
                    raise NotFound(f"Không tìm thấy tài khoản {account_id}")
                self._conn.execute(
                    "UPDATE accounts SET display_name = ?, handle = ?, bio = ?, profile_completed = 1,"
                    f" updated_at = {_NOW} WHERE id = ?",
                    (update.display_name, update.handle, update.bio, account_id),
                )
                # Phase 4b (docs/auth.md §3.4): lần thử đăng nhập ghi theo handle; đổi handle thì chúng đi theo
                # tài khoản (trình duyệt đã biết vẫn được miễn khoá, lần sai vẫn được đếm).
                if str(old["handle"]).casefold() != update.handle.casefold() and self._has_attempts():
                    self._conn.execute(
                        "UPDATE auth_attempts SET handle = ? WHERE handle = ?", (update.handle, str(old["handle"]))
                    )
        except sqlite3.IntegrityError as exc:
            raise HandleTaken(update.handle) from exc
        return self.get_account(account_id)

    @_locked
    def set_account_image(self, account_id: int, kind: AccountImage, name: str | None) -> Account:
        """Đặt tên file avatar hoặc ảnh bìa của account (None = bỏ ảnh). Không đụng tới file."""
        if kind not in ("avatar", "banner"):
            raise ValueError(f"Loại ảnh không hợp lệ: {kind!r}")
        with self.transaction():
            if not self._exists("accounts", account_id):
                raise NotFound(f"Không tìm thấy tài khoản {account_id}")
            self._conn.execute(
                f"UPDATE accounts SET {kind} = ?, updated_at = {_NOW} WHERE id = ?", (name, account_id)
            )
        return self.get_account(account_id)

    @_locked
    def account_counts(self, account_id: int) -> dict[str, int]:
        """Số card (không đếm bản sao, §4.3), story, persona của account."""
        row = self._conn.execute(
            f"SELECT (SELECT COUNT(*) FROM character_cards WHERE account_id = ? AND {self._no_copy()}) AS card_count,"
            "       (SELECT COUNT(*) FROM stories WHERE account_id = ?) AS story_count,"
            "       (SELECT COUNT(*) FROM personas WHERE account_id = ?) AS persona_count",
            (account_id, account_id, account_id),
        ).fetchone()
        return {k: int(row[k]) for k in ("card_count", "story_count", "persona_count")}

    @_locked
    def card_account_id(self, card_id: int) -> int | None:
        """Chủ sở hữu của card (None nếu card không có hoặc chưa gán)."""
        row = self._conn.execute("SELECT account_id FROM character_cards WHERE id = ?", (card_id,)).fetchone()
        return None if row is None or row[0] is None else int(row[0])

    def _count_stories(self, column: str, value: int) -> int:
        assert column in ("card_id", "persona_id")
        row = self._conn.execute(f"SELECT COUNT(*) FROM stories WHERE {column} = ?", (value,)).fetchone()
        return int(row[0])

    def _delete_stories_of(
        self, column: str, value: int, *, with_stories: bool, account_id: AccountScope
    ) -> list[int]:
        """Xoá các story có `column = value` của `account_id` (message/feedback/edit/job đi theo FK). InUse
        nếu không cho xoá. Bản sao không còn story nào thì dọn luôn (§4.3, `_drop_orphan_copies`).

        Phase 4b: nhờ bất biến §2.2 chỉ story của chính tài khoản dùng card/persona của nó; vẫn lọc
        `account_id` cho chắc (docs/auth.md §4.1). Trả id các story đã xoá (caller báo hàng đợi job).
        """
        assert column in ("card_id", "persona_id")
        where, params = _scope(account_id)
        ids = [
            int(r[0])
            for r in self._conn.execute(f"SELECT id FROM stories WHERE {column} = ? AND {where}", (value, *params))
        ]
        if ids and not with_stories:
            raise InUse(len(ids))
        if ids:
            self._conn.execute(f"DELETE FROM stories WHERE {column} = ? AND {where}", (value, *params))
            self._drop_orphan_copies()
        return ids

    def _drop_orphan_copies(self) -> int:
        """Phase 4b (§4.3): xoá mọi card bản sao (`story_copy = 1`) không còn story nào trỏ tới (sổ thế giới đi
        theo ON DELETE CASCADE). Chạy cuối mọi transaction xoá story. Tên file avatar của chúng được giữ ở
        `pop_orphan_avatars()` để caller xoá file SAU khi commit. Trả số bản sao đã xoá."""
        if not self._copies_supported():
            return 0
        rows = self._conn.execute(
            "SELECT id, avatar FROM character_cards c WHERE c.story_copy = 1"
            " AND NOT EXISTS (SELECT 1 FROM stories s WHERE s.card_id = c.id)"
        ).fetchall()
        if not rows:
            return 0
        ids = [int(r["id"]) for r in rows]
        marks = ", ".join("?" for _ in ids)
        self._conn.execute(f"DELETE FROM character_cards WHERE id IN ({marks})", ids)
        self._orphan_avatars.extend(str(r["avatar"]) for r in rows if r["avatar"])
        return len(ids)

    @_locked
    def drop_orphan_copies(self) -> int:
        """Dọn bản sao mồ côi (lúc khởi động: phần sót lại). Tên file avatar: `pop_orphan_avatars()`."""
        with self.transaction():
            return self._drop_orphan_copies()

    @_locked
    def pop_orphan_avatars(self) -> list[str]:
        """Tên file avatar của các bản sao đã bị dọn (và đã commit), rồi quên chúng. Caller xoá file."""
        if self._conn.in_transaction:
            return []  # chưa commit: để lần gọi sau (transaction ngoài có thể còn rollback)
        names, self._orphan_avatars = self._orphan_avatars, []
        # Transaction đã rollback thì card còn đó: không xoá file của card còn sống.
        return [
            n for n in dict.fromkeys(names)
            if self._conn.execute("SELECT 1 FROM character_cards WHERE avatar = ?", (n,)).fetchone() is None
        ]

    # ------------------------------------------------------------------ cards

    @_locked
    def create_card(self, card: CharacterCard, *, account_id: int) -> CharacterCard:
        """Thêm card thuộc `account_id` (bắt buộc, Phase 4b) với uid mới (bỏ qua `card.uid`)."""
        owner = account_int(account_id)
        with self.transaction():
            values: dict[str, Any] = {
                **_card_columns(card),
                "avatar": card.avatar,
                "account_id": owner,
                "uid": new_uid(),
            }
            if card.id is not None:
                values = {"id": card.id, **values}
            card_id = self._insert("character_cards", values)
            # F44 (docs/coins.md §5.5): lúc bật Công khai (thưởng công khai lần đầu cần ≥ 24 giờ liên tục).
            sync_public_since(self._conn, card_id)
        return self.get_card(card_id, account_id=owner)

    @_locked
    def get_card(self, card_id: int, *, account_id: AccountScope, copies: bool = True) -> CharacterCard:
        """Card theo id thuộc `account_id`. `copies=False`: bản sao (§4.3) coi như không có (NotFound), dùng ở
        mọi route "Không bản sao" của docs/auth.md §4.1."""
        where, params = _scope(account_id)
        extra = "" if copies else f" AND {self._no_copy()}"
        row = self._conn.execute(
            f"SELECT * FROM character_cards WHERE id = ? AND {where}{extra}", (card_id, *params)
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy nhân vật {card_id}")
        return _row_to_card(row)

    @_locked
    def card_origin(self, card_id: int) -> CardOrigin:
        """Card có phải bản sao không, và của card gốc nào (§4.3). NotFound nếu không có card."""
        if not self._copies_supported():
            if not self._exists("character_cards", card_id):
                raise NotFound(f"Không tìm thấy nhân vật {card_id}")
            return CardOrigin(story_copy=False)
        row = self._conn.execute(
            "SELECT story_copy, origin_card_id, origin_account_id, origin_updated_at FROM character_cards"
            " WHERE id = ?",
            (card_id,),
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy nhân vật {card_id}")
        return CardOrigin(
            story_copy=bool(row["story_copy"]),
            origin_card_id=row["origin_card_id"],
            origin_account_id=row["origin_account_id"],
            origin_updated_at=row["origin_updated_at"],
        )

    @_locked
    def list_cards(self, *, account_id: AccountScope, public_only: bool = False) -> list[CharacterCard]:
        """Card của `account_id`, sửa gần nhất trước. Không bao giờ có bản sao (§4.2).
        `public_only`: chỉ card `visibility = 'public'` (profile công khai)."""
        where, params = _scope(account_id)
        public = " AND visibility = 'public'" if public_only else ""
        rows = self._conn.execute(
            f"SELECT * FROM character_cards WHERE {where} AND {self._no_copy()}{public}"
            " ORDER BY updated_at DESC, id DESC",
            params,
        ).fetchall()
        return [_row_to_card(r) for r in rows]

    def _public_where(self, alias: str = "c") -> str:
        """Card công khai dùng được ở tài khoản khác: `public`, không phải bản sao, người tạo đang active."""
        return (
            f"{alias}.visibility = 'public' AND {alias}.story_copy = 0"
            f" AND EXISTS (SELECT 1 FROM accounts a WHERE a.id = {alias}.account_id AND a.status = 'active')"
        )

    @_locked
    def get_public_card(self, card_id: int) -> CharacterCard:
        """Card công khai (§4.1 "Công khai": `public`, không phải bản sao, người tạo active). Không thì NotFound.
        Không lọc người xem: route tự quyết định card của chính người xem đi đường nào."""
        if not self._copies_supported():
            raise NotFound(f"Không tìm thấy nhân vật {card_id}")
        row = self._conn.execute(
            f"SELECT c.* FROM character_cards c WHERE c.id = ? AND {self._public_where()}", (card_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy nhân vật {card_id}")
        return _row_to_card(row)

    @_locked
    def list_public_cards(self, *, exclude_account_id: int, limit: int = 200) -> list[tuple[CharacterCard, Account]]:
        """Card công khai của tài khoản KHÁC `exclude_account_id` (Khám phá), mới sửa trước, tối đa `limit`.
        Kèm tài khoản người tạo."""
        if not self._copies_supported():
            return []
        rows = self._conn.execute(
            f"SELECT c.* FROM character_cards c WHERE {self._public_where()} AND c.account_id != ?"
            " ORDER BY c.updated_at DESC, c.id DESC LIMIT ?",
            (account_int(exclude_account_id), int(limit)),
        ).fetchall()
        creators: dict[int, Account] = {}
        out: list[tuple[CharacterCard, Account]] = []
        for r in rows:
            owner = int(r["account_id"])
            if owner not in creators:
                creators[owner] = self.get_account(owner)
            out.append((_row_to_card(r), creators[owner]))
        return out

    @_locked
    def copy_public_card(self, card_id: int, *, account_id: int) -> CharacterCard:
        """Phase 4b (§4.3): chụp card công khai `card_id` thành một card bản sao của `account_id`
        (`story_copy = 1`, `origin_*`, luôn riêng tư, bỏ dấu mẫu) kèm sổ thế giới (mục bật, chưa xoá).

        Đọc gốc và ghi bản sao trong MỘT transaction (caller tạo story trong cùng transaction đó): gốc vừa
        chuyển Riêng tư, vừa bị xoá, người tạo bị khoá, hay gốc là của chính `account_id` -> NotFound
        "Nhân vật này không còn được chia sẻ." và không ghi gì. File avatar KHÔNG chép ở đây (sau commit)."""
        player = account_int(account_id)
        with self.transaction():
            row = None
            if self._copies_supported():
                row = self._conn.execute(
                    f"SELECT c.* FROM character_cards c WHERE c.id = ? AND {self._public_where()}"
                    " AND c.account_id != ?",
                    (card_id, player),
                ).fetchone()
            if row is None:
                raise NotFound(NO_LONGER_SHARED)
            source = _row_to_card(row)
            extensions = _without_template_marker(source.extensions)
            values: dict[str, Any] = {
                **_card_columns(source.model_copy(update={"visibility": "private", "extensions": extensions})),
                "avatar": None,
                "account_id": player,
                "uid": new_uid(),
                "story_copy": 1,
                "origin_card_id": int(row["id"]),
                "origin_account_id": int(row["account_id"]),
                "origin_updated_at": row["updated_at"],
            }
            copy_id = self._insert("character_cards", values)
            now = self._now()
            self._conn.execute(
                "INSERT INTO lore_entries (card_id, slug, title, category, keys_json, known_by_json, content, source,"
                " edited, removed, enabled, priority, position, extra_json, created_at, updated_at)"
                " SELECT ?, slug, title, category, keys_json, known_by_json, content, source, edited, 0,"
                " enabled, priority, position, extra_json, ?, ? FROM lore_entries"
                " WHERE card_id = ? AND enabled = 1 AND removed = 0 ORDER BY id",
                (copy_id, now, now, card_id),
            )
        return self.get_card(copy_id, account_id=player)

    @_locked
    def update_card(
        self, card_id: int, card: CharacterCard, *, account_id: AccountScope, copies: bool = False
    ) -> CharacterCard:
        """Thay toàn bộ nội dung card (gồm visibility), giữ id; đặt updated_at.

        `card.id`, `card.uid` và `card.avatar` bị bỏ qua: avatar chỉ đổi qua `set_card_avatar`, uid không đổi.
        Bản sao (§4.3) không sửa được trừ khi `copies=True` (nội bộ).
        """
        columns = _card_columns(card)
        assignments = ", ".join(f"{col} = ?" for col in columns)
        with self.transaction():
            self._require_card(card_id, account_id, copies=copies)
            self._conn.execute(
                f"UPDATE character_cards SET {assignments}, updated_at = {_NOW} WHERE id = ?",
                (*columns.values(), card_id),
            )
            # F44 (§5.5): Riêng tư → Công khai ghi lúc bật; Công khai → Riêng tư xoá (bật lại thì đếm 24 giờ lại).
            sync_public_since(self._conn, card_id)
        return self.get_card(card_id, account_id=account_id)

    @_locked
    def set_card_avatar(
        self, card_id: int, avatar: str | None, *, account_id: AccountScope, copies: bool = False
    ) -> CharacterCard:
        """Đặt tên file avatar (None = bỏ ảnh); đặt updated_at. Không đụng tới file.
        `copies=True` chỉ dùng khi chép ảnh cho bản sao vừa tạo (§4.3)."""
        with self.transaction():
            self._require_card(card_id, account_id, copies=copies)
            self._conn.execute(
                f"UPDATE character_cards SET avatar = ?, updated_at = {_NOW} WHERE id = ?",
                (avatar, card_id),
            )
        return self.get_card(card_id, account_id=account_id)

    @_locked
    def delete_card(self, card_id: int, *, with_stories: bool = False, account_id: AccountScope) -> int:
        """Xoá card; trả số story đã xoá theo. Có story mà with_stories=False -> InUse(count).

        Không xoá file avatar (việc của caller). Cần id các story đã xoá thì dùng `delete_card_stories`.
        Bản sao không xoá được qua đây (chúng tự đi theo story cuối cùng, §4.3).
        """
        return len(self.delete_card_stories(card_id, with_stories=with_stories, account_id=account_id))

    @_locked
    def delete_card_stories(
        self, card_id: int, *, with_stories: bool = False, account_id: AccountScope
    ) -> list[int]:
        """Như `delete_card` nhưng trả id các story đã xoá theo (để báo hàng đợi job)."""
        with self.transaction():
            self._require_card(card_id, account_id, copies=False)
            deleted = self._delete_stories_of("card_id", card_id, with_stories=with_stories, account_id=account_id)
            self._conn.execute("DELETE FROM character_cards WHERE id = ?", (card_id,))
        return deleted

    @_locked
    def card_story_count(self, card_id: int) -> int:
        self._require_card(card_id)
        return self._count_stories("card_id", card_id)

    @_locked
    def card_updated_at(self, card_id: int) -> str | None:
        row = self._conn.execute("SELECT updated_at FROM character_cards WHERE id = ?", (card_id,)).fetchone()
        return None if row is None else str(row["updated_at"])

    @_locked
    def template_card_ids(self, *, account_id: AccountScope) -> dict[str, int]:
        """slug -> id card nhỏ nhất có `extensions.lyris.template == slug` (card cài từ template). Không xét
        bản sao (§4.2)."""
        where, params = _scope(account_id)
        rows = self._conn.execute(
            "SELECT json_extract(extensions_json, '$.lyris.template') AS slug, MIN(id) AS id"
            "  FROM character_cards"
            " WHERE json_valid(extensions_json)"
            "   AND json_type(extensions_json, '$.lyris.template') = 'text'"
            f"  AND {where} AND {self._no_copy()}"
            " GROUP BY slug",
            params,
        ).fetchall()
        return {str(r["slug"]): int(r["id"]) for r in rows}

    @_locked
    def card_ids_by_name(self, name: str, style_profile: str, *, account_id: AccountScope) -> list[int]:
        """Id các card trùng tên (bỏ khoảng trắng hai đầu) và style profile, nhỏ nhất trước. Không có bản sao."""
        where, params = _scope(account_id)
        rows = self._conn.execute(
            f"SELECT id FROM character_cards WHERE TRIM(name) = ? AND style_profile = ? AND {where}"
            f" AND {self._no_copy()} ORDER BY id",
            (name.strip(), style_profile, *params),
        ).fetchall()
        return [int(r["id"]) for r in rows]

    # ------------------------------------------------------------------ personas

    @_locked
    def create_persona(self, p: Persona, *, account_id: int) -> Persona:
        """Thêm persona thuộc `account_id` (bắt buộc, Phase 4b) với uid mới (bỏ qua `p.uid`)."""
        owner = account_int(account_id)
        with self.transaction():
            values: dict[str, Any] = {
                "name": p.name,
                "gender": p.gender,
                "description": p.description,
                "avatar": p.avatar,
                "account_id": owner,
                "uid": new_uid(),
            }
            if p.id is not None:
                values = {"id": p.id, **values}
            persona_id = self._insert("personas", values)
        return self.get_persona(persona_id, account_id=owner)

    @_locked
    def get_persona(self, persona_id: int, *, account_id: AccountScope) -> Persona:
        where, params = _scope(account_id)
        row = self._conn.execute(f"SELECT * FROM personas WHERE id = ? AND {where}", (persona_id, *params)).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy persona {persona_id}")
        return _row_to_persona(row)

    @_locked
    def list_personas(self, *, account_id: AccountScope) -> list[Persona]:
        """Sửa gần nhất trước."""
        where, params = _scope(account_id)
        rows = self._conn.execute(
            f"SELECT * FROM personas WHERE {where} ORDER BY updated_at DESC, id DESC", params
        ).fetchall()
        return [_row_to_persona(r) for r in rows]

    @_locked
    def update_persona(self, persona_id: int, p: Persona, *, account_id: AccountScope) -> Persona:
        """Thay tên, giới tính, mô tả của persona, giữ id (bỏ qua `p.id`, `p.uid`, `p.avatar`); đặt updated_at."""
        with self.transaction():
            self._require_persona(persona_id, account_id)
            self._conn.execute(
                f"UPDATE personas SET name = ?, gender = ?, description = ?, updated_at = {_NOW} WHERE id = ?",
                (p.name, p.gender, p.description, persona_id),
            )
        return self.get_persona(persona_id, account_id=account_id)

    @_locked
    def set_persona_avatar(self, persona_id: int, avatar: str | None, *, account_id: AccountScope) -> Persona:
        """Đặt tên file avatar của persona (None = bỏ ảnh). Không đụng tới file."""
        with self.transaction():
            self._require_persona(persona_id, account_id)
            self._conn.execute(
                f"UPDATE personas SET avatar = ?, updated_at = {_NOW} WHERE id = ?", (avatar, persona_id)
            )
        return self.get_persona(persona_id, account_id=account_id)

    @_locked
    def delete_persona(self, persona_id: int, *, with_stories: bool = False, account_id: AccountScope) -> int:
        """Xoá persona; trả số story đã xoá theo. Có story mà with_stories=False -> InUse(count).

        Không xoá file avatar (việc của caller). Cần id các story đã xoá thì dùng `delete_persona_stories`.
        """
        return len(self.delete_persona_stories(persona_id, with_stories=with_stories, account_id=account_id))

    @_locked
    def delete_persona_stories(
        self, persona_id: int, *, with_stories: bool = False, account_id: AccountScope
    ) -> list[int]:
        """Như `delete_persona` nhưng trả id các story đã xoá theo (để báo hàng đợi job). Bản sao card của
        các story đó không còn story nào thì bị dọn luôn (§4.3); tên file ảnh: `pop_orphan_avatars()`."""
        with self.transaction():
            self._require_persona(persona_id, account_id)
            deleted = self._delete_stories_of(
                "persona_id", persona_id, with_stories=with_stories, account_id=account_id
            )
            # id persona không AUTOINCREMENT nên SQLite có thể cấp lại id này cho persona tạo sau. Persona mặc
            # định nằm ở `accounts.default_persona_id` (Phase 4b) với ON DELETE SET NULL, nên xoá persona là
            # bỏ luôn lựa chọn đó, không "tự chọn" persona mới.
            self._conn.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        return deleted

    @_locked
    def persona_story_count(self, persona_id: int) -> int:
        self._require_persona(persona_id)
        return self._count_stories("persona_id", persona_id)

    @_locked
    def persona_exists(self, persona_id: int, *, account_id: AccountScope) -> bool:
        return self._exists("personas", persona_id, account_id)

    @_locked
    def first_persona_id(self, *, account_id: AccountScope) -> int | None:
        """Persona tạo sớm nhất (id nhỏ nhất); None nếu chưa có persona nào."""
        where, params = _scope(account_id)
        row = self._conn.execute(f"SELECT MIN(id) FROM personas WHERE {where}", params).fetchone()
        return None if row[0] is None else int(row[0])

    # ------------------------------------------------------------------ app settings

    @_locked
    def get_app_settings(self, *, account_id: int) -> AppSettings:
        """Cài đặt đã lưu (khoá thiếu lấy mặc định). Persona mặc định đã bị xoá -> None.

        Phase 4b (docs/auth.md §2.1): `default_chat_model` là cài đặt của máy (bảng app_settings);
        `default_persona_id` là của tài khoản `account_id` (cột `accounts.default_persona_id`; bắt buộc).
        Chỉ cần model của máy thì dùng `default_chat_model()`.
        """
        machine_keys = [k for k in AppSettings.model_fields if k != "default_persona_id"]
        marks = ", ".join("?" for _ in machine_keys)
        rows = self._conn.execute(
            f"SELECT key, value_json FROM app_settings WHERE key IN ({marks})", machine_keys
        ).fetchall()
        stored: dict[str, Any] = {}
        for r in rows:
            try:
                stored[r["key"]] = json.loads(r["value_json"])
            except json.JSONDecodeError:
                continue
        try:
            settings = AppSettings.model_validate(stored)
        except ValueError:
            settings = AppSettings()
        owner = account_int(account_id)
        persona_id = self._default_persona_column(owner)
        if persona_id is not None and self._exists("personas", persona_id, owner):
            settings = settings.model_copy(update={"default_persona_id": persona_id})
        return settings

    @_locked
    def default_chat_model(self) -> str | None:
        """Model mặc định cho story mới (cài đặt của máy, `app_settings`); None = theo LYRIS_CHAT_MODEL."""
        row = self._conn.execute(
            "SELECT value_json FROM app_settings WHERE key = 'default_chat_model'"
        ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row["value_json"])
        except json.JSONDecodeError:
            return None
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _default_persona_column(self, account_id: int) -> int | None:
        target = account_id
        try:
            row = self._conn.execute(
                "SELECT default_persona_id FROM accounts WHERE id = ?", (target,)
            ).fetchone()
        except sqlite3.OperationalError:  # DB trước 0008: chưa có cột
            return None
        return None if row is None or row[0] is None else int(row[0])

    @_locked
    def set_app_settings(self, settings: AppSettings, *, account_id: int) -> AppSettings:
        """Ghi toàn bộ cài đặt: model mặc định vào app_settings (của máy), persona mặc định vào cột của tài
        khoản `account_id` (bắt buộc). Không kiểm tra nghiệp vụ (quyền đổi model: route)."""
        owner = account_int(account_id)
        values = settings.model_dump(mode="json")
        persona_id = values.pop("default_persona_id", None)
        with self.transaction():
            for key, value in values.items():
                self._conn.execute(
                    "INSERT INTO app_settings (key, value_json) VALUES (?, ?)"
                    f" ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = {_NOW}",
                    (key, _dumps(value)),
                )
            self._conn.execute(
                f"UPDATE accounts SET default_persona_id = ?, updated_at = {_NOW} WHERE id = ?",
                (persona_id, owner),
            )
        return self.get_app_settings(account_id=owner)

    @_locked
    def get_flag(self, key: str) -> bool:
        """Cờ nội bộ lưu trong app_settings (không thuộc AppSettings); thiếu hoặc hỏng -> False."""
        row = self._conn.execute("SELECT value_json FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return False
        try:
            return json.loads(row["value_json"]) is True
        except json.JSONDecodeError:
            return False

    @_locked
    def set_flag(self, key: str, value: bool = True) -> None:
        with self.transaction():
            self._conn.execute(
                "INSERT INTO app_settings (key, value_json) VALUES (?, ?)"
                f" ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = {_NOW}",
                (key, _dumps(value)),
            )

    # ------------------------------------------------------------------ stories

    @_locked
    def create_story(
        self,
        story: Story,
        *,
        account_id: int,
        initial_relationship: RelationshipValues | None = None,
    ) -> Story:
        """Thêm story thuộc `account_id` (bắt buộc, Phase 4b) với uid mới (bỏ qua `story.uid`).

        Card và persona phải thuộc chính account đó (không thì NotFound): bất biến §2.2 của docs/auth.md,
        story chỉ trỏ tới card (kể cả bản sao của chính mình) và persona cùng tài khoản.
        Phase 3: chụp lại điểm xuất phát của 6 chỉ số cảm xúc (`initial_relationship_json`);
        `initial_relationship` None = tính từ card lúc này (card, rồi mặc định).
        """
        owner = account_int(account_id)
        with self.transaction():
            if not self._exists("character_cards", story.card_id, owner):
                raise NotFound(f"Không tìm thấy nhân vật {story.card_id}")
            if not self._exists("personas", story.persona_id, owner):
                raise NotFound(f"Không tìm thấy persona {story.persona_id}")
            if initial_relationship is None:
                initial_relationship = self._card_initial_relationship(story.card_id)
            values: dict[str, Any] = {
                "initial_relationship_json": _dumps(initial_relationship.model_dump(mode="json")),
                "account_id": owner,
                "uid": new_uid(),
                "card_id": story.card_id,
                "persona_id": story.persona_id,
                "title": story.title,
                "scenario": story.scenario,
                "language": story.language,
                "mode": story.mode,
                "relationship_type": story.relationship_type,
                "pov": story.pov,
                "thought_style": story.thought_style,
                "narration_pronouns_json": _dumps(story.narration_pronouns.model_dump(mode="json")),
                "model_name": story.model_name,
                "scene_summary": story.scene_summary,
                "show_thoughts": 1 if story.show_thoughts else 0,
            }
            if story.id is not None:
                values = {"id": story.id, **values}
            story_id = self._insert("stories", values)
        return self.get_story(story_id, account_id=owner)

    def _card_initial_relationship(self, card_id: int) -> RelationshipValues:
        row = self._conn.execute("SELECT extensions_json FROM character_cards WHERE id = ?", (card_id,)).fetchone()
        extensions: Any = None
        if row is not None:
            try:
                extensions = json.loads(row["extensions_json"])
            except (json.JSONDecodeError, TypeError):
                extensions = None
        return initial_relationship(None, extensions if isinstance(extensions, dict) else None)

    @_locked
    def story_initial_relationship(self, story_id: int) -> dict[str, Any] | None:
        """Ảnh chụp điểm xuất phát lưu lúc tạo story (chưa kiểm tra); None với story tạo trước Phase 3."""
        row = self._conn.execute(
            "SELECT initial_relationship_json FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy story {story_id}")
        raw = row["initial_relationship_json"]
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    @_locked
    def set_story_initial_relationship(self, story_id: int, values: RelationshipValues | None) -> None:
        """Ghi (None = xoá) ảnh chụp điểm xuất phát của story."""
        with self.transaction():
            self._require_story(story_id)
            self._conn.execute(
                "UPDATE stories SET initial_relationship_json = ? WHERE id = ?",
                (None if values is None else _dumps(values.model_dump(mode="json")), story_id),
            )

    @_locked
    def get_story(self, story_id: int, *, account_id: AccountScope) -> Story:
        where, params = _scope(account_id)
        row = self._conn.execute(f"SELECT * FROM stories WHERE id = ? AND {where}", (story_id, *params)).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy story {story_id}")
        return _row_to_story(row)

    @_locked
    def list_stories(self, *, account_id: AccountScope) -> list[Story]:
        """Hoạt động gần nhất trước (message mới nhất hoặc lần sửa thiết lập gần nhất)."""
        where, params = _scope(account_id, "s.account_id")
        rows = self._conn.execute(
            f"SELECT s.* FROM stories s WHERE {where} ORDER BY {_STORY_ACTIVITY} DESC, s.id DESC", params
        ).fetchall()
        return [_row_to_story(r) for r in rows]

    @_locked
    def story_updated_at(self, story_id: int) -> str | None:
        """max(created_at của message mới nhất, stories.updated_at); None nếu không có story."""
        row = self._conn.execute(
            f"SELECT {_STORY_ACTIVITY} AS activity FROM stories s WHERE s.id = ?", (story_id,)
        ).fetchone()
        return None if row is None else str(row["activity"])

    @_locked
    def story_rows(self, story_id: int | None = None, *, account_id: AccountScope) -> list[StoryRow]:
        """Story kèm dữ liệu cho danh sách (tên/vai trò/avatar nhân vật, tên persona, hoạt động gần nhất,
        tin nhắn active mới nhất có nội dung hiển thị) trong MỘT câu SQL; thứ tự như `list_stories`.

        `story_id` khác None: chỉ story đó (rỗng nếu không có). `account_id`: chỉ story của account đó
        (`ANY_ACCOUNT`: mọi tài khoản).
        """
        clause, params = _scope(account_id, "s.account_id")
        where = f"WHERE {clause}"
        if story_id is not None:
            where += " AND s.id = ?"
            params = (*params, story_id)
        rows = self._conn.execute(
            f"""
            SELECT s.*,
                   c.name AS _card_name, c.role AS _card_role, c.avatar AS _card_avatar,
                   p.name AS _persona_name,
                   {_STORY_ACTIVITY} AS _activity,
                   lm.visible_content AS _last_visible, lm.role AS _last_role, lm.mode AS _last_mode
              FROM stories s
              JOIN character_cards c ON c.id = s.card_id
              JOIN personas p ON p.id = s.persona_id
              LEFT JOIN messages lm ON lm.id = (
                    SELECT m.id FROM messages m
                     WHERE m.story_id = s.id AND m.is_active = 1 AND TRIM(m.visible_content) != ''
                     ORDER BY m.turn_index DESC LIMIT 1)
              {where}
             ORDER BY _activity DESC, s.id DESC
            """,
            params,
        ).fetchall()
        return [
            StoryRow(
                story=_row_to_story(r),
                card_name=r["_card_name"],
                card_role=r["_card_role"],
                card_avatar=r["_card_avatar"],
                persona_name=r["_persona_name"],
                updated_at=None if r["_activity"] is None else str(r["_activity"]),
                last_visible=r["_last_visible"],
                last_role=r["_last_role"],
                last_mode=r["_last_mode"],
            )
            for r in rows
        ]

    @_locked
    def delete_story(self, story_id: int, *, account_id: AccountScope) -> None:
        """Xoá story; message, feedback, lịch sử sửa đi theo (ON DELETE CASCADE). Card của story là bản sao và
        không còn story nào dùng thì xoá luôn bản sao (§4.3; tên file ảnh: `pop_orphan_avatars()`)."""
        with self.transaction():
            self._require_story(story_id, account_id)
            self._conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            self._drop_orphan_copies()

    @_locked
    def story_account_id(self, story_id: int) -> int:
        """Chủ của story (cổng sinh chung cần biết lượt sinh là của tài khoản nào, §5.1). NotFound nếu không có."""
        row = self._conn.execute("SELECT account_id FROM stories WHERE id = ?", (story_id,)).fetchone()
        if row is None or row[0] is None:
            raise NotFound(f"Không tìm thấy story {story_id}")
        return int(row[0])

    @_locked
    def update_story(self, story_id: int, *, account_id: AccountScope, **fields: Any) -> Story:
        """Sửa các trường trong STORY_UPDATABLE_FIELDS (uid, card, persona, chủ sở hữu không đổi được)."""
        unknown = set(fields) - STORY_UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Không được sửa trường của story: {', '.join(sorted(unknown))}")
        current = self.get_story(story_id, account_id=account_id)
        if not fields:
            return current
        # Kiểm tra kiểu bằng chính model Story (ValidationError là ValueError).
        updated = Story.model_validate({**current.model_dump(), **fields})
        columns: dict[str, Any] = {}
        for name in fields:
            if name == "narration_pronouns":
                columns["narration_pronouns_json"] = _dumps(updated.narration_pronouns.model_dump(mode="json"))
            elif name == "show_thoughts":
                columns[name] = 1 if updated.show_thoughts else 0
            else:
                columns[name] = getattr(updated, name)
        assignments = ", ".join(f"{col} = ?" for col in columns)
        touch = "" if set(fields) <= STORY_DISPLAY_FIELDS else f", updated_at = {_NOW}"
        with self.transaction():
            self._conn.execute(
                f"UPDATE stories SET {assignments}{touch} WHERE id = ?",
                (*columns.values(), story_id),
            )
        return self.get_story(story_id, account_id=account_id)

    # ------------------------------------------------------------------ messages

    @_locked
    def active_messages(self, story_id: int) -> list[Message]:
        """Message active của story theo turn_index; có variant_count và rating."""
        self._require_story(story_id)
        rows = self._conn.execute(
            _MESSAGE_SELECT + " WHERE m.story_id = ? AND m.is_active = 1 ORDER BY m.turn_index",
            (story_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @_locked
    def list_variants(self, story_id: int, turn_index: int) -> list[Message]:
        """Mọi variant của một lượt, theo variant_index."""
        self._require_story(story_id)
        rows = self._conn.execute(
            _MESSAGE_SELECT + " WHERE m.story_id = ? AND m.turn_index = ? ORDER BY m.variant_index",
            (story_id, turn_index),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @_locked
    def get_message(self, message_id: int, *, account_id: AccountScope) -> Message:
        """Message theo id; story chứa nó phải thuộc `account_id` (`ANY_ACCOUNT`: không lọc)."""
        where, params = _scope(account_id)
        row = self._conn.execute(
            _MESSAGE_SELECT + f" WHERE m.id = ? AND m.story_id IN (SELECT id FROM stories WHERE {where})",
            (message_id, *params),
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
        return _row_to_message(row)

    @_locked
    def last_turn_index(self, story_id: int) -> int | None:
        self._require_story(story_id)
        row = self._conn.execute(
            "SELECT MAX(turn_index) FROM messages WHERE story_id = ?", (story_id,)
        ).fetchone()
        return None if row[0] is None else int(row[0])

    @_locked
    def next_turn_index(self, story_id: int) -> int:
        last = self.last_turn_index(story_id)
        return 0 if last is None else last + 1

    @_locked
    def insert_message(self, msg: Message) -> Message:
        """Thêm lượt mới: turn_index lấy từ msg, variant 0, active."""
        with self.transaction():
            self._require_story(msg.story_id)
            taken = self._conn.execute(
                "SELECT 1 FROM messages WHERE story_id = ? AND turn_index = ?",
                (msg.story_id, msg.turn_index),
            ).fetchone()
            if taken is not None:
                raise ValueError(f"Lượt {msg.turn_index} của story {msg.story_id} đã tồn tại")
            message_id = self._insert(
                "messages",
                {
                    "story_id": msg.story_id,
                    "turn_index": msg.turn_index,
                    "variant_index": 0,
                    "is_active": 1,
                    **_message_columns(msg),
                },
            )
        return self.get_message(message_id, account_id=ANY_ACCOUNT)

    @_locked
    def add_variant(self, msg: Message) -> Message:
        """Thêm variant mới cho lượt đã có (cùng story/turn) và đặt nó active."""
        if msg.role != "assistant":
            raise ValueError("Chỉ lượt của nhân vật AI mới có nhiều variant")
        with self.transaction():
            self._require_story(msg.story_id)
            row = self._conn.execute(
                "SELECT MAX(variant_index) AS max_variant, MIN(role) AS role, COUNT(DISTINCT role) AS roles"
                " FROM messages WHERE story_id = ? AND turn_index = ?",
                (msg.story_id, msg.turn_index),
            ).fetchone()
            if row["max_variant"] is None:
                raise NotFound(f"Không tìm thấy lượt {msg.turn_index} của story {msg.story_id}")
            if row["roles"] != 1 or row["role"] != msg.role:
                raise ValueError(f"Lượt {msg.turn_index} không phải lượt của nhân vật AI")
            # Tắt các variant cũ trước rồi mới chèn, để không vi phạm idx_messages_one_active.
            self._conn.execute(
                "UPDATE messages SET is_active = 0 WHERE story_id = ? AND turn_index = ?",
                (msg.story_id, msg.turn_index),
            )
            message_id = self._insert(
                "messages",
                {
                    "story_id": msg.story_id,
                    "turn_index": msg.turn_index,
                    "variant_index": int(row["max_variant"]) + 1,
                    "is_active": 1,
                    **_message_columns(msg),
                },
            )
        return self.get_message(message_id, account_id=ANY_ACCOUNT)

    @_locked
    def select_variant(self, story_id: int, turn_index: int, variant_index: int) -> Message:
        with self.transaction():
            self._require_story(story_id)
            row = self._conn.execute(
                "SELECT id FROM messages WHERE story_id = ? AND turn_index = ? AND variant_index = ?",
                (story_id, turn_index, variant_index),
            ).fetchone()
            if row is None:
                raise NotFound(
                    f"Không tìm thấy variant {variant_index} của lượt {turn_index} trong story {story_id}"
                )
            self._conn.execute(
                "UPDATE messages SET is_active = 0 WHERE story_id = ? AND turn_index = ? AND id != ?",
                (story_id, turn_index, row["id"]),
            )
            self._conn.execute("UPDATE messages SET is_active = 1 WHERE id = ?", (row["id"],))
        return self.get_message(row["id"], account_id=ANY_ACCOUNT)

    @_locked
    def edit_message(
        self,
        message_id: int,
        *,
        raw_content: str,
        visible_content: str,
        thought: str | None,
        directive: str | None,
    ) -> Message:
        """Sửa nội dung; ghi message_edits(before, after), đặt edited_at; model_output giữ nguyên."""
        with self.transaction():
            row = self._conn.execute(
                "SELECT raw_content FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
            if row is None:
                raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
            self._insert(
                "message_edits",
                {"message_id": message_id, "before_raw": row["raw_content"], "after_raw": raw_content},
            )
            self._conn.execute(
                "UPDATE messages SET raw_content = ?, visible_content = ?, thought = ?, directive = ?,"
                f" edited_at = {_NOW} WHERE id = ?",
                (raw_content, visible_content, thought, directive, message_id),
            )
        return self.get_message(message_id, account_id=ANY_ACCOUNT)

    @_locked
    def message_edits(self, message_id: int) -> list[dict[str, Any]]:
        """Lịch sử sửa của một message, cũ nhất trước: {id, before_raw, after_raw, created_at}."""
        if not self._exists("messages", message_id):
            raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
        rows = self._conn.execute(
            "SELECT id, before_raw, after_raw, created_at FROM message_edits"
            " WHERE message_id = ? ORDER BY id",
            (message_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @_locked
    def truncate_from(self, story_id: int, turn_index: int) -> int:
        """Xoá mọi variant của các lượt >= turn_index. Trả số message đã xoá."""
        with self.transaction():
            self._require_story(story_id)
            cur = self._conn.execute(
                "DELETE FROM messages WHERE story_id = ? AND turn_index >= ?",
                (story_id, turn_index),
            )
            deleted = cur.rowcount
        return deleted

    @_locked
    def set_feedback(self, message_id: int, rating: Rating | None, note: str | None = None) -> Message:
        """Đặt đánh giá; note=None giữ nguyên ghi chú cũ."""
        if rating not in ("up", "down", None):
            raise ValueError(f"Đánh giá không hợp lệ: {rating!r}")
        with self.transaction():
            if not self._exists("messages", message_id):
                raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
            self._conn.execute(
                "INSERT INTO feedback (message_id, rating, note) VALUES (?, ?, ?)"
                " ON CONFLICT(message_id) DO UPDATE SET"
                "   rating = excluded.rating,"
                "   note = CASE WHEN ? IS NULL THEN feedback.note ELSE excluded.note END,"
                f"   updated_at = {_NOW}",
                (message_id, rating, note if note is not None else "", note),
            )
        return self.get_message(message_id, account_id=ANY_ACCOUNT)

    @_locked
    def get_feedback_note(self, message_id: int) -> str:
        if not self._exists("messages", message_id):
            raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
        row = self._conn.execute("SELECT note FROM feedback WHERE message_id = ?", (message_id,)).fetchone()
        return "" if row is None else str(row["note"])

    # ------------------------------------------------------------------ Phase 3: message active

    @_locked
    def story_exists(self, story_id: int) -> bool:
        """Story còn tồn tại (không lọc account; dùng cho worker)."""
        return self._exists("stories", story_id)

    @_locked
    def message_is_active(self, message_id: int) -> bool:
        """Message còn tồn tại và đang active (False nếu đã xoá hoặc đã bị variant khác thay)."""
        row = self._conn.execute("SELECT is_active FROM messages WHERE id = ?", (message_id,)).fetchone()
        return row is not None and bool(row["is_active"])

    @_locked
    def last_active_message_ref(self, story_id: int) -> tuple[int, str, int] | None:
        """(id, role, turn_index) của message active cuối của story; None nếu story chưa có message."""
        row = self._conn.execute(
            "SELECT id, role, turn_index FROM messages WHERE story_id = ? AND is_active = 1"
            " ORDER BY turn_index DESC LIMIT 1",
            (story_id,),
        ).fetchone()
        return None if row is None else (int(row["id"]), str(row["role"]), int(row["turn_index"]))

    # ------------------------------------------------------------------ Phase 3: state_events

    def _message_ref(self, message_id: int) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT id, story_id, turn_index, is_active FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy tin nhắn {message_id}")
        return row

    def _insert_event(self, story_id: int, message_id: int, kind: EventKind, payload: dict[str, Any]) -> int:
        if kind not in EVENT_KINDS:
            raise ValueError(f"Loại state event không hợp lệ: {kind!r}")
        return self._insert(
            "state_events",
            {
                "story_id": story_id,
                "message_id": message_id,
                "kind": kind,
                "payload_json": _dumps(payload),
                "created_at": self._now(),
            },
        )

    def _now(self) -> str:
        return str(self._conn.execute(f"SELECT {_NOW}").fetchone()[0])

    @_locked
    def add_state_event(self, message_id: int, kind: EventKind, payload: dict[str, Any]) -> int:
        """Ghi một event cho message (story lấy theo message). NotFound nếu message không có."""
        with self.transaction():
            ref = self._message_ref(message_id)
            return self._insert_event(int(ref["story_id"]), message_id, kind, payload)

    @_locked
    def state_events(
        self,
        story_id: int,
        *,
        kinds: tuple[EventKind, ...] | None = None,
        upto_turn: int | None = None,
    ) -> list[StateEvent]:
        """Event của các message ACTIVE, theo turn_index rồi id. Payload hỏng thì bị bỏ qua."""
        sql = (
            "SELECT e.*, m.turn_index AS turn_index FROM state_events e "
            + _ACTIVE_JOIN.format(alias="e")
            + " WHERE e.story_id = ?"
        )
        params: list[Any] = [story_id]
        if kinds:
            sql += f" AND e.kind IN ({', '.join('?' for _ in kinds)})"
            params.extend(kinds)
        if upto_turn is not None:
            sql += " AND m.turn_index <= ?"
            params.append(upto_turn)
        rows = self._conn.execute(sql + " ORDER BY m.turn_index, e.id", params).fetchall()
        return [e for e in (_row_to_event(r) for r in rows) if e is not None]

    @_locked
    def message_state_events(self, message_id: int) -> list[StateEvent]:
        """Mọi event của một message (kể cả khi message không active), theo id."""
        rows = self._conn.execute(
            "SELECT e.*, m.turn_index AS turn_index FROM state_events e"
            " JOIN messages m ON m.id = e.message_id WHERE e.message_id = ? ORDER BY e.id",
            (message_id,),
        ).fetchall()
        return [e for e in (_row_to_event(r) for r in rows) if e is not None]

    @_locked
    def delete_message_state(self, message_id: int) -> int:
        """Xoá event loại trích xuất, gợi ý và memories của message (khi sửa nội dung). Trả số dòng đã xoá.

        Event `summary` neo ở message được GIỮ: đó là tóm tắt dồn của mọi lượt tới mốc này, không phải
        kết quả của riêng message (giống `replace_extraction`, cũng không xoá nó).
        """
        marks = ", ".join("?" for _ in MESSAGE_STATE_KINDS)
        with self.transaction():
            a = self._conn.execute(
                f"DELETE FROM state_events WHERE message_id = ? AND kind IN ({marks})",
                (message_id, *MESSAGE_STATE_KINDS),
            ).rowcount
            b = self._conn.execute("DELETE FROM memories WHERE message_id = ?", (message_id,)).rowcount
        return a + b

    @_locked
    def replace_extraction(
        self,
        message_id: int,
        events: list[tuple[EventKind, dict[str, Any]]],
        memories: list[NewMemory],
        *,
        story_id: int | None = None,
        turn_index: int | None = None,
    ) -> list[MemoryItem] | None:
        """Ghi kết quả trích xuất của một message trong MỘT transaction, thay kết quả cũ (nếu có):
        xoá event loại trích xuất (relationship_delta, scene) và ký ức/fact cũ của message. Gợi ý (theo yêu
        cầu, Phase 3b) không bị đụng tới.

        Message đã xoá hoặc không còn active -> không ghi gì, trả None. Trả các ký ức/fact vừa ghi.
        `story_id`/`turn_index` (worker luôn truyền): message phải còn thuộc đúng story/lượt đó. id message
        không AUTOINCREMENT nên message bị xoá (xoá story/card) có thể nhường id cho message của story
        khác; khi đó không được ghi kết quả cũ vào nó -> trả None.
        """
        with self.transaction():
            row = self._conn.execute(
                "SELECT story_id, turn_index, is_active FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
            if row is None or not row["is_active"]:
                return None
            if story_id is not None and int(row["story_id"]) != story_id:
                return None
            if turn_index is not None and int(row["turn_index"]) != turn_index:
                return None
            story_id, turn_index = int(row["story_id"]), int(row["turn_index"])
            marks = ", ".join("?" for _ in EXTRACTION_KINDS)
            self._conn.execute(
                f"DELETE FROM state_events WHERE message_id = ? AND kind IN ({marks})", (message_id, *EXTRACTION_KINDS)
            )
            self._conn.execute("DELETE FROM memories WHERE message_id = ?", (message_id,))
            for kind, payload in events:
                if kind not in EXTRACTION_KINDS:
                    raise ValueError(f"Loại event không thuộc trích xuất: {kind!r}")
                self._insert_event(story_id, message_id, kind, payload)
            ids: list[int] = []
            now = self._now()
            for mem in memories:
                text = mem.text.strip()
                if not text:
                    continue
                ids.append(
                    self._insert(
                        "memories",
                        {
                            "story_id": story_id,
                            "message_id": message_id,
                            "turn_index": turn_index,
                            "kind": mem.kind,
                            "subject": (mem.subject or "").strip() or None,
                            "text": text,
                            "importance": min(5, max(1, int(mem.importance))),
                            "created_at": now,
                        },
                    )
                )
        return [self._get_memory_row(i) for i in ids]

    @_locked
    def replace_suggestions(self, message_id: int, items: list[str]) -> bool:
        """Phase 3b: ghi gợi ý theo yêu cầu cho message, thay gợi ý cũ của nó (một event 'suggestions').

        Chỉ ghi khi message còn là message active CUỐI của story và là của nhân vật (người chơi chưa trả
        lời); không thì không ghi gì, trả False.
        """
        with self.transaction():
            ref = self._message_ref(message_id)
            story_id = int(ref["story_id"])
            last = self._conn.execute(
                "SELECT id, role FROM messages WHERE story_id = ? AND is_active = 1 ORDER BY turn_index DESC LIMIT 1",
                (story_id,),
            ).fetchone()
            if last is None or int(last["id"]) != message_id or last["role"] != "assistant":
                return False
            self._conn.execute(
                "DELETE FROM state_events WHERE message_id = ? AND kind = 'suggestions'", (message_id,)
            )
            self._insert_event(story_id, message_id, "suggestions", {"items": list(items)})
        return True

    @_locked
    def add_summary(self, message_id: int, text: str, upto_turn: int) -> int:
        """Ghi tóm tắt tự động (event 'summary') gắn với message ở lượt cuối được tóm tắt."""
        return self.add_state_event(message_id, "summary", {"text": text, "upto_turn": int(upto_turn)})

    # ------------------------------------------------------------------ Phase 3: memories

    def _get_memory_row(self, memory_id: int) -> MemoryItem:
        row = self._conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy ký ức {memory_id}")
        return _row_to_memory(row)

    @_locked
    def get_memory(self, memory_id: int) -> MemoryItem:
        return self._get_memory_row(memory_id)

    @_locked
    def list_memories(
        self,
        story_id: int,
        *,
        limit: int | None = 50,
        kind: MemoryKind | None = None,
        upto_turn: int | None = None,
        message_id: int | None = None,
    ) -> list[MemoryItem]:
        """Ký ức/fact của message active, mới nhất trước (turn_index giảm dần, rồi id giảm dần).

        `message_id` khác None: chỉ của message đó (kể cả khi message không active).
        """
        if message_id is not None:
            sql = "SELECT k.* FROM memories k WHERE k.story_id = ? AND k.message_id = ?"
            params: list[Any] = [story_id, message_id]
        else:
            sql = "SELECT k.* FROM memories k " + _ACTIVE_JOIN.format(alias="k") + " WHERE k.story_id = ?"
            params = [story_id]
        if kind is not None:
            sql += " AND k.kind = ?"
            params.append(kind)
        if upto_turn is not None:
            sql += " AND k.turn_index <= ?"
            params.append(upto_turn)
        sql += " ORDER BY k.turn_index DESC, k.id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        return [_row_to_memory(r) for r in self._conn.execute(sql, params).fetchall()]

    @_locked
    def delete_memory(self, story_id: int, memory_id: int, *, account_id: AccountScope) -> None:
        """Quên một ký ức/fact. NotFound nếu không thuộc story (hoặc story không thuộc account)."""
        with self.transaction():
            self._require_story(story_id, account_id)
            cur = self._conn.execute("DELETE FROM memories WHERE id = ? AND story_id = ?", (memory_id, story_id))
            if cur.rowcount == 0:
                raise NotFound(f"Không tìm thấy ký ức {memory_id} trong story {story_id}")

    @_locked
    def search_memories_fts(self, story_id: int, terms: list[str], limit: int) -> list[tuple[MemoryItem, float]]:
        """Tìm ký ức/fact active theo từ khoá (FTS5, các term nối bằng OR).

        Trả (ký ức, bm25) theo bm25 tăng dần (SQLite: nhỏ hơn = khớp hơn). Không có term -> [].
        """
        expr = fts_match_expression(terms)
        if expr is None or limit <= 0:
            return []
        try:
            rows = self._conn.execute(
                "SELECT k.*, bm25(memories_fts) AS _rank FROM memories_fts"
                " JOIN memories k ON k.id = memories_fts.rowid "
                + _ACTIVE_JOIN.format(alias="k")
                + " WHERE memories_fts MATCH ? AND k.story_id = ?"
                " ORDER BY _rank, k.id LIMIT ?",
                (expr, story_id, int(limit)),
            ).fetchall()
        except sqlite3.OperationalError:
            # Biểu thức đã được đặt trong ngoặc kép nên không nên lỗi; phòng hờ thì coi như không thấy gì.
            return []
        return [(_row_to_memory(r), float(r["_rank"])) for r in rows]

    @_locked
    def memory_embeddings(self, story_id: int, embed_model: str) -> list[tuple[MemoryItem, bytes]]:
        """Ký ức/fact active đã embed bằng `embed_model`: (ký ức, BLOB float32 little-endian)."""
        rows = self._conn.execute(
            "SELECT k.* FROM memories k "
            + _ACTIVE_JOIN.format(alias="k")
            + " WHERE k.story_id = ? AND k.embedding IS NOT NULL AND k.embed_model = ? ORDER BY k.id",
            (story_id, embed_model),
        ).fetchall()
        return [(_row_to_memory(r), bytes(r["embedding"])) for r in rows]

    @_locked
    def memories_missing_embedding(self, story_id: int, embed_model: str, *, limit: int = 64) -> list[MemoryItem]:
        """Ký ức/fact active chưa có embedding của `embed_model` (cũ nhất trước)."""
        rows = self._conn.execute(
            "SELECT k.* FROM memories k "
            + _ACTIVE_JOIN.format(alias="k")
            + " WHERE k.story_id = ? AND (k.embedding IS NULL OR k.embed_model IS NOT ?) ORDER BY k.id LIMIT ?",
            (story_id, embed_model, int(limit)),
        ).fetchall()
        return [_row_to_memory(r) for r in rows]

    @_locked
    def set_memory_embedding(self, memory_id: int, embedding: bytes, embed_model: str) -> bool:
        """Lưu embedding; False nếu ký ức đã bị xoá trong lúc embed."""
        with self.transaction():
            cur = self._conn.execute(
                "UPDATE memories SET embedding = ?, embed_model = ? WHERE id = ?",
                (sqlite3.Binary(embedding), embed_model, memory_id),
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------ Phase 3: jobs

    @_locked
    def enqueue_job(self, story_id: int, kind: JobKind, message_id: int | None = None) -> int:
        """Xếp job `queued`. Đã có job cùng (story, kind, message) đang `queued` thì trả id job đó."""
        if kind not in JOB_KINDS:
            raise ValueError(f"Loại job không hợp lệ: {kind!r}")
        with self.transaction():
            self._require_story(story_id)
            row = self._conn.execute(
                "SELECT id FROM jobs WHERE story_id = ? AND kind = ? AND message_id IS ? AND status = 'queued'"
                " ORDER BY id LIMIT 1",
                (story_id, kind, message_id),
            ).fetchone()
            if row is not None:
                return int(row["id"])
            now = self._now()
            return self._insert(
                "jobs",
                {
                    "story_id": story_id,
                    "message_id": message_id,
                    "kind": kind,
                    "status": "queued",
                    "attempts": 0,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    @_locked
    def get_job(self, job_id: int) -> Job:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy job {job_id}")
        return _row_to_job(row)

    @_locked
    def list_jobs(self, story_id: int | None = None, *, statuses: tuple[JobStatus, ...] | None = None) -> list[Job]:
        """Job theo id tăng dần; lọc theo story và trạng thái nếu có."""
        sql, params = "SELECT * FROM jobs WHERE (? IS NULL OR story_id = ?)", [story_id, story_id]
        if statuses:
            sql += f" AND status IN ({', '.join('?' for _ in statuses)})"
            params.extend(statuses)
        return [_row_to_job(r) for r in self._conn.execute(sql + " ORDER BY id", params).fetchall()]

    @_locked
    def claim_next_job(self) -> Job | None:
        """Lấy job `queued` và đặt `running`. Hàng đợi rỗng -> None.

        Phase 4b (docs/auth.md §5.3): xen kẽ theo tài khoản. Lấy job cũ nhất của tài khoản KHÁC tài khoản của
        job vừa lấy ra, nếu có; không có thì job cũ nhất (FIFO). Một người "Đọc lại story" (hàng trăm job)
        không bắt người khác chờ ghi nhớ.
        """
        with self.transaction():
            base = (
                "SELECT j.id AS id, s.account_id AS account_id FROM jobs j JOIN stories s ON s.id = j.story_id"
                " WHERE j.status = 'queued'"
            )
            row = None
            if self._last_job_account is not None:
                row = self._conn.execute(
                    base + " AND s.account_id IS NOT ? ORDER BY j.id LIMIT 1", (self._last_job_account,)
                ).fetchone()
            if row is None:
                row = self._conn.execute(base + " ORDER BY j.id LIMIT 1").fetchone()
            if row is None:
                return None
            self._last_job_account = None if row["account_id"] is None else int(row["account_id"])
            self._conn.execute(
                f"UPDATE jobs SET status = 'running', updated_at = {_NOW} WHERE id = ?", (row["id"],)
            )
            return self.get_job(int(row["id"]))

    @_locked
    def finish_job(
        self,
        job_id: int,
        status: JobStatus,
        *,
        error: str | None = None,
        attempts: int | None = None,
        only_running: bool = True,
    ) -> bool:
        """Kết thúc job (done/failed/cancelled); `attempts` None = giữ nguyên. False nếu không cập nhật.

        Mặc định chỉ kết thúc job đang `running`: id job không AUTOINCREMENT nên job bị xoá theo story
        (CASCADE) có thể nhường id cho job mới đang `queued`; worker không được đánh dấu nhầm job đó.
        `only_running=False` dành cho script ghi sẵn kết quả (job chưa từng chạy).
        """
        if status not in ("done", "failed", "cancelled"):
            raise ValueError(f"Trạng thái kết thúc không hợp lệ: {status!r}")
        guard = " AND status = 'running'" if only_running else ""
        with self.transaction():
            cur = self._conn.execute(
                f"UPDATE jobs SET status = ?, error = ?, attempts = COALESCE(?, attempts), updated_at = {_NOW}"
                " WHERE id = ?" + guard,
                (status, error, attempts, job_id),
            )
        return cur.rowcount > 0

    @_locked
    def requeue_job(self, job_id: int) -> bool:
        """Đưa job đang chạy về `queued` (bị lượt chat chen ngang); `attempts` giữ nguyên."""
        with self.transaction():
            cur = self._conn.execute(
                f"UPDATE jobs SET status = 'queued', updated_at = {_NOW} WHERE id = ? AND status = 'running'",
                (job_id,),
            )
        return cur.rowcount > 0

    @_locked
    def reset_running_jobs(self) -> int:
        """Lúc khởi động: job `running` còn sót (app tắt giữa chừng) quay về `queued`."""
        with self.transaction():
            cur = self._conn.execute(
                f"UPDATE jobs SET status = 'queued', updated_at = {_NOW} WHERE status = 'running'"
            )
        return cur.rowcount

    @_locked
    def cancel_stale_jobs(self, story_id: int | None = None) -> int:
        """Job `queued` của message không còn active (đã regenerate/lật variant) -> `cancelled`."""
        with self.transaction():
            cur = self._conn.execute(
                "UPDATE jobs SET status = 'cancelled', error = 'Message không còn active',"
                f" updated_at = {_NOW}"
                " WHERE status = 'queued' AND message_id IS NOT NULL AND (? IS NULL OR story_id = ?)"
                "   AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.id = jobs.message_id AND m.is_active = 1)",
                (story_id, story_id),
            )
        return cur.rowcount

    @_locked
    def forget_extract_jobs(self, message_id: int) -> int:
        """Xoá lịch sử job extract đã kết thúc của message (sửa nội dung: phải trích xuất lại từ đầu)."""
        with self.transaction():
            cur = self._conn.execute(
                "DELETE FROM jobs WHERE message_id = ? AND kind = 'extract' AND status IN ('done','failed','cancelled')",
                (message_id,),
            )
        return cur.rowcount

    @_locked
    def has_pending_jobs(self, story_id: int, *, kinds: tuple[JobKind, ...] | None = None) -> bool:
        """Story còn job `queued`/`running` (lọc theo loại nếu có)."""
        sql = "SELECT 1 FROM jobs WHERE story_id = ? AND status IN ('queued','running')"
        params: list[Any] = [story_id]
        if kinds:
            sql += f" AND kind IN ({', '.join('?' for _ in kinds)})"
            params.extend(kinds)
        return self._conn.execute(sql + " LIMIT 1", params).fetchone() is not None

    @_locked
    def message_has_extract_job(self, message_id: int, statuses: tuple[JobStatus, ...]) -> bool:
        marks = ", ".join("?" for _ in statuses)
        row = self._conn.execute(
            f"SELECT 1 FROM jobs WHERE message_id = ? AND kind = 'extract' AND status IN ({marks}) LIMIT 1",
            (message_id, *statuses),
        ).fetchone()
        return row is not None

    _UNPROCESSED = """
        FROM messages m
       WHERE m.story_id = ? AND m.is_active = 1 AND m.role = 'assistant' AND m.turn_index >= 0
         AND COALESCE(json_extract(m.gen_stats_json, '$.aborted'), 0) = 0
         AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.message_id = m.id AND j.kind = 'extract'
                          AND j.status IN ('done','queued','running'))
    """

    @_locked
    def unprocessed_turns(self, story_id: int) -> int:
        """Số lượt trả lời active (kể cả lời mở đầu lượt 0, Phase 3b; trừ lượt bị Dừng giữa chừng) chưa được
        trích xuất và cũng không có job đang chờ."""
        row = self._conn.execute("SELECT COUNT(*) " + self._UNPROCESSED, (story_id,)).fetchone()
        return int(row[0])

    @_locked
    def messages_needing_extract(self, story_id: int) -> list[Message]:
        """Message assistant active (kể cả lượt 0; trừ lượt aborted) chưa có job extract done/đang chờ, theo lượt."""
        rows = self._conn.execute(
            "SELECT m.id " + self._UNPROCESSED + " ORDER BY m.turn_index", (story_id,)
        ).fetchall()
        return [self.get_message(int(r["id"]), account_id=ANY_ACCOUNT) for r in rows]

    # ------------------------------------------------------------------ Phase 4: sổ thế giới

    @_locked
    def list_lore(self, card_id: int, *, include_removed: bool = False) -> list[LoreEntry]:
        """Mục thế giới của card theo `position, id`. Mặc định bỏ các hàng "bia mộ" (removed)."""
        where = "" if include_removed else " AND removed = 0"
        rows = self._conn.execute(
            f"SELECT * FROM lore_entries WHERE card_id = ?{where} ORDER BY position, id", (card_id,)
        ).fetchall()
        return [_row_to_lore(r) for r in rows]

    @_locked
    def lore_by_slug(self, card_id: int) -> dict[str, tuple[LoreEntry, bool]]:
        """slug -> (mục, đã xoá/bia mộ) cho mọi hàng của card (kể cả removed), để nhập lại theo slug."""
        rows = self._conn.execute("SELECT * FROM lore_entries WHERE card_id = ?", (card_id,)).fetchall()
        return {str(r["slug"]): (_row_to_lore(r), bool(r["removed"])) for r in rows}

    @_locked
    def get_lore(self, card_id: int, entry_id: int) -> LoreEntry:
        """Mục `entry_id` của card `card_id`. Không có, thuộc card khác, hoặc đã xoá -> NotFound."""
        row = self._conn.execute(
            "SELECT * FROM lore_entries WHERE id = ? AND card_id = ? AND removed = 0", (entry_id, card_id)
        ).fetchone()
        if row is None:
            raise NotFound(f"Không tìm thấy mục thế giới {entry_id}")
        return _row_to_lore(row)

    @_locked
    def count_lore(self, card_id: int) -> int:
        """Số mục (chưa xoá) của card."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM lore_entries WHERE card_id = ? AND removed = 0", (card_id,)
        ).fetchone()
        return int(row[0])

    @_locked
    def count_lore_for_account(self, account_id: AccountScope) -> int:
        """Số mục (chưa xoá) trên mọi card của account, không đếm sổ thế giới của bản sao (§4.1)."""
        where, params = _scope(account_id, "c.account_id")
        row = self._conn.execute(
            "SELECT COUNT(*) FROM lore_entries e JOIN character_cards c ON c.id = e.card_id"
            f" WHERE e.removed = 0 AND {where} AND {self._no_copy('c.')}",
            params,
        ).fetchone()
        return int(row[0])

    @_locked
    def next_lore_position(self, card_id: int) -> int:
        row = self._conn.execute("SELECT MAX(position) FROM lore_entries WHERE card_id = ?", (card_id,)).fetchone()
        return 0 if row[0] is None else int(row[0]) + 1

    @_locked
    def insert_lore(self, entry: LoreEntry) -> LoreEntry:
        """Thêm một mục (bỏ qua `entry.id`, created_at/updated_at do DB đặt). Slug trùng -> sqlite3.IntegrityError."""
        with self.transaction():
            self._require_card(entry.card_id)
            now = self._now()
            values = {
                "card_id": entry.card_id,
                "slug": entry.slug,
                **_lore_columns(
                    {
                        "title": entry.title,
                        "category": entry.category,
                        "keys": entry.keys,
                        "known_by": entry.known_by,
                        "content": entry.content,
                        "source": entry.source,
                        "edited": entry.edited,
                        "removed": False,
                        "enabled": entry.enabled,
                        "priority": entry.priority,
                        "position": entry.position,
                        "extra": entry.extra,
                    }
                ),
                "created_at": now,
                "updated_at": now,
            }
            entry_id = self._insert("lore_entries", values)
        row = self._conn.execute("SELECT * FROM lore_entries WHERE id = ?", (entry_id,)).fetchone()
        return _row_to_lore(row)

    @_locked
    def update_lore(self, entry_id: int, **fields: Any) -> LoreEntry:
        """Sửa các trường trong LORE_UPDATABLE_FIELDS (kể cả hàng removed); đặt updated_at."""
        unknown = set(fields) - LORE_UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Không được sửa trường của mục thế giới: {', '.join(sorted(unknown))}")
        with self.transaction():
            if not self._exists("lore_entries", entry_id):
                raise NotFound(f"Không tìm thấy mục thế giới {entry_id}")
            columns = _lore_columns(fields)
            if columns:
                assignments = ", ".join(f"{col} = ?" for col in columns)
                self._conn.execute(
                    f"UPDATE lore_entries SET {assignments}, updated_at = ? WHERE id = ?",
                    (*columns.values(), self._now(), entry_id),
                )
        row = self._conn.execute("SELECT * FROM lore_entries WHERE id = ?", (entry_id,)).fetchone()
        return _row_to_lore(row)

    @_locked
    def delete_lore(self, entry_id: int) -> None:
        """Xoá hẳn một mục (hit đi theo CASCADE)."""
        with self.transaction():
            self._conn.execute("DELETE FROM lore_entries WHERE id = ?", (entry_id,))

    @_locked
    def tombstone_lore(self, entry_id: int) -> None:
        """Mục nhập từ file/card bị người dùng xoá: giữ hàng làm bia mộ (removed, tắt) để nhập lại không thêm
        lại nó, và xoá các hit của nó (danh sách đã mở khoá đúng ngay)."""
        with self.transaction():
            self._conn.execute(
                "UPDATE lore_entries SET removed = 1, enabled = 0, updated_at = ? WHERE id = ?",
                (self._now(), entry_id),
            )
            self._conn.execute("DELETE FROM lore_hits WHERE entry_id = ?", (entry_id,))

    @_locked
    def copy_lore(self, src_card_id: int, dst_card_id: int) -> int:
        """Sao chép mọi hàng (kể cả bia mộ) sang card khác, giữ slug, source, edited. Trả số hàng."""
        with self.transaction():
            now = self._now()
            cur = self._conn.execute(
                "INSERT INTO lore_entries (card_id, slug, title, category, keys_json, known_by_json, content, source,"
                " edited, removed, enabled, priority, position, extra_json, created_at, updated_at)"
                " SELECT ?, slug, title, category, keys_json, known_by_json, content, source, edited, removed,"
                " enabled, priority, position, extra_json, ?, ? FROM lore_entries WHERE card_id = ? ORDER BY id",
                (dst_card_id, now, now, src_card_id),
            )
            return cur.rowcount

    @_locked
    def card_story_ids(self, card_id: int) -> list[int]:
        rows = self._conn.execute("SELECT id FROM stories WHERE card_id = ? ORDER BY id", (card_id,)).fetchall()
        return [int(r["id"]) for r in rows]

    @_locked
    def record_lore_hits(self, story_id: int, message_id: int, hits: list[tuple[int, LoreSlot]]) -> int:
        """Ghi lượt `message_id` đã gợi ra các mục nào (INSERT OR IGNORE theo UNIQUE(message_id, entry_id)).
        Mục đã bị xoá giữa lúc dựng prompt và lúc ghi thì bỏ qua (không làm hỏng cả lượt). Trả số hàng mới."""
        if not hits:
            return 0
        with self.transaction():
            ids = sorted({entry_id for entry_id, _ in hits})
            marks = ", ".join("?" for _ in ids)
            alive = {
                int(r["id"])
                for r in self._conn.execute(
                    f"SELECT id FROM lore_entries WHERE id IN ({marks}) AND removed = 0", ids
                ).fetchall()
            }
            now = self._now()
            added = 0
            for entry_id, slot in hits:
                if entry_id not in alive:
                    continue
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO lore_hits (story_id, message_id, entry_id, slot, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (story_id, message_id, entry_id, slot, now),
                )
                added += cur.rowcount
            return added

    @_locked
    def unlocked_lore(self, story_id: int) -> list[LoreHitRow]:
        """Mục đã được gợi ra ở các lượt ACTIVE của story (mục đã xoá bị bỏ), gợi ra gần nhất trước."""
        rows = self._conn.execute(
            "SELECT h.entry_id AS entry_id, MIN(m.turn_index) AS first_turn, MAX(m.turn_index) AS last_turn,"
            "       COUNT(DISTINCT m.turn_index) AS turns, MAX(h.slot IN ('carried', 'fresh')) AS sent"
            "  FROM lore_hits h"
            "  JOIN messages m ON m.id = h.message_id AND m.is_active = 1"
            "  JOIN lore_entries e ON e.id = h.entry_id AND e.removed = 0"
            " WHERE h.story_id = ?"
            " GROUP BY h.entry_id"
            " ORDER BY last_turn DESC, h.entry_id",
            (story_id,),
        ).fetchall()
        if not rows:
            return []
        ids = [int(r["entry_id"]) for r in rows]
        marks = ", ".join("?" for _ in ids)
        entries = {
            int(r["id"]): _row_to_lore(r)
            for r in self._conn.execute(f"SELECT * FROM lore_entries WHERE id IN ({marks})", ids).fetchall()
        }
        return [
            LoreHitRow(
                entry=entries[int(r["entry_id"])],
                first_turn=int(r["first_turn"]),
                last_turn=int(r["last_turn"]),
                turns=int(r["turns"]),
                sent=bool(r["sent"]),
            )
            for r in rows
            if int(r["entry_id"]) in entries
        ]
