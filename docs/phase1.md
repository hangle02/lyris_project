# Phase 1: thiết kế (cây file, interface, API)

Mục tiêu: chat được với Lạc Dương trên trình duyệt Mac, dùng `gemma4:12b` gốc qua Ollama; mọi lượt được lưu (kèm prompt snapshot, đánh giá, lịch sử sửa) để train sau. Fine-tune hoãn lại (xem kết quả Phase 0 trong `plan.md`).

## Phạm vi

Có trong Phase 1:
- Một nhân vật seed (Lạc Dương) + persona seed (Lâm Vãn), nhiều story song song (mỗi story = một cuộc chat riêng).
- Story Mode và DM Mode, đổi được giữa chừng.
- Gửi, stream, dừng giữa chừng; regenerate lượt cuối và lật qua lại các variant; sửa bất kỳ tin nhắn; xoá từ một lượt trở về sau ("tua lại"); thích/chê.
- Chỉ đạo ẩn `((...))` và việc người chơi viết hành động cho nhân vật AI.
- Prompt builder khối A, B, C, E, F (F = lời nhắc bám sát lượt người chơi + chỉ đạo).
- Harness `run_eval.py` với 5 kịch bản: format, xưng hô trong dẫn truyện, godmodding (LLM judge), bám sát lượt người chơi (LLM judge), tốc độ.

Chưa có (phase sau): Character Studio UI, quan hệ/trí nhớ/luồng nền (Phase 3), lorebook (Phase 4), train (Phase 5), iPhone (Phase 6).

Quy ước "regenerate, sửa, xoá bất kỳ lượt nào" ở Phase 1:
- **Sửa**: mọi tin nhắn.
- **Xoá**: xoá lượt được chọn và mọi lượt sau (tua lại). Muốn viết lại từ một lượt cũ thì xoá từ đó rồi gửi tiếp.
- **Regenerate / lật variant**: chỉ lượt cuối, và lượt cuối phải là của AI, lượt ngay trước là của người chơi. Lời mở đầu (lượt 0) không regenerate được.

## Cây file và người phụ trách

```
backend/
  pyproject.toml                (có sẵn)
  lyris/
    models.py                   (có sẵn, HỢP ĐỒNG) kiểu dữ liệu chung
    config.py                   [core] Settings từ biến môi trường
    db/
      migrations/0001_init.sql  (có sẵn, HỢP ĐỒNG) schema
      connection.py             [core] connect(), migrate()
      repo.py                   [core] class Repo, NotFound
    seed/
      __init__.py               [core] ensure_seed()
      lac_duong.json            [core] card
      lam_van.json              [core] persona
      default_story.json        [core] thiết lập story mặc định
    llm/
      base.py                   (có sẵn, HỢP ĐỒNG) LLMClient, TextDelta, Done, LLMError, ParsedDelta
      ollama.py                 [llm] OllamaClient
      fake.py                   [llm] FakeLLM cho test
      thought.py                [llm] ThoughtStreamParser, split_thought()
    prompt/
      tokens.py                 [prompt] estimate_tokens()
      directives.py             [prompt] extract_directives()
      templates/vi.py, en.py    [prompt] văn bản luật theo ngôn ngữ và mode
      styles/trung_hien_dai.md  [prompt] style profile
      builder.py                [prompt] build_prompt(), load_style()
    chat/
      service.py                [api] ChatService, ChatEvent, Busy
    api/
      app.py                    [api] create_app(), app
      routes.py                 [api] các endpoint
      sse.py                    [api] định dạng SSE
  tests/
    conftest.py                 [core] fixture: repo tạm, repo đã seed
    test_repo.py                [core]
    test_thought.py, test_ollama_client.py   [llm]
    test_prompt.py              [prompt]
    test_api.py                 [api]
    test_harness_checks.py      [harness]
frontend/                       [frontend] Vite + React + TypeScript + Tailwind
harness/
  bakeoff.py                    (có sẵn) sửa để import từ checks.py [harness]
  checks.py                     [harness] các kiểm tra máy
  run_eval.py                   [harness]
  scenarios/*.yaml              [harness] 5 kịch bản
scripts/
  dev.sh                        [api] chạy backend + frontend
  ollama-env.sh                 [core] tự đặt biến môi trường Ollama khi đăng nhập
.gitignore                      [core]
```

Mỗi người phụ trách chỉ tạo/sửa file của mình. Không sửa file HỢP ĐỒNG; nếu thấy hợp đồng sai, ghi vào báo cáo.

## Môi trường

- Backend: `backend/.venv` (Python 3.12, đã cài fastapi, uvicorn, httpx, pydantic, pyyaml, pytest, pytest-asyncio; package `lyris` cài dạng editable). Chạy test: `cd backend && .venv/bin/pytest -q`. Không dùng `python3` của hệ thống (3.15).
- Thêm dependency: `cd backend && uv add <pkg>` (hạn chế; hỏi trong báo cáo nếu cần).
- Ollama ở `http://127.0.0.1:11434`, có `gemma4:12b` (chat) và `gemma4:e4b` (judge). Máy 24GB RAM: không chạy nhiều lời gọi Ollama song song ngoài mức cần.
- Frontend: Node 22, npm.

## Interface từng module

### config.py
```python
@dataclass(frozen=True)
class Settings:
    db_path: Path            # LYRIS_DB_PATH, mặc định <repo>/data/lyris.db
    ollama_url: str          # OLLAMA_URL, mặc định http://127.0.0.1:11434
    chat_model: str          # LYRIS_CHAT_MODEL, mặc định gemma4:12b
    num_ctx: int             # LYRIS_NUM_CTX, mặc định 8192
def get_settings() -> Settings
REPO_ROOT: Path              # thư mục gốc dự án
```

### db/connection.py
```python
def connect(path: Path | str) -> sqlite3.Connection
    # check_same_thread=False, row_factory=sqlite3.Row, PRAGMA foreign_keys=ON, journal_mode=WAL
    # ":memory:" được phép; tạo thư mục cha nếu chưa có
def migrate(conn) -> int
    # áp dụng migrations/NNNN_*.sql có số > PRAGMA user_version, mỗi file một transaction, trả version mới
```

### db/repo.py
```python
class NotFound(LookupError): ...
class Repo:
    def __init__(self, conn: sqlite3.Connection)   # mọi method khoá bằng threading.RLock
    def create_card(self, card: CharacterCard) -> CharacterCard
    def get_card(self, card_id: int) -> CharacterCard
    def list_cards(self) -> list[CharacterCard]
    def create_persona(self, p: Persona) -> Persona
    def get_persona(self, persona_id: int) -> Persona
    def create_story(self, story: Story) -> Story
    def get_story(self, story_id: int) -> Story
    def list_stories(self) -> list[Story]               # mới nhất trước
    def update_story(self, story_id: int, **fields) -> Story
        # cho phép: title, scenario, mode, language, relationship_type, pov, narration_pronouns, model_name, scene_summary
    def active_messages(self, story_id: int) -> list[Message]   # theo turn_index; có variant_count, rating
    def get_message(self, message_id: int) -> Message
    def last_turn_index(self, story_id: int) -> int | None
    def next_turn_index(self, story_id: int) -> int
    def insert_message(self, msg: Message) -> Message   # lượt mới: turn_index do msg cung cấp, variant 0, active
    def add_variant(self, msg: Message) -> Message      # cùng story/turn; variant_index = max+1; tắt các variant khác; active
    def select_variant(self, story_id: int, turn_index: int, variant_index: int) -> Message
    def edit_message(self, message_id: int, *, raw_content: str, visible_content: str,
                     thought: str | None, directive: str | None) -> Message
        # ghi message_edits(before, after), đặt edited_at; model_output giữ nguyên
    def truncate_from(self, story_id: int, turn_index: int) -> int   # xoá mọi variant của các lượt >= turn_index
    def set_feedback(self, message_id: int, rating: Rating | None, note: str | None = None) -> Message
```
Message trả về không bao giờ thiếu `variant_count`/`rating`. `prompt_snapshot`, `gen_stats` là JSON trong DB, object trong model.

### seed
- `ensure_seed(repo) -> int`: nếu chưa có card thì tạo card từ `lac_duong.json`, persona từ `lam_van.json`; nếu chưa có story thì tạo story từ `default_story.json` và chèn lời mở đầu (`card.greeting`) làm message assistant lượt 0 (tách Thought bằng `split_thought`). Trả id story mới nhất.
- `create_default_story(repo, title: str | None = None) -> Story`: tạo story mới với card/persona seed + lời mở đầu.
- Nội dung nhân vật lấy theo `harness/prompts.json` (Lạc Dương nam 20 tuổi, sinh viên, lạnh lùng với người ngoài, chiều chuộng Lâm Vãn; Lâm Vãn nữ 20 tuổi, lạc quan; thanh mai trúc mã). Story: `relationship_type=het`, `pov=third`, đại từ dẫn truyện anh/cô, xưng hô tớ/cậu, biệt danh Vãn Vãn, A Vãn, style `trung_hien_dai`.

### llm/thought.py
```python
class ThoughtStreamParser:
    def feed(self, delta: str) -> list[ParsedDelta]
    def flush(self) -> list[ParsedDelta]
def split_thought(raw: str) -> tuple[str, str | None]   # (visible, thought)
```
- Thẻ mở: `[Thought:` không phân biệt hoa thường, cho phép khoảng trắng (`[ thought :`). Kết thúc ở `]` đầu tiên; nếu chưa gặp `]` thì ở chỗ ngắt đoạn đầu tiên (`\n`, space/tab tuỳ ý, `\n` — một dòng trống) hoặc hết văn bản. Một `\n` đơn trong Thought không kết thúc nó; phần sau chỗ ngắt đoạn lại là chữ hiển thị.
- Thought kết thúc không có `]`: bỏ một dấu ngoặc kép lẻ ở cuối (`"` lẻ số lần, `”` nhiều hơn `“`, hoặc `“`) cùng khoảng trắng quanh nó. Quy ước này lặp y hệt ở `splitSegments` (frontend/src/lib/text.ts) và harness/checks.py (harness vẫn báo "Thought chưa đóng").
- Thẻ có thể bị cắt giữa các chunk bất kỳ: giữ lại phần có thể là tiền tố của thẻ, không phát ra sớm; nhưng không giữ quá lâu (chữ `[` thường phải được phát ra ngay khi chắc chắn không phải thẻ).
- Nhiều Thought → nối bằng `\n`. Thought chưa đóng khi hết stream → phần còn lại (tới dòng trống đầu tiên) là thought.
- `visible` bỏ khoảng trắng thừa ở đầu/cuối và gộp ≥3 dòng trống thành 2. Kết quả của `split_thought(raw)` phải khớp với ghép các delta của parser.

### llm/ollama.py
```python
class OllamaClient:  # thoả LLMClient
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 600)
    async def chat_stream(self, model, messages, *, stop, options) -> AsyncIterator[LLMEvent]
    async def list_models(self) -> list[str]     # cho /api/health; LLMError nếu không kết nối được
```
- POST `/api/chat` với `{"model", "messages", "stream": true, "think": false, "keep_alive": "30m", "options": {**options, "stop": stop}}`; đọc NDJSON. Nếu HTTP 400 vì model không hỗ trợ `think`, thử lại không có trường `think`.
- Done.stats: `ttft_ms` đo phía client, `total_ms`, `prompt_tokens=prompt_eval_count`, `output_tokens=eval_count`, `tok_per_s=eval_count/eval_duration`, `done_reason`.
- Lỗi kết nối / 404 model / HTTP lỗi → `LLMError` với thông điệp tiếng Việt dễ hiểu (ví dụ "Không kết nối được Ollama ở ...; hãy mở app Ollama").
- Đóng generator giữa chừng phải đóng response HTTP (dùng `async with client.stream(...)`).

### llm/fake.py
```python
class FakeLLM:  # thoả LLMClient
    def __init__(self, replies: list[str] | None = None, chunk_size: int = 7, delay: float = 0.0, error: Exception | None = None)
    calls: list[dict]   # lưu model/messages/stop/options của mỗi lần gọi
```
Mỗi lần gọi lấy reply kế tiếp (lặp lại cái cuối nếu hết), chia thành chunk cỡ `chunk_size`, rồi Done.

### prompt/
```python
def estimate_tokens(text: str) -> int      # ceil(len(text) / 3.0) + 4; đo thực tế Gemma 4 tiếng Việt ~3.4 ký tự/token
def extract_directives(text: str) -> tuple[str, str | None]
    # tìm mọi ((...)) (cho phép xuống dòng); trả (văn bản đã bỏ chỉ đạo và dọn khoảng trắng, các chỉ đạo nối bằng "; " hoặc None)
def load_style(name: str) -> str           # đọc styles/<name>.md; ValueError nếu không có
@dataclass(frozen=True)
class PromptBudget:
    num_ctx: int = 8192
    reply_tokens_story: int = 900
    reply_tokens_dm: int = 200
    safety_tokens: int = 256
def build_prompt(card, persona, story, history: list[Message], *, budget: PromptBudget | None = None) -> BuiltPrompt
```
`build_prompt`:
- `history` = các message active theo thứ tự; message cuối phải là `user` (ValueError nếu không). Mode lấy từ `story.mode`.
- messages[0] = system = A + B + C (cố định giữa các lượt để Ollama tái dùng cache).
  - **A** luật theo `story.language` + `story.mode` (templates/vi.py, en.py), gồm: thiết lập (giới tính hai bên, kiểu quan hệ, ngôi kể, đại từ dẫn truyện), và luật. Bám sát nguyên văn đã kiểm chứng trong `harness/prompts.json` (systems `vi_story`, `vi_dm`, `en_story`; bản `vi_story` đạt 0/15 lỗi), chỉ thay tên/đại từ/xưng hô bằng tham số.
  - **B** card (tên, giới tính, tuổi/mô tả, tính cách, ngoại hình, hoàn cảnh, mục tiêu, bí mật, cách nói, ví dụ hội thoại nếu có) + persona + xưng hô (`address_terms`) + nội dung style profile.
  - **C** bối cảnh (`story.scenario`) + tóm tắt cảnh (`story.scene_summary` nếu có).
- **E** lịch sử: user → `visible_content` (đã bỏ `((...))`); assistant → `raw_content` (giữ Thought để model giữ format). Nếu message đầu tiên sau system là assistant (lời mở đầu), chèn trước một user giả `"(Câu chuyện bắt đầu.)"` / `"(The story begins.)"`. Gộp các message liền nhau cùng role bằng `\n\n`. Bỏ lượt cũ nhất trước cho đến khi tổng ước lượng ≤ `num_ctx - reply_tokens - safety_tokens`; không bao giờ bỏ message user cuối. Ghi số lượt bị bỏ vào `dropped_turns`.
- **F** nối vào cuối message user cuối, sau `\n\n`, dạng một khối ghi chú cho người dẫn truyện (không phải lời người chơi): tiếp nối trực tiếp từ đúng điều người chơi vừa viết; nếu có `directive` của message đó thì ghi "Chỉ đạo của người chơi cho lượt này: ..." và nhắc không in lại; ở Story Mode nhắc ngắn luật Thought theo `story.thought_style` (inline: 2-3 dòng rải giữa truyện, không liền nhau; end: đúng một dòng ở cuối) và đại từ dẫn truyện.
- `stop`: `[f"{persona.name}:", f"\n{persona.name}:", "\nPlayer:", "\nUser:"]`.
- `options`: `num_ctx`, `num_predict` (900 story / 200 dm), `temperature` 0.8, `top_p` 0.95.
- `token_estimate`: A, B, C, E, F, total.

Luật nội dung bắt buộc (quyết định của người dùng, phải có trong A/F):
1. Giới tính, kiểu quan hệ (het: nam - nữ, ngôn tình; bl: nam - nam, đam mỹ; gl: nữ - nữ, bách hợp; none: không lãng mạn), ngôi kể, đại từ dẫn truyện.
2. Xưng hô (`address_terms`) chỉ dùng trong lời thoại và Thought; phần dẫn truyện dùng đại từ dẫn truyện hoặc tên. Ngôi thứ ba: người dẫn truyện không xưng "tôi"/"tớ". Ngôi thứ nhất: nhân vật AI kể, tự gọi mình bằng `narration_pronouns.character` (ví dụ "tôi"), gọi người chơi bằng `narration_pronouns.player`.
3. Văn phong theo style profile (với `trung_hien_dai`: văn phong ngôn tình Trung Quốc dịch sang tiếng Việt, tên Hán Việt, đời sống Trung Quốc; với người ngoài gọi "bạn học + họ", "học trưởng", "học tỷ" và xưng "tôi").
4. Story Mode: văn tiểu thuyết, dẫn truyện và lời thoại 120-200 từ (không tính Thought); Thought của nhân vật AI theo `story.thought_style` (mặc định inline: 2-3 dòng, mỗi dòng 2-3 câu, rải giữa truyện; end: một dòng 2-4 câu ở cuối). Viết tiếng Việt tự nhiên, tả chi tiết cụ thể, không tả "bầu không khí". DM Mode: tin nhắn 1-3 câu (có thể tách thành vài tin, mỗi tin một dòng), không mô tả hành động, không dẫn truyện, không Thought.
5. Người chơi điều khiển persona: được phản ứng với mọi điều người chơi viết và mô tả lại qua mắt nhân vật AI; được tả thêm trạng thái nhỏ nhìn thấy/cảm nhận được (má ửng đỏ, tay lạnh, chóp mũi đỏ vì gió) nếu hợp với điều người chơi viết; không viết lời thoại, hành động có chủ đích, suy nghĩ hay quyết định cho persona; dừng lượt ở chỗ cần người chơi đáp lại.
6. Lượt của người chơi là sự thật: tiếp nối trực tiếp, không bỏ qua, không tự đổi cảnh hay lái sang chuyện khác.
7. Người chơi là tác giả: nếu người chơi viết hành động cho nhân vật AI, hoặc ghi `((...))`, làm theo nhưng giữ giọng nhân vật; không in lại `((...))`.
8. Chỉ dùng ngôn ngữ của story.

### chat/service.py
```python
@dataclass(frozen=True)
class ChatEvent:
    name: Literal["user_message", "start", "delta", "done", "error"]
    data: dict
class Busy(RuntimeError): ...      # story đang sinh câu trả lời khác
class InvalidOperation(ValueError): ...
class ChatService:
    def __init__(self, repo: Repo, llm: LLMClient)
    def send(self, story_id: int, text: str) -> AsyncIterator[ChatEvent]
        # extract_directives; text rỗng hoàn toàn (không chữ, không chỉ đạo) → InvalidOperation
        # lưu user message (lượt mới) → user_message; rồi như respond()
    def respond(self, story_id: int) -> AsyncIterator[ChatEvent]
        # trả lời message user cuối (dùng để thử lại sau lỗi); InvalidOperation nếu message cuối không phải user
    def regenerate(self, message_id: int) -> AsyncIterator[ChatEvent]
        # message phải là assistant, ở lượt cuối, lượt trước là user; tạo variant mới
```
- Khoá theo story (asyncio.Lock); đang bận → raise `Busy` ngay khi bắt đầu (trước khi yield gì).
- Thứ tự sự kiện: [`user_message` {message}] → `start` {turn_index, variant_index} → `delta` {kind, text}* → `done` {message} hoặc `error` {detail}.
- Message assistant được ghi một lần sau khi sinh xong: `raw_content = model_output = text thô`, `visible_content`/`thought` từ `split_thought`, `prompt_snapshot = BuiltPrompt.model_dump()`, `gen_stats`, `model_name = story.model_name`, `mode = story.mode`.
- Bị ngắt giữa chừng (client đóng kết nối → generator bị đóng/huỷ): nếu đã có chữ thì vẫn lưu phần đã sinh với `gen_stats.aborted = true`; rồi để ngoại lệ lan tiếp.
- LLMError → sự kiện `error` (message user vẫn giữ; người chơi bấm thử lại → `respond`).

### api (tiền tố /api, JSON; lỗi trả `{"detail": "..."}`)
| Method | Path | Body | Trả về |
|---|---|---|---|
| GET | /api/health | | `{ok, chat_model, ollama: {reachable, models, error}}` |
| GET | /api/stories | | `[StoryOut]` (Story + `card_name`, `persona_name`), mới nhất trước |
| POST | /api/stories | `{title?}` | `StoryOut` (story mới với nhân vật seed + lời mở đầu) |
| GET | /api/stories/{id} | | `{story, card, persona}` |
| PATCH | /api/stories/{id} | `{mode?, title?, scenario?}` | `Story` |
| GET | /api/stories/{id}/messages | | `[Message]` active, không kèm `prompt_snapshot` |
| POST | /api/stories/{id}/messages | `{content}` | SSE (send) |
| POST | /api/stories/{id}/reply | | SSE (respond) |
| POST | /api/messages/{id}/regenerate | | SSE |
| POST | /api/messages/{id}/variant | `{variant_index}` | `Message` (chỉ lượt cuối) |
| PATCH | /api/messages/{id} | `{content}` | `Message` (assistant: tách lại Thought; user: tách lại `((...))`) |
| DELETE | /api/messages/{id} | | `{deleted, messages: [Message]}` (tua lại từ lượt này) |
| PUT | /api/messages/{id}/feedback | `{rating: "up"\|"down"\|null, note?}` | `Message` |
| GET | /api/messages/{id}/snapshot | | prompt snapshot (gỡ lỗi) |

Mã lỗi: 404 không tìm thấy; 409 đang bận hoặc thao tác không hợp lệ (regenerate lượt không phải lượt cuối...); 422 dữ liệu sai.

SSE: `Content-Type: text/event-stream`, header `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Mỗi sự kiện:
```
event: <name>
data: <json một dòng>

```
`Message` trong sự kiện là `model_dump(mode="json", exclude={"prompt_snapshot"})`. Lỗi trước khi stream bắt đầu (404, 409 Busy/InvalidOperation) trả HTTP status bình thường, không phải SSE.

App: `create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI`; lifespan: connect + migrate + ensure_seed. `app = create_app()` ở cấp module cho uvicorn. CORS cho `http://localhost:5173` và `http://127.0.0.1:5173`.

### frontend
Vite + React 18 + TypeScript + Tailwind v4 (`@tailwindcss/vite`). Dev server 5173, proxy `/api` → `http://127.0.0.1:8000`. Giao diện tiếng Việt, nền tối, mobile-first, cột giữa tối đa khoảng 720px, font hệ thống (không tải font ngoài). `npm run build` và `npm run typecheck` phải qua.
- Mở app: GET /api/stories; chưa có thì POST; mở story mới nhất. Chọn story khác và tạo story mới từ header.
- Header: tên story, công tắc Story/DM (PATCH), chấm trạng thái Ollama (/api/health).
- Story Mode: lượt AI là khối văn xuôi toàn chiều rộng, giữ đoạn, lời thoại trong ngoặc kép hơi nổi bật; Thought thu gọn mặc định ("💭 Suy nghĩ", bấm để mở, chữ nghiêng). DM Mode: bong bóng chat AI bên trái. Lượt người chơi: bong bóng bên phải; chỉ đạo `((...))` hiện thành nhãn nhỏ mờ.
- Stream: chữ hiện dần; thought đang sinh hiện "đang nghĩ…" trong khối thu gọn.
- Lượt AI cuối: ↻ regenerate, ‹ i/n › lật variant. Mọi tin nhắn: ✎ sửa (textarea tại chỗ, Lưu/Huỷ), 🗑 xoá từ đây (hỏi xác nhận "Xoá lượt này và mọi lượt sau?"). Lượt AI: 👍 / 👎.
- Ô nhập: tự giãn, Enter gửi, Shift+Enter xuống dòng; placeholder "Viết lời nói, *hành động*, hoặc ((chỉ đạo cho AI))…"; nút Dừng khi đang sinh (AbortController).
- Lỗi: thanh báo lỗi có nút "Thử lại" (POST /reply).
- SSE qua `fetch` + đọc `ReadableStream` (EventSource không POST được).

### harness
- `checks.py`: chuyển `HAN`, `narration_only`, `auto_check` từ `bakeoff.py` sang (bakeoff import lại, hành vi không đổi); thêm `directive_leak(text)` (có `((`), `persona_line(text, persona_name)` (dòng bắt đầu bằng tên persona + `:`), `word_count`.
- `scenarios/*.yaml`, 5 kịch bản dùng nhân vật seed: mở đầu đơn giản; bẫy im lặng (godmodding); người chơi viết hành động cho Lạc Dương; chỉ đạo `((...))`; DM Mode. Mỗi kịch bản: `id`, `mode`, `history` (tuỳ chọn, list `{role, content}`), `input`, `checks` (`thought_count`, `narration_forbidden`, `max_words`...).
- `run_eval.py` (chạy bằng `backend/.venv/bin/python harness/run_eval.py --model gemma4:12b [--judge-model gemma4:e4b]`): dựng prompt bằng đúng `lyris.prompt.builder.build_prompt`, gọi `OllamaClient`; báo cáo mỗi kịch bản: TTFT, tok/s, lỗi máy, phán quyết judge (`godmodding`, `follows_player`, `reason`, gọi Ollama với `format` = JSON schema, `think: false`). Ghi `harness/results/eval-<thời gian>/report.md` + `raw.json`, in bảng tóm tắt.

## Kiểm tra cuối Phase 1
1. `cd backend && .venv/bin/pytest -q` qua hết (không cần Ollama).
2. `cd frontend && npm run build` qua.
3. `bash scripts/dev.sh`, mở http://localhost:5173, chat 20 lượt với Lạc Dương; thử sửa, xoá, regenerate, lật variant, ((chỉ đạo)), đổi DM.
4. `backend/.venv/bin/python harness/run_eval.py --model gemma4:12b` chạy hết 5 kịch bản.
