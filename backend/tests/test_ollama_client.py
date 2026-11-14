"""Test OllamaClient bằng httpx.MockTransport (không cần Ollama thật) và FakeLLM."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Awaitable

import httpx
import pytest

from lyris.llm.base import Done, LLMError, LLMEvent, LLMOutputError, TextDelta
from lyris.llm.fake import FakeLLM
from lyris.llm.ollama import OllamaClient
from lyris.models import ChatTurn

BASE = "http://ollama.test:11434"
MESSAGES = [
    ChatTurn(role="system", content="Bạn là Lạc Dương."),
    ChatTurn(role="user", content="Lạc Dương ơi, hôm nay cậu vẫn đến đón tớ chứ?"),
]
STOP = ["Lâm Vãn:", "\nLâm Vãn:", "\nPlayer:", "\nUser:"]
OPTIONS = {"num_ctx": 8192, "num_predict": 200, "temperature": 0.8, "top_p": 0.95}

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def ndjson(*chunks: dict) -> bytes:
    return b"".join(json.dumps(c, ensure_ascii=False).encode() + b"\n" for c in chunks)


def content_chunk(text: str) -> dict:
    return {"model": "gemma4:12b", "message": {"role": "assistant", "content": text}, "done": False}


DONE_CHUNK = {
    "model": "gemma4:12b",
    "message": {"role": "assistant", "content": ""},
    "done": True,
    "done_reason": "stop",
    "total_duration": 6_000_000_000,
    "prompt_eval_count": 423,
    "prompt_eval_duration": 3_800_000_000,
    "eval_count": 25,
    "eval_duration": 2_500_000_000,
}

NORMAL_BODY = ndjson(
    content_chunk("Có. "),
    content_chunk("8 giờ tớ đến"),
    content_chunk(""),
    content_chunk(" trước cửa ký túc xá."),
    DONE_CHUNK,
)


def make_client(handler: Handler) -> OllamaClient:
    return OllamaClient(BASE, timeout=30, transport=httpx.MockTransport(handler))


async def collect(client: OllamaClient) -> list[LLMEvent]:
    return [ev async for ev in client.chat_stream("gemma4:12b", MESSAGES, stop=STOP, options=OPTIONS)]


class TrackingStream(httpx.AsyncByteStream):
    """Body stream ghi nhận việc bị đóng; yield từng dòng để có thể ngắt giữa chừng."""

    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines
        self.sent = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for line in self.lines:
            self.sent += 1
            yield line

    async def aclose(self) -> None:
        self.closed = True


# ---- stream bình thường --------------------------------------------------------------------------


async def test_normal_stream_yields_deltas_then_done() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=NORMAL_BODY, headers={"Content-Type": "application/x-ndjson"})

    events = await collect(make_client(handler))

    assert [e for e in events if isinstance(e, TextDelta)] == [
        TextDelta("Có. "),
        TextDelta("8 giờ tớ đến"),
        TextDelta(" trước cửa ký túc xá."),
    ]
    assert isinstance(events[-1], Done)
    assert sum(isinstance(e, Done) for e in events) == 1
    stats = events[-1].stats
    assert stats.prompt_tokens == 423
    assert stats.output_tokens == 25
    assert stats.tok_per_s == pytest.approx(10.0)
    assert stats.done_reason == "stop"
    assert stats.ttft_ms is not None and stats.ttft_ms >= 0
    assert stats.total_ms is not None and stats.total_ms >= stats.ttft_ms
    assert stats.aborted is False

    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    assert str(req.url) == f"{BASE}/api/chat"
    body = json.loads(req.content)
    assert body == {
        "model": "gemma4:12b",
        "messages": [{"role": m.role, "content": m.content} for m in MESSAGES],
        "stream": True,
        "think": False,
        "keep_alive": "30m",
        "options": {**OPTIONS, "stop": STOP},
    }


async def test_stream_split_across_byte_boundaries() -> None:
    """NDJSON bị cắt giữa dòng (và giữa ký tự UTF-8) vẫn đọc đúng."""
    raw = NORMAL_BODY

    async def handler(request: httpx.Request) -> httpx.Response:
        pieces = [raw[i : i + 5] for i in range(0, len(raw), 5)]
        return httpx.Response(200, stream=TrackingStream(pieces))

    events = await collect(make_client(handler))
    text = "".join(e.text for e in events if isinstance(e, TextDelta))
    assert text == "Có. 8 giờ tớ đến trước cửa ký túc xá."
    assert isinstance(events[-1], Done)


async def test_no_content_gives_no_ttft() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson({**DONE_CHUNK, "eval_count": 0, "eval_duration": 0}))

    events = await collect(make_client(handler))
    assert len(events) == 1 and isinstance(events[0], Done)
    assert events[0].stats.ttft_ms is None
    assert events[0].stats.tok_per_s is None


# ---- think không được hỗ trợ ---------------------------------------------------------------------


async def test_think_unsupported_400_retries_without_think() -> None:
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": '"gemma4:12b" does not support thinking'})
        return httpx.Response(200, content=NORMAL_BODY)

    events = await collect(make_client(handler))
    assert len(bodies) == 2
    assert bodies[0]["think"] is False
    assert "think" not in bodies[1]
    assert {k: v for k, v in bodies[0].items() if k != "think"} == bodies[1]
    assert isinstance(events[-1], Done)
    assert "".join(e.text for e in events if isinstance(e, TextDelta)).startswith("Có.")


async def test_other_400_is_not_retried() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "invalid options"})

    with pytest.raises(LLMError) as info:
        await collect(make_client(handler))
    assert calls == 1
    assert "HTTP 400" in str(info.value) and "invalid options" in str(info.value)


async def test_think_400_twice_raises() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "think is broken"})

    with pytest.raises(LLMError):
        await collect(make_client(handler))
    assert calls == 2


# ---- lỗi -------------------------------------------------------------------------------------------


async def test_connection_error_gives_vietnamese_llm_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(LLMError) as info:
        await collect(make_client(handler))
    msg = str(info.value)
    assert "Không kết nối được Ollama" in msg
    assert BASE in msg
    assert "mở app Ollama" in msg


async def test_model_not_found_404() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'gemma9:99b' not found"})

    client = make_client(handler)
    with pytest.raises(LLMError) as info:
        async for _ in client.chat_stream("gemma9:99b", MESSAGES, stop=STOP, options=OPTIONS):
            pass
    msg = str(info.value)
    assert "chưa có model gemma9:99b" in msg
    assert "ollama pull gemma9:99b" in msg


async def test_http_500_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal boom")

    with pytest.raises(LLMError, match="HTTP 500"):
        await collect(make_client(handler))


async def test_error_line_mid_stream() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson(content_chunk("Anh"), {"error": "out of memory"}))

    client = make_client(handler)
    got: list[LLMEvent] = []
    with pytest.raises(LLMError, match="out of memory"):
        async for ev in client.chat_stream("gemma4:12b", MESSAGES, stop=STOP, options=OPTIONS):
            got.append(ev)
    assert got == [TextDelta("Anh")]


async def test_stream_ending_without_done_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson(content_chunk("Anh khẽ")))

    with pytest.raises(LLMError, match="trước khi trả lời xong"):
        await collect(make_client(handler))


async def test_invalid_json_line_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json\n")

    with pytest.raises(LLMError, match="không đọc được"):
        await collect(make_client(handler))


async def test_read_error_mid_stream_is_llm_error() -> None:
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield ndjson(content_chunk("Anh"))
            raise httpx.ReadError("connection reset")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=BrokenStream())

    with pytest.raises(LLMError, match="Mất kết nối"):
        await collect(make_client(handler))


# ---- đóng sớm ----------------------------------------------------------------------------------


async def test_early_close_closes_response() -> None:
    stream = TrackingStream([ndjson(content_chunk(f"chữ {i} ")) for i in range(50)] + [ndjson(DONE_CHUNK)])

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    client = make_client(handler)
    gen = client.chat_stream("gemma4:12b", MESSAGES, stop=STOP, options=OPTIONS)
    first = await gen.__anext__()
    second = await gen.__anext__()
    assert first == TextDelta("chữ 0 ") and second == TextDelta("chữ 1 ")
    assert not stream.closed
    await gen.aclose()
    assert stream.closed
    assert stream.sent < 50


async def test_break_out_of_async_for_closes_response() -> None:
    stream = TrackingStream([ndjson(content_chunk(f"chữ {i} ")) for i in range(50)] + [ndjson(DONE_CHUNK)])

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    client = make_client(handler)
    gen = client.chat_stream("gemma4:12b", MESSAGES, stop=STOP, options=OPTIONS)
    async for ev in gen:
        assert isinstance(ev, TextDelta)
        break
    await gen.aclose()
    assert stream.closed


# ---- list_models ---------------------------------------------------------------------------------


async def test_list_models() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET" and request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "gemma4:12b"}, {"name": "gemma4:e4b"}]})

    assert await make_client(handler).list_models() == ["gemma4:12b", "gemma4:e4b"]


async def test_list_models_connection_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(LLMError, match="Không kết nối được Ollama"):
        await make_client(handler).list_models()


async def test_list_models_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "đang khởi động"})

    with pytest.raises(LLMError, match="HTTP 503"):
        await make_client(handler).list_models()


# ---- FakeLLM -------------------------------------------------------------------------------------


async def test_fake_llm_chunks_and_records_calls() -> None:
    fake = FakeLLM(["Một hai ba bốn năm", "Câu thứ hai"], chunk_size=4)
    events = [ev async for ev in fake.chat_stream("m", MESSAGES, stop=STOP, options=OPTIONS)]
    deltas = [e.text for e in events if isinstance(e, TextDelta)]
    assert deltas == ["Một ", "hai ", "ba b", "ốn n", "ăm"]
    assert isinstance(events[-1], Done) and events[-1].stats.output_tokens == 5

    for expected in ["Câu thứ hai", "Câu thứ hai"]:  # hết reply thì lặp lại cái cuối
        events = [ev async for ev in fake.chat_stream("m", MESSAGES, stop=STOP, options=OPTIONS)]
        assert "".join(e.text for e in events if isinstance(e, TextDelta)) == expected

    assert len(fake.calls) == 3
    assert fake.calls[0] == {"model": "m", "messages": MESSAGES, "stop": STOP, "options": OPTIONS}


async def test_fake_llm_error_and_default_reply() -> None:
    fake = FakeLLM(error=LLMError("Không kết nối được Ollama"))
    with pytest.raises(LLMError):
        async for _ in fake.chat_stream("m", MESSAGES, stop=STOP, options=OPTIONS):
            pass
    assert len(fake.calls) == 1
    fake.error = None
    events = [ev async for ev in fake.chat_stream("m", MESSAGES, stop=STOP, options=OPTIONS)]
    text = "".join(e.text for e in events if isinstance(e, TextDelta))
    assert "[Thought:" in text


# ---- chat_json (structured output) ----------------------------------------------------------------

JSON_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "gender": {"type": "string", "enum": ["male", "female", "other"]}},
    "required": ["name", "gender"],
}
JSON_OPTIONS = {"temperature": 0.8, "num_predict": 2048, "num_ctx": 8192}


def json_response(content: str, *, done_reason: str = "stop", status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "model": "gemma4:12b",
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": done_reason,
            "eval_count": 120,
        },
    )


async def call_json(client: OllamaClient) -> dict:
    return await client.chat_json("gemma4:12b", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS)


async def test_chat_json_request_body_and_result() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return json_response('{"name": "Tạ Vân Lan", "gender": "female"}')

    result = await call_json(make_client(handler))
    assert result == {"name": "Tạ Vân Lan", "gender": "female"}
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST" and str(req.url) == f"{BASE}/api/chat"
    body = json.loads(req.content)
    assert body == {
        "model": "gemma4:12b",
        "messages": [{"role": m.role, "content": m.content} for m in MESSAGES],
        "stream": False,
        "think": False,
        "format": JSON_SCHEMA,
        "keep_alive": "30m",
        "options": JSON_OPTIONS,
    }


async def test_chat_json_strips_code_fence() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response('```json\n{"name": "A", "gender": "male"}\n```')

    assert await call_json(make_client(handler)) == {"name": "A", "gender": "male"}


async def test_chat_json_length_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response('{"name": "Tạ Vân Lan", "greeting": "Tuyết rơi trắng', done_reason="length")

    with pytest.raises(LLMError) as info:
        await call_json(make_client(handler))
    assert str(info.value) == "Model viết quá dài, bị cắt giữa chừng. Hãy thử lại."


@pytest.mark.parametrize("content", ['{"name": "A", "gender": ', "không phải JSON", "[1, 2]", '"chuỗi"'])
async def test_chat_json_bad_json_is_error(content: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response(content)

    with pytest.raises(LLMError, match="JSON"):
        await call_json(make_client(handler))


async def test_chat_json_empty_content_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response("   ")

    with pytest.raises(LLMError, match="không trả về nội dung"):
        await call_json(make_client(handler))


async def test_chat_json_unreadable_body_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>proxy</html>")

    with pytest.raises(LLMError, match="không đọc được"):
        await call_json(make_client(handler))


async def test_chat_json_error_field_is_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "out of memory"})

    with pytest.raises(LLMError, match="out of memory"):
        await call_json(make_client(handler))


async def test_chat_json_think_unsupported_retries_without_think() -> None:
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": '"gemma4:12b" does not support thinking'})
        return json_response('{"name": "A", "gender": "other"}')

    assert await call_json(make_client(handler)) == {"name": "A", "gender": "other"}
    assert len(bodies) == 2
    assert bodies[0]["think"] is False and "think" not in bodies[1]
    assert {k: v for k, v in bodies[0].items() if k != "think"} == bodies[1]
    assert bodies[1]["format"] == JSON_SCHEMA and bodies[1]["stream"] is False


async def test_chat_json_think_400_twice_raises() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "think is broken"})

    with pytest.raises(LLMError, match="HTTP 400"):
        await call_json(make_client(handler))
    assert calls == 2


async def test_chat_json_other_400_not_retried() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "invalid format schema"})

    with pytest.raises(LLMError, match="invalid format schema"):
        await call_json(make_client(handler))
    assert calls == 1


async def test_chat_json_404_model() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'gemma9:99b' not found"})

    with pytest.raises(LLMError, match="ollama pull gemma9:99b"):
        await make_client(handler).chat_json("gemma9:99b", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS)


async def test_chat_json_connection_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(LLMError, match="Không kết nối được Ollama"):
        await call_json(make_client(handler))


async def test_chat_json_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(LLMError, match="quá lâu"):
        await call_json(make_client(handler))


async def test_fake_llm_chat_json() -> None:
    fake = FakeLLM(json_replies=[{"name": "A", "tags": ["x"]}, {"name": "B"}])
    first = await fake.chat_json("m", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS)
    assert first == {"name": "A", "tags": ["x"]}
    first["tags"].append("bị sửa")  # trả bản sao: sửa kết quả không ảnh hưởng lần gọi sau
    assert await fake.chat_json("m", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS) == {"name": "B"}
    assert await fake.chat_json("m", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS) == {"name": "B"}
    assert len(fake.calls) == 3
    assert fake.calls[0] == {
        "model": "m",
        "messages": MESSAGES,
        "stop": [],
        "options": JSON_OPTIONS,
        "schema": JSON_SCHEMA,
    }
    # chat_stream vẫn dùng replies riêng.
    events = [ev async for ev in fake.chat_stream("m", MESSAGES, stop=STOP, options=OPTIONS)]
    assert isinstance(events[-1], Done)


async def test_fake_llm_chat_json_error_and_unconfigured() -> None:
    fake = FakeLLM(error=LLMError("hỏng"))
    with pytest.raises(LLMError, match="hỏng"):
        await fake.chat_json("m", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS)
    fake.error = None
    with pytest.raises(LLMError, match="json_replies"):
        await fake.chat_json("m", MESSAGES, schema=JSON_SCHEMA, options=JSON_OPTIONS)
    assert len(fake.calls) == 2


# ---- Phase 3: lỗi nội dung (LLMOutputError) -------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "done_reason"),
    [('{"name": ', "stop"), ("[1]", "stop"), ("   ", "stop"), ('{"name": "A"', "length")],
)
async def test_chat_json_output_problems_are_output_errors(content: str, done_reason: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return json_response(content, done_reason=done_reason)

    with pytest.raises(LLMOutputError):
        await call_json(make_client(handler))


async def test_chat_json_connection_error_is_not_output_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMError) as info:
        await call_json(make_client(handler))
    assert not isinstance(info.value, LLMOutputError)


# ---- Phase 3: embed -------------------------------------------------------------------------------


async def test_embed_request_body_and_result() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"model": "bge-m3", "embeddings": [[0.1, -0.2, 3], [1, 0, 0]]})

    out = await make_client(handler).embed("bge-m3", ["trà sữa", "thư viện"])
    assert out == [[0.1, -0.2, 3.0], [1.0, 0.0, 0.0]]
    assert all(isinstance(x, float) for v in out for x in v)
    req = requests[0]
    assert req.method == "POST" and str(req.url) == f"{BASE}/api/embed"
    assert json.loads(req.content) == {"model": "bge-m3", "input": ["trà sữa", "thư viện"], "keep_alive": "1m"}


async def test_embed_empty_input_makes_no_request() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - không được gọi
        raise AssertionError("không được gọi Ollama")

    assert await make_client(handler).embed("bge-m3", []) == []


async def test_embed_model_missing_404() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": 'model "bge-m3" not found, try pulling it first'})

    with pytest.raises(LLMError, match="ollama pull bge-m3"):
        await make_client(handler).embed("bge-m3", ["x"])


@pytest.mark.parametrize(
    "body",
    [
        {"embeddings": [[0.1]]},  # thiếu một vector
        {"embeddings": [[0.1], []]},
        {"embeddings": [[0.1], ["a"]]},
        {"embeddings": [[0.1], [True]]},
        {"other": 1},
        [1, 2],
    ],
)
async def test_embed_bad_shape_is_error(body: object) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(LLMError, match="embedding"):
        await make_client(handler).embed("bge-m3", ["a", "b"])


async def test_embed_unreadable_body_and_connection_error() -> None:
    async def bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>")

    with pytest.raises(LLMError, match="không đọc được"):
        await make_client(bad).embed("bge-m3", ["a"])

    async def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMError, match="Không kết nối được Ollama"):
        await make_client(down).embed("bge-m3", ["a"])


async def test_fake_llm_embed_deterministic_and_similar() -> None:
    fake = FakeLLM(embed_dim=32)
    a, b, c, empty = await fake.embed("bge-m3", ["Trà sữa khoai môn", "trà  sữa KHOAI môn", "lẩu cay", ""])
    assert len(a) == 32 and a == b
    assert sum(x * x for x in a) == pytest.approx(1.0)
    assert sum(x * y for x, y in zip(a, c, strict=True)) < 0.9
    assert empty == [0.0] * 32
    assert fake.embed_calls == [{"model": "bge-m3", "texts": ["Trà sữa khoai môn", "trà  sữa KHOAI môn", "lẩu cay", ""]}]
    assert fake.calls == []  # embed không ghi vào calls của chat


async def test_fake_llm_embed_error_independent_of_chat_error() -> None:
    fake = FakeLLM(error=LLMError("chat hỏng"))
    assert len((await fake.embed("m", ["x"]))[0]) == 64
    fake = FakeLLM(embed_error=LLMError("embed hỏng"))
    with pytest.raises(LLMError, match="embed hỏng"):
        await fake.embed("m", ["x"])


# ---- prefill raw (docs/phase3.md §10.6) -----------------------------------------------------------

PREFIX = [
    ChatTurn(role="system", content="  Bạn là Lạc Dương.\n"),
    ChatTurn(role="user", content="\nChào cậu. "),
    ChatTurn(role="assistant", content="<|channel>thought\nnghĩ<channel|> *Anh cười.*\n"),
]
# Đã đối chiếu với /api/chat thật (gemma4:12b, Ollama 0.40.16): trim nội dung, bỏ khối suy nghĩ, không có
# generation prompt ở cuối (prompt thật nối tiếp bằng "<|turn>user\n...").
PREFIX_TEXT = (
    "<bos><|turn>system\nBạn là Lạc Dương.<turn|>\n"
    "<|turn>user\nChào cậu.<turn|>\n"
    "<|turn>model\n*Anh cười.*<turn|>\n"
)


def test_render_prefix_gemma4_matches_ollama_chat_template() -> None:
    from lyris.llm.render import render_prefix

    assert render_prefix("gemma4-large", PREFIX) == PREFIX_TEXT
    # Prompt thật (thêm lượt người chơi) có đúng văn bản này làm phần đầu.
    full = render_prefix("gemma4-large", [*PREFIX, ChatTurn(role="user", content="Đi thôi.")])
    assert full is not None and full.startswith(PREFIX_TEXT)
    assert render_prefix("gemma4", PREFIX) is None  # renderer chưa đối chiếu
    assert render_prefix(None, PREFIX) is None
    assert render_prefix("gemma4-large", []) is None


def prefill_handler(renderer: str | None, seen: list[tuple[str, dict]], *, gen_status: int = 200) -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"renderer": renderer} if renderer else {"template": "{{ .Prompt }}"})
        if request.url.path == "/api/generate":
            if gen_status != 200:
                return httpx.Response(gen_status, json={"error": "raw not allowed"})
            return httpx.Response(200, content=ndjson({"response": "x", "done": False}, {"response": "", "done": True}))
        return httpx.Response(500)

    return handler


async def test_prefill_prefix_sends_raw_text_ending_where_next_prompt_diverges() -> None:
    seen: list[tuple[str, dict]] = []
    client = make_client(prefill_handler("gemma4-large", seen))
    assert await client.prefill_prefix("gemma4:12b", PREFIX, options=OPTIONS) is True
    assert await client.prefill_prefix("gemma4:12b", PREFIX, options=OPTIONS) is True
    assert [p for p, _ in seen] == ["/api/show", "/api/generate", "/api/generate"]  # renderer nhớ theo model
    body = seen[1][1]
    assert body["prompt"] == PREFIX_TEXT and body["raw"] is True and body["model"] == "gemma4:12b"
    assert body["options"]["num_predict"] == 1 and body["options"]["num_ctx"] == 8192
    assert body["keep_alive"] == "30m"


async def test_prefill_prefix_unknown_renderer_returns_false_without_generating() -> None:
    seen: list[tuple[str, dict]] = []
    client = make_client(prefill_handler(None, seen))
    assert await client.prefill_prefix("llama3:8b", PREFIX, options=OPTIONS) is False
    assert await client.prefill_prefix("llama3:8b", PREFIX, options=OPTIONS) is False
    assert [p for p, _ in seen] == ["/api/show"]


async def test_prefill_prefix_errors_raise_llm_error() -> None:
    seen: list[tuple[str, dict]] = []
    with pytest.raises(LLMError, match="HTTP 400"):
        await make_client(prefill_handler("gemma4-large", seen, gen_status=400)).prefill_prefix(
            "gemma4:12b", PREFIX, options=OPTIONS
        )

    async def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMError, match="Không kết nối được Ollama"):
        await make_client(down).prefill_prefix("gemma4:12b", PREFIX, options=OPTIONS)


async def test_fake_llm_prefill_prefix() -> None:
    fake = FakeLLM()
    assert await fake.prefill_prefix("m", PREFIX, options=OPTIONS) is True
    assert fake.calls[-1]["raw"] is True and fake.calls[-1]["options"]["num_predict"] == 1
    assert fake.calls[-1]["messages"] == PREFIX
    assert await FakeLLM(raw_prefill=False).prefill_prefix("m", PREFIX, options=OPTIONS) is False
    with pytest.raises(LLMError):
        await FakeLLM(error=LLMError("x")).prefill_prefix("m", PREFIX, options=OPTIONS)
