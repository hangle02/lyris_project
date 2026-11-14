"""LLM giả cho test: trả các câu trả lời định sẵn, chia thành chunk như stream thật."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import math
import re
import time
import unicodedata
from collections.abc import AsyncIterator
from typing import Any

from lyris.llm.base import Done, LLMError, LLMEvent, TextDelta
from lyris.models import ChatTurn, GenStats

DEFAULT_REPLY = (
    "Lạc Dương khẽ liếc nhìn cô, khoé môi hơi nhếch lên.\n\n"
    "\"Lại nghĩ ra trò gì nữa đây?\"\n\n"
    "[Thought: Cô ngốc này lúc nào cũng làm người ta không yên tâm được.]"
)


class FakeLLM:
    """Thoả `LLMClient`.

    - Mỗi lần gọi lấy reply kế tiếp trong `replies` (hết thì lặp lại cái cuối),
      chia thành các chunk dài `chunk_size` ký tự, yield từng `TextDelta` rồi một `Done`.
    - `delay`: số giây chờ trước mỗi chunk (để test ngắt giữa chừng / Busy).
    - `error`: nếu khác None thì mỗi lần gọi raise lỗi này ngay khi bắt đầu đọc (trước mọi delta).
      Đặt lại `fake.error = None` để các lần gọi sau chạy bình thường.
    - `calls`: mỗi lần gọi lưu `{"model", "messages", "stop", "options"}`
      (`messages` là bản sao list `ChatTurn` đã nhận).
    - `chat_json`: lấy lần lượt các dict trong `json_replies` (hết thì lặp lại cái cuối; trả bản sao sâu).
      Không có `json_replies` thì raise LLMError. Chờ `delay` giây một lần trước khi trả (để test "đang bận"),
      cũng raise `error` nếu có. `calls` ghi thêm khoá `"schema"` (và `"stop": []`).
    - `embed`: vector xác định dài `embed_dim`, băm theo từ (chữ thường, NFC) rồi chuẩn hoá về độ dài 1,
      nên hai đoạn chung nhiều từ thì cosine cao. Ghi vào `embed_calls` (`{"model", "texts"}`, không vào
      `calls`). Raise `embed_error` nếu khác None (không dùng `error`, để test lỗi chat không làm hỏng embed).
    - `prefill_prefix` (prefill raw §10.6): ghi vào `calls` kèm `"raw": True`; `raw_prefill=False` thì trả
      False để worker quay về prefill bằng `chat_stream`.
    """

    def __init__(
        self,
        replies: list[str] | None = None,
        chunk_size: int = 7,
        delay: float = 0.0,
        error: Exception | None = None,
        json_replies: list[dict[str, Any]] | None = None,
        embed_dim: int = 64,
        embed_error: Exception | None = None,
        raw_prefill: bool = True,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size phải >= 1")
        self.replies: list[str] = list(replies) if replies else [DEFAULT_REPLY]
        self.json_replies: list[dict[str, Any]] = list(json_replies) if json_replies else []
        self.chunk_size = chunk_size
        self.delay = delay
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.embed_dim = embed_dim
        self.embed_error = embed_error
        self.embed_calls: list[dict[str, Any]] = []
        self.raw_prefill = raw_prefill
        self._next = 0
        self._next_json = 0

    def _take_reply(self) -> str:
        idx = min(self._next, len(self.replies) - 1)
        self._next += 1
        return self.replies[idx]

    async def chat_stream(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        stop: list[str],
        options: dict[str, Any],
    ) -> AsyncIterator[LLMEvent]:
        self.calls.append(
            {"model": model, "messages": list(messages), "stop": list(stop), "options": dict(options)}
        )
        if self.error is not None:
            raise self.error
        reply = self._take_reply()
        start = time.perf_counter()
        ttft_ms: float | None = None
        chunks = [reply[i : i + self.chunk_size] for i in range(0, len(reply), self.chunk_size)]
        for chunk in chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - start) * 1000
            yield TextDelta(chunk)
        total_ms = (time.perf_counter() - start) * 1000
        yield Done(
            GenStats(
                ttft_ms=ttft_ms,
                total_ms=total_ms,
                prompt_tokens=sum(len(m.content) for m in messages) // 3,
                output_tokens=len(chunks),
                tok_per_s=(len(chunks) / (total_ms / 1000)) if total_ms > 0 else None,
                done_reason="stop",
            )
        )

    async def prefill_prefix(
        self, model: str, messages: list[ChatTurn], *, options: dict[str, Any], open_last: bool = False
    ) -> bool:
        """Giả `OllamaClient.prefill_prefix`. `raw_prefill=False`: trả False (như model chưa render được),
        worker prefill bằng `chat_stream`. Ghi vào `calls` với `"raw": True`, không lấy reply nào.
        Raise `error` nếu có; chờ `delay` giây cho mỗi message (để test huỷ giữa chừng).
        Phase 4: `open_last` (lượt user còn mở) được ghi vào `calls` khi True.
        """
        if not self.raw_prefill:
            return False
        call: dict[str, Any] = {
            "model": model, "messages": list(messages), "stop": [], "options": {**options, "num_predict": 1}, "raw": True
        }
        if open_last:
            call["open_last"] = True
        self.calls.append(call)
        if self.error is not None:
            raise self.error
        for _ in messages:
            if self.delay:
                await asyncio.sleep(self.delay)
        return True

    async def chat_json(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        schema: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model": model,
                "messages": list(messages),
                "stop": [],
                "options": dict(options),
                "schema": copy.deepcopy(schema),
            }
        )
        if self.error is not None:
            raise self.error
        if self.delay:
            await asyncio.sleep(self.delay)
        if not self.json_replies:
            raise LLMError("FakeLLM chưa được cấu hình json_replies.")
        idx = min(self._next_json, len(self.json_replies) - 1)
        self._next_json += 1
        return copy.deepcopy(self.json_replies[idx])

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append({"model": model, "texts": list(texts)})
        if self.embed_error is not None:
            raise self.embed_error
        return [fake_vector(text, self.embed_dim) for text in texts]


_WORD = re.compile(r"[^\W_]+")


def fake_vector(text: str, dim: int = 64) -> list[float]:
    """Vector băm theo từ: mỗi từ cộng ±1 vào một ô xác định bởi hash; chuẩn hoá L2 (toàn 0 nếu không có từ)."""
    vec = [0.0] * dim
    for word in _WORD.findall(unicodedata.normalize("NFC", text).lower()):
        digest = hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        vec[value % dim] += 1.0 if (value >> 32) & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec
