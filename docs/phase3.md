# Phase 3: State và trí nhớ

Mục tiêu (plan.md §10, Phase 3): nhân vật nhớ chuyện cũ, thái độ thay đổi theo quan hệ, regenerate/sửa/xoá không làm hỏng state. Giao diện có dữ liệu thật cho ngăn cảm xúc, gợi ý trả lời nhanh, cảnh hiện tại.

Kiểu dữ liệu dùng chung đã có trong `backend/lyris/models.py` (khối "Phase 3": `EMOTION_KEYS`, `DEFAULT_INITIAL_RELATIONSHIP`, `MAX_DELTA`, `RelationshipValues`, `RelationshipState`, `RelationshipDelta`, `SceneState`, `MemoryItem`, `FactDraft`, `ExtractionResult`, `MemoryHit`, `PromptState`, `MAX_PROMPT_MEMORIES`, `MAX_PROMPT_FACTS`, `StoryExtras`, `DominantEmotion`). Đây là hợp đồng; muốn đổi thì ghi lại lý do ở cuối file này.

## 0. Ràng buộc phần cứng (đã đo 2026-11-13)

- Ollama đang nạp `gemma4:12b` chiếm khoảng 16GB (runner mlx, `OLLAMA_NUM_PARALLEL=2`, context 8192). Nạp thêm `gemma4:e4b` (9.5GB) sẽ đẩy model chat ra khỏi RAM 24GB. **Vì vậy mọi lời gọi nền (trích xuất, tóm tắt) dùng chính model chat của story**, chạy ở slot thứ hai. Cấu hình được bằng `LYRIS_EXTRACT_MODEL` (mặc định: model của story).
- **Mọi lời gọi tới model chat phải dùng đúng `num_ctx` của `PromptBudget` (8192).** Ollama nạp lại model nếu `num_ctx` khác, mất 10-20 giây.
- Một lời gọi trích xuất mất khoảng 32-36 giây với gemma4:12b (prompt khoảng 1.5k token, JSON khoảng 300 token). Từ §10.7: khoảng 15 giây khi Ollama còn cache phần luật, khoảng 33 giây khi không còn. Khi bạn gửi tin, lượt trả lời của nhân vật phải luôn được ưu tiên (mục 4).
- Embedding: `bge-m3` (1.2GB) **không bắt buộc**. Nếu `ollama list` có model `LYRIS_EMBED_MODEL` (mặc định `bge-m3`), app tìm kiếm lai (vector + từ khoá); nếu không có thì chỉ tìm theo từ khoá. App không tự pull model. Lời gọi embed dùng `keep_alive: "1m"` để model rời RAM ngay sau đó.
- Không dùng `sqlite-vec`: mỗi story chỉ có vài trăm ký ức, nên tính cosine bằng Python trên vector float32 lưu dạng BLOB là đủ nhanh, và tránh phải cài extension native. Đây là điểm khác plan.md (ghi lại ở mục 9).

## 1. Dữ liệu: migration `0006_state.sql`

```sql
ALTER TABLE stories ADD COLUMN initial_relationship_json TEXT;  -- chụp lại lúc tạo story; NULL (story cũ) = đọc từ card hiện tại

CREATE TABLE state_events (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('relationship_delta','scene','summary','suggestions')),
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_state_events_story ON state_events(story_id, message_id);

CREATE TABLE memories (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('memory','fact')),
  subject TEXT,
  text TEXT NOT NULL,
  importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  embedding BLOB,            -- float32 little-endian, NULL nếu chưa embed
  embed_model TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_memories_story ON memories(story_id, turn_index);
-- FTS5 giữ dấu tiếng Việt (ma/má/mà khác nhau): remove_diacritics 0. Đồng bộ bằng trigger insert/delete/update.
CREATE VIRTUAL TABLE memories_fts USING fts5(text, content='memories', content_rowid='id', tokenize='unicode61 remove_diacritics 0');

CREATE TABLE jobs (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('extract','summarize','embed')),
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','cancelled')),
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_jobs_status ON jobs(status, id);
```

- Version mới nhất là **6**. Sửa các test đang khẳng định 5 (`LATEST` trong `test_repo.py`, `test_integration_phase2.py`).
- `state_events` và `memories` chỉ được đọc qua message **active** (`JOIN messages ON is_active = 1`). Regenerate sinh variant mới nên variant cũ hết active và hiệu ứng của nó biến mất; lật lại variant cũ thì hiệu ứng quay lại. Xoá thì CASCADE.
- Payload:
  - `relationship_delta`: `RelationshipDelta`
  - `scene`: `SceneState`; trường None = không đổi
  - `summary`: `{"text": str, "upto_turn": int}`
  - `suggestions`: `{"items": [str, ...]}`

## 2. Phép gộp state (`lyris/state/fold.py`, hàm thuần + repo)

- **Quan hệ.** Bắt đầu từ `initial_relationship` của story, rồi đến `extensions.lyris.initial_relationship` của card, rồi đến `DEFAULT_INITIAL_RELATIONSHIP`; mỗi giá trị được kiểm tra và kẹp trong 0-100, giống `readInitialRelationship` ở frontend. Cộng lần lượt các `relationship_delta` active theo `turn_index` tăng dần, **kẹp 0-100 sau mỗi bước**. Có tham số `upto_turn` để lấy state như tại một lượt (dùng khi trích xuất lại lượt cũ).
- **Cảnh.** Lấy event `scene` active mới nhất cho từng trường khác None.
- **Tóm tắt.** Lấy event `summary` active mới nhất.
- **Gợi ý.** Lấy event `suggestions` của message assistant active cuối cùng, **chỉ khi** đó là message cuối của story (người chơi chưa trả lời).
- `dominant_emotion`: chỉ số cao nhất trong sáu. Nếu bằng nhau thì theo thứ tự `EMOTION_KEYS`. Trả None khi story chưa có event `relationship_delta` nào (chip ở hub chỉ hiện khi đã có dữ liệu thật).
- Tạo story mới (`create_story_for` và `POST /api/stories`) thì ghi `initial_relationship_json` từ card.

## 3. Chỉ dẫn diễn xuất (`lyris/state/directive.py`, hàm thuần)

`acting_directive(values: RelationshipValues, *, char: str, player: str, language: Language) -> str`

- Kết quả là 1-2 câu tiếng Việt (hoặc tiếng Anh) nói thái độ hiện tại của nhân vật với người chơi. **Không bao giờ có số.**
- Dùng các mức: thấp (<30), vừa (30-69), cao (≥70).
- Dựa trên 2-3 cảm xúc nổi bật và các tổ hợp đáng chú ý:
  - rung động cao nhưng khoảng cách cao: muốn lại gần nhưng còn giữ ý;
  - lo sợ mất mát cao + nhung nhớ cao: dễ ghen, muốn giữ chặt;
  - tin cậy thấp + thương mến cao: quan tâm nhưng chưa dám mở lòng.
- Ví dụ tiếng Việt: "Lạc Dương rất thương mến và tin cậy Lâm Vãn; đang rung động nhưng vẫn giữ trong lòng, chưa nói ra."
- Câu văn tự nhiên, không ghép máy móc. Có bảng luật và test cho từng tổ hợp chính.
- Chỉ dẫn này được dùng ở khối F và hiện ở thẻ "Chỉ dẫn diễn xuất" trong ngăn cảm xúc.

## 4. Job worker (`lyris/jobs/`)

- **Bảng và chạy.** Hàng đợi dùng bảng `jobs`, chạy trong tiến trình: một asyncio task khởi động trong lifespan của app, xử lý **lần lượt từng job** (FIFO).
- **Khi khởi động.** Job `running` còn sót được đặt lại thành `queued`.
- **Lỗi.** Model trả JSON hỏng thì thử lại 1 lần. Lỗi kết nối thì ghi `failed` kèm thông báo. Worker không bao giờ chết; lỗi chỉ được ghi log.
- **Ưu tiên lượt chat.**
  - `ChatService` báo cho worker khi bắt đầu và khi kết thúc một lượt stream (send, respond, regenerate, chat thử trong Studio thì không cần).
  - Trong lúc có stream, worker **không bắt đầu job mới**. Job đang chạy bị huỷ (huỷ request HTTP tới Ollama) và đưa lại vào `queued`, không tính vào `attempts`.
  - Stream xong thì worker chạy tiếp.
- **Khi nào xếp job.**
  - `extract` cho message assistant vừa lưu (không xếp với lượt bị huỷ giữa chừng, `aborted`).
  - Sửa nội dung một message assistant: xoá state_events và memories của message đó, xếp lại `extract`.
  - Sau mỗi `extract` thành công:
    - nếu có ký ức mới và có embed model thì xếp `embed`;
    - nếu `build_prompt` của lượt vừa rồi đã cắt bớt lượt cũ (`dropped_turns > 0`) và tóm tắt hiện tại chưa bao phủ tới lượt bị cắt cuối cùng thì xếp `summarize`.
- **Bỏ qua job thừa.** Job cho message không còn active (đã regenerate hoặc đã xoá) thì chuyển `cancelled`, không gọi model.
- **API cho trạng thái.** Worker trả `pending(story_id) -> bool` (còn job `queued`/`running`). API dùng nó cho `StoryExtras.pending`.
- **Dựng lại state.** `POST /api/stories/{id}/state/rebuild` xếp `extract` cho mọi message assistant active (trừ lượt 0) chưa có job `done`, theo thứ tự lượt; `summarize` được xếp sau cùng nếu cần. Lượt cũ được trích xuất với state tính tới lượt đó (`upto_turn`).

## 5. Trích xuất, tóm tắt, tìm ký ức (phần gọi model)

**`lyris/state/extract.py`**

```python
async def extract_turn(llm, *, model, num_ctx, card, persona, story, before: RelationshipValues, scene: SceneState, summary: str | None, turn: list[Message]) -> ExtractionResult
```

- `turn` gồm các message user của lượt (có thể không có) và message assistant (`raw_content`, có Thought vì Thought nói rõ cảm xúc thật).
- **Prompt** theo ngôn ngữ của story (vi/en), có system message ngắn. Một mẫu thử với gemma4:12b ngày 2026-11-13 đã cho kết quả tốt (delta hợp lý, gợi ý tự nhiên). Cần chỉnh thêm:
  - **facts:** sự thật cụ thể, bền vững về người và thế giới (sở thích, quan hệ, lời hứa, sự kiện đã xảy ra, thông tin nhân thân), **không** phải nhận xét tính cách. Không có fact mới thì trả mảng rỗng.
  - **memory:** một câu ai làm gì, nói gì đáng nhớ, kèm `importance` 1-5.
  - **delta:** phần lớn bằng 0; mỗi giá trị trong khoảng -5..5; có thể âm khi bị tổn thương hoặc bị từ chối.
  - **scene:** chuỗi rỗng = không đổi. Đưa cảnh hiện tại vào prompt để model không đoán sai.
  - **suggestions:** 3 gợi ý cho lượt tiếp của người chơi, viết như người chơi tự gõ, theo 3 hướng khác nhau, mỗi gợi ý ≤ 20 từ.
    - Story mode: ngôi "tôi" kèm hành động và lời thoại trong ngoặc kép (giống cách người dùng viết).
    - DM mode: một tin nhắn ngắn.
    - Đúng xưng hô của người chơi với nhân vật: người chơi gọi nhân vật bằng từ mà nhân vật dùng để tự xưng, ví dụ nhân vật xưng "tớ" thì người chơi gọi nhân vật là "cậu".
    - Không lặp lại câu người chơi đã viết.
- **Schema JSON:** không dùng `maxLength` (làm hỏng escape và xuống dòng). `minimum`/`maximum` trên số nguyên thì dùng được.
- **Options:** `num_ctx` = budget, `num_predict` 600, `temperature` 0.3.
- **Kiểm tra kết quả:** kẹp delta về ±5; cắt khoảng trắng; bỏ gợi ý rỗng và gợi ý trùng; tối đa 3 gợi ý, 3 fact; bỏ fact trùng với fact đã có (so khớp sau khi chuẩn hoá).

**`lyris/memory/summarize.py`**

```python
async def summarize(llm, *, model, num_ctx, card, persona, story, previous: str | None, messages: list[Message]) -> str
```

- Tóm tắt nối tiếp: tóm tắt cũ cộng các lượt mới bị cắt, ra ≤ 180 từ. Ngôi thứ ba, giữ tên riêng, lời hứa và bước ngoặt quan hệ.

**`lyris/memory/retrieval.py`**

- `query_terms(text, language) -> list[str]`
  - Chuẩn hoá NFC, chữ thường.
  - Bỏ stopword tiếng Việt: đại từ xưng hô và hư từ, ví dụ anh, em, tớ, cậu, tôi, cô, là, và, thì, mà, của, đã, đang, sẽ, không, có, những, một, này, đó, rồi, nhé, ạ.
  - Bỏ token dưới 2 ký tự.
  - Thêm bigram của các âm tiết liền nhau, vì từ tiếng Việt thường có hai âm tiết ("thư viện", "trà sữa").
- `fuse(keyword: list[(id, bm25)], vector: list[(id, cosine)], items) -> list[MemoryHit]`
  - Reciprocal rank fusion (k=60).
  - Cộng thêm `0.02 * importance`.
  - Đầu vào thiếu một phía vẫn chạy.
- `async def retrieve(repo, llm, story, history, *, embed_model: str | None, limit=8) -> list[MemoryHit]`
  - Truy vấn là tin cuối của người chơi cộng lượt trả lời trước đó.
  - Từ khoá: `repo.search_memories_fts`.
  - Vector: embed truy vấn, rồi tính cosine với embedding đã lưu cùng `embed_model`.
  - Lỗi embed thì quay về chỉ dùng từ khoá.
- `LLMClient` thêm `async def embed(model: str, texts: list[str]) -> list[list[float]]`.
  - Ollama: `POST /api/embed` với `keep_alive "1m"`.
  - `FakeLLM`: trả vector xác định, ví dụ băm theo từ, để test chạy được.

## 6. Prompt: khối C và F

- `build_prompt(card, persona, story, history, *, budget=None, state: PromptState | None = None)`. `state=None` cho ra **đúng prompt như cũ**, vì chat thử trong Studio và harness cũ cần giữ nguyên.
- **Khối C (system):**
  - `scenario`;
  - `story.scene_summary` (tóm tắt do người dùng tự viết, nếu có);
  - `state.summary` với nhãn "Những gì đã xảy ra trước đó" / "Earlier in the story".
  - Tóm tắt chỉ đổi khi job `summarize` chạy, nên tiền tố system vẫn ổn định để Ollama dùng lại prompt cache.
- **Khối F (ghi chú cuối)**, thêm các dòng sau trước luật của lượt:
  - `- Cảnh hiện tại: {location}, {time}.` (nếu có);
  - `- Thái độ của {c} lúc này: {directive}`;
  - `- Chuyện cũ {c} còn nhớ (chỉ nhắc khi hợp cảnh, không kể lại nguyên văn):` kèm tối đa 3 ký ức. Chỉ lấy kind `memory` có `turn_index` < lượt đầu tiên còn trong cửa sổ lịch sử;
  - `- Điều {c} biết:` kèm tối đa 3 fact;
  - Phần chống lặp (`repetition.py`) giữ nguyên.
  - Bản tiếng Anh tương ứng.
- **Ngân sách token.** Các dòng state của F tối đa khoảng 350 token. Builder đo lại F khi tìm điểm cắt lịch sử (vòng lặp hiện có).
- **Ghi snapshot.** `ChatService` dựng `PromptState` qua `StateService.prompt_state(...)` (async, vì phải embed truy vấn). Snapshot lưu kèm `state` để Phase 5 train đúng định dạng.

## 7. API

| Method | Path | Ghi chú |
|---|---|---|
| GET | /api/stories/{id}/extras | `StoryExtras` đầy đủ. `relationship` luôn có (giá trị khởi đầu nếu chưa có event), kèm `directive`. `memory_search` = "hybrid" nếu có embed model. |
| DELETE | /api/stories/{id}/memories/{memory_id} | Quên một ký ức hoặc fact (xoá dòng). 404 nếu không thuộc story hoặc account. |
| POST | /api/stories/{id}/state/rebuild | Xếp job dựng lại (mục 4). Trả `{queued: int}`. |
| (đổi) | GET /api/stories (StoryOut) | Thêm `dominant_emotion: DominantEmotion \| None`, `location: str \| None`. |
| (đổi) | GET /api/account | `card_count` chỉ đếm nhân vật account tự tạo, **không tính nhân vật mẫu đã cài**, để khớp với trang profile. |

- Mọi route lọc theo `current_account` như Phase 2c.
- Không thêm kênh SSE: frontend hỏi lại `/extras` khi `pending` là true (mục 8).

## 8. Giao diện (DESIGN.md §5, design-impl §10)

- **`useStoryExtras`.**
  - Gọi lại sau mỗi lượt xong (done hoặc abort), regenerate, lật phiên bản, sửa, xoá.
  - Khi `pending` là true thì hỏi lại mỗi 2 giây, dừng khi hết pending hoặc rời trang. Không hỏi khi tab bị ẩn.
- **Ngăn cảm xúc (`HeartDrawer`).**
  - **Thẻ "Chỉ dẫn diễn xuất":** câu `directive`.
  - **6 thanh đo:** màu theo DESIGN.md §3.3, có `transition-[width] duration-500`, nhãn tiếng Việt như `EMOTION_LABEL`, kèm phần trăm.
  - **"Cảnh":** nơi chốn và thời gian.
  - **"Ký ức":**
    - liệt kê ký ức và fact, phân biệt bằng nhãn nhỏ "Sự kiện" / "Điều đã biết";
    - mỗi mục có nút "Quên" (xác nhận trước khi xoá);
    - nếu `unprocessed_turns > 0` thì có khối mời "Story này có N lượt chưa được ghi nhớ" kèm nút "Đọc lại story" (gọi rebuild);
    - khi pending thì hiện một dòng nhỏ "Đang ghi nhớ lượt vừa rồi…".
  - **Wiki:** giữ trạng thái rỗng hiện có (Phase 4).
  - **Chế độ tìm ký ức:** một dòng nhỏ ở cuối: "Tìm ký ức theo từ khoá" hoặc "theo nghĩa (bge-m3)".
- **Gợi ý trả lời (`QuickReplies`).**
  - 3 chip cuộn ngang phía trên ô nhập. Chạm vào là gửi ngay (DESIGN.md).
  - Ẩn khi đang sinh lượt trả lời, khi người chơi đang gõ dở (ô nhập có chữ), và khi không có gợi ý.
  - Trong lúc chờ gợi ý (pending, chưa có gợi ý) thì không hiện khung giả nào.
- **Header chat.** Dòng phụ hiện `location · time` khi có. Sửa luôn lỗi dòng phụ bị cắt chữ trên desktop.
- **Thẻ story ở hub.** Thêm chip cảm xúc nổi bật (`Thương mến 91%`, dùng icon tim, không dùng emoji) và chip nơi chốn, khi có dữ liệu.
- **Máy MacBook M2 trong sheet Tài khoản.** Thêm một dòng "Ký ức: tìm theo từ khoá" (hoặc "theo nghĩa, bge-m3"), kèm gợi ý `ollama pull bge-m3` khi chưa có.
- **Việc nhỏ còn lại từ Phase 2c:**
  - nhân vật mẫu không còn nhãn "Riêng tư" (Khám phá, Studio, profile);
  - trang profile không lặp chữ "Riêng tư";
  - New Story trên điện thoại: khi đã chọn sẵn nhân vật (`?card=`), thu lưới nhân vật về một dòng nhân vật đã chọn kèm nút "Đổi nhân vật", để phần persona nằm trong màn hình đầu;
  - `detailToText` trong `client.ts` giữ vị trí lỗi (`loc`);
  - design-impl.md ghi `?open=profile` và `?tab=`.

## 9. Khác với plan.md

- Không có bảng `relationship_state` cache: state được tính lại từ event, vì mỗi story chỉ có vài trăm event.
- Không dùng `sqlite-vec` (mục 0).
- Facts và ký ức nằm chung bảng `memories` (cột `kind`), dùng chung FTS.
- Mặc định trích xuất bằng model chat, không phải e4b, vì RAM (mục 0).
- Đẩy cập nhật lên giao diện bằng cách frontend hỏi lại `/extras` khi `pending`, không mở kênh SSE riêng.

### Ghi chú khi ghép các phần (2026-11-13)

- **`SystemInfo` thêm `memory_search` và `embed_model`** (`models.py`, đều có giá trị mặc định nên không phá client cũ). Sheet Tài khoản cần biết đang tìm ký ức kiểu nào và tên model để gợi ý `ollama pull` (mục 8); trước đó không có endpoint nào trả thông tin này ngoài `/extras` của từng story.
- **`extract_turn(..., known_facts=())`**: thêm tham số so với chữ ký ở mục 5. Prompt cho model thấy các fact đã có (tối đa 12) để không ghi lại, và `validate` bỏ fact trùng sau khi chuẩn hoá. Worker truyền vào và vẫn tự bỏ trùng thêm một lần.
- **Tóm tắt**: chỉ xếp `summarize` khi có ít nhất 4 lượt đã rơi khỏi cửa sổ mà tóm tắt chưa bao phủ (`SUMMARY_MIN_NEW_TURNS`), vì mỗi lần tóm tắt tốn khoảng 30 giây model. Lượt cũ được tóm tắt theo từng khúc khoảng 3000 token, mỗi khúc một event `summary`. Đã có job `summarize` đang chờ thì không xếp thêm.
- **Embed**: một job `embed` cho cả story (`message_id` NULL), embed mọi ký ức active còn thiếu vector của model.
- **Thử lại**: worker thử lại một lần với mọi lỗi trừ lỗi kết nối/timeout tới Ollama (`httpx.TransportError` trong chuỗi `__cause__`), không chỉ JSON hỏng.
- **Snapshot** lưu thêm `window_start_turn` (lượt đầu còn trong cửa sổ lịch sử) để worker quyết định tóm tắt mà không phải dựng lại prompt.
- **Lật lại variant chưa từng được trích xuất** (job của nó đã bị huỷ khi regenerate) thì xếp lại `extract`.
- **Tìm ký ức cho prompt** lấy 16 ứng viên (`RETRIEVE_LIMIT`), vì builder bỏ những ký ức còn nằm trong cửa sổ lịch sử; lấy 8 thì thường chỉ còn ký ức gần.
- **Worker chỉ tự chạy khi dùng Ollama thật** (`create_app(llm=None)`); test và `scripts/make_demo_db.py` dùng `FakeLLM` thì gọi `worker.run_until_idle()`.

### Ghi chú khi chạy thử với gemma4:12b thật (2026-11-13)

- **Tìm ký ức theo từ khoá (`retrieval.py`)**: `retrieve(..., names=...)` thêm tham số so với mục 5; `StateService` truyền tên nhân vật và người chơi, âm tiết của tên không dùng làm từ khoá. Trước đó tên khớp gần như mọi ký ức, nên mọi ký ức đều thành ứng viên và điểm `0.02 * importance` quyết định thứ hạng thay cho độ liên quan. Cụm từ khoá của tin người chơi giờ đứng trước cụm của lượt trả lời trước đó (`keyword_terms`): lượt trả lời dài từng chiếm hết 32 cụm, làm mất đúng chữ người chơi vừa hỏi ("hứa", "sinh nhật").
- **Cảnh (`extract.py`)**: prompt dặn rõ phải ghi nơi/lúc mới khi nhân vật đã sang chỗ khác hoặc sang buổi khác, suy ra `time` từ dấu hiệu trong lượt, và với lượt DM thì `location` là nơi người chơi đang ở nếu tin nhắn có nói. Trước đó 12 lượt của story thật chỉ ra một event cảnh ("Thư viện"), kể cả khi hai người đã ra quán ăn rồi về nhà nhắn tin.
  - Sửa 2026-11-14: câu DM từng có nơi mẫu `(ví dụ "Nhà {p}")`. gemma4:12b chép nguyên mẫu đó cho tin nhắn không nói nơi nào (3/3 lần: "Nhà Diệp Linh"), làm F của lượt Story kế tiếp mang cảnh sai. Giờ câu đó không còn nơi mẫu, chỉ ghi khi tin nhắn nói rõ người chơi đang ở đâu lúc này, nơi hẹn sau này không phải cảnh hiện tại, không đoán. Đo lại: DM không nói nơi 0/9 ghi nơi (trước 3/3 ở DM1); DM "vừa về tới ký túc xá" 2/3 ghi "Ký túc xá" (trước 0/3); lượt Story vẫn 6/6 ghi đúng nơi.
- **Fact trùng ký ức**: `validate` bỏ fact trùng câu ký ức của cùng lượt; builder không in fact trùng chữ một ký ức đã có trong "Chuyện cũ".

## 10. Phase 3b

Từ góp ý sau khi dùng thử (2026-11-13). Mục 10.1 là backend, 10.2 là hợp đồng API cho giao diện; phần giao diện ghi ở 10.3.

### 10.1 Backend

**Gợi ý theo yêu cầu (`lyris/state/suggest.py`).** Chỉ sinh khi người chơi bấm "Nhận gợi ý" (hoặc "Gợi ý khác"), không bao giờ tự chạy sau một lượt.
- Một lời gọi `chat_json` bằng model chat của story, `num_ctx` của budget, `num_predict` 400, `temperature` 0.8. Schema `{"suggestions": [str]}`, không `maxLength`.
- Prompt vi/en giữ các luật tốt của bản cũ trong `extract.py`: giọng người chơi, đúng xưng hô (`player_address`), 3 hướng khác nhau, tối đa 25 từ. Story: ngôi "tôi", một hành động rồi một câu thoại trong ngoặc kép. DM: tin nhắn ngắn. Model đọc 6 message cuối (chỉ phần hiển thị, không có Thought, vì người chơi không biết suy nghĩ thầm), cảnh và tóm tắt. Bấm lại thì gợi ý cũ được đưa vào prompt để lần này ra hướng khác.
- `validate`: bỏ gạch đầu dòng, số thứ tự và ngoặc kép bọc cả câu; bỏ gợi ý rỗng, trùng nhau, trùng lời người chơi đã viết hoặc trùng gợi ý lần trước. Giữ tối đa 3; không còn gợi ý nào thì báo lỗi.
- `ChatService.suggest` coi việc này như một lượt sinh. Nó giữ khoá của story và báo worker nhường model (`generation_started`/`finished`).
  - Story đang sinh câu trả lời: 409 `BUSY_DETAIL`.
  - Trong lúc đang nghĩ gợi ý, gửi, sửa, xoá hay xin gợi ý lần nữa: 409 "Đang nghĩ gợi ý cho bạn. Đợi một chút rồi thử lại nhé."
  - Message active cuối không phải của nhân vật: 409 "Chỉ nhận gợi ý được khi nhân vật vừa trả lời xong và bạn chưa viết tiếp."
  - Client ngắt kết nối: huỷ lời gọi model và nhả khoá.
- Gợi ý được lưu thành một event `suggestions` trên message đó và thay event cũ (`Repo.replace_suggestions`). `/extras` trả gợi ý cho tới khi người chơi trả lời.
  - Trích xuất lại **không** xoá gợi ý: `EXTRACTION_KINDS` chỉ còn `relationship_delta` và `scene`.
  - Sửa nội dung message thì xoá gợi ý (`MESSAGE_STATE_KINDS`).

**Trích xuất (`extract.py`).**
- Bỏ gợi ý khỏi schema, prompt, `validate` và phần worker ghi kết quả. `ExtractionResult.suggestions` vẫn còn (mặc định `[]`) để không phá code cũ.
- Delta:
  - Kẹp ±5 rồi chỉ giữ **2** thay đổi lớn nhất theo trị tuyệt đối; bằng nhau thì theo thứ tự `EMOTION_KEYS` (`top_delta`). Đã đổi ở §10.5: giữ 0-3 tuỳ `tone` và chiều ấm lòng / tổn thương (`pick_changes`).
  - Prompt: "Phần lớn các lượt chỉ 0-1 chỉ số đổi (nhiều nhất 2)… 4-5 chỉ dành cho bước ngoặt." Đã thay ở §10.5.
- **Lời mở đầu (lượt 0)** cũng được trích xuất, nhưng chỉ cảnh và ký ức (`OPENING_SCHEMA`). Không có event `relationship_delta` và không có fact.
  - Job được xếp khi tạo story qua `POST /api/stories` (`JobQueue.story_created`) và khi rebuild.
  - Story seed lúc khởi động chỉ được xếp khi worker tự chạy (Ollama thật).
  - `unprocessed_turns` và `messages_needing_extract` giờ tính cả lượt 0. Vì vậy story cũ sẽ thấy thêm 1 lượt chưa ghi nhớ; "Đọc lại story" xử lý lượt đó.
- Tìm ký ức: `IMPORTANCE_WEIGHT` 0.02 → 0.003.
- Chỉ dẫn diễn xuất: tên người chơi chỉ xuất hiện một lần. Những lần sau dùng đại từ dẫn truyện của người chơi (`acting_directive(..., player_pronoun=story.narration_pronouns.player)`); đại từ ngôi 1/2 hoặc không có thì dùng "người ấy" (tiếng Anh: "them"). Hai câu từng lặp tên đã được viết lại. Tên nhân vật cũng chỉ một lần, xem §10.5.

**Cửa sổ lịch sử cắt theo khúc (`builder.py`).** Trước đây, khi story đầy cửa sổ, mỗi lượt mới đẩy 1-3 lượt cũ ra. Điểm bắt đầu đổi nên Ollama phải đọc lại cả prompt (TTFT khoảng 60 giây thay vì 4 giây).
- Lịch sử vừa ngân sách thì giữ trọn, như cũ (`state=None` cho đúng prompt cũ).
- Không vừa thì cửa sổ chỉ được bắt đầu ở **mốc khúc**:
  - Một khúc = `TRIM_CHUNK_FRACTION` (1/3) × (giới hạn − A − B − C không kèm tóm tắt), tính theo chế độ chật hơn (phần trả lời Story, luật dài nhất). Nhờ vậy Story và DM có **cùng các mốc**.
  - Mốc là đầu lượt người chơi đầu tiên sau mỗi khúc, đếm từ đầu story. Mốc chỉ phụ thuộc phần lịch sử phía trước nên không dịch khi story dài thêm. Không cần lưu gì.
  - Builder chọn mốc sớm nhất còn vừa. Mọi phép kiểm tra (kể cả "có cần cắt không" ở mốc 0 khi có state) dùng phần dự phòng **cố định** cho F (`_f_reserve`: ghi chú dài nhất với đủ 3 câu cần tránh, mỗi câu `AVOID_PHRASE_CHARS` ký tự, + `STATE_TOKEN_LIMIT`) và cho C (tóm tắt dài nhất). Fact, ký ức hay chỉ dẫn của từng lượt không còn làm điểm bắt đầu lùi lại.
  - `state=None` (Studio, harness) vẫn dùng phép kiểm tra cũ ở mốc 0, nên prompt chưa đầy giữ nguyên từng byte. `PromptState()` rỗng chỉ khác `None` khi lịch sử đã đầy (cắt sớm hơn một chút vì có phần dự phòng).
  - Không mốc nào vừa (ví dụ có một lượt khổng lồ) thì cắt từng lượt từ mốc cuối, như cũ.
- Kết quả: mỗi lần cắt bỏ cả một khúc, nên lịch sử còn khoảng 2/3 ngân sách và cửa sổ đứng yên cho tới khi đầy lại. Với `num_ctx` 8192 và card seed, ngân sách lịch sử story khoảng 5000 token, một khúc khoảng 1700 token, tức khoảng 2-3 lượt story thật. Muốn cửa sổ đứng lâu hơn thì tăng `TRIM_CHUNK_FRACTION`.
- **Tóm tắt khớp với khúc:**
  - `PromptState.summaries` chứa mọi mốc tóm tắt active.
  - Khối C dùng mốc mới nhất có `upto_turn` < lượt đầu của cửa sổ (`pick_summary`), nên C chỉ đổi khi cửa sổ dịch.
  - `BuiltPrompt.summary_upto_turn` ghi mốc đã dùng. Trong snapshot, `state.summary` là tóm tắt thật sự đã vào C (không lưu `summaries`).
  - Worker (`StateService.summary_target`) tóm tắt phủ mọi mốc ≤ điểm bắt đầu hiện tại. Nó tóm tắt **trước** khúc sắp rơi ra chỉ khi cửa sổ sẽ dịch ngay ở lượt kế tiếp: `next_window_start` dựng thử prompt với một lượt người chơi giả dài bằng lượt dài nhất trong 3 lượt gần đây + 120 ký tự. Gọi model tóm tắt đẩy prompt chat ra khỏi cache, nên chỉ làm đúng trước lượt vốn phải đọc lại prompt; không còn tóm tắt ngay sau mỗi lần cửa sổ dịch (lỗi cũ: thêm một lượt chậm ~50 giây mỗi khúc).
  - Đổi Story ↔ DM (`PATCH /stories/{id}` có `mode` mới) gọi `JobQueue.mode_changed`: xét lại và xếp tóm tắt trước nếu ở chế độ mới cửa sổ sắp dịch. Đổi chế độ vốn đã đổi khối luật nên không mất thêm cache. Vì mốc chung cho hai chế độ, cửa sổ ở chế độ nào cũng có mốc tóm tắt `mốc − 1` ngay trước nó.
  - Mỗi khúc kết thúc bằng một event `summary` có `upto_turn` = mốc − 1. Bỏ `SUMMARY_MIN_NEW_TURNS`.
  - Kết quả đo trong test: khi cửa sổ dịch thì tóm tắt đã sẵn, system và điểm bắt đầu đổi cùng một lượt, nên phần đầu prompt chỉ đổi một lần mỗi khúc. Trên Ollama thật thì chưa đủ: lượt ngay sau lượt dịch cũng đọc lại cả prompt, và lượt thường đọc lại khoảng 2 lượt (cache của model sliding window). Đã sửa bằng prefill, xem §10.6. Job tóm tắt chỉ được xếp ngay trước lượt cửa sổ dịch. Đổi chế độ giữa chừng thì `summary_upto_turn` vẫn luôn = lượt đầu cửa sổ − 1.

**Dòng thời gian.** `StateService.timeline(story)` liệt kê các lượt active có state (ký ức, fact, delta khác 0, cảnh), lượt cũ trước.

**Lỗi dễ hiểu (`lyris/llm/errors.py`).**
- `LLMError` có thêm `kind`: `connect`, `timeout`, `missing_model`, `server`, `output` hoặc `unknown`; client Ollama gán `kind` cho từng lỗi.
- `friendly(exc, action)` trả một câu tiếng Việt không có "Ollama" hay "model", kèm chi tiết kỹ thuật nguyên văn.
- Dùng cho chat (SSE), chat thử ở Studio, AI viết nháp và gợi ý.
- `/api/system`, `/api/health` và kiểm tra tên model vẫn giữ chữ kỹ thuật, vì chúng chỉ hiện trong "Nâng cao".

**Demo DB (`scripts/make_demo_db.py`).** Delta qua `top_delta` như worker (từ §10.5: tối đa 3 chỉ số, 3 chỉ khi có thay đổi tổn thương; demo DB không có `tone` nên `pick_changes` đoán theo số). Lời mở đầu có cảnh và ký ức, nên "Xem sự kiện" có dòng thời gian. Chỉ story Hạ Vy có gợi ý, như thể vừa bấm "Nhận gợi ý". Story Tạ Vân Lan vẫn "cũ", có 2 lượt chưa ghi nhớ.

### 10.2 API cho giao diện

| Method | Path | Kết quả |
|---|---|---|
| POST | /api/stories/{id}/suggestions | 200 `{"items": [str, ...]}` (1-3, thường 3). 404: story không có hoặc thuộc account khác. 409 `{"detail"}`: đang bận, hoặc lượt cuối không phải của nhân vật. 502 `{"detail", "technical"}`: lỗi model. |
| GET | /api/stories/{id}/timeline | 200 `TimelineEntry[]`, lượt cũ trước. 404 như trên. |

```json
{"turn_index": 2, "message_id": 21, "mode": "story", "created_at": "2026-11-13T03:04:12.070Z",
 "memory": "Một câu ký ức" , "facts": ["..."], "delta": {"affection": 3, "trust": 2},
 "scene": {"location": "Tiệm sách", "time": "Chiều mưa"}}
```

- `memory` là `null` khi lượt không có ký ức. `delta` chỉ có các chỉ số khác 0, theo thứ tự `EMOTION_KEYS`; lượt 0 luôn là `{}`. `scene` là `null` khi lượt không đổi cảnh; từng trường trong `scene` cũng có thể `null`. Chạm một mục thì nhảy tới message `message_id` (`turn_index`).
- **Định dạng lỗi:**
  - Lỗi model ở HTTP (gợi ý, AI viết nháp) trả `{"detail": "câu dễ hiểu", "technical": "chi tiết" | null}`.
  - Sự kiện SSE `error` (chat, chat thử) có cùng hai trường.
  - Các lỗi khác vẫn chỉ có `{"detail"}`.
  - Giao diện hiện `detail` và để `technical` dưới "Chi tiết" (chỉ khi có).
- `StoryExtras.suggestions` chỉ có dữ liệu sau khi gọi POST gợi ý, và rỗng lại khi người chơi trả lời hoặc khi sửa message đó. Trong lúc POST gợi ý đang chạy, gửi tin sẽ nhận 409 với câu riêng; giao diện nên khoá nút gửi hoặc hiện trạng thái "đang nghĩ".

### 10.3 Giao diện

Chi tiết cách dựng ở `docs/design-impl.md` §15.

- **Nút "+" ở ô nhập** (`pages/chat/ComposerMenu.tsx`, danh sách mục lấy từ `suggestLogic.composerActions`, thêm mục sau chỉ cần thêm dữ liệu).
  - Nút 44px bên trái ô nhập, có `aria-expanded`.
  - Từ 640px là popover phía trên nút; trên điện thoại là sheet từ dưới, nền mờ phía sau.
  - Phím mũi tên, Home, End đi qua mọi mục (kể cả mục bị khoá, để screen reader đọc lý do). Esc hoặc bấm ra ngoài thì đóng, focus về lại nút "+".
- **Nhận gợi ý:** chỉ gọi `POST /suggestions` khi người chơi chọn mục này. Không còn gợi ý tự hiện sau mỗi lượt.
  - Bị khoá kèm một câu lý do khi:
    - story đang tải;
    - máy không trả lời được;
    - nhân vật đang trả lời;
    - đang nghĩ gợi ý;
    - lượt cuối là của người chơi;
    - story chưa có lượt nào.
  - Trong lúc nghĩ, vùng gợi ý hiện ba chấm nhảy kèm nút "Huỷ gợi ý". Nút gửi, đổi Story/DM và thao tác trên tin đều chờ, vì server giữ story và sẽ trả 409.
  - Xong thì hiện 3 thẻ gợi ý như cũ: chạm là gửi ngay; chữ hiện có định dạng, nhưng gửi đúng nguyên văn. Kèm "Gợi ý khác" và nút đóng.
  - Lỗi: một câu dễ hiểu, "Chi tiết" và "Thử lại".
  - Gợi ý mà `/extras` còn giữ (người chơi đã xin trước đó) vẫn hiện khi mở lại story. Đóng thì ẩn cho tới khi có gợi ý mới. Lượt mới bắt đầu thì bỏ gợi ý.
  - Gợi ý gắn với lượt trả lời đã xin (`replyAnchor`: id, variant, lúc sửa). Xoá từ lượt đó, sửa nó hay chọn variant khác thì gợi ý (cả bản server giữ) ẩn ngay và bị bỏ.
  - Server viết gợi ý theo chế độ của lượt trả lời cuối, nên "Nhận gợi ý" bị khoá khi lượt đó thuộc chế độ kia ("Nhân vật vừa trả lời bên Story. Mở Story để nhận gợi ý.").
  - Focus không rơi về trang: "Gợi ý khác"/"Thử lại" chuyển focus tới "Huỷ gợi ý"; đóng, huỷ hay gửi một gợi ý thì focus về nút "+" (không bật bàn phím điện thoại).
- **Xem sự kiện** (`EventsSheet.tsx`, `eventsLogic.ts`): sheet "Sự kiện" có hai tab.
  - **"Dòng thời gian":** lượt mới ở trên, bỏ những lượt không có gì. Mỗi mục gồm:
    - nhãn Story/DM và giờ;
    - câu ký ức;
    - "Điều đã biết";
    - chip cảm xúc như "+2 Thương mến" / "−3 Tin cậy", chấm màu theo DESIGN.md §3.3;
    - chip cảnh.
  - Chạm một mục thì đóng sheet, cuộn tới lượt đó, viền sáng lượt đó khoảng 2.4 giây và chuyển focus vào nó. Lượt thuộc chế độ kia thì đổi chế độ trước. Đang bận (đang trả lời, đang nghĩ gợi ý, đang đổi chế độ) thì chỉ báo một dòng, không để lượt nhảy chờ sẵn; đổi chế độ thất bại, tự đổi chế độ, hoặc lượt không hiện ra sau 4 giây thì bỏ lượt nhảy (`jumpPlan`, `JUMP_WAIT_MS`).
  - Mỗi lượt được render với `id="turn-{turn_index}"`.
  - **"Khoảnh khắc":** để trống chờ Phase 8, hoặc hiện `extras.moment` nếu có.
- **Gửi hình ảnh:** mục bị khoá, có nhãn "Sắp có" và một câu giải thích.
- **Ẩn chữ kỹ thuật:**
  - Sheet Tài khoản chỉ còn tài khoản, persona, và một câu dễ hiểu khi máy không trả lời được.
  - Mục "Nâng cao" gập sẵn. Trong đó: máy, RAM, model đang nạp, model mặc định, KV cache, phiên bản, cách tìm ký ức, gợi ý `ollama pull`, và công tắc "Công cụ nâng cao" (`localStorage["lyris.advanced"]`, mặc định tắt). `/api/system` chỉ được hỏi khi mục này mở.
  - Link nhỏ "Giới thiệu & bản quyền ảnh" mở trang giới thiệu: wordmark, một câu về Lyris và danh sách nguồn ảnh. Ảnh CC BY vẫn được ghi nguồn đầy đủ.
  - Khám phá bỏ dòng "Ảnh: …".
  - Ngăn cảm xúc bỏ dòng "Đang ghi nhớ…" và dòng cách tìm ký ức. Khi còn lượt chưa đọc, ngăn chỉ mời "Lyris chưa đọc hết story này." kèm nút "Đọc lại story". Lúc đang đọc lại chỉ hiện ba chấm, không có số.
  - Thiết lập story: chọn model nằm trong "Nâng cao".
  - Studio: "Xem trước prompt", ước lượng token và thời gian sinh chỉ hiện khi bật công cụ nâng cao.
  - Lỗi ở mọi nơi qua `errorMessage` (`lib/friendlyError.ts`) thành câu dễ hiểu (AI viết nháp và chat thử ở Studio cũng có "Chi tiết", qua `Notice technical`). Ưu tiên `technical` của server; nếu server không gửi thì client tự đổi câu kỹ thuật. Chữ gốc nằm dưới "Chi tiết" (`ErrorDetails`, `InlineAlert technical`).
- **Chỉ báo đang trả lời:** bỏ câu "… đang ngập ngừng tìm lời hồi đáp…" và đồng hồ chờ. Thay bằng ba chấm nhảy (`TypingDots`):
  - Story: ở cột nhân vật;
  - DM: bong bóng cạnh avatar nhân vật;
  - Studio chat thử: cũng vậy.
  Chữ "{Tên} đang trả lời" chỉ dành cho screen reader, đặt vào một vùng `LiveStatus` (role=status) luôn gắn sẵn ở danh sách tin, ở ô nhập (cho "Đang nghĩ gợi ý…" / "Có N gợi ý") và ở chat thử, vì vùng live chỉ được đọc chắc chắn khi chữ đổi bên trong vùng đã có. Ba chấm chỉ để nhìn (aria-hidden). Khi bật reduced-motion, các chấm đứng yên.
- **Lượt của người chơi ở Story:** `lib/playerBlocks.ts` dùng lại `storyBlocks.paragraphBlocks`.
  - Lời trong ngoặc kép thành thẻ thoại trong bong bóng hồng `bg-user-gradient`.
  - `*hành động*` và dẫn truyện thành dòng nghiêng, bỏ dấu sao.
  - Giữ nguyên đoạn. Cả lượt căn phải, kèm avatar persona. Chỉ đạo `((…))` vẫn là chip.
  - Đoạn chỉ có dấu câu hay emoji ("...", "😳", "?!", "*...*") vẫn hiện thành một dòng dẫn truyện; `**x**` đọc như `*x*`.
  - DM giữ bong bóng; `*hành động*` hiện nghiêng, không còn dấu sao.
  - Chỉ thay đổi cách hiển thị, chữ đã lưu không đổi.

### 10.4 Tích hợp

Kiểm tra chung frontend + backend (backend thật trên DB demo, một Ollama giả trả JSON cố định, Chrome headless ở 390 và 1280 px, cả hai theme).
- JSON thật của `/suggestions`, `/timeline`, `/extras`, `/system` và lỗi (`{"detail", "technical"}` ở HTTP 502 và sự kiện SSE `error`) khớp `types.ts`.
- **Huỷ gợi ý rồi gửi ngay:** server chỉ nhận ra client đã ngắt sau một nhịp kiểm tra, nên trong lúc đó lượt gửi bị 409 "Đang nghĩ gợi ý…".
  - Nhịp kiểm tra giảm từ 0.5 giây xuống 0.25 giây (`SUGGEST_DISCONNECT_POLL_S`).
  - Giao diện khoá nút gửi và "Nhận gợi ý" thêm 0.8 giây sau khi huỷ (`useSuggestions.releasing`). Chữ đang gõ vẫn giữ nguyên.
- **Lỗi thiếu model chỉ đúng chỗ sửa:** model của story nằm ở "Thiết lập story > Nâng cao". Viết nháp và chat thử dùng model mặc định, xem ở "Tài khoản > Nâng cao" (`_MISSING_MODEL` theo việc đang làm).
- Câu lỗi dễ hiểu của server được giữ nguyên ở client, không bị diễn đạt lại. Có test ở cả hai phía: `friendlyError.test.ts` liệt kê các câu, `test_phase3b_e2e.py` kiểm tra backend không có câu nào ngoài danh sách.
- **Nhảy tới lượt từ dòng thời gian:** lượt cao hơn khung nhìn thì cuộn sao cho đầu lượt nằm ngay dưới header, thay vì canh giữa làm mất mấy dòng đầu.
- **Test e2e mới (`tests/test_phase3b_e2e.py`):**
  - xin gợi ý → `/extras` có gợi ý → người chơi gửi → gợi ý mất, worker không tự sinh lại;
  - trích xuất lại không xoá gợi ý, sửa message thì xoá;
  - dòng thời gian sau vài lượt, kể cả lượt 0: top-2 delta, cảnh, fact, trỏ đúng message, variant mới;
  - cửa sổ theo khúc qua đường `ChatService` thật với worker chạy giữa các lượt. Qua 30 lượt gửi, cửa sổ dịch 2 lần và đứng yên 8 lượt giữa hai lần dịch. System giữ nguyên từng byte khi cửa sổ chưa dịch, và tóm tắt luôn sẵn khi cửa sổ dịch. Job tóm tắt chỉ xếp ngay trước lượt cửa sổ dịch, không bao giờ ngay sau;
  - đổi Story ↔ DM mỗi 5 lượt: lượt nào đã cắt thì `summary_upto_turn` = lượt đầu cửa sổ − 1.

### 10.5 Cảm xúc tăng giảm theo tình huống

Góp ý của người dùng (2026-11-13): "mình làm gì nhân vật thấy không đúng thì chỉ số phải giảm được, ví dụ mình thân với người khác thì chiếm hữu tăng còn tin cậy giảm". Với gemma4:12b thật, 11/12 lượt thường của story Lạc Dương đổi đúng 2 chỉ số và hầu như luôn +1/+2 (thương mến +1 kèm rung động hoặc tin cậy), nên chỉ số cứ nhích lên. Lượt ghen duy nhất chỉ ra nhung nhớ +1, tin cậy không giảm.

**Prompt (`extract.py`, vi + en).**
- Thêm trường `reason` đứng **đầu** schema (`{"type": "string"}`, không `maxLength`): 1-2 câu model tự nghĩ trước khi chấm số. Nội dung: người chơi vừa làm gì, và theo tính cách cùng Thought thì nhân vật thật sự thấy thế nào. `validate` bỏ trường này. `NUM_PREDICT` 600 → 700 (§10.7: 500, `reason` một câu, JSON một dòng).
- Mỗi chỉ số có một dòng nói **khi nào tăng, khi nào giảm**. Ví dụ tin cậy giảm khi người chơi nói dối, giấu giếm, thất hứa, hay vô tư thân thiết với người khác, "kể cả khi nhân vật ngoài mặt vẫn dịu dàng bỏ qua".
- Ví dụ tương phản, viết chung chung (không chép tình huống của story):

  | Tình huống | Delta mẫu |
  |---|---|
  | Ghen | obsession 2, fear 2, trust -1, không tăng affection |
  | Bị nói dối | trust -3, aversion 2 |
  | Bị đẩy ra | affection -1, fear 2, aversion 2 |
  | Xin lỗi thật lòng | trust 1, aversion -2 |
  | Khoảnh khắc thân mật thật sự | attraction 2, affection 1 |
  | Chuyện thường ngày | tất cả 0, "kể cả khi nhân vật vẫn thấy vui, ấm lòng như mọi ngày" |

- Prompt có thêm tính cách (≤ 400 ký tự) và bí mật (≤ 200 ký tự) của card. Có dặn: nhân vật chiếm hữu, nhạy cảm hay đa nghi thì phản ứng mạnh hơn; nhân vật điềm tĩnh thì nhẹ hơn. Mức 3 là "chuyện lớn", bị lừa dối là chuyện lớn với tin cậy.

**Kiểm tra (`pick_changes`, `top_delta` gọi nó khi không truyền `keep`).** Bản sửa sau verifier (xem "Vòng sửa thứ hai" bên dưới) xét theo **ấm lòng / tổn thương**, không theo dấu số học: thương mến, tin cậy, rung động tăng là ấm; nhung nhớ, lo sợ, khoảng cách **giảm** mới là ấm (`WARM_SIGN`, `is_warm`).
- Schema có thêm `tone` (enum `everyday` / `warm` / `hurt` / `mixed`) ngay sau `reason`, trước số.
- `everyday`: không giữ gì.
- `warm`: chỉ giữ thay đổi ấm lòng, tối đa 2; nếu đều ±1 thì giữ 1 (chống trôi). Thay đổi tổn thương lẻ (nhung nhớ +1, lo sợ +1 lúc được tựa vai) là nhiễu, bị bỏ.
- `hurt`: chỉ giữ thay đổi tổn thương, tối đa 3, kể cả ±1 (ghen: nhung nhớ 2, lo sợ 2, tin cậy -1 giữ cả ba). Thay đổi ấm lòng lẻ (rung động +1 lúc đang ghen) bị bỏ.
- `mixed`: giữ thay đổi lớn nhất của mỗi phía, thêm cái thứ ba khi nó đổi từ 2 trở lên.
- Không có `tone` hợp lệ (dữ liệu cũ, `scripts/make_demo_db.py`): đoán theo số. Chỉ một phía thì lấy phía đó; cả hai phía đều có thay đổi từ 2 thì `mixed`; còn lại lấy phía nặng hơn (bằng nhau thì nghiêng về tổn thương).
- `MAX_DELTA` vẫn 5. Một lượt đổi tối đa 3 chỉ số, và chỉ đổi 3 khi có thay đổi tổn thương.

**Đo bằng harness.**
- Harness nằm ngoài repo. Story 1 (Lạc Dương & Lâm Vãn) chạy trên bản sao DB, xuất phát từ cùng một state (thương mến 50, tin cậy 45, rung động 30, nhung nhớ 15, lo sợ 10, khoảng cách 15). Mỗi kịch bản sinh 2 câu trả lời bằng đường chat thật (`prompt_state` + `build_prompt`), rồi chạy `extract_turn` thật 2 lần mỗi câu.
- Kết quả sau kiểm tra, trước → sau:

  | Kịch bản | Trước | Sau |
  |---|---|---|
  | Ghen: khoe cho học trưởng WeChat | rung động +2, nhung nhớ +3 / thương mến +1, rung động +2 | tin cậy -1, nhung nhớ +2, lo sợ +2 (4/4 lần) |
  | Bị bắt gặp nói dối | thương mến +1, tin cậy +1 / thương mến +1, nhung nhớ +2 | tin cậy -1 (có lần thêm nhung nhớ +2) / tin cậy -2, nhung nhớ +2 |
  | "Cậu đừng quản tớ nữa, phiền lắm" | thương mến -2, tin cậy -1 | thương mến -2, lo sợ +2, khoảng cách +2 (4/4) |
  | Xin lỗi sau đó | thương mến +1, tin cậy +1 | tin cậy +2, khoảng cách -2 (4/4) |
  | Hỏi "hôm nay cậu ăn gì chưa?" | thương mến +1, tin cậy hoặc rung động +1 | chỉ thương mến +1 (4/4) |
  | Ngủ gục trên vai, "không tưởng tượng được cuộc sống thiếu cậu" | thương mến +1, rung động +2 | thương mến +1/+2, rung động +2/+3, khoảng cách -1 |

- Bỏ `reason` (prompt mới, không có trường này): kịch bản xin lỗi mất tin cậy +2 (còn thương mến +1, khoảng cách -2), và một lượt hỏi han thường ngày lại đổi 3 chỉ số. Vì vậy giữ `reason`.
- **Thời gian một lời gọi:**

  | | Prompt mới (chưa có cache) | Có cache prompt |
  |---|---|---|
  | Trước | median 20s | 10s |
  | Sau | median 28s | 12s |
  | Sau, bỏ `reason` | 26s | |

  Prompt dài thêm khoảng 600 token.
- Chỗ còn yếu: kịch bản nói dối chỉ ra tin cậy -1/-2, chưa tới -3. Mức giảm phụ thuộc câu trả lời của nhân vật: một câu trả lời chỉ dịu dàng đưa thuốc, Thought không trách gì, thì cho tin cậy -1. Khoảng cách +1 có trong output thô nhưng bị phép giữ 2-3 thay đổi bỏ đi.

**Vòng sửa thứ hai (sau verifier).** Verifier chạy 7 kịch bản riêng (2 câu trả lời thật × 2 lần trích xuất, xuất phát thương mến 60, tin cậy 55, rung động 40, nhung nhớ 20, lo sợ 15, khoảng cách 10). Kết quả tìm ra:
- **Quên sinh nhật cho ra thương mến +1 ở 4/4 lần.** Câu trả lời bao dung ("tớ quen rồi", Thought "chẳng thể giận nổi") nên model thưởng. Luật "giảm khi" chưa có chuyện quên, thờ ơ, lỡ hẹn.
- **Huỷ hẹn xem phim qua tin nhắn:** 2/4 lần tin cậy không giảm.
- **Lượt thường vẫn nhích:** nhờ giảng bài cho rung động +1 ở 4/4 lần.
- **`pick_changes` xét theo dấu số học.** Khoảng cách -1 bị coi là "chiều ngược lại" nên lượt ấm lòng giữ 3 thay đổi, và "thương mến +1, khoảng cách -1" lọt qua ngoại lệ "cặp xin lỗi". Khi mọi thay đổi đều ±1, cái còn lại được chọn theo thứ tự khoá.

Đã sửa:
- **`tone`** trong schema (sau `reason`, trước số) và luật chọn theo ấm lòng / tổn thương, xem phần "Kiểm tra" ở trên. Prompt giải thích từng nhãn: `everyday` gồm chào hỏi, hỏi han, nhờ giảng bài, trêu đùa, "kể cả khi nhân vật vẫn thấy vui, ấm lòng hay muốn che chở như mọi ngày"; `hurt` gồm quên điều quan trọng, lỡ hẹn, huỷ hẹn, thờ ơ, "kể cả khi nhân vật ngoài mặt bỏ qua".
- **Prompt:**
  - `reason` hỏi thẳng người chơi vừa làm gì (quan tâm, bênh vực… hay thờ ơ, quên, lỡ hẹn…).
  - Thêm câu chung: "Chấm theo điều người chơi đã làm: nhân vật ngoài mặt cười bảo 'không sao', vẫn dịu dàng hay dung túng thì trong lòng vẫn hụt hẫng, chỉ số vẫn giảm."
  - Sửa sau: câu chung về dấu nói rõ chiều theo `WARM_SIGN`. Chuyện ấm lòng thì affection, trust, attraction tăng còn obsession, fear, aversion giảm; chuyện làm đau thì ngược lại. Câu "hụt hẫng" kết bằng "vẫn chấm như chuyện làm đau" thay cho "chỉ số vẫn giảm". Câu cũ ("làm đau thì giảm (hoặc tăng khoảng cách)") trái với ví dụ ghen (obsession 2, fear 2): model theo câu chung sẽ cho fear -2 dưới tone `hurt`, và `pick_changes` bỏ như nhiễu chiều ngược lại.
  - Thương mến giảm khi thờ ơ, quên điều quan trọng. Tin cậy giảm khi lỡ hẹn hay huỷ hẹn không báo trước. Khoảng cách tăng khi bị bỏ quên.
  - Rung động "không tăng vì những lần ngồi gần, giúp đỡ như mọi ngày".
  - Ví dụ mới: "quên ngày quan trọng / huỷ hẹn phút chót: hurt; affection -1, trust -1, aversion 1 (kể cả khi nhân vật cười bảo 'không sao')". Mỗi ví dụ ghi kèm nhãn `tone`.
- Prompt dài thêm khoảng 250 token (khoảng 2400 token cho một lượt story). `NUM_PREDICT` giữ 700.

Đo lại bằng gemma4:12b thật, trên đúng các câu trả lời đã lưu của verifier và tuner (1 lần trích xuất mỗi câu, raw → sau kiểm tra):

| Kịch bản | Trước (verifier / tuner v3) | Sau |
|---|---|---|
| Kể nhớ người yêu cũ | tin cậy -1, nhung nhớ +2 (lo sợ +2) ở 3/4; 1 lần rung động +2 | `hurt` 2/2: tin cậy -1, nhung nhớ +2, lo sợ +1 |
| Quên sinh nhật | thương mến +1 (4/4) | `hurt` 2/2: thương mến -1, tin cậy -1, khoảng cách +1 |
| Bênh vực trước lớp | thương mến +2, rung động +3, khoảng cách -1 (4/4) | `warm` 2/2: thương mến +2, rung động +3 / +2 |
| Huỷ hẹn qua tin nhắn | 2/4 không giảm tin cậy | `hurt` 2/2: thương mến -1, tin cậy -1 / -2, nhung nhớ +2 / +1 |
| DM "chào buổi sáng nha" | 0 (4/4) | `everyday` 2/2: 0 |
| Nhận chocolate của bạn khác | tin cậy -1, nhung nhớ +2, lo sợ +2 (4/4) | `hurt` 2/2: tin cậy -1, nhung nhớ +2, lo sợ +1 |
| Nhờ giảng bài | rung động +1 (4/4) | câu 2 `everyday`: 0; câu 1 `warm`: thương mến +1, rung động +2 (câu trả lời tả anh rướn sát, ngửi mùi tóc cô) |
| Ghen (WeChat) | tin cậy -1, nhung nhớ +2, lo sợ +2 | `hurt` 2/2: như cũ |
| Bị bắt gặp nói dối | tin cậy -1 / -2 | `hurt` 2/2: tin cậy -2, nhung nhớ +1 / +2, lo sợ +1 hoặc thương mến -1 |
| "Đừng quản tớ nữa" | thương mến -2, lo sợ +2, khoảng cách +2 | `hurt` 2/2: như cũ, hoặc nhung nhớ +2 thay khoảng cách |
| Xin lỗi | tin cậy +2, khoảng cách -2 | `warm`: 1 câu tin cậy +2, khoảng cách -2; câu kia raw toàn ±1 nên chỉ còn thương mến +1 |
| "Cậu ăn gì chưa?" | thương mến +1 | `warm` 2/2: thương mến +1 (vẫn một +1; model coi là ấm vì câu trả lời nhắc "sau những ngày xa cách") |
| Ngủ gục trên vai | thương mến +1/+2, rung động +2/+3, khoảng cách -1 | `warm` 2/2: thương mến +1, rung động +2 |

- Thời gian một lời gọi trích xuất (prompt mới, chưa có cache): median 35.7s, khoảng 30-40s, 26 lần. Lần đo trước là 28-30s. Một phần do prompt dài hơn; Ollama dùng chung nên số này dao động.
- Lượt `warm` toàn ±1 chỉ giữ một thay đổi, chọn theo nghĩa (`_REPAIR_ORDER`): khoảng cách, lo sợ, nhung nhớ **giảm** đứng trước, vì chúng chỉ xuất hiện khi có chuyện làm lành, còn thương mến +1 là con số model rắc vào mọi lượt. Không có dấu hiệu làm lành thì theo thứ tự khoá. Câu xin lỗi ở trên (raw thương mến +1, tin cậy +1, rung động +1, khoảng cách -1) giờ giữ khoảng cách -1 thay vì thương mến +1. Áp lại luật mới lên toàn bộ output thô đã lưu thì chỉ lượt này đổi.
- Lượt nhờ giảng bài (lần 2) lại ra `warm` ở cả hai câu trả lời, thương mến +1, rung động +2: chính nhân vật tự rướn sát lại, ngửi mùi tóc cô, còn người chơi chỉ làm như mọi chiều. Prompt thêm câu: "Chọn tone theo điều {người chơi} làm ở lượt này, không theo việc {nhân vật} vui hay rung động đến đâu: {nhân vật} tự sáp lại gần, tự thấy {người chơi} đáng yêu trong một buổi như mọi ngày thì vẫn là everyday" (tiếng Anh tương tự).

  Đo lại bằng gemma4:12b thật, 1 lần mỗi câu trả lời. Ollama lúc đó dùng chung với việc khác, nên mỗi lời gọi mất 56-102s; con số này không dùng để đo tốc độ.

  | Kịch bản | Trước câu mới | Sau câu mới |
  |---|---|---|
  | Nhờ giảng bài | `warm` 2/2: thương mến +1, rung động +2 | `everyday` 2/2: 0 |
  | "Cậu ăn gì chưa?" | `warm`: thương mến +1 | như cũ (câu trả lời nhắc "sau những ngày xa cách", người chơi chủ động rủ đi ăn) |
  | DM "chào buổi sáng nha" | 0 | 0 |
  | Quên sinh nhật | thương mến -1, tin cậy -1, khoảng cách +1 | như cũ (2/2) |
  | Nhận chocolate của bạn khác | tin cậy -1, nhung nhớ +2, lo sợ +1/+2 | như cũ (2/2) |
  | Bênh vực trước lớp | thương mến +2, rung động +2/+3 | như cũ (2/2) |
  | Ngủ gục trên vai | thương mến +1, rung động +2 | như cũ (2/2) |
  | Xin lỗi | tin cậy +2, khoảng cách -2 / khoảng cách -1 | như cũ |

- Còn lại: lượt thường ngày mà người chơi chủ động quan tâm đôi khi vẫn được gọi là `warm`, nhưng chỉ giữ một +1 nhờ luật "đều ±1 thì giữ 1".

**Chỉ dẫn diễn xuất (`directive.py`).**
- Tên nhân vật chỉ còn một lần. Câu thứ hai bắt đầu bằng đại từ dẫn truyện của nhân vật (`acting_directive(..., char_pronoun=story.narration_pronouns.character)`): "Lạc Dương …; dễ ghen, chỉ muốn giữ chặt cô bên mình. Anh còn đôi lúc thấy lòng xao động vì cô."
- Không có đại từ dùng được (trống, ngôi 1/2, hoặc trùng đại từ của người chơi) thì gộp vào câu đầu: "…, và còn đôi lúc …".
- Đại từ thật ra là tên (giới tính "khác": hồ sơ văn phong tiếng Việt để trống đại từ nên story lưu tên vào chỗ đại từ) cũng coi là không dùng được, so khớp không phân biệt hoa thường với tên nhân vật lẫn tên người chơi: nhân vật thì gộp câu như trên, người chơi thì thành "người ấy". Trước đây ra "Lạc Dương …; dễ ghen, chỉ muốn giữ chặt Lâm Vãn bên mình. Lạc Dương còn … vì Lâm Vãn.", lặp cả hai tên. Đại từ một chữ viết hoa ("Cô") được viết thường vì nằm giữa câu.
- Tiếng Anh: chỉ "he"/"she" thành "He …/She …", vì động từ trong bảng luật chia ngôi thứ ba số ít. Các trường hợp khác gộp vào câu đầu thành một danh sách: "…, A, and B." (một nỗi lòng: "…, and A."), không nối ", and" hai lần.

### 10.6 Prefill prompt chat khi rảnh

Verifier đo §10.1 trên gemma4:12b thật: tóm tắt trước khúc chạy đúng, nhưng mỗi khúc vẫn có **hai** lượt chậm (lượt cửa sổ dịch và lượt ngay sau nó, 49 → 36s và 27 → 31s), còn lượt thường khoảng 12s chứ không phải ~4s. Nguyên nhân nằm ở cache của Ollama, không phải ở prompt: phát lại các prompt đã lưu thẳng vào Ollama (không có job nào của app) vẫn ra đúng như vậy. Model có sliding window, nên Ollama chỉ dùng lại cache tới chỗ prompt mới rẽ khỏi prompt cũ khi chỗ đó nằm gần cuối phần đã đọc. Prompt chat lượt sau luôn rẽ ở ghi chú F trong lượt người chơi trước, và job trích xuất/tóm tắt chen giữa hai lượt cũng đẩy prompt chat ra khỏi cache.

**Cách sửa.**
- `StateService.next_prompt_prefix(story)` dựng phần đầu prompt chat của lượt kế tiếp: system và lịch sử tới câu trả lời cuối của nhân vật, bỏ lượt người chơi (chưa viết) cùng ghi chú F. Lượt người chơi giả dài bằng **trung vị** 5 lượt người chơi gần đây (`_prefill_user_chars`), không phải "dài nhất trong 3 lượt + 120" như `summary_target`. Đoán dư thì hợp cho tóm tắt (làm sớm một lượt không sao), nhưng với prefill thì đoán cửa sổ dịch mà lượt thật không dịch (hay ngược lại) là lệch ngay ở system, mất trắng. Trung vị làm sai lệch giữa lượt giả và lượt thật nhỏ nhất. Người chơi viết lượt dài cỡ thường lệ thì phần đầu trùng prompt thật, kể cả ở lượt cửa sổ dịch (cửa sổ mới kèm tóm tắt mới). Chỉ lượt dài hay ngắn khác thường rơi đúng mốc dịch mới lệch, và khi đó lượt ấy đọc lại cả prompt như không có prefill. Tóm tắt luôn đã sẵn khi phần đầu dịch, vì phép đoán của `summary_target` dài hơn. `num_predict` 1, `num_ctx` như chat.
- Worker (`Worker.prefill`): khi hàng đợi rỗng, nó gửi phần đầu đó cho model chat của story. Đây không phải job trong DB. Lỗi thì chỉ ghi log, không bao giờ raise.
  - Chỉ prefill **một** story: story của lượt chat hay lượt "Nhận gợi ý" gần nhất (chưa có thì story của job vừa chạy). Cache của Ollama chỉ giữ một prompt, nên job của story khác (tạo story, sửa, rebuild) không làm worker prefill story đó. Job đó vẫn có thể đẩy cache ra, nên sau mọi job worker hẹn prefill lại story đang chơi (rẻ nếu cache còn).
  - Lượt chat hay gợi ý bắt đầu thì prefill đang chạy bị huỷ; đang có lượt stream thì không prefill. Kết thúc lượt nào cũng hẹn prefill lại story đó: lượt chat thì sau job trích xuất, gợi ý (gọi model chat với prompt khác, không xếp job) thì ngay khi rảnh.
  - Lịch sử đổi (xoá lượt, lật variant, sửa message của nhân vật hay của người chơi) thì prefill đang chạy của story đó bị huỷ (phần đầu đã cũ, không chặn job trích xuất mới) và story được hẹn prefill lại với phần đầu mới.
- Chỉ bật với Ollama thật (`create_app` không nhận LLM tiêm vào); test bật bằng `Worker(..., prefill=True)`.
- Test: `test_prefill_prefix_is_exactly_the_next_prompt_head` (30 lượt cùng độ dài, có lượt cửa sổ dịch) kiểm tra phần đầu gửi trước trùng từng message với prompt thật của lượt sau, trừ message cuối. Lệch một byte là Ollama đọc lại từ đó. `test_prefill_prefix_matches_when_player_writes_a_typical_turn` (45 lượt, độ dài 80 ký tự đều, hoặc phần lớn 30 ký tự xen 400) kiểm tra điều đó ở mọi lượt người chơi dài bằng trung vị, kể cả lượt cửa sổ dịch. Với cách đoán cũ (dài nhất + 120) test này lệch ở lượt 24 và 30. Các test trong `test_jobs.py` kiểm tra: prefill chạy sau job, tắt mặc định, bị lượt chat huỷ, nuốt lỗi, chỉ prefill story đang chơi, prefill lại sau gợi ý, huỷ và hẹn lại khi lịch sử đổi.

**Đo trên gemma4:12b thật** (story 3 dài, lượt 0-34, `num_ctx` 8192):

- Phát lại prompt đã lưu thẳng vào Ollama (P = prompt thật của lượt, R = phần đầu prefill của lượt đó):

  | Thứ tự | Đọc prompt |
  |---|---|
  | P38 → P40, không prefill (verifier) | 47.7s → **52.0s** |
  | P38 → R40 → P40 | 47.7s → 47.5s → **4.4s** |
  | → R42 → P42 | 4.8s → **4.9s** |

- Chạy qua app (server thật, chờ hàng đợi và prefill xong rồi mới gửi lượt sau). TTFT là thời gian tới token đầu:

  | Lượt | Không prefill (verifier) | Có prefill, Ollama rảnh | Có prefill, Ollama đang bận việc khác |
  |---|---|---|---|
  | 36 (lần gọi đầu, chưa có cache) | 41.2s | 57.2s (prefill sau đó 45s) | 57.9s (prefill 58s) |
  | 38 (cửa sổ dịch) | 49.2s | 30.6s (prefill sau đó 4.5s) | 101.8s (prefill 52s) |
  | 40 (ngay sau lượt dịch) | **35.7s** | **8.0s** | 82.4s (prefill 17.6s) |
  | 42 | 12.3s | | 16.6s |

  - Khi Ollama rảnh, lượt ngay sau lượt dịch nhanh lại (35.7 → 8.0s), và prefill chạy trong lúc người chơi đang gõ. Lần chạy này dừng sau 3 lượt; chưa đo lượt dịch khúc thứ hai.
  - Cột cuối: trong lúc đo có một tiến trình khác liên tục gửi lời gọi cỡ trích xuất (2300-2700 token) vào cùng Ollama. Các lời gọi đó đẩy phần đã prefill ra khỏi cache: lượt 40 chỉ khớp tới token 4695, đúng chỗ prompt lượt 38 rẽ, tức là không còn gì của prefill. Ở lượt 42, prefill khớp 5455 token nhưng Ollama chỉ dùng lại được tới 5101 (điểm lưu gần nhất của sliding window) và đọc lại 750 token.
- Giới hạn:
  - Prefill chỉ giúp khi người chơi gõ lâu hơn thời gian prefill. Lượt ngay sau lần đọc lại cả prompt, prefill mất khoảng 45-55s.
  - Khi Ollama dùng chung với việc khác (app khác, script), cache có thể bị đẩy ra trước lượt sau.
  - Ollama chạy model chat thêm một lời gọi mỗi lượt. Lời gọi này rẻ khi cache còn, và bị huỷ ngay khi người chơi gửi tin.

**Sửa lần 2: prefill raw, kết thúc đúng chỗ prompt thật rẽ ra.** Đo lại qua app (story 3, lượt 36-54, prefill bật và tắt) thấy lượt ngay sau lượt dịch đã nhanh (khoảng 8s), nhưng chính lượt cửa sổ dịch vẫn 26-30s, dù prefill đã đoán đúng cửa sổ mới.

- Nguyên nhân (đã chứng minh bằng lời gọi thẳng vào Ollama 0.40.16, runner mlx, gemma4:12b, `num_ctx` 8192). Với model sliding window, runner không cắt cache về một vị trí tuỳ ý. Nó chỉ khôi phục tại các điểm chụp của request trước: chỗ request đó bắt đầu đọc, và cuối prompt của nó trừ 4 token. Prefill qua `/api/chat` luôn kết thúc bằng generation prompt `<|turn>model\n<|channel>thought\n<channel|>`. Prompt thật lại nối tiếp bằng `<|turn>user\n...`, nên rẽ khỏi prefill 6 token trước cuối, tức là trước điểm chụp cuối. Kết quả là lượt thật chỉ dùng lại được tới chỗ prefill bắt đầu đọc. Lượt thường thì chỗ đó gần cuối (đọc lại khoảng 800 token), còn trước lượt dịch thì prefill phải đọc lại gần hết, nên lượt dịch gần như không được gì. Phép phát lại "R40 → P40 4.4s" ở trên không mâu thuẫn: R40 bắt đầu đọc ở gần cuối P38.

  | Thí nghiệm (prompt lượt 44, 4941 token, cache lạnh) | Lượt thật dùng lại | Đọc lại | Đọc prompt |
  |---|---|---|---|
  | `/api/chat` prefill (như cũ) → chat thật | 6 | 4935 | 46.6s |
  | `/api/chat` prefill hai lần → chat thật | 6 | 4935 | 46.6s |
  | `/api/generate` `raw`, văn bản kết thúc ở `<turn|>\n` của câu trả lời cuối → chat thật | 4432 | 509 | **4.8s** |

- Cách sửa:
  - `lyris/llm/render.py`: `render_prefix(renderer, messages)` dựng lại đúng văn bản `/api/chat` render, không kèm generation prompt. Hiện chỉ có renderer `gemma4-large` (gemma4:12b): `<bos>`, rồi mỗi message là `<|turn>{role}\n{nội dung đã trim}<turn|>\n`, với assistant → `model` và bỏ khối `<|channel>...<channel|>`. Đã đối chiếu token-từng-token với `/api/chat` thật (`matched == total`), kể cả khoảng trắng đầu/cuối, tab, NBSP, khối suy nghĩ và câu trả lời rỗng. Renderer khác trả None.
  - `OllamaClient.prefill_prefix(model, messages, options=...)`: lấy renderer qua `/api/show` (nhớ theo model), rồi gửi `/api/generate` với `raw: true`, stream, `num_predict` 1 và `num_ctx` như chat. Trả False khi chưa render được model đó. Lỗi thì raise LLMError.
  - `Worker.prefill` gọi `prefill_prefix` nếu client có. Khi nó trả False hoặc lỗi (trừ khi bị huỷ), worker prefill bằng `chat_stream` như cũ. Mọi quy tắc khác giữ nguyên: không bao giờ raise, lượt chat bắt đầu thì huỷ. `FakeLLM.prefill_prefix` ghi vào `calls` kèm `"raw": True`; `FakeLLM(raw_prefill=False)` thì trả False.
  - Test: `test_render_prefix_gemma4_matches_ollama_chat_template`, `test_prefill_prefix_*`, `test_fake_llm_prefill_prefix` (test_ollama_client.py), và `test_prefill_uses_raw_prefix_and_falls_back_to_chat` (test_jobs.py).
- Đo lại qua app: cùng `base.db`, cùng 20 lượt người chơi, chờ hàng đợi và prefill xong rồi mới gửi lượt sau. TTFT tính bằng giây.

  | Lượt | Không prefill | Prefill `/api/chat` (cũ) | Prefill raw (mới) | Raw: đọc lại (token) |
  |---|---|---|---|---|
  | 36 (cửa sổ dịch, lần gọi đầu, chưa có cache) | 45.1 | 46.4 | 46.3 | 4681 |
  | 38 | 34.2 | 32.5 | **5.3** | 508 |
  | 40 | 34.7 | 8.4 | **4.2** | 368 |
  | 42 | 12.4 | 8.5 | 4.7 | 433 |
  | 44 (cửa sổ dịch) | 47.5 | 30.0 | **4.7** | 404 |
  | 46 | 32.1 | 7.9 | 4.7 | 390 |
  | 48 | 11.8 | 8.5 | 4.8 | 440 |
  | 50 (dịch ở hai lần chạy cũ) | 27.6 | 26.1 | 4.7 | 422 |
  | 52 (dịch ở lần chạy mới) | 29.4 | 8.5 | **4.6** | 439 |
  | 54 | 13.8 | 9.1 | 5.3 | 500 |

  - Câu trả lời được sample (temperature 0.8) nên độ dài khác nhau giữa các lần chạy. Ở lần chạy mới, lần dịch thứ hai rơi vào lượt 52 thay vì 50. Lần chạy ngắn trước đó (cũng prefill raw) cho lượt 44 dịch: 5.2s.
  - Mọi lượt sau lượt gọi đầu đều 4.2-5.3s, kể cả hai lượt cửa sổ dịch. Mỗi lượt chỉ đọc lại 370-510 token: lượt mới của người chơi kèm ghi chú F, cộng 4 token cuối.
  - Prefill thường mất 3-5s trong lúc người chơi gõ. Prefill trước lượt dịch phải đọc lại cả prompt mới, mất 41-43s. Người chơi gửi sớm hơn thì prefill bị huỷ, và lượt dịch đọc lại như khi không prefill.

- Giới hạn: model có renderer khác `gemma4-large` vẫn prefill bằng `/api/chat` (lượt dịch còn chậm). Muốn thêm renderer thì phải đối chiếu với `/api/chat` thật trước, vì lệch một token là mất trắng. Bản Ollama khác có thể render khác; khi đó lượt sau đọc lại như chưa prefill, app vẫn chạy đúng.

### 10.7 Trích xuất cảm xúc nhanh hơn

Lần đo cuối của §10.5 (harness `fixemo`, 20 lời gọi) cho median **68s** một lời gọi `extract_turn`, trong khi trước đó chỉ 28-36s.

**Nguyên nhân 68s: máy chậm, không phải prompt.** Đọc log Ollama (`~/.ollama/logs/server.log`):
- Trong lần đo đó, Ollama chỉ nhận đúng 20 request `/api/chat` của harness, lần lượt từng cái, không có request nào chạy song song.
- Prompt dài đúng như bây giờ (2464-2588 token). Nhưng tốc độ đọc prompt chỉ còn **54 token/s** (bình thường 107) và tốc độ sinh cũng giảm một nửa. Cùng prompt đó chạy lại lúc máy rảnh mất 39s.
- Từ 14:47 tới 18:20 ngày 2026-11-13, mọi request đều chậm như vậy, rồi tự hết mà không đổi code hay khởi động lại Ollama. Có lẽ do RAM hoặc GPU đang bị việc khác chiếm (swap lúc đó dùng 7.8/9.2GB).
- Kết luận: cả hai tốc độ đều giảm một nửa trên đúng một prompt, nên nguyên nhân nằm ở máy chứ không phải ở prompt. Dòng tính cách và bí mật chỉ khoảng 180 token, tức khoảng 1.7 giây.

**Một lời gọi tốn gì (gemma4:12b, runner mlx, lúc máy bình thường):**

| Phần | Bản §10.5 | Bây giờ |
|---|---|---|
| Prompt | ~2470 token, đọc ~22s; không dùng lại được cache (luật nằm sau lượt cần đọc) | system ~2070 token (luật, cố định cho cả story) + user ~450-700 token. Có cache phần system: đọc ~4-6s |
| Output | ~235 token: JSON thụt lề (23 dòng), `reason` 38-40 từ; ~16.6s | 120-166 token: JSON một dòng, `reason` 17-28 từ; ~9-11s |
| Grammar JSON schema | | Không tốn thêm: cùng prompt đã cache, `format` = schema, `"json"` hay không có đều ~14 token/s |
| `num_predict` | 700, chưa bao giờ chạm tới | 500 |

Trong prompt system, luật chấm cảm xúc chiếm ~1380 token (dòng `reason` ~120, `tone` ~260, luật từng chỉ số ~570, ví dụ ~290); luật cảnh, ký ức, fact ~450; nhân vật ~180.

**Thay đổi (`lyris/state/extract.py`):**
- `_split_prompt`:
  - System chứa vai trò, nhân vật và toàn bộ luật, giống hệt nhau giữa mọi lượt của một story (Story lẫn DM). Dòng "Lượt nhắn tin (DM): location…" giờ luôn có mặt.
  - User chứa kiểu lượt, trạng thái trước lượt, tóm tắt, fact và lượt cần đọc.
- `reason`: "đúng một câu ngắn (dưới 25 từ)" thay cho "1-2 câu". Câu mở đầu dặn "JSON gọn trên một dòng (không xuống dòng, không thụt lề)". Không dùng `maxLength` trong schema, vì grammar của Ollama làm hỏng escape khi có nó.
- **Mức mẫu sau lượt cần đọc** (`_RECAP_VI` / `_RECAP_EN`, ~170 token, không có ở lời mở đầu):
  - Vấn đề: khi luật nằm ở system, xa lượt cần đọc, model chấm nhẹ tay hơn. Lời xin lỗi chỉ ra toàn ±1 (4/4 lần), nên sau kiểm tra chỉ còn khoảng cách -1; lượt bênh vực có lần cũng chỉ còn ±1.
  - Cách sửa: thêm một dòng ở cuối user, nhắc lại các ví dụ sẵn có. Có thêm mẫu "được bênh vực trước mọi người: warm, affection 2, attraction 2"; nhãn này đã có trong luật `tone`, chỉ chưa có số.
  - Câu cuối của dòng nhắc lại hai luật đã có: thất hứa, lỡ hẹn, huỷ hẹn thì tin cậy giảm; xin lỗi thật lòng thì khoảng cách giảm 2, tin cậy tăng.
  - Kết quả đo: xin lỗi ra tin cậy +1, khoảng cách -2 ở 7/7 lần (khi chưa có câu cuối là 2/4).
- `pick_changes`, lượt `hurt`: các thay đổi cùng cỡ thì **tin cậy giảm đứng trước** (`_HURT_ORDER`).
  - Lý do: với prompt mới, model hay ra cụm "thương mến -1, tin cậy -1, rung động -1" kèm nhung nhớ +2, lo sợ +2. Theo thứ tự khoá, thương mến -1 được giữ còn tin cậy -1 bị bỏ.
  - Thương mến -1 là con số model rắc vào gần như mọi lượt tổn thương. Tin cậy giảm mới cho biết chuyện gì đã xảy ra, và ví dụ ghen trong prompt cũng đòi đúng nó. Cách này giống `_REPAIR_ORDER` của lượt `warm`.
- `NUM_PREDICT` 700 → 500. Output đo được cao nhất là 166 token với các kịch bản thường (khi đó chưa có fact). Giới hạn này chỉ để dừng sớm khi model viết lan man.
- Kiểm tra độc lập: lượt dày fact (hai bên kể tiểu sử, ~20 fact) làm model viết 14+ fact, chạm 500 token, `done_reason=length` → mất cả lượt trích xuất. Sửa: `SCHEMA.facts` có `"maxItems": MAX_FACTS` (3), khớp với `validate` vốn chỉ giữ 3; lượt đó còn 309 token. Chỉ đổi grammar nên không ảnh hưởng cache phần system. Test `test_schema_caps_facts_so_output_fits_num_predict`.

**Thời gian một lời gọi** (`extract_turn` thật qua `OllamaClient`, máy bình thường, harness `fixemo`):

| | Median | Khoảng |
|---|---|---|
| Bản §10.5 trong lần đo 68s (máy chậm) | 68.0s | 62-78s |
| Bản §10.5, prompt chưa có cache, máy bình thường | 39s | 38.9-39.4s |
| Bây giờ, prompt chưa có cache | ~33s | 32-35s |
| Bây giờ, có cache phần system (20 kịch bản chạy liền nhau) | **15.1s** | 11-17s |

**Cache trong app thật** (đo bằng chuỗi giống app: chat ~2.5k token → prefill → trích xuất):
- Phần system được dùng lại khi chỉ có một lời gọi chat chen giữa (15.9s).
- Khi có cả chat lẫn prefill chen giữa thì không dùng lại được (35.4s). Có một lần đọc lại cả prompt mà không rõ lý do, dù không có gì chen giữa (32.9s).
- Vậy trong app, mỗi lời gọi mất khoảng 15s hoặc 33s, tuỳ cache còn hay không. Worker còn gửi thêm tóm tắt (≤ 1500 ký tự) và tối đa 12 fact trong user; phần này không cache được, thêm vài giây.

**Kết quả cảm xúc** (2 câu trả lời mỗi kịch bản, 1 lần trích xuất mỗi câu, sau kiểm tra):

| Kịch bản | Bản §10.5 (lần đo 68s) | Bây giờ |
|---|---|---|
| Quên sinh nhật | thương mến -1, tin cậy -1, khoảng cách +1 (2/2) | thương mến -1, tin cậy -1, nhung nhớ +1 (2/2) |
| Bênh vực trước lớp | thương mến +2, rung động +2 (2/2) | như cũ (2/2) |
| Huỷ hẹn qua tin nhắn | thương mến -1, tin cậy -1/-2, rung động -1 | thương mến -1, tin cậy -1, nhung nhớ +1 (2/2) |
| Nhận quà của bạn khác (ghen) | thương mến -1, nhung nhớ +2, lo sợ +2 / thương mến -1, tin cậy -1, nhung nhớ +2 | tin cậy -1, nhung nhớ +2, lo sợ +2 (2/2), đúng ví dụ ghen |
| Bị bắt gặp nói dối | tin cậy -2 (+ thương mến -1, nhung nhớ) | tin cậy -2 / **-3** (+ nhung nhớ, lo sợ) |
| Ngủ gục trên vai | thương mến +1, rung động +2 (2/2) | như cũ (2/2) |
| Xin lỗi | tin cậy +2, khoảng cách -2 (2/2) | tin cậy +1, khoảng cách -2 (2/2), đúng ví dụ trong prompt |
| "Cậu ăn gì chưa?" | **thương mến +2, tin cậy +1** / thương mến +1 | khoảng cách -1 / thương mến +1 (luôn chỉ một thay đổi ±1) |
| DM "chào buổi sáng" | 0 (2/2) | 0 (2/2) |
| Nhờ giảng bài | 0 (2/2) | 0 (2/2) |

- "Cậu ăn gì chưa?" không còn ra hai chỉ số tăng: trong 6 lần đo gần nhất, mỗi lần nhiều nhất một thay đổi ±1. Lý do là `reason` ngắn hơn và luật mới đặt trước lượt cần đọc. Không cần sửa thêm phần kiểm tra.
- Hai chỗ khác bản §10.5: xin lỗi cho tin cậy +1 thay vì +2, và quên sinh nhật có nhung nhớ +1 thay cho khoảng cách +1.

### 10.8 Story và DM chung một dòng thời gian (2026-11-13)

Vấn đề: người chơi nhắn tin (DM) với Tần Dương, nhân vật xưng tên qua tin nhắn; quay lại Story Mode, Thought của nhân vật lại nói "mình chưa hề nói tên với ai". Lượt DM vẫn nằm trong lịch sử gửi model nhưng không có gì đánh dấu đó là tin nhắn điện thoại, nên model ở Story Mode không coi chúng là chuyện đã xảy ra.

Sửa:
- `Template.dm_label` (vi "[Tin nhắn điện thoại]", en "[Text message]"). Ở Story Mode, `build_prompt` đặt nhãn trước mỗi lượt DM (`_to_item(msg, dm_label)`). Ở DM Mode không gắn nhãn (model sẽ bắt chước nhãn vào tin của nó).
- `Template.dm_note(ctx)`: một dòng ở đầu phần state của khối F, chỉ khi Story Mode và cửa sổ lịch sử có lượt DM: lượt có nhãn là tin nhắn thật đã gửi, nhân vật nhớ mọi điều trong đó, lượt này vẫn là dẫn truyện. Đặt ở F chứ không ở khối A, để story không có DM giữ nguyên từng byte (golden test, cache prefix).
- Mốc khúc (`window_boundaries`, `costs` trong `build_prompt`) luôn đo với nhãn, nên giống nhau ở hai mode.
- Tóm tắt (`memory/summarize._transcript`) ghi "Tên [Tin nhắn điện thoại]: ..." cho lượt DM.
- Test: `tests/test_dm_continuity.py`. Chưa thử trên model thật (người dùng đang dùng app); sẽ thử cùng đợt kiểm tra Phase 4.
