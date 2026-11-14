"""Tìm ký ức cho lượt sắp viết: từ khoá (FTS5, bm25) cộng vector (cosine), gộp bằng reciprocal rank fusion.

Mỗi story chỉ có vài trăm ký ức nên cosine tính bằng Python trên vector float32 lưu dạng BLOB
(little-endian) là đủ nhanh; không cần sqlite-vec hay numpy (docs/phase3.md §0).

Hợp đồng với repo (lyris/db/repo.py):
  - `search_memories_fts(story_id, terms, limit) -> list[tuple[MemoryItem, float]]`: bm25, nhỏ hơn là khớp hơn.
    Mỗi phần tử của `terms` là một cụm (có thể hai âm tiết, ví dụ "thư viện"): repo phải đặt nó trong
    ngoặc kép như một phrase FTS5 (nhân đôi dấu `"` bên trong) rồi nối bằng OR.
  - `memory_embeddings(story_id, embed_model) -> list[tuple[MemoryItem, bytes]]`: blob do `pack_vector` tạo.
Cả hai chỉ trả ký ức của message active.
"""
from __future__ import annotations

import logging
import math
import re
import sys
import unicodedata
from array import array
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol

from lyris.models import Language, MemoryHit, MemoryItem, Message, Story

log = logging.getLogger(__name__)

RRF_K = 60
IMPORTANCE_WEIGHT = 0.003  # Phase 3b: 0.02 làm importance lấn át thứ hạng từ khoá
MAX_QUERY_TERMS = 32
# Phía vector luôn xếp hạng được mọi ký ức; chỉ lấy những cái đủ gần và đứng đầu, không thì ký ức
# chẳng liên quan cũng được điểm RRF và điểm importance sẽ kéo chúng lên.
VECTOR_MIN_COSINE = 0.3
MAX_QUERY_CHARS = 2000

# Đại từ xưng hô và hư từ tiếng Việt: có mặt ở mọi câu nên không giúp phân biệt ký ức.
STOPWORDS_VI: frozenset[str] = frozenset(
    """
    anh em tớ cậu tôi tui tao mày mình ta ngươi cô chú bác bạn chị ông bà cháu con nó họ hắn chúng
    là và thì mà của đã đang sẽ không có những một này đó kia rồi nhé ạ à ơi nhỉ nha nhá hả hử chứ
    cũng vẫn còn lại được bị cho với để thế vậy nào gì ai đâu sao khi lúc nếu nhưng vì nên hay hoặc
    ra vào lên xuống đi đến tới từ trong ngoài trên dưới ở về theo như rất quá lắm hơn nhất chỉ cái
    các mọi ấy này kìa đấy đây thôi chưa đều cùng nữa vừa mới luôn nè
    """.split()
)
STOPWORDS_EN: frozenset[str] = frozenset(
    """
    the a an and or but if then so of to in on at by for with from into onto about as is are was were be been
    being am do does did have has had not no yes this that these those it its i me my mine you your yours he him
    his she her hers we us our they them their what which who whom whose when where why how all any some just
    very too can could will would shall should may might must there here out up down over again also still
    """.split()
)

_TOKEN = re.compile(r"[^\W_]+")


# ---- vector blob -----------------------------------------------------------------------------------


def pack_vector(vec: Sequence[float]) -> bytes:
    """list[float] -> BLOB float32 little-endian (cột `memories.embedding`)."""
    arr = array("f", (float(x) for x in vec))
    if sys.byteorder != "little":
        arr.byteswap()
    return arr.tobytes()


def unpack_vector(blob: bytes) -> list[float]:
    """BLOB float32 little-endian -> list[float]. ValueError nếu độ dài không chia hết cho 4."""
    if len(blob) % 4:
        raise ValueError(f"Blob embedding dài {len(blob)} byte, không phải bội số của 4.")
    arr = array("f")
    arr.frombytes(blob)
    if sys.byteorder != "little":
        arr.byteswap()
    return arr.tolist()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine của hai vector cùng số chiều; 0.0 nếu khác chiều hoặc một bên toàn 0."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---- truy vấn từ khoá ------------------------------------------------------------------------------


def name_tokens(names: Iterable[str]) -> frozenset[str]:
    """Âm tiết trong tên nhân vật/người chơi (NFC, chữ thường), để bỏ khỏi truy vấn từ khoá."""
    return frozenset(t for n in names for t in _TOKEN.findall(unicodedata.normalize("NFC", n or "").lower()))


def query_terms(text: str, language: Language, *, exclude: Iterable[str] = ()) -> list[str]:
    """Cụm từ khoá cho FTS5 từ `text`: NFC, chữ thường, bỏ stopword và token dưới 2 ký tự.

    Tiếng Việt thêm bigram của hai âm tiết liền nhau (cả hai đều không phải stopword), vì từ tiếng Việt
    thường có hai âm tiết ("thư viện", "trà sữa"). Giữ thứ tự xuất hiện, không trùng, tối đa 32 cụm.
    `exclude`: token bỏ thêm (âm tiết tên nhân vật và người chơi: có trong gần như mọi ký ức nên khớp tên
    sẽ kéo cả story vào kết quả).
    """
    tokens = _TOKEN.findall(unicodedata.normalize("NFC", text).lower())
    stop = (STOPWORDS_EN if language == "en" else STOPWORDS_VI) | frozenset(exclude)
    keep = [len(t) >= 2 and t not in stop for t in tokens]
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        if term not in seen:
            seen.add(term)
            terms.append(term)

    for i, token in enumerate(tokens):
        if not keep[i]:
            continue
        if language != "en" and i > 0 and keep[i - 1]:
            add(f"{tokens[i - 1]} {token}")
        add(token)
    # Ưu tiên bigram khi phải cắt bớt: chúng đặc trưng hơn âm tiết đơn.
    if len(terms) > MAX_QUERY_TERMS:
        bigrams = [t for t in terms if " " in t]
        singles = [t for t in terms if " " not in t]
        picked = set((bigrams + singles)[:MAX_QUERY_TERMS])
        terms = [t for t in terms if t in picked]
    return terms


# ---- gộp kết quả -----------------------------------------------------------------------------------


def fuse(
    keyword: Sequence[tuple[int, float]],
    vector: Sequence[tuple[int, float]],
    items: Mapping[int, MemoryItem] | Iterable[MemoryItem],
) -> list[MemoryHit]:
    """Reciprocal rank fusion (k=60) của hai danh sách, cộng `IMPORTANCE_WEIGHT * importance` (0.003); điểm cao trước.

    - `keyword`: (memory_id, bm25), bm25 nhỏ hơn là khớp hơn.
    - `vector`: (memory_id, cosine), lớn hơn là gần hơn.
    - `items`: MemoryItem theo id (dict hoặc danh sách); id không có trong `items` bị bỏ qua.
    Thiếu một phía (danh sách rỗng) vẫn chạy. Hoà điểm thì lượt mới hơn trước, rồi id lớn hơn trước.
    """
    by_id = dict(items) if isinstance(items, Mapping) else {m.id: m for m in items if m.id is not None}
    scores: dict[int, float] = {}
    for ranked in (
        sorted(keyword, key=lambda kv: kv[1]),
        sorted(vector, key=lambda kv: -kv[1]),
    ):
        seen: set[int] = set()
        rank = 0
        for memory_id, _ in ranked:
            if memory_id in seen or memory_id not in by_id:
                continue
            seen.add(memory_id)
            rank += 1
            scores[memory_id] = scores.get(memory_id, 0.0) + 1.0 / (RRF_K + rank)
    hits = [
        MemoryHit(
            memory_id=memory_id,
            turn_index=by_id[memory_id].turn_index,
            kind=by_id[memory_id].kind,
            text=by_id[memory_id].text,
            score=score + IMPORTANCE_WEIGHT * by_id[memory_id].importance,
        )
        for memory_id, score in scores.items()
    ]
    hits.sort(key=lambda h: (-h.score, -h.turn_index, -h.memory_id))
    return hits


# ---- tìm ký ức ---------------------------------------------------------------------------------------


class MemoryRepo(Protocol):
    def search_memories_fts(self, story_id: int, terms: list[str], limit: int) -> list[tuple[MemoryItem, float]]: ...

    def memory_embeddings(self, story_id: int, embed_model: str) -> list[tuple[MemoryItem, bytes]]: ...


class Embedder(Protocol):
    async def embed(self, model: str, texts: list[str]) -> list[list[float]]: ...


def _query_parts(history: Sequence[Message]) -> tuple[str, str]:
    """(lượt trả lời ngay trước của nhân vật, (các) tin cuối của người chơi), dùng `visible_content`."""
    tail: list[str] = []
    i = len(history) - 1
    while i >= 0 and history[i].role == "user":
        tail.append(history[i].visible_content)
        i -= 1
    reply = history[i].visible_content.strip() if i >= 0 and history[i].role == "assistant" else ""
    player = "\n".join(p.strip() for p in reversed(tail) if p.strip())
    return reply, player


def query_text(history: Sequence[Message]) -> str:
    """Truy vấn: (các) tin cuối của người chơi cộng lượt trả lời ngay trước đó của nhân vật.

    Dùng `visible_content` (không có Thought, không có chỉ đạo ((...))). Cắt còn 2000 ký tự cuối.
    """
    text = "\n".join(p for p in _query_parts(history) if p)
    return text[-MAX_QUERY_CHARS:]


def keyword_terms(history: Sequence[Message], language: Language, *, exclude: Iterable[str] = ()) -> list[str]:
    """Từ khoá của truy vấn, cụm trong tin của người chơi đứng trước (khi phải cắt còn 32 cụm, lượt trả
    lời dài của nhân vật không được đẩy mất điều người chơi vừa hỏi), rồi tới lượt trả lời trước đó."""
    reply, player = _query_parts(history)
    terms: list[str] = []
    for part in (player, reply[-MAX_QUERY_CHARS:]):
        for term in query_terms(part, language, exclude=exclude):
            if term not in terms:
                terms.append(term)
    return terms[:MAX_QUERY_TERMS]


async def retrieve(
    repo: Any,
    llm: Any,
    story: Story,
    history: Sequence[Message],
    *,
    embed_model: str | None,
    limit: int = 8,
    names: Sequence[str] = (),
) -> list[MemoryHit]:
    """Ký ức và fact liên quan tới lượt sắp viết, đã xếp hạng, tối đa `limit`.

    Từ khoá qua `repo.search_memories_fts`; vector chỉ khi có `embed_model` và story đã có embedding của
    model đó (không thì không gọi embed, tránh nạp bge-m3 vô ích). Embed lỗi thì chỉ dùng từ khoá.
    `repo`: thoả `MemoryRepo`; `llm`: thoả `Embedder` (LLMClient).
    `names`: tên nhân vật và người chơi; âm tiết của chúng không dùng làm từ khoá.
    """
    if story.id is None or limit <= 0:
        return []
    text = query_text(history)
    if not text:
        return []
    items: dict[int, MemoryItem] = {}

    keyword: list[tuple[int, float]] = []
    terms = keyword_terms(history, story.language, exclude=name_tokens(names))
    if terms:
        for item, bm25 in repo.search_memories_fts(story.id, terms, limit * 2):
            if item.id is not None:
                items[item.id] = item
                keyword.append((item.id, float(bm25)))

    vector: list[tuple[int, float]] = []
    if embed_model:
        stored = repo.memory_embeddings(story.id, embed_model)
        if stored:
            try:
                query_vec = (await llm.embed(embed_model, [text]))[0]
            except Exception as exc:  # noqa: BLE001 - embed lỗi gì cũng quay về chỉ dùng từ khoá
                log.warning("Embed truy vấn ký ức lỗi, chỉ tìm theo từ khoá: %s", exc)
                query_vec = None
            if query_vec:
                scored: list[tuple[MemoryItem, float]] = []
                for item, blob in stored:
                    if item.id is None:
                        continue
                    try:
                        sim = cosine(query_vec, unpack_vector(blob))
                    except ValueError:
                        continue
                    if sim >= VECTOR_MIN_COSINE:
                        scored.append((item, sim))
                scored.sort(key=lambda pair: -pair[1])
                for item, sim in scored[: limit * 2]:
                    items.setdefault(item.id, item)  # type: ignore[arg-type]
                    vector.append((item.id, sim))  # type: ignore[arg-type]

    return fuse(keyword, vector, items)[:limit]
