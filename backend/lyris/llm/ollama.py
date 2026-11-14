"""Client Ollama thật: stream `/api/chat` dạng NDJSON qua httpx; `chat_json` cho structured output."""
from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from lyris.llm.base import Done, LLMError, LLMEvent, LLMOutputError, TextDelta
from lyris.llm.render import render_prefix
from lyris.models import ChatTurn, GenStats

_CONNECT_TIMEOUT = 5.0
_LIST_TIMEOUT = 10.0
_MAX_ERROR_CHARS = 300
# Model embed (bge-m3) rời RAM sau 1 phút để không tranh chỗ với model chat (docs/phase3.md §0).
EMBED_KEEP_ALIVE = "1m"


def _error_text(resp: httpx.Response) -> str:
    """Lấy thông điệp lỗi Ollama trả về (`{"error": "..."}`), hoặc nguyên văn body nếu không phải JSON."""
    try:
        data = resp.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return resp.text.strip()[:_MAX_ERROR_CHARS]
    if isinstance(data, dict) and isinstance(data.get("error"), str):
        return data["error"].strip()[:_MAX_ERROR_CHARS]
    return resp.text.strip()[:_MAX_ERROR_CHARS]


def _is_think_unsupported(status: int, error: str) -> bool:
    return status == 400 and "think" in error.lower()


_CODE_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", re.S)


def _parse_json_object(content: str) -> dict[str, Any]:
    """Parse nội dung model trả về thành object JSON; LLMError nếu hỏng hoặc không phải object.

    Với `format` Ollama luôn trả JSON trần, nhưng vẫn gỡ khối ```json ... ``` phòng khi model/bản Ollama khác.
    """
    text = content.strip()
    fenced = _CODE_FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"Model trả về JSON hỏng ({exc.msg}, vị trí {exc.pos}). Hãy thử lại.") from exc
    if not isinstance(data, dict):
        raise LLMOutputError("Model trả về JSON không đúng dạng (cần một object). Hãy thử lại.")
    return data


class OllamaClient:
    """Thoả `LLMClient`. Mỗi lời gọi mở một `httpx.AsyncClient` riêng nên dùng được từ mọi event loop."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 600,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport  # chỉ dùng cho test (httpx.MockTransport)
        self._renderers: dict[str, str | None] = {}  # model -> renderer chat (`/api/show`), cho prefill raw

    def _client(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=timeout, transport=self._transport)

    # ---- thông điệp lỗi -----------------------------------------------------------------------

    def _connect_error(self) -> LLMError:
        return LLMError(
            f"Không kết nối được Ollama ở {self.base_url}. Hãy mở app Ollama (hoặc chạy `ollama serve`) rồi thử lại.",
            kind="connect",
        )

    def _transport_error(self, exc: httpx.HTTPError) -> LLMError:
        if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout):
            return self._connect_error()
        if isinstance(exc, httpx.TimeoutException):
            return LLMError(
                f"Ollama phản hồi quá lâu (quá {self.timeout:g} giây). Máy có thể đang thiếu RAM; hãy thử lại sau.",
                kind="timeout",
            )
        detail = str(exc) or type(exc).__name__
        return LLMError(f"Mất kết nối với Ollama ở {self.base_url} giữa chừng ({detail}). Hãy thử lại.", kind="connect")

    @staticmethod
    def _status_error(status: int, error: str, model: str) -> LLMError:
        if status == 404:
            return LLMError(
                f"Ollama chưa có model {model}. Hãy tải về bằng lệnh: ollama pull {model}"
                + (f" (Ollama báo: {error})" if error else ""),
                kind="missing_model",
            )
        return LLMError(f"Ollama báo lỗi (HTTP {status})" + (f": {error}" if error else "."), kind="server")

    # ---- chat ---------------------------------------------------------------------------------

    async def chat_stream(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        stop: list[str],
        options: dict[str, Any],
    ) -> AsyncIterator[LLMEvent]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "think": False,
            "keep_alive": "30m",
            "options": {**options, "stop": list(stop)},
        }
        timeout = httpx.Timeout(self.timeout, connect=_CONNECT_TIMEOUT)
        start = time.perf_counter()
        ttft_ms: float | None = None
        final: dict[str, Any] | None = None

        try:
            async with self._client(timeout) as client:
                for attempt in range(2):
                    async with client.stream("POST", "/api/chat", json=body) as resp:
                        if resp.status_code != 200:
                            await resp.aread()
                            error = _error_text(resp)
                            if attempt == 0 and "think" in body and _is_think_unsupported(resp.status_code, error):
                                # Model không hỗ trợ tham số think: gửi lại không kèm trường này.
                                del body["think"]
                                continue
                            raise self._status_error(resp.status_code, error, model)

                        async for line in resp.aiter_lines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise LLMError(f"Ollama trả về dữ liệu không đọc được: {line[:120]!r}") from exc
                            if not isinstance(chunk, dict):
                                raise LLMError(f"Ollama trả về dữ liệu không đọc được: {line[:120]!r}")
                            if chunk.get("error"):
                                raise LLMError(
                                    f"Ollama báo lỗi khi đang sinh câu trả lời: {chunk['error']}", kind="server"
                                )
                            message = chunk.get("message") or {}
                            piece = message.get("content") if isinstance(message, dict) else None
                            if isinstance(piece, str) and piece:
                                if ttft_ms is None:
                                    ttft_ms = (time.perf_counter() - start) * 1000
                                yield TextDelta(piece)
                            if chunk.get("done"):
                                final = chunk
                                break
                    break
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc

        if final is None:
            raise LLMError("Ollama đóng kết nối trước khi trả lời xong. Hãy thử lại.", kind="connect")
        yield Done(self._stats(final, start, ttft_ms))

    # ---- prefill phần đầu prompt (docs/phase3.md §10.6) ----------------------------------------------

    async def _renderer(self, model: str) -> str | None:
        """Tên renderer chat của model (`/api/show`, trường `renderer`), nhớ theo tên model. None nếu không có."""
        if model in self._renderers:
            return self._renderers[model]
        timeout = httpx.Timeout(min(self.timeout, _LIST_TIMEOUT), connect=_CONNECT_TIMEOUT)
        try:
            async with self._client(timeout) as client:
                resp = await client.post("/api/show", json={"model": model})
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc
        if resp.status_code != 200:
            raise self._status_error(resp.status_code, _error_text(resp), model)
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("Ollama trả về thông tin model không đọc được.") from exc
        renderer = data.get("renderer") if isinstance(data, dict) else None
        self._renderers[model] = renderer if isinstance(renderer, str) and renderer else None
        return self._renderers[model]

    async def prefill_prefix(
        self, model: str, messages: list[ChatTurn], *, options: dict[str, Any], open_last: bool = False
    ) -> bool:
        """Đọc trước `messages` vào cache prompt của Ollama, kết thúc ĐÚNG chỗ prompt chat lượt sau rẽ ra.

        Gửi `/api/generate` `raw` với văn bản `/api/chat` sẽ render cho `messages` nhưng không có generation
        prompt (`lyris.llm.render`), sinh 1 token. Runner mlx chỉ khôi phục cache tại các điểm chụp (chỗ một
        request bắt đầu đọc, và cuối prompt trừ vài token); prefill qua `/api/chat` kết thúc bằng generation
        prompt mà prompt thật không có, nên điểm cuối của nó vô dụng (§10.6).
        Trả False khi chưa biết render cho model này (người gọi prefill bằng `chat_stream`). LLMError khi lỗi.
        `open_last` (Phase 4): message cuối là lượt user còn mở (`render_prefix(..., open_last=True)`).
        """
        text = render_prefix(await self._renderer(model), messages, open_last=open_last)
        if text is None:
            return False
        body: dict[str, Any] = {
            "model": model,
            "prompt": text,
            "raw": True,
            "stream": True,
            "keep_alive": "30m",
            "options": {**options, "num_predict": 1},
        }
        timeout = httpx.Timeout(self.timeout, connect=_CONNECT_TIMEOUT)
        try:
            async with self._client(timeout) as client:
                # stream: huỷ task thì đóng kết nối, Ollama dừng đọc prompt ngay.
                async with client.stream("POST", "/api/generate", json=body) as resp:
                    if resp.status_code != 200:
                        await resp.aread()
                        raise self._status_error(resp.status_code, _error_text(resp), model)
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise LLMError(f"Ollama trả về dữ liệu không đọc được: {line[:120]!r}") from exc
                        if isinstance(chunk, dict) and chunk.get("error"):
                            raise LLMError(f"Ollama báo lỗi khi prefill: {chunk['error']}", kind="server")
                        if isinstance(chunk, dict) and chunk.get("done"):
                            return True
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc
        raise LLMError("Ollama đóng kết nối trước khi prefill xong.", kind="connect")

    # ---- structured output (JSON) ---------------------------------------------------------------

    async def chat_json(
        self,
        model: str,
        messages: list[ChatTurn],
        *,
        schema: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Một lượt không stream với `format` = JSON schema. Trả object JSON đã parse."""
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "think": False,
            "format": schema,
            "keep_alive": "30m",
            "options": dict(options),
        }
        timeout = httpx.Timeout(self.timeout, connect=_CONNECT_TIMEOUT)
        try:
            async with self._client(timeout) as client:
                resp = await client.post("/api/chat", json=body)
                if resp.status_code != 200:
                    error = _error_text(resp)
                    if "think" in body and _is_think_unsupported(resp.status_code, error):
                        # Model không hỗ trợ tham số think: gửi lại không kèm trường này.
                        del body["think"]
                        resp = await client.post("/api/chat", json=body)
                if resp.status_code != 200:
                    raise self._status_error(resp.status_code, _error_text(resp), model)
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc

        try:
            data = resp.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise LLMError(f"Ollama trả về dữ liệu không đọc được: {resp.text[:120]!r}") from exc
        if not isinstance(data, dict):
            raise LLMError(f"Ollama trả về dữ liệu không đọc được: {resp.text[:120]!r}")
        if data.get("error"):
            raise LLMError(f"Ollama báo lỗi khi đang sinh câu trả lời: {data['error']}", kind="server")
        if data.get("done_reason") == "length":
            raise LLMOutputError("Model viết quá dài, bị cắt giữa chừng. Hãy thử lại.")
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise LLMOutputError("Model không trả về nội dung nào. Hãy thử lại.")
        return _parse_json_object(content)

    # ---- embedding ------------------------------------------------------------------------------

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """`POST /api/embed`; model embed chỉ ở lại RAM 1 phút (không đẩy model chat ra ngoài lâu)."""
        if not texts:
            return []
        body: dict[str, Any] = {"model": model, "input": list(texts), "keep_alive": EMBED_KEEP_ALIVE}
        timeout = httpx.Timeout(self.timeout, connect=_CONNECT_TIMEOUT)
        try:
            async with self._client(timeout) as client:
                resp = await client.post("/api/embed", json=body)
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc
        if resp.status_code != 200:
            raise self._status_error(resp.status_code, _error_text(resp), model)
        try:
            data = resp.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise LLMError(f"Ollama trả về embedding không đọc được: {resp.text[:120]!r}") from exc
        vectors = data.get("embeddings") if isinstance(data, dict) else None
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise LLMError("Ollama trả về embedding không đúng dạng (số vector không khớp số đoạn văn).")
        out: list[list[float]] = []
        for vec in vectors:
            if (
                not isinstance(vec, list)
                or not vec
                or not all(isinstance(x, int | float) and not isinstance(x, bool) for x in vec)
            ):
                raise LLMError("Ollama trả về embedding không đúng dạng (vector rỗng hoặc không phải số).")
            out.append([float(x) for x in vec])
        return out

    @staticmethod
    def _stats(final: dict[str, Any], start: float, ttft_ms: float | None) -> GenStats:
        eval_count = final.get("eval_count")
        eval_duration = final.get("eval_duration")  # nano giây
        tok_per_s: float | None = None
        if isinstance(eval_count, int) and isinstance(eval_duration, int | float) and eval_duration > 0:
            tok_per_s = eval_count / (eval_duration / 1e9)
        prompt_tokens = final.get("prompt_eval_count")
        done_reason = final.get("done_reason")
        return GenStats(
            ttft_ms=ttft_ms,
            total_ms=(time.perf_counter() - start) * 1000,
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            output_tokens=eval_count if isinstance(eval_count, int) else None,
            tok_per_s=tok_per_s,
            done_reason=done_reason if isinstance(done_reason, str) else None,
        )

    # ---- danh sách model ------------------------------------------------------------------------

    async def list_models(self) -> list[str]:
        """Tên các model đã pull (GET /api/tags). LLMError nếu không kết nối được hoặc HTTP lỗi."""
        timeout = httpx.Timeout(min(self.timeout, _LIST_TIMEOUT), connect=_CONNECT_TIMEOUT)
        try:
            async with self._client(timeout) as client:
                resp = await client.get("/api/tags")
        except httpx.HTTPError as exc:
            raise self._transport_error(exc) from exc
        if resp.status_code != 200:
            raise LLMError(f"Ollama báo lỗi (HTTP {resp.status_code})" + (f": {e}" if (e := _error_text(resp)) else "."))
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("Ollama trả về danh sách model không đọc được.") from exc
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise LLMError("Ollama trả về danh sách model không đọc được.")
        names: list[str] = []
        for m in models:
            if isinstance(m, dict):
                name = m.get("name") or m.get("model")
                if isinstance(name, str) and name:
                    names.append(name)
        return names
