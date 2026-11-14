"""Interface LLM client. Backend cụ thể: ollama.py (thật), fake.py (cho test)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from lyris.models import ChatTurn, GenStats


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class Done:
    stats: GenStats


LLMEvent = TextDelta | Done


LLMErrorKind = Literal["connect", "timeout", "missing_model", "server", "output", "unknown"]


class LLMError(RuntimeError):
    """Lỗi khi gọi LLM (không kết nối được, model chưa pull, HTTP lỗi...).

    Thông điệp (`str(exc)`) là chi tiết kỹ thuật (có thể nhắc Ollama, tên model). Phase 3b: giao diện
    hiện câu dễ hiểu theo `kind` (`lyris.llm.errors.friendly`), chi tiết kỹ thuật để dưới "Chi tiết".
    """

    default_kind: LLMErrorKind = "unknown"

    def __init__(self, message: str = "", *, kind: LLMErrorKind | None = None) -> None:
        super().__init__(message)
        self.kind: LLMErrorKind = kind or self.default_kind


class LLMOutputError(LLMError):
    """Model trả lời được nhưng nội dung không dùng được: JSON hỏng, bị cắt vì hết `num_predict`, rỗng.

    Phase 3: job worker thử lại một lần với lỗi này (và mọi lỗi khác trừ lỗi kết nối/timeout tới Ollama,
    nhận ra qua `httpx.TransportError` trong chuỗi `__cause__`; xem `lyris/jobs/worker.py`).
    """

    default_kind: LLMErrorKind = "output"


class LLMClient(Protocol):
    def chat_stream(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        stop: list[str],
        options: dict[str, Any],
    ) -> AsyncIterator[LLMEvent]:
        """Stream một lượt chat. Yield các TextDelta, rồi đúng một Done ở cuối.

        Thinking của model luôn tắt. Nếu người gọi ngừng đọc giữa chừng (client ngắt kết nối),
        generator bị đóng và phải huỷ request HTTP tới backend.
        Raise LLMError khi lỗi.
        """
        ...

    async def chat_json(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        schema: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Một lượt không stream, ép model trả JSON đúng `schema` (Ollama structured output: `format`).

        Thinking tắt. Trả object JSON đã parse. Raise LLMError khi lỗi kết nối/HTTP, khi model trả
        JSON hỏng, hoặc khi bị cắt vì hết `num_predict` (done_reason "length").
        Phase 2 dùng cho "AI viết nháp" card; Phase 3 dùng cho luồng trích xuất state.
        JSON hỏng, bị cắt, hoặc rỗng thì raise LLMOutputError (lớp con của LLMError).
        """
        ...

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """Vector embedding cho từng chuỗi trong `texts`, cùng thứ tự (Phase 3: tìm ký ức theo nghĩa).

        Ollama: `POST /api/embed` với `keep_alive "1m"` để model embed rời RAM ngay sau đó.
        Raise LLMError khi lỗi kết nối/HTTP, model chưa pull, hoặc số vector trả về không khớp.
        """
        ...


@dataclass(frozen=True)
class ParsedDelta:
    kind: Literal["text", "thought"]
    text: str
