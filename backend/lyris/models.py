"""Kiểu dữ liệu dùng chung giữa DB, prompt builder, LLM và API.

Đây là hợp đồng giữa các module: đổi gì ở đây phải đổi theo ở mọi nơi dùng.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Gender = Literal["male", "female", "other"]
Language = Literal["vi", "en"]
Mode = Literal["story", "dm"]
Role = Literal["user", "assistant"]
# het = nam-nữ (ngôn tình), bl = nam-nam (đam mỹ), gl = nữ-nữ (bách hợp), none = không lãng mạn
RelationshipType = Literal["het", "bl", "gl", "none"]
Pov = Literal["third", "first"]
# inline = vài dòng [Thought: ...] lồng giữa truyện; end = đúng một dòng ở cuối lượt
ThoughtStyle = Literal["inline", "end"]
# Phase 2c: ai thấy card khi có cộng đồng (Phase 7). Bây giờ chỉ lưu; mặc định riêng tư.
Visibility = Literal["private", "unlisted", "public"]
Rating = Literal["up", "down"]


class AddressTerms(BaseModel):
    """Xưng hô của nhân vật AI. Chỉ dùng trong lời thoại và Thought, không dùng để dẫn truyện."""

    self_term: str = Field(description='Nhân vật tự xưng, ví dụ "tớ"')
    player_term: str = Field(description='Nhân vật gọi người chơi, ví dụ "cậu"')
    nicknames: list[str] = Field(default_factory=list, description='Tên gọi thân mật cho người chơi, ví dụ ["Vãn Vãn", "A Vãn"]')
    others: str = Field(default="", description="Cách xưng hô với người khác, mô tả tự do")


class NarrationPronouns(BaseModel):
    """Đại từ dùng trong phần dẫn truyện (ngoài lời thoại và Thought)."""

    character: str = Field(description='Ví dụ "anh"')
    player: str = Field(description='Ví dụ "cô"')


class CharacterCard(BaseModel):
    id: int | None = None
    uid: str | None = Field(default=None, description="Phase 2c: mã toàn cầu 32 hex, backend đặt khi tạo, không đổi")
    visibility: Visibility = "private"
    name: str
    role: str = Field(default="", description='Vai trò/thân phận ngắn hiện dưới tên, ví dụ "Chủ tiệm sách mùa thu"')
    gender: Gender
    language: Language = "vi"
    description: str = ""
    personality: str = ""
    appearance: str = ""
    background: str = ""
    goals: str = ""
    secrets: str = ""
    speech_style: str = ""
    style_profile: str = Field(description="Tên file trong lyris/prompt/styles/ không kèm .md, ví dụ trung_hien_dai")
    address_terms: AddressTerms
    greeting: str = Field(default="", description="Lời mở đầu của nhân vật, dạng raw (có thể chứa [Thought: ...])")
    example_dialogues: str = ""
    tags: list[str] = Field(default_factory=list)
    # ---- Phase 2 ----
    scenario: str = Field(default="", description="Bối cảnh mặc định cho story mới (Character Card V2: scenario)")
    alternate_greetings: list[str] = Field(
        default_factory=list, description="Lời mở đầu khác; khi tạo story chọn một trong greeting + các bản này"
    )
    creator_notes: str = Field(default="", description="Ghi chú của người tạo; không bao giờ đưa vào prompt")
    avatar: str | None = Field(
        default=None, description="Tên file ảnh trong Settings.avatars_dir (chỉ backend đặt; API trả avatar_url)"
    )
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description="Dữ liệu Character Card V2 không dùng tới (character_book, creator, ...) để export lại không mất",
    )


class StorySettings(BaseModel):
    """Thiết lập của một story (dùng khi tạo story, xem trước prompt, chat thử)."""

    scenario: str = ""
    language: Language = "vi"
    mode: Mode = "story"
    relationship_type: RelationshipType = "het"
    pov: Pov = "third"
    thought_style: ThoughtStyle = "inline"
    narration_pronouns: NarrationPronouns


class StyleProfileInfo(BaseModel):
    """Thông tin một style profile (đọc từ YAML frontmatter của styles/<name>.md)."""

    name: str = Field(description="Tên file không kèm .md")
    title: str
    description: str = ""
    # narration[language][gender] = đại từ dẫn truyện ngôi thứ ba mặc định, ví dụ narration["vi"]["male"] = "anh"
    narration: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Gợi ý cặp xưng hô cho trình sửa xưng hô: [{"self": "tớ", "player": "cậu", "note": "bạn thân"}]
    address_examples: list[dict[str, str]] = Field(default_factory=list)


class Persona(BaseModel):
    id: int | None = None
    uid: str | None = Field(default=None, description="Phase 2c: mã toàn cầu, backend đặt")
    name: str
    gender: Gender
    description: str = ""
    avatar: str | None = Field(default=None, description="Phase 2c: file trong avatars_dir; chỉ backend đặt")


class Story(BaseModel):
    id: int | None = None
    uid: str | None = Field(default=None, description="Phase 2c: mã toàn cầu, backend đặt")
    card_id: int
    persona_id: int
    title: str
    scenario: str = ""
    language: Language = "vi"
    mode: Mode = "story"
    relationship_type: RelationshipType = "het"
    pov: Pov = "third"
    thought_style: ThoughtStyle = "inline"
    narration_pronouns: NarrationPronouns
    model_name: str = "gemma4:12b"
    scene_summary: str = ""
    created_at: str | None = None
    # Phase 4 (B): hiện thẻ suy nghĩ của nhân vật trong story. Chỉ là cách hiển thị: prompt không đổi.
    show_thoughts: bool = True


class GenStats(BaseModel):
    ttft_ms: float | None = None
    total_ms: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    tok_per_s: float | None = None
    done_reason: str | None = None
    aborted: bool = False


class Message(BaseModel):
    id: int | None = None
    story_id: int
    turn_index: int
    variant_index: int = 0
    is_active: bool = True
    role: Role
    mode: Mode
    raw_content: str = Field(description="Nội dung hiện tại đầy đủ (assistant: gồm cả [Thought: ...]; user: nguyên văn gồm cả ((...)))")
    visible_content: str = Field(description="Phần hiển thị (assistant: bỏ Thought; user: bỏ ((...)))")
    thought: str | None = None
    directive: str | None = Field(default=None, description="Chỉ đạo ((...)) của người chơi ở lượt này, đã gộp")
    model_output: str | None = Field(default=None, description="Nguyên văn model sinh ra, không bao giờ đổi khi sửa")
    prompt_snapshot: dict[str, Any] | None = None
    model_name: str | None = None
    gen_stats: GenStats | None = None
    rating: Rating | None = None
    variant_count: int = 1
    created_at: str | None = None
    edited_at: str | None = None


class ChatTurn(BaseModel):
    """Một message gửi cho LLM."""

    role: Literal["system", "user", "assistant"]
    content: str


class LoreUse(BaseModel):
    """Phase 4: một mục thế giới đã vào prompt (ghi trong BuiltPrompt và snapshot)."""

    entry_id: int
    title: str
    slot: Literal["carried", "fresh"]
    tokens: int


class BuiltPrompt(BaseModel):
    messages: list[ChatTurn]
    stop: list[str]
    options: dict[str, Any] = Field(description="Tuỳ chọn Ollama: num_ctx, num_predict, temperature, ...")
    token_estimate: dict[str, int] = Field(default_factory=dict, description="Ước lượng token theo khối: A, B, C, E, F, total")
    dropped_turns: int = 0
    # Phase 3b: tóm tắt tự động đã đưa vào khối C bao phủ tới lượt này (None = không có tóm tắt).
    summary_upto_turn: int | None = None
    # Phase 4: đầu message user cuối mà prefill gửi trước được (dòng mở + mục carried, docs/phase4.md §6.5);
    # None khi không có mục carried. `open_last`: message cuối là lượt user còn mở (chỉ prefill dùng).
    lore_head: str | None = None
    open_last: bool = False
    lore_used: list[LoreUse] = Field(default_factory=list)


# ---- Lyris design (Phase 2b) -------------------------------------------------------------------


class AppSettings(BaseModel):
    """Cài đặt chung của app (bảng app_settings)."""

    default_persona_id: int | None = Field(default=None, description="Persona dùng mặc định cho story mới")
    default_chat_model: str | None = Field(default=None, description="Model Ollama cho story mới; None = Settings.chat_model")


EmotionKey = Literal["affection", "trust", "attraction", "obsession", "fear", "aversion"]
# Thứ tự theo DESIGN.md §3.3.
EMOTION_KEYS: tuple[EmotionKey, ...] = ("affection", "trust", "attraction", "obsession", "fear", "aversion")
# Điểm xuất phát khi card không đặt extensions.lyris.initial_relationship (giống frontend lib/cardForm.ts).
DEFAULT_INITIAL_RELATIONSHIP: dict[str, int] = {
    "affection": 30, "trust": 30, "attraction": 10, "obsession": 0, "fear": 0, "aversion": 20,
}
MAX_DELTA = 5  # mỗi lượt, mỗi chỉ số đổi tối đa ±5


class RelationshipValues(BaseModel):
    """Sáu chỉ số cảm xúc của nhân vật AI với người chơi, 0-100."""

    affection: int = Field(ge=0, le=100)
    trust: int = Field(ge=0, le=100)
    attraction: int = Field(ge=0, le=100)
    obsession: int = Field(ge=0, le=100)
    fear: int = Field(ge=0, le=100)
    aversion: int = Field(ge=0, le=100)


class RelationshipState(RelationshipValues):
    """Ma trận 6 cảm xúc (0-100) và chỉ dẫn diễn xuất (lyris/state/directive.py)."""

    directive: str | None = None


class RelationshipDelta(BaseModel):
    """Thay đổi của một lượt (state_events kind 'relationship_delta'). Mỗi giá trị trong [-MAX_DELTA, MAX_DELTA]."""

    affection: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)
    trust: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)
    attraction: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)
    obsession: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)
    fear: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)
    aversion: int = Field(default=0, ge=-MAX_DELTA, le=MAX_DELTA)


class SceneState(BaseModel):
    """Cảnh hiện tại theo luồng trích xuất (state_events kind 'scene'). None = chưa biết."""

    location: str | None = None
    time: str | None = Field(default=None, description='Thời điểm trong truyện, ví dụ "Chiều tối"')


MemoryKind = Literal["memory", "fact"]


class MemoryItem(BaseModel):
    """Một ký ức (sự việc của một lượt) hoặc một fact (sự thật bền vững). Bảng `memories`.

    Thuộc về message assistant đã sinh ra nó: message bị xoá thì ký ức mất (CASCADE); message không còn
    active (đã regenerate sang phiên bản khác) thì ký ức bị bỏ qua khi đọc.
    """

    id: int | None = None
    story_id: int
    message_id: int
    turn_index: int
    kind: MemoryKind
    text: str
    subject: str | None = Field(default=None, description="fact: nói về ai/cái gì")
    importance: int = Field(default=3, ge=1, le=5)
    created_at: str | None = None


class FactDraft(BaseModel):
    subject: str
    text: str


class ExtractionResult(BaseModel):
    """Kết quả đã kiểm tra của một lời gọi trích xuất cho một lượt trả lời (lyris/state/extract.py)."""

    relationship_delta: RelationshipDelta = Field(default_factory=RelationshipDelta)
    scene: SceneState = Field(default_factory=SceneState, description="None ở trường nào = không đổi")
    memory: str | None = Field(default=None, description="Một câu: sự việc đáng nhớ của lượt; None nếu không có")
    memory_importance: int = Field(default=3, ge=1, le=5)
    facts: list[FactDraft] = Field(default_factory=list, description="0-3 fact mới")
    suggestions: list[str] = Field(default_factory=list, description="0-3 gợi ý cho lượt tiếp của người chơi")


class MemoryHit(BaseModel):
    """Một ký ức/fact tìm được cho lượt sắp viết (lyris/memory/retrieval.py), đã xếp hạng."""

    memory_id: int
    turn_index: int
    kind: MemoryKind
    text: str
    score: float = 0.0


class SummaryPoint(BaseModel):
    """Một mốc tóm tắt tự động (event 'summary'): tóm tắt dồn mọi lượt tới `upto_turn`."""

    text: str
    upto_turn: int


class PromptState(BaseModel):
    """Phần state đưa vào prompt (builder.build_prompt(..., state=)). Mọi trường tuỳ chọn.

    - summary: tóm tắt tự động những lượt đã rơi khỏi cửa sổ (khối C).
    - directive: chỉ dẫn diễn xuất từ 6 chỉ số (khối F). Không bao giờ có số thô.
    - scene: cảnh hiện tại (khối F).
    - memories: ứng viên đã xếp hạng; builder chỉ giữ kind 'memory' có turn_index nằm trước cửa sổ lịch sử
      (lượt trong cửa sổ model đã thấy), fact thì giữ luôn; tối đa MAX_PROMPT_MEMORIES + MAX_PROMPT_FACTS.
    """

    summary: str | None = None
    directive: str | None = None
    scene: SceneState | None = None
    memories: list[MemoryHit] = Field(default_factory=list)
    # Phase 3b: mọi mốc tóm tắt active (theo upto_turn tăng dần). Có thì builder bỏ qua `summary` và chọn
    # mốc mới nhất nằm hẳn trước cửa sổ lịch sử, nên khối C chỉ đổi khi cửa sổ dịch theo khúc
    # (docs/phase3.md §10). Rỗng = dùng `summary` như Phase 3.
    summaries: list[SummaryPoint] = Field(default_factory=list)


MAX_PROMPT_MEMORIES = 3
MAX_PROMPT_FACTS = 3


class Moment(BaseModel):
    """Banner "Khoảnh khắc" trong chat (Phase 8: director)."""

    text: str
    effect: str | None = Field(default=None, description='Ví dụ "+Thương mến"')


MemorySearch = Literal["keyword", "hybrid"]


class StoryExtras(BaseModel):
    """Dữ liệu phụ của một story cho giao diện (GET /api/stories/{id}/extras)."""

    relationship: RelationshipState | None = None
    suggestions: list[str] = Field(
        default_factory=list, description="3 gợi ý trả lời nhanh; chỉ khi tin active cuối là của nhân vật"
    )
    moment: Moment | None = None  # Phase 8
    lore_tags: list[str] = Field(
        default_factory=list,
        description="Phase 4: tên các mục thế giới đã mở khoá mà người chơi được xem (mọi người biết + chỉ bạn biết), mới nhất trước",
    )
    lore_available: bool = Field(default=False, description="Phase 4: card của story có ít nhất một mục thế giới đang bật")
    lore_count: int = Field(
        default=0, description="Phase 4: số mục đã mở khoá, kể cả mục chỉ nhân vật biết (chữ ký để tải lại ngăn cảm xúc)"
    )
    location: str | None = None
    in_world_time: str | None = None
    # Phase 3
    memories: list[MemoryItem] = Field(default_factory=list, description="Ký ức + fact active, mới nhất trước, tối đa 50")
    pending: bool = Field(default=False, description="Còn job trích xuất/tóm tắt đang chờ hoặc đang chạy cho story này")
    unprocessed_turns: int = Field(
        default=0, description="Số lượt của nhân vật active (kể cả lời mở đầu, Phase 3b) chưa từng được trích xuất; > 0 thì drawer mời dựng lại"
    )
    memory_search: MemorySearch = "keyword"
    summary: str | None = Field(default=None, description="Tóm tắt tự động hiện tại (nếu có)")


class TimelineScene(BaseModel):
    location: str | None = None
    time: str | None = None


class TimelineEntry(BaseModel):
    """Một lượt có state trong dòng thời gian của story (GET /api/stories/{id}/timeline, Phase 3b)."""

    turn_index: int
    message_id: int
    mode: Mode
    created_at: str | None = None
    memory: str | None = Field(default=None, description="Câu ký ức của lượt (kind 'memory'); None nếu không có")
    facts: list[str] = Field(default_factory=list, description="Fact ghi được ở lượt này")
    delta: dict[str, int] = Field(default_factory=dict, description="Thay đổi cảm xúc khác 0, theo thứ tự EMOTION_KEYS")
    scene: TimelineScene | None = Field(default=None, description="Cảnh đổi ở lượt này (trường None = không đổi)")


class SuggestionsOut(BaseModel):
    """Gợi ý trả lời theo yêu cầu (POST /api/stories/{id}/suggestions, Phase 3b)."""

    items: list[str]


class DominantEmotion(BaseModel):
    """Chip cảm xúc nổi bật trên thẻ story ở hub."""

    key: EmotionKey
    value: int = Field(ge=0, le=100)


class TemplateInfo(BaseModel):
    """Nhân vật mẫu đi kèm app (seed/templates/*.json), hiện ở trang Khám Phá."""

    slug: str
    featured: bool = False
    vibes: list[str] = Field(default_factory=list, description='Ví dụ ["Chữa lành", "Dịu dàng"]')
    card: CharacterCard
    installed_card_id: int | None = None


class LoreStatus(BaseModel):
    """GET /api/lore/status. Phase 4: lore nằm trong DB theo từng card (không còn thư mục world_wiki):
    `enabled` true, `entries` = số mục của account, `files` 0, `dir` ""."""

    enabled: bool = False
    dir: str = "world_wiki"
    files: int = 0
    entries: int = 0
    last_sync: str | None = None


# ---- Phase 4: sổ thế giới (docs/phase4.md §2) ---------------------------------------------------

LoreCategory = Literal["lore", "character", "place"]
LoreSource = Literal["manual", "world_md", "card_book"]
# Ai biết, suy ra từ known_by so với tên nhân vật của card:
#   everyone: có "*";  character: có tên nhân vật (hoặc "{{char}}");  player: chỉ "{{user}}";
#   others: chỉ tên người khác (nhân vật phụ). Thứ tự xét: everyone > character > player > others.
LoreAudience = Literal["everyone", "character", "player", "others"]
LoreSlot = Literal["carried", "fresh", "unsent"]

MAX_LORE_TITLE = 120
MAX_LORE_KEYS = 32
MAX_LORE_KEY_CHARS = 80
MAX_LORE_KNOWN_BY = 8
MAX_LORE_CONTENT = 4000
MAX_LORE_ENTRIES_PER_CARD = 500
MAX_LORE_IMPORT_BYTES = 512_000


class LoreEntry(BaseModel):
    """Một mục thế giới của một card (bảng lore_entries)."""

    id: int | None = None
    card_id: int
    slug: str
    title: str
    category: LoreCategory = "lore"
    keys: list[str] = Field(default_factory=list)
    known_by: list[str] = Field(default_factory=lambda: ["*"])
    content: str = ""
    source: LoreSource = "manual"
    edited: bool = False
    enabled: bool = True
    priority: int = 0
    position: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class LoreEntryIn(BaseModel):
    """Body tạo/sửa (POST, PUT). Backend làm sạch: cắt khoảng trắng, bỏ khoá rỗng và trùng."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=MAX_LORE_TITLE)
    category: LoreCategory = "lore"
    keys: list[str] = Field(default_factory=list)
    known_by: list[str] = Field(default_factory=lambda: ["*"])
    content: str = Field(default="", max_length=MAX_LORE_CONTENT)
    enabled: bool = True
    priority: int = Field(default=0, ge=-100, le=100)


class LorePatch(BaseModel):
    """PATCH: bật/tắt hoặc đổi chỗ, không tính là "đã sửa" (edited giữ nguyên)."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    position: int | None = Field(default=None, ge=0)


class LoreEntryOut(LoreEntry):
    audience: LoreAudience
    # Câu nhắc dễ hiểu cho Studio, ví dụ 'Từ khoá “mẹ” chỉ có một chữ nên sẽ gợi rất thường xuyên.'
    warnings: list[str] = Field(default_factory=list)


class LoreImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    filename: str | None = Field(default=None, max_length=200)
    dry_run: bool = False
    # Mặc định chỉ thêm/cập nhật. Xoá mục không còn trong file chỉ khi người dùng tự đánh dấu ở bước xem trước
    # (card có thể có hai file thế giới; nhập file thứ hai không được xoá mục của file thứ nhất).
    delete_missing: bool = False


class LoreBookImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dry_run: bool = False


# keep_missing: mục từ file, không còn trong file mới, giữ lại vì delete_missing false.
# skip_removed: mục có trong file nhưng người dùng đã xoá trong Studio (bia mộ), không thêm lại.
LoreImportAction = Literal["create", "update", "unchanged", "keep_edited", "delete", "keep_missing", "skip_removed"]


class LoreImportItem(BaseModel):
    slug: str
    title: str
    category: LoreCategory
    action: LoreImportAction


class LoreImportResult(BaseModel):
    dry_run: bool
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    kept_edited: int = 0  # mục từ file đã được sửa tay: không ghi đè, không xoá
    deleted: int = 0  # mục từ file (chưa sửa tay) không còn trong file mới, chỉ khi delete_missing
    missing: int = 0  # mục từ file không còn trong file mới (xoá được nếu bật delete_missing)
    skipped_removed: int = 0  # mục bạn đã xoá, không thêm lại
    player_only: list[str] = Field(default_factory=list)  # người/nơi nhập là "Chỉ bạn" (§4.3)
    dropped_sentences: list[str] = Field(default_factory=list)  # "Tên mục: câu…" (≤ 50)
    items: list[LoreImportItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LoreSnippet(BaseModel):
    """Một mục đã chọn cho prompt của lượt này (lyris/lore/select.py)."""

    entry_id: int
    title: str
    text: str  # nội dung đã thay {{user}}/{{char}}, gộp dòng, cắt ≤ MAX_LORE_ITEM_CHARS
    private: bool  # chỉ nhân vật biết: prompt dặn không tự kể ra
    tokens: int
    slot: Literal["carried", "fresh"]


class PromptLore(BaseModel):
    """Lore đưa vào build_prompt. `reserve_tokens` = phần dự phòng cố định cho khối lore (0 = card không có
    mục nào gửi được cho model; khi đó prompt giống hệt Phase 3)."""

    carried: list[LoreSnippet] = Field(default_factory=list)
    fresh: list[LoreSnippet] = Field(default_factory=list)
    reserve_tokens: int = 0
    unsent_ids: list[int] = Field(default_factory=list)  # khớp nhưng không gửi (ghi lore_hits slot 'unsent')


class UnlockedLore(BaseModel):
    """Một mục đã mở khoá trong story (GET /api/stories/{id}/lore)."""

    entry_id: int
    title: str
    category: LoreCategory
    audience: Literal["everyone", "character", "player"]  # "others" không bao giờ trả về
    content: str  # đã thay {{user}} = tên persona, {{char}} = tên nhân vật
    first_turn: int  # turn_index nội bộ, chỉ để nhảy tới; giao diện KHÔNG in số này
    last_turn: int
    turns: int  # số lượt đã gợi ra


class StoryLore(BaseModel):
    available: bool  # card có ít nhất một mục đang bật
    can_edit: bool  # card thuộc account: giao diện mời "Thêm trong Studio"
    card_id: int
    entries: list[UnlockedLore]  # mới gợi ra gần nhất trước


class LoreSummary(BaseModel):
    """Phần "Thế giới" ở hồ sơ nhân vật: chỉ tên người và nơi chốn ai cũng biết, không nội dung."""

    total: int  # mục đang bật
    people: list[str]  # category 'character', audience everyone, tối đa 8
    places: list[str]  # category 'place', audience everyone, tối đa 8
    people_more: int = 0  # số tên người không liệt kê (giao diện in "+N")
    places_more: int = 0


class OllamaModelInfo(BaseModel):
    name: str
    size_gb: float | None = None
    parameter_size: str | None = None
    quantization: str | None = None


class LoadedModelInfo(BaseModel):
    name: str
    size_gb: float | None = None
    expires_at: str | None = None


class SystemInfo(BaseModel):
    """Trạng thái máy Mac và Ollama cho modal "Persona & Máy chủ". Lỗi từng phần thì phần đó là None/rỗng."""

    ollama_reachable: bool
    ollama_version: str | None = None
    ollama_error: str | None = None
    models: list[OllamaModelInfo] = Field(default_factory=list)
    loaded: list[LoadedModelInfo] = Field(default_factory=list)
    memory_total_gb: float | None = None
    memory_used_gb: float | None = None
    on_battery: bool | None = None
    low_power_mode: bool | None = None
    kv_cache_type: str | None = None
    flash_attention: bool | None = None
    num_parallel: int | None = None
    max_loaded_models: int | None = None
    chat_model_default: str
    # Phase 3: cách tìm ký ức (dòng "Ký ức" trong sheet Tài khoản) và tên embed model đã cấu hình
    # (LYRIS_EMBED_MODEL), để gợi ý `ollama pull <tên>` khi Ollama chưa có nó.
    memory_search: MemorySearch = "keyword"
    embed_model: str | None = None


# ---- Phase 2c: account (docs/accounts.md) -----------------------------------------------------


AccountRole = Literal["owner", "member"]
AccountStatus = Literal["active", "disabled"]


class Account(BaseModel):
    """Người dùng Lyris bên ngoài story. Sở hữu persona, card, story (và sau này bài đăng, bình luận)."""

    id: int | None = None
    uid: str | None = None
    handle: str = Field(description="3-30 ký tự a-z 0-9 _ . ; không đầu/cuối bằng dấu chấm; duy nhất, không phân biệt hoa thường")
    display_name: str
    bio: str = ""
    avatar: str | None = None
    banner: str | None = None
    profile_completed: bool = Field(default=False, description="False cho tới khi người dùng tự lưu profile lần đầu")
    created_at: str | None = None
    # Phase 4b (docs/auth.md §1): vai trò, trạng thái, đang dùng mật khẩu tạm.
    role: AccountRole = "member"
    status: AccountStatus = "active"
    must_change_password: bool = False


class AccountUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    handle: str = Field(min_length=3, max_length=30)
    bio: str = Field(default="", max_length=500)
