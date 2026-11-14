"""Lỗi hiện cho người dùng (Phase 3b, docs/phase3.md §10).

Giao diện thường không nói "Ollama", "model", HTTP... Mỗi lỗi có hai phần:

- `detail`: một câu tiếng Việt dễ hiểu (hiện ngay);
- `technical`: chi tiết kỹ thuật nguyên văn (giao diện để dưới "Chi tiết"), có thể None.

HTTP: `{"detail": str, "technical": str | null}` (bộ xử lý `UserFacingError` trong app.py).
SSE: sự kiện `error` có cùng hai trường.
"""
from __future__ import annotations

from typing import Literal

from lyris.llm.base import LLMError

Action = Literal["reply", "suggest", "draft", "preview"]

# Câu theo loại lỗi (không phụ thuộc việc đang làm).
_BY_KIND: dict[str, str] = {
    "connect": "Chưa kết nối được với phần AI của Lyris. Hãy thử lại sau ít phút.",
    "timeout": "Máy đang bận nên phản hồi quá lâu. Hãy thử lại sau ít phút.",
}

# Thiếu model: chỉ chỗ đổi được tuỳ việc đang làm (model của story ở Thiết lập story; nháp/chat thử dùng
# model mặc định, xem ở Tài khoản).
_MISSING_MODEL: dict[Action, str] = {
    "reply": "Bộ AI mà story này dùng chưa có trên máy. Hãy chọn bộ khác trong Thiết lập story > Nâng cao.",
    "suggest": "Bộ AI mà story này dùng chưa có trên máy. Hãy chọn bộ khác trong Thiết lập story > Nâng cao.",
    "draft": "Bộ AI dùng để viết nháp chưa có trên máy. Xem các bộ đang có trong Tài khoản > Nâng cao.",
    "preview": "Bộ AI dùng để chat thử chưa có trên máy. Xem các bộ đang có trong Tài khoản > Nâng cao.",
}

# Câu chung khi lỗi không thuộc các loại trên (theo việc đang làm).
_FALLBACK: dict[Action, str] = {
    "reply": "Nhân vật chưa trả lời được. Hãy thử lại.",
    "suggest": "Chưa nghĩ ra được gợi ý. Hãy thử lại.",
    "draft": "Chưa viết nháp được nhân vật. Hãy thử lại.",
    "preview": "Nhân vật chưa trả lời được. Hãy bấm Làm lại.",
}

EMPTY_REPLY = "Nhân vật chưa nói được gì. Hãy bấm Thử lại."
EMPTY_PREVIEW = "Nhân vật chưa nói được gì. Hãy bấm Làm lại."
SAVE_FAILED = "Không lưu được câu trả lời. Hãy thử lại."
UNEXPECTED = "Có lỗi không mong đợi. Hãy thử lại."


class UserFacingError(Exception):
    """Lỗi trả cho giao diện dưới dạng `{"detail", "technical"}` với mã HTTP `status`."""

    def __init__(self, detail: str, *, status: int = 502, technical: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.technical = technical

    def payload(self) -> dict[str, str | None]:
        return {"detail": self.detail, "technical": self.technical}


def friendly(exc: BaseException, action: Action) -> tuple[str, str | None]:
    """(câu dễ hiểu, chi tiết kỹ thuật) cho một lỗi khi gọi LLM."""
    technical = str(exc).strip() or type(exc).__name__
    if isinstance(exc, LLMError):
        if exc.kind == "missing_model":
            return _MISSING_MODEL[action], technical
        return _BY_KIND.get(exc.kind, _FALLBACK[action]), technical
    return _FALLBACK[action], f"{type(exc).__name__}: {technical}"


def error_event(exc: BaseException, action: Action) -> dict[str, str | None]:
    """Dữ liệu sự kiện SSE `error` cho lỗi khi gọi LLM."""
    detail, technical = friendly(exc, action)
    return {"detail": detail, "technical": technical}


__all__ = [
    "EMPTY_PREVIEW",
    "EMPTY_REPLY",
    "SAVE_FAILED",
    "UNEXPECTED",
    "Action",
    "UserFacingError",
    "error_event",
    "friendly",
]
