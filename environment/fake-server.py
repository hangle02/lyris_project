#!/usr/bin/env python3
"""② ENVIRONMENT — backend Lyris THẬT với LLM giả (ScriptedLLM), cho bot chạy thử giao diện.

Chạy (luôn bằng Python của backend, không dùng python3 của hệ thống):

    backend/.venv/bin/python environment/fake-server.py            # cổng BOT_BACKEND_PORT (mặc định 8066)

Bot (`node environment/bot.mjs`) tự bật file này, không cần chạy tay.

- App là `lyris.api.app.create_app` thật (mọi route, auth, worker trích xuất) — chỉ thay Ollama bằng
  ScriptedLLM trả lời định sẵn: Story có dẫn truyện, một câu thoại trong ngoặc kép và một [Thought: …];
  DM là 2 tin nhắn ngắn; gợi ý (JSON), trích xuất cảm xúc/cảnh/ký ức (JSON), tóm tắt (JSON), AI viết nháp (JSON:
  ý tưởng có chữ "Thủ thư" thì ra card nháp, ý tưởng khác thì báo lỗi).
- DB TẠM ở `reports/bot/lyris.db` (xoá và tạo lại mỗi lần chạy). Không bao giờ đụng `data/`.
- Chủ máy được đặt sẵn mật khẩu bằng chính store của app: handle `BOT_HANDLE` (mặc định `chumay`),
  mật khẩu `BOT_PASSWORD` (mặc định `bot mat khau 2026`), đã đồng ý Điều khoản.
- Thành viên thứ hai `BOT_MEMBER_HANDLE` (mặc định `thanhvien`, cùng mật khẩu): chưa đặt profile, chưa có story
  (bot dùng để xem nhân vật được chia sẻ, hub rỗng, chặn `#/admin`).
- OLLAMA_URL trỏ vào cổng chết (9): không bao giờ gọi Ollama.
"""
from __future__ import annotations

import asyncio
import copy
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from lyris.api.app import create_app  # noqa: E402
from lyris.auth import clock, passwords  # noqa: E402
from lyris.auth import store as auth_store  # noqa: E402
from lyris.compliance import legal  # noqa: E402
from lyris.config import Settings  # noqa: E402
from lyris.db.connection import connect, migrate  # noqa: E402
from lyris.db.repo import Repo, new_uid  # noqa: E402
from lyris.llm.base import Done, LLMError, TextDelta  # noqa: E402
from lyris.llm.fake import FakeLLM  # noqa: E402
from lyris.models import AccountUpdate, GenStats  # noqa: E402

PORT = int(os.environ.get("BOT_BACKEND_PORT", "8066"))
DATA_DIR = Path(os.environ.get("BOT_DATA_DIR", str(ROOT / "reports" / "bot"))).resolve()
HANDLE = os.environ.get("BOT_HANDLE", "chumay")
PASSWORD = os.environ.get("BOT_PASSWORD", "bot mat khau 2026")
MEMBER_HANDLE = os.environ.get("BOT_MEMBER_HANDLE", "thanhvien")
MEMBER_PASSWORD = os.environ.get("BOT_MEMBER_PASSWORD", "bot mat khau 2026")
DEAD_OLLAMA_URL = "http://127.0.0.1:9"

# Mỗi lần gọi Story lấy câu kế tiếp (Tạo lại ra phiên bản KHÁC). Đủ ba loại khối: dẫn truyện, câu thoại
# ≥ 3 chữ trong ngoặc kép (thành thẻ thoại) và đúng một [Thought: …] (thành thẻ suy nghĩ bị làm mờ).
STORY_REPLIES = [
    (
        "Nhân vật khẽ nghiêng đầu, ánh đèn vàng hắt lên nửa gương mặt, khoé môi nhếch lên như đang cố nhịn cười.\n\n"
        "\"Lại nghĩ ra trò gì nữa đây, kể nghe thử xem nào?\"\n\n"
        "[Thought: Người này lúc nào cũng làm mình không yên tâm được.]\n\n"
        "Gió ngoài hiên lùa qua khe cửa, mang theo mùi mưa đầu mùa."
    ),
    (
        "Nhân vật đặt tách trà xuống bàn, ngón tay gõ nhẹ lên mặt gỗ như đang đếm từng nhịp chờ đợi.\n\n"
        "\"Nói thật đi, hôm nay có chuyện gì vui à?\"\n\n"
        "[Thought: Ánh mắt kia sáng quá, chắc lại sắp bày trò gì đó.]"
    ),
    (
        "Nhân vật bật cười thành tiếng, lắc đầu rồi kéo ghế ngồi xuống đối diện, chống cằm nhìn sang.\n\n"
        "\"Được rồi, lần này mình nghe theo cậu một lần thôi đấy.\"\n\n"
        "[Thought: Thật ra mình đã muốn đồng ý ngay từ đầu rồi.]"
    ),
]
DM_REPLIES = [
    # Tin đầu có một [Thought: …]: ở DM nó thành thẻ suy nghĩ thu gọn dưới bong bóng.
    "Ơ, nhắn giờ này à?\nĐang làm gì đấy, kể nghe đi\n[Thought: Tự nhiên thấy vui vì được nhắn.]",
    "Haha, biết ngay mà\nMai gặp nhau ở quán cũ nhé",
]
SUGGESTIONS = [
    "\"Không có gì đâu, chỉ là nhớ cậu thôi.\"",
    "*Mỉm cười* \"Bí mật, đoán thử xem?\"",
    "\"Đi dạo một vòng với mình không?\"",
]
SUGGESTIONS_MORE = [
    "\"Kể cậu nghe chuyện này hay lắm.\"",
    "*Nhún vai* \"Tự nhiên thấy vui thôi.\"",
    "\"Hôm nay trời đẹp quá, ra ngoài nhé?\"",
]
EXTRACTION: dict[str, Any] = {
    "reason": "Người chơi trêu đùa thân thiện, nhân vật thấy vui và gần gũi hơn.",
    "tone": "warm",
    "relationship_delta": {"affection": 3, "trust": 2, "attraction": 1, "obsession": 0, "fear": 0, "aversion": 0},
    "location": "Quán trà nhỏ cuối phố",
    "time": "Chiều mưa",
    "memory": {"text": "Người chơi ghé quán trà và trêu nhân vật một câu.", "importance": 3},
    "facts": [{"subject": "người chơi", "text": "Thích uống trà nóng ngày mưa."}],
}
# AI viết nháp (Studio): ý tưởng có chữ "Thủ thư" thì viết được card này; ý tưởng khác thì báo lỗi (để bot thử cả
# đường lỗi: câu dễ hiểu + "Chi tiết", không lộ chữ kỹ thuật).
DRAFT_TRIGGER = "Thủ thư"
DRAFT_CARD: dict[str, Any] = {
    "name": "Mai Chi Nháp", "gender": "female", "style_profile": "viet_hien_dai",
    "role": "Thủ thư thư viện cũ", "description": "Thủ thư ở thư viện cũ phố Hàng Bài.",
    "personality": "Trầm tính, tỉ mỉ, hay để ý những điều nhỏ nhặt của người khác.",
    "appearance": "Tóc búi thấp, đeo kính gọng mảnh.", "background": "Làm thủ thư năm năm.", "goals": "Giữ thư viện mở cửa.",
    "secrets": "Thầm để dành sách cho {{user}}.", "speech_style": "Nói nhỏ, chậm.", "self_term": "chị", "player_term": "em",
    "nicknames": [], "others": "Với người lạ xưng tôi.", "scenario": "Thư viện cũ phố Hàng Bài, chiều thứ bảy.",
    "greeting": (
        "Chiều thứ bảy, nắng nghiêng qua những giá sách gỗ cũ. Mai Chi ngồi sau quầy, lật từng trang sổ mượn đã ngả vàng.\n\n"
        "[Thought: Ba giờ rồi. Người đó sắp tới.]\n\n"
        "Chuông cửa khẽ reo. Cô đẩy cuốn thơ đã gói sẵn sang phía trước.\n\n"
        "\"Cuốn em hỏi tuần trước, chị để dành rồi. Bìa hơi cũ, em đọc nhẹ tay nhé.\"\n\n"
        "[Thought: Mong là em thích.]"
    ),
    "example_dialogues": '{{char}}: "Em đọc nhẹ tay nhé."', "tags": ["hiện đại"],
}
OPENING: dict[str, Any] = {
    "location": "Quán trà nhỏ cuối phố",
    "time": "Chiều mưa",
    "memory": {"text": "Hai người gặp nhau ở quán trà nhỏ.", "importance": 2},
}

# Thời gian giả: chờ trước chữ đầu tiên (để thấy chấm đang gõ), rồi stream từng mẩu.
FIRST_TOKEN_DELAY = float(os.environ.get("BOT_FIRST_TOKEN_DELAY", "0.9"))
CHUNK_DELAY = float(os.environ.get("BOT_CHUNK_DELAY", "0.025"))
JSON_DELAY = float(os.environ.get("BOT_JSON_DELAY", "0.4"))


def _is_dm(messages: list[Any]) -> bool:
    """Prompt DM (vi/en) nói rõ là nhắn tin; Story thì không."""
    system = "\n".join(m.content for m in messages if getattr(m, "role", "") == "system")
    return "đang nhắn tin với" in system or "Trả lời như tin nhắn thật" in system or "texting" in system.lower()


FAKE_MODELS = ["gemma4:12b", "bge-m3"]


def _fake_ollama(request: httpx.Request) -> httpx.Response:
    """Ollama GIẢ trong tiến trình (httpx.MockTransport, không có mạng) cho GET /api/system: máy "sẵn sàng",
    để giao diện không hiện cảnh báo "Máy chưa sẵn sàng" chỉ vì đang chạy LLM giả."""
    path = request.url.path
    if path == "/api/version":
        return httpx.Response(200, json={"version": "0.0.0-bot"})
    if path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": m, "size": 1_000_000_000} for m in FAKE_MODELS]})
    if path == "/api/ps":
        return httpx.Response(200, json={"models": []})
    return httpx.Response(404, json={"error": "không có"})


class ScriptedLLM(FakeLLM):
    """FakeLLM có kịch bản: chọn câu theo loại lời gọi (Story / DM / gợi ý / trích xuất / tóm tắt)."""

    # SystemMonitor đọc `base_url` + `_transport` của client: trỏ vào Ollama giả ở trên (không bao giờ ra mạng).
    base_url = "http://ollama-gia.invalid"

    def __init__(self) -> None:
        super().__init__(chunk_size=6)
        self._transport = httpx.MockTransport(_fake_ollama)
        self._story = 0
        self._dm = 0
        self._suggest = 0

    async def list_models(self) -> list[str]:
        """/api/health và ModelCatalog: model chat mặc định "đã cài" → giao diện coi máy là sẵn sàng."""
        return list(FAKE_MODELS)

    async def chat_stream(self, model: str, messages: list[Any], *, stop: list[str], options: dict[str, Any]):  # type: ignore[override]
        self.calls.append({"model": model, "messages": list(messages), "stop": list(stop), "options": dict(options)})
        if _is_dm(messages):
            reply = DM_REPLIES[self._dm % len(DM_REPLIES)]
            self._dm += 1
        else:
            reply = STORY_REPLIES[self._story % len(STORY_REPLIES)]
            self._story += 1
        start = time.perf_counter()
        await asyncio.sleep(FIRST_TOKEN_DELAY)
        ttft = (time.perf_counter() - start) * 1000
        chunks = [reply[i : i + self.chunk_size] for i in range(0, len(reply), self.chunk_size)]
        for i, chunk in enumerate(chunks):
            if i and CHUNK_DELAY:
                await asyncio.sleep(CHUNK_DELAY)
            yield TextDelta(chunk)
        total = (time.perf_counter() - start) * 1000
        yield Done(
            GenStats(
                ttft_ms=ttft,
                total_ms=total,
                prompt_tokens=sum(len(m.content) for m in messages) // 3,
                output_tokens=len(chunks),
                tok_per_s=len(chunks) / (total / 1000) if total > 0 else None,
                done_reason="stop",
            )
        )

    async def chat_json(self, model: str, messages: list[Any], *, schema: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        self.calls.append({"model": model, "messages": list(messages), "stop": [], "options": dict(options), "schema": copy.deepcopy(schema)})
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if JSON_DELAY:
            await asyncio.sleep(JSON_DELAY)
        if "suggestions" in props:
            items = SUGGESTIONS if self._suggest % 2 == 0 else SUGGESTIONS_MORE
            self._suggest += 1
            return {"suggestions": list(items)}
        if "relationship_delta" in props:
            return copy.deepcopy(EXTRACTION)
        if "location" in props and "memory" in props:
            return copy.deepcopy(OPENING)
        if "summary" in props:
            return {"summary": "Hai người gặp nhau ở quán trà nhỏ, trêu đùa và hẹn gặp lại."}
        if "greeting" in props and any(DRAFT_TRIGGER in str(getattr(m, "content", "")) for m in messages):
            return copy.deepcopy(DRAFT_CARD)
        raise LLMError("ScriptedLLM không có kịch bản cho lời gọi này.")


MARKER = ".lyris-bot-data"
DEFAULT_DATA_DIR = (ROOT / "reports" / "bot").resolve()


def _safe_data_dir(path: Path) -> Path:
    """Thư mục này sẽ bị XOÁ rồi tạo lại: chỉ cho phép thư mục tạm của bot, không bao giờ là data/ hay thư mục cha.

    Được phép: nằm hẳn BÊN TRONG `reports/` của repo hoặc thư mục tạm của hệ thống. Thư mục khác mặc định mà đã có
    sẵn dữ liệu thì phải có dấu `.lyris-bot-data` (do chính file này tạo) mới được xoá.
    """
    path = path.resolve()
    forbidden = (ROOT / "data").resolve()
    if path == forbidden or forbidden in path.parents or path in forbidden.parents:
        raise SystemExit(f"Từ chối: {path} là data/, nằm trong data/ hoặc chứa data/ (DB thật của người dùng).")
    if path == ROOT or path in ROOT.parents:
        raise SystemExit(f"Từ chối: {path} là repo hoặc thư mục cha của repo.")
    allowed = [(ROOT / "reports").resolve(), Path(tempfile.gettempdir()).resolve()]
    if not any(root in path.parents for root in allowed):
        raise SystemExit(f"Từ chối: BOT_DATA_DIR={path} phải nằm bên trong reports/ của repo hoặc thư mục tạm.")
    if path != DEFAULT_DATA_DIR and path.exists() and any(path.iterdir()) and not (path / MARKER).exists():
        raise SystemExit(f"Từ chối: {path} đã có dữ liệu không phải của bot (thiếu {MARKER}).")
    return path


def _exit_with_parent() -> None:
    """Bot bị giết ngang (kill -9) thì server này cũng tự tắt, không để mồ côi giữ cổng 8066."""
    parent = os.getppid()

    def watch() -> None:
        while True:
            time.sleep(1)
            if os.getppid() != parent:
                os._exit(0)

    threading.Thread(target=watch, daemon=True, name="exit-with-parent").start()


def prepare_db(data_dir: Path) -> Path:
    """DB tạm mới: chủ máy có mật khẩu, có profile, đã đồng ý Điều khoản. Seed (nhân vật, persona) do app tự làm."""
    data_dir = _safe_data_dir(data_dir)
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    (data_dir / MARKER).write_text("Thư mục DB tạm của environment/fake-server.py — xoá được.\n", encoding="utf-8")
    db_path = data_dir / "lyris.db"
    conn = connect(db_path)
    try:
        migrate(conn)
        repo = Repo(conn)
        owner = repo.owner_account()
        assert owner.id is not None
        repo.update_account(owner.id, AccountUpdate(display_name="Chủ máy", handle=HANDLE, bio=""))
        hashed = passwords.hash_password_sync(PASSWORD)
        now = clock.now()
        member_hashed = passwords.hash_password_sync(MEMBER_PASSWORD)
        with repo.transaction():
            auth_store.write_password(conn, owner.id, hashed, now, temporary=False)
            auth_store.delete_setup(conn)
            legal.accept(conn, owner.id, now)
            # Thành viên thứ hai: chưa đặt profile (hub mời "Đặt tên cho tài khoản"), chưa có story nào.
            member_id = auth_store.insert_member(
                conn, uid=new_uid(), handle=MEMBER_HANDLE, display_name="Thành viên", invited_by=owner.id
            )
            conn.execute("UPDATE accounts SET profile_completed = 0 WHERE id = ?", (member_id,))
            auth_store.write_password(conn, member_id, member_hashed, now, temporary=False)
            legal.accept(conn, member_id, now)
    finally:
        conn.close()
    return db_path


def main() -> int:
    if os.environ.get("BOT_PARENT_WATCH", "1") != "0":
        _exit_with_parent()
    db_path = prepare_db(DATA_DIR)
    settings = Settings(
        db_path=db_path,
        ollama_url=DEAD_OLLAMA_URL,
        chat_model="gemma4:12b",
        num_ctx=8192,
        avatars_dir=DATA_DIR / "avatars",
    )
    app = create_app(settings, llm=ScriptedLLM(), start_worker=True, start_forwarder=False)
    print(f"Lyris (LLM giả) ở http://127.0.0.1:{PORT} · DB tạm {db_path} · đăng nhập @{HANDLE}", flush=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", proxy_headers=False, access_log=False)
    uvicorn.Server(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
