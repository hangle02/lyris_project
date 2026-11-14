"""Cấu hình đọc từ biến môi trường."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# backend/lyris/config.py -> thư mục gốc dự án là cha của backend/
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

DEFAULT_DB_PATH: Path = REPO_ROOT / "data" / "lyris.db"
DEFAULT_AVATARS_DIR: Path = REPO_ROOT / "data" / "avatars"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_CHAT_MODEL = "gemma4:12b"
DEFAULT_NUM_CTX = 8192
DEFAULT_EMBED_MODEL = "bge-m3"
DEFAULT_CHAT_SLOTS = 2
DEFAULT_POSTHOG_HOST = "https://us.i.posthog.com"


@dataclass(frozen=True)
class Settings:
    db_path: Path  # LYRIS_DB_PATH, mặc định <repo>/data/lyris.db
    ollama_url: str  # OLLAMA_URL, mặc định http://127.0.0.1:11434
    chat_model: str  # LYRIS_CHAT_MODEL, mặc định gemma4:12b
    num_ctx: int  # LYRIS_NUM_CTX, mặc định 8192
    # LYRIS_AVATARS_DIR, mặc định <thư mục chứa db>/avatars (db ":memory:" -> <repo>/data/avatars).
    # Có giá trị mặc định để các chỗ tạo Settings(...) bằng tay (test) vẫn chạy.
    avatars_dir: Path = DEFAULT_AVATARS_DIR
    draft_model: str = DEFAULT_CHAT_MODEL  # LYRIS_DRAFT_MODEL, mặc định = chat_model
    # Phase 3 (docs/phase3.md §0). LYRIS_EXTRACT_MODEL: model cho trích xuất/tóm tắt nền;
    # None = dùng model chat của chính story (không nạp thêm model vào RAM).
    extract_model: str | None = None
    # LYRIS_EMBED_MODEL: model embedding cho tìm ký ức theo nghĩa; chỉ dùng khi `ollama list` có nó.
    embed_model: str = DEFAULT_EMBED_MODEL
    # Phase 4b (docs/auth.md §3.2, §3.7): LYRIS_COOKIE_SECURE=1 thì cookie đăng nhập luôn có Secure
    # (dùng khi chỉ vào Lyris qua HTTPS, ví dụ Tailscale Serve ở Phase 6).
    cookie_secure: bool = False
    # Phase 4b (docs/auth.md §5.1): LYRIS_CHAT_SLOTS = số lượt sinh cùng lúc trên cả máy (mặc định 2, bằng
    # OLLAMA_NUM_PARALLEL). 1 = lần lượt từng người.
    chat_slots: int = 2
    # Event tracking (docs/tracking-plan.md): LYRIS_POSTHOG_KEY bật chuyển tiếp sự kiện sang PostHog (không có thì
    # sự kiện chỉ nằm trong DB của app). Không bao giờ in ra (repr=False). LYRIS_POSTHOG_HOST mặc định PostHog Mỹ.
    posthog_key: str | None = field(default=None, repr=False)
    posthog_host: str = DEFAULT_POSTHOG_HOST
    # LYRIS_CONTACT: email (hoặc địa chỉ https://) của người vận hành. Trang đăng nhập dùng cho "Xin mã mời" và
    # "Quên mật khẩu"; văn bản pháp lý điền vào chỗ [ĐIỀN EMAIL LIÊN HỆ]. Không đặt thì trang nói chung chung.
    contact: str | None = None


def _env(name: str) -> str | None:
    """Đọc biến môi trường; với LYRIS_X mà chưa đặt thì đọc tên cũ NORA_X (trước khi đổi tên app)."""
    names = [name]
    if name.startswith("LYRIS_"):
        names.append("NORA_" + name[len("LYRIS_"):])
    for n in names:
        value = os.environ.get(n)
        if value is None:
            continue
        value = value.strip()
        if value:
            return value
    return None


LEGACY_DB_NAME = "nora.db"


def migrate_legacy_db(db_path: Path) -> bool:
    """Đổi tên DB cũ `nora.db` (và -wal, -shm) thành `db_path` nếu DB mới chưa có. Trả True nếu đã đổi.

    Chỉ áp dụng khi db_path là file thật tên khác `nora.db` và file cũ nằm cùng thư mục.
    Gọi lúc khởi động, trước khi mở kết nối (không tiến trình nào khác được đang mở DB cũ).
    """
    target = str(db_path)
    if target == ":memory:" or target.startswith("file:") or db_path.name == LEGACY_DB_NAME:
        return False
    legacy = db_path.with_name(LEGACY_DB_NAME)
    if db_path.exists() or not legacy.exists():
        return False
    for suffix in ("-wal", "-shm"):
        side = Path(str(legacy) + suffix)
        if side.exists():
            side.rename(Path(str(db_path) + suffix))
    legacy.rename(db_path)
    return True


def _db_path() -> Path:
    raw = _env("LYRIS_DB_PATH")
    if raw is None:
        return DEFAULT_DB_PATH
    if raw == ":memory:":
        return Path(raw)
    return Path(raw).expanduser()


def _num_ctx() -> int:
    raw = _env("LYRIS_NUM_CTX")
    if raw is None:
        return DEFAULT_NUM_CTX
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"LYRIS_NUM_CTX phải là số nguyên dương, đang là {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"LYRIS_NUM_CTX phải là số nguyên dương, đang là {raw!r}")
    return value


def _avatars_dir(db_path: Path) -> Path:
    raw = _env("LYRIS_AVATARS_DIR")
    if raw is not None:
        return Path(raw).expanduser()
    target = str(db_path)
    if target == ":memory:" or target.startswith("file:"):
        return DEFAULT_AVATARS_DIR
    return db_path.parent / "avatars"


def _chat_slots() -> int:
    raw = _env("LYRIS_CHAT_SLOTS")
    if raw is None or not raw.strip():
        return DEFAULT_CHAT_SLOTS
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"LYRIS_CHAT_SLOTS phải là số nguyên dương, đang là {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"LYRIS_CHAT_SLOTS phải là số nguyên dương, đang là {raw!r}")
    return value


def _posthog_host() -> str:
    raw = _env("LYRIS_POSTHOG_HOST")
    if raw is None:
        return DEFAULT_POSTHOG_HOST
    # Chỉ https: sự kiện không bao giờ đi qua mạng mà không mã hoá (gõ nhầm http:// thì báo lỗi, không gửi).
    if not raw.startswith("https://"):
        raise ValueError(f"LYRIS_POSTHOG_HOST phải bắt đầu bằng https://, đang là {raw!r}")
    return raw.rstrip("/")


_EMAIL = re.compile(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+")
_HTTPS = re.compile(r"https://[^\s<>\"]+")


def _contact() -> str | None:
    raw = _env("LYRIS_CONTACT")
    if raw is None:
        return None
    if not (_EMAIL.fullmatch(raw) or _HTTPS.fullmatch(raw)) or len(raw) > 200:
        raise ValueError(f"LYRIS_CONTACT phải là một email hoặc địa chỉ https://, đang là {raw!r}")
    return raw


def get_settings() -> Settings:
    """Đọc cấu hình từ biến môi trường (mỗi lần gọi đọc lại, tiện cho test)."""
    db_path = _db_path()
    chat_model = _env("LYRIS_CHAT_MODEL") or DEFAULT_CHAT_MODEL
    return Settings(
        db_path=db_path,
        ollama_url=(_env("OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/"),
        chat_model=chat_model,
        num_ctx=_num_ctx(),
        avatars_dir=_avatars_dir(db_path),
        draft_model=_env("LYRIS_DRAFT_MODEL") or chat_model,
        extract_model=_env("LYRIS_EXTRACT_MODEL"),
        embed_model=_env("LYRIS_EMBED_MODEL") or DEFAULT_EMBED_MODEL,
        cookie_secure=(_env("LYRIS_COOKIE_SECURE") or "0").lower() in ("1", "true", "yes"),
        chat_slots=_chat_slots(),
        posthog_key=_env("LYRIS_POSTHOG_KEY"),
        posthog_host=_posthog_host(),
        contact=_contact(),
    )
