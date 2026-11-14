# Phase 4: Sổ thế giới (lorebook) và tuỳ chọn không đọc suy nghĩ

Mục tiêu (plan.md §10, Phase 4): nhắc tới một người, một nơi hay một chuyện cũ trong thế giới của nhân vật thì nhân vật trả lời đúng theo lore, và không biết điều nó không được biết. Kèm một yêu cầu của người dùng (2026-11-13): "thêm một lựa chọn không đọc suy nghĩ".

Tài liệu này là thiết kế, chưa có code. Kiểu dữ liệu ở §2 là hợp đồng giữa backend và frontend; muốn đổi thì ghi lý do ở cuối file như phase3.md.

Hai phần độc lập, làm song song được:
- **A. Sổ thế giới**: §1-§11.
- **B. Không đọc suy nghĩ**: §12.

Thuật ngữ: trong code dùng `lore`, `keys`, `known_by`. Trên giao diện **không bao giờ** hiện các chữ đó. Giao diện dùng "Thế giới", "Mục thế giới", "Từ khoá gợi nhớ" và "Ai biết điều này".

## 0. Ràng buộc

- **Cache prompt của Ollama** (phase3.md §10.6): model sliding window chỉ dùng lại cache tới chỗ prompt mới rẽ khỏi prompt cũ, và chỉ khôi phục tại điểm chụp (chỗ request bắt đầu đọc, và cuối prompt trừ 4 token). Đổi bất kỳ thứ gì trong system message là đọc lại cả prompt (~45s). Vì vậy:
  - lore **không bao giờ** nằm trong system message;
  - lore không làm điểm bắt đầu cửa sổ lịch sử nhảy (phần dự phòng cố định, §6.4);
  - prefill vẫn phải là phần đầu đúng từng byte của prompt thật (§6.5);
  - lịch sử của lượt sau không chứa khối lore của lượt trước, nên prompt lượt sau rẽ khỏi prompt lượt này ngay ở đầu lượt người chơi vừa rồi. Chỗ rẽ đó phải nằm **sau** một điểm chụp còn dùng được, nếu không prefill của lượt sau phải đọc lại cả prompt (§6.5, lý do mặc định không gửi trước phần lore).
- **Một model chat, 8192 token.** Khối lore tối đa 520 token, tính cả dòng mở và dòng đóng (§6.2 giải thích vì sao không phải 700).
- **Không gọi model** trong Phase 4: so khớp chỉ là chuỗi, không có embedding hay lời gọi phân loại. Lượt chat không chậm thêm vì phải chờ model.
- **Máy của người dùng đang chạy app** (uvicorn `--reload` ở 8000, vite ở 5173). Thứ tự làm ở §15 giữ cây code luôn import được; migration 0007 được viết **sau cùng**, khi đã chạy thử trên DB tạm, vì nó sẽ tự áp vào DB thật khi app tải lại.

## 1. Dữ liệu: migration `0007_lore.sql`

```sql
-- Phase 4: sổ thế giới theo nhân vật, lượt nào đã mở mục nào, và tuỳ chọn không đọc suy nghĩ.
-- Chỉ thêm cột/bảng mới (story và card cũ giữ nguyên).

-- B. Hiện thẻ suy nghĩ của nhân vật trong story (1) hay không (0). Chỉ là cách hiển thị: model vẫn viết
-- [Thought: ...], chữ đã lưu không đổi.
ALTER TABLE stories ADD COLUMN show_thoughts INTEGER NOT NULL DEFAULT 1 CHECK (show_thoughts IN (0, 1));

CREATE TABLE lore_entries (
  id            INTEGER PRIMARY KEY,
  card_id       INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
  -- Khoá ổn định trong một card. "md:<loại>/<slug tiêu đề>" (nhập từ world.md), "book:<n>-<slug>"
  -- (character_book của Card V2), "manual:<12 hex>" (tự thêm). Nhập lại cập nhật theo slug, không nhân đôi.
  slug          TEXT NOT NULL,
  title         TEXT NOT NULL,
  category      TEXT NOT NULL DEFAULT 'lore' CHECK (category IN ('lore', 'character', 'place')),
  keys_json     TEXT NOT NULL DEFAULT '[]',     -- ["Hôn ước", "đính hôn", ...]
  known_by_json TEXT NOT NULL DEFAULT '["*"]',  -- "*" mọi người, "{{user}}" người chơi, hoặc tên nhân vật
  content       TEXT NOT NULL DEFAULT '',       -- được có {{user}} / {{char}}
  source        TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'world_md', 'card_book')),
  edited        INTEGER NOT NULL DEFAULT 0 CHECK (edited IN (0, 1)),  -- mục nhập từ file đã được sửa tay
  -- Mục nhập từ file/card mà người dùng đã xoá: giữ hàng làm "bia mộ" để nhập lại không thêm lại nó.
  -- Hàng removed = 1 không bao giờ được so khớp, liệt kê, export hay đếm (§4.4, §7).
  removed       INTEGER NOT NULL DEFAULT 0 CHECK (removed IN (0, 1)),
  enabled       INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  priority      INTEGER NOT NULL DEFAULT 0,     -- lớn hơn thì được chọn trước khi hết chỗ
  position      INTEGER NOT NULL DEFAULT 0,     -- thứ tự hiển thị; Card V2 insertion_order
  extra_json    TEXT,                           -- trường Card V2 chưa dùng (secondary_keys, constant, ...) để export lại
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL,
  UNIQUE (card_id, slug)
);
CREATE INDEX idx_lore_entries_card ON lore_entries(card_id, position, id);

-- Mục nào đã được so khớp ở lượt nào. Gắn với message assistant mà prompt của nó đã dùng mục đó.
-- Chỉ đọc qua message active (giống state_events), nên regenerate / lật variant / xoá tự rollback.
CREATE TABLE lore_hits (
  id          INTEGER PRIMARY KEY,
  story_id    INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  entry_id    INTEGER NOT NULL REFERENCES lore_entries(id) ON DELETE CASCADE,
  -- carried: trong khối lore, đã gửi trước nhờ prefill; fresh: trong khối lore, vừa được lượt người chơi
  -- gợi ra; unsent: khớp nhưng không gửi (chỉ người chơi biết, người khác biết, hoặc hết chỗ).
  slot        TEXT NOT NULL CHECK (slot IN ('carried', 'fresh', 'unsent')),
  created_at  TEXT NOT NULL,
  UNIQUE (message_id, entry_id)   -- ghi lại (lượt bị ngắt rồi lưu) không nhân đôi
);
CREATE INDEX idx_lore_hits_story ON lore_hits(story_id, message_id);
CREATE INDEX idx_lore_hits_message ON lore_hits(message_id);  -- CASCADE khi xoá message (truncate_from)
CREATE INDEX idx_lore_hits_entry ON lore_hits(entry_id);
```

- Version mới nhất là **7**. Sửa các test đang khẳng định 6: `LATEST` trong `test_repo.py`, `test_integration_phase2.py` (2 chỗ), `test_accounts.py:257`.
- `created_at` / `updated_at` dùng cùng hàm giờ ISO của `Repo` như các bảng khác.
- `stories.show_thoughts` có mặc định 1, nên mọi story cũ vẫn hiện suy nghĩ như trước.
- Không đụng tới `state_events.kind`. CHECK của nó chỉ đổi được bằng cách dựng lại bảng, quá rủi ro với DB đang chạy. Vì vậy dữ liệu "đã mở khoá" nằm ở bảng riêng `lore_hits`.
- **Thử migration** trên DB tạm trong `scratchpad/p4/`: DB dựng bằng `migrate(conn, target=6)` cộng dữ liệu kiểu demo, rồi `migrate(conn)`. Mọi hàng cũ phải còn đủ, `show_thoughts = 1`. Không đọc hay copy `data/lyris.db`. Khi file 0007 còn nằm ngoài `migrations/`, test vá `lyris.db.connection.MIGRATIONS_DIR` sang một thư mục tạm chứa bản sao 0001-0006 cộng 0007 nháp.
- **Áp vào app đang chạy (uvicorn `--reload`)**:
  - `--reload` chỉ theo dõi file `.py`, nên chép `0007_lore.sql` vào `migrations/` chưa làm gì cả. Migration được áp ở lần tải lại kế tiếp (`create_app` gọi `migrate`), tức lần lưu `.py` kế tiếp.
  - Code đọc hay ghi cột/bảng mới (`_row_to_story` đọc `show_thoughts`, `create_story` ghi nó, mọi câu SQL trên `lore_*`) **không được** tới app trước migration. Nếu tới trước, mọi route story của người dùng trả 500 (`IndexError: No item with that key`).
  - Thứ tự đúng ở §15 bước 4. Ngoài ra `_row_to_story` đọc phòng thủ: `bool(row["show_thoughts"]) if "show_thoughts" in row.keys() else True`.
- **Migration là cuối cùng ngay khi nằm trong `migrations/`**: mọi cột cần cho Phase 4 (kể cả `removed`, chỉ mục `message_id`, `UNIQUE`) phải có trong bản đầu tiên.

## 2. Kiểu dữ liệu (`backend/lyris/models.py`, khối "Phase 4")

```python
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
    """Body tạo/sửa (POST, PUT). extra="forbid". Backend làm sạch: cắt khoảng trắng, bỏ khoá rỗng và trùng."""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=MAX_LORE_TITLE)
    category: LoreCategory = "lore"
    keys: list[str] = Field(default_factory=list, max_length=MAX_LORE_KEYS)
    known_by: list[str] = Field(default_factory=lambda: ["*"], min_length=1, max_length=MAX_LORE_KNOWN_BY)
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
    # Câu nhắc dễ hiểu cho Studio, ví dụ 'Từ khoá "mẹ" chỉ có một chữ nên sẽ gợi rất thường xuyên.'
    warnings: list[str] = Field(default_factory=list)


class LoreImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=MAX_LORE_IMPORT_BYTES)
    filename: str | None = Field(default=None, max_length=200)
    dry_run: bool = False
    # Mặc định chỉ thêm/cập nhật. Xoá mục không còn trong file chỉ khi người dùng tự đánh dấu ở bước xem trước
    # (card có thể có hai file thế giới; nhập file thứ hai không được xoá mục của file thứ nhất).
    delete_missing: bool = False


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
    kept_edited: int = 0   # mục từ file đã được sửa tay: không ghi đè, không xoá
    deleted: int = 0       # mục từ file (chưa sửa tay) không còn trong file mới, chỉ khi delete_missing
    missing: int = 0       # mục từ file không còn trong file mới (xoá được nếu bật delete_missing)
    skipped_removed: int = 0  # mục bạn đã xoá, không thêm lại
    player_only: list[str] = Field(default_factory=list)  # người/nơi nhập là "Chỉ bạn" vì trùng điều chỉ bạn biết (§4.3)
    dropped_sentences: list[str] = Field(default_factory=list)  # câu bị bỏ vì lộ điều chỉ bạn biết, dạng "Tên mục: câu…" (≤ 50)
    items: list[LoreImportItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)     # câu thông tin, ví dụ bỏ phần "Bí mật"
    warnings: list[str] = Field(default_factory=list)  # mục không có từ khoá, từ khoá một chữ...


class LoreSnippet(BaseModel):
    """Một mục đã chọn cho prompt của lượt này (lyris/lore/select.py)."""
    entry_id: int
    title: str
    text: str            # nội dung đã thay {{user}}/{{char}}, gộp dòng, cắt ≤ MAX_LORE_ITEM_CHARS
    private: bool        # chỉ nhân vật biết: prompt dặn không tự kể ra
    tokens: int
    slot: Literal["carried", "fresh"]


class PromptLore(BaseModel):
    """Lore đưa vào build_prompt. reserve_tokens = phần dự phòng cố định cho khối lore (0 = card không có
    mục nào gửi được cho model; khi đó prompt giống hệt Phase 3)."""
    carried: list[LoreSnippet] = Field(default_factory=list)
    fresh: list[LoreSnippet] = Field(default_factory=list)
    reserve_tokens: int = 0
    unsent_ids: list[int] = Field(default_factory=list)  # khớp nhưng không gửi (ghi lore_hits slot 'unsent')


class LoreUse(BaseModel):
    """Một mục đã vào prompt (ghi trong BuiltPrompt và snapshot)."""
    entry_id: int
    title: str
    slot: Literal["carried", "fresh"]
    tokens: int


class UnlockedLore(BaseModel):
    """Một mục đã mở khoá trong story (GET /api/stories/{id}/lore)."""
    entry_id: int
    title: str
    category: LoreCategory
    audience: Literal["everyone", "character", "player"]   # "others" không bao giờ trả về
    content: str          # đã thay {{user}} = tên persona, {{char}} = tên nhân vật
    first_turn: int       # turn_index nội bộ, chỉ để nhảy tới; giao diện KHÔNG in số này (§11.2)
    last_turn: int
    turns: int            # số lượt đã gợi ra


class StoryLore(BaseModel):
    available: bool       # card có ít nhất một mục đang bật
    can_edit: bool        # card thuộc account (không phải mẫu chưa cài): giao diện mời "Thêm trong Studio"
    card_id: int
    entries: list[UnlockedLore]   # mới gợi ra gần nhất trước


class LoreSummary(BaseModel):
    """Phần "Thế giới" ở hồ sơ nhân vật: chỉ tên người và nơi chốn ai cũng biết, không nội dung."""
    total: int            # mục đang bật
    people: list[str]     # category 'character', audience everyone, tối đa 8
    places: list[str]     # category 'place', audience everyone, tối đa 8
    people_more: int = 0  # số tên không liệt kê, để giao diện in "+N" (thêm khi làm backend)
    places_more: int = 0
```

Đổi kiểu có sẵn:

| Kiểu | Thêm |
|---|---|
| `Story` | `show_thoughts: bool = True` |
| `BuiltPrompt` | `lore_head: str \| None = None` (đầu message user cuối mà prefill được gửi trước, §6.5), `open_last: bool = False` (message cuối là lượt user còn mở, chỉ cho prefill; chỉ True khi `LORE_PREFILL_OPEN_TURN` bật), `lore_used: list[LoreUse] = []`; `token_estimate` có thêm khoá `"D"` khi có khối lore |
| `StoryExtras` | `lore_tags` giờ có dữ liệu thật: tên các mục đã mở mà người chơi được xem (everyone + player, theo luật đã mở khoá ở §7), gợi ra gần nhất trước; `lore_available: bool = False`; `lore_count: int = 0` (số mục đã mở, kể cả "Chỉ {tên}", dùng làm chữ ký tải lại ở §11.1) |
| `LoreStatus` | giữ kiểu; `enabled` true, `entries` = tổng mục của account, `files` 0, `dir` "" (không còn thư mục `world_wiki`) |

## 3. Cấu trúc module

```
backend/lyris/lore/
  __init__.py
  normalize.py   # match_form(), canon_tone(), has_cjk(), syllables()      (hàm thuần)
  parse.py       # parse_world_md(text) -> ParsedWorld; heading_keys(); slugify()   (hàm thuần)
  match.py       # LoreMatcher(entries, ignore=(char, persona)).scan(text) -> {entry_id: vị trí}   (thuần)
  select.py      # audience_of(); select_lore(...) -> PromptLore + danh sách unsent    (thuần)
  book.py        # character_book (Card V2) <-> LoreEntry                              (thuần)
  service.py     # LoreService(repo): CRUD, import, prompt_lore(), story_lore(), summary(), record_hits()
backend/lyris/api/routes_lore.py      # route ở §8, đăng ký trong app.py
backend/lyris/db/repo.py              # list/get/insert/update/delete/upsert lore; lore_hits; unlocked_lore
backend/lyris/prompt/builder.py       # build_prompt(..., lore=); khối D; phần dự phòng
backend/lyris/prompt/templates/{vi,en}.py   # lore_header(), lore_item(), lore_footer()
backend/lyris/llm/render.py           # render_prefix(..., open_last=)
backend/lyris/llm/{ollama,fake}.py    # prefill_prefix(..., open_last=)
backend/lyris/state/service.py        # next_prompt_prefix + summary_target có lore
backend/lyris/chat/service.py         # _build lấy lore; _persist ghi lore_hits + snapshot
backend/lyris/jobs/{queue,worker}.py  # lore_changed(card_id): hẹn prefill lại
backend/lyris/studio/card_v2.py       # import/export character_book
```

`LoreService` được tạo trong `create_app` cạnh `StateService` và truyền cho `ChatService`, `StateService`, routes. Thiếu `LoreService` (test cũ dựng `ChatService` bằng tay) thì đi đúng đường Phase 3, prompt giữ nguyên từng byte.

## 4. Nhập từ `world.md` (`lore/parse.py`)

### 4.1 Phần được đọc

Chỉ ba mục cấp `##`, so tiêu đề sau `match_form` và theo tiền tố, nên "Mục lore (chuẩn bị cho Phase 4)" vẫn khớp:

| Tiêu đề `##` | category | Mỗi mục là |
|---|---|---|
| `Mục lore` | `lore` | một `### Tiêu đề` kèm các dòng `keys`, `known_by`, `content` |
| `Nhân vật xung quanh` | `character` | một `### Tên (中文)`, **hoặc** một đoạn mở đầu bằng `**Tên (中文)**` (kiểu của `tan-duong`) |
| `Địa điểm` | `place` | một `### Tên`, hoặc một đoạn mở đầu bằng `**Tên.**` |

Các mục khác ("Thế giới", "Nhân vật chính", "Vai của {{user}}", "Cốt truyện", "Luật của thế giới…") bị bỏ qua. Những phần này đã nằm trong card và bối cảnh, hoặc là ghi chú cho tác giả. Một mục kết thúc ở heading `###`/`##` kế tiếp hoặc ở đoạn `**…**` mới (chỉ trong character/place).

### 4.2 Mục lore

- Mỗi dòng trường khớp `^\s*[-*]\s+(\*\*)?(keys|known_by|content)\s*:?(\*\*)?\s*:?\s*(.*)$` (không phân biệt hoa thường). Nhờ vậy đọc được cả `- **keys:** …` (luc-bac-uyen) lẫn `- keys: …` (ba file còn lại).
- `keys`: tách theo dấu phẩy, cắt khoảng trắng, bỏ khoá rỗng hoặc trùng (so bằng `match_form`).
- `known_by`: tách theo dấu phẩy. Giữ nguyên `*` và `{{user}}`. Tên trùng tên nhân vật của card (so bằng `match_form`, bỏ phần trong ngoặc của cả hai bên) được lưu thành `{{char}}`, để đổi tên nhân vật trong Studio về sau không biến mục đó thành "Người khác" mà không ai hay. Tên khác giữ nguyên chữ, kèm cảnh báo 'Mục "…" chỉ {tên đó} biết, nên {tên} sẽ không dùng mục này.' (bắt lỗi viết tên lệch như "Hoài Dã" thay vì "Cố Hoài Dã"). Không có dòng này thì là `["*"]`, kèm một cảnh báo.
- `content`: phần sau `content:`, cộng các dòng thường nối tiếp cho tới mục sau (nội dung nhiều dòng).
- Đoạn thường đứng trước mục đầu tiên bị bỏ, ví dụ dòng "Quy ước known_by…" của `co-hoai-da`.
- Tiêu đề giữ nguyên chữ, kể cả ngoặc: `Năm đã sống qua (chỉ khi chọn "Lần thứ hai")`.

### 4.3 Nhân vật xung quanh và địa điểm

- **Tiêu đề và khoá** (`heading_keys`):
  1. Tách phần trong ngoặc. Ví dụ `Lương ma ma (梁秀琴, Lương Tú Cầm)` cho tiêu đề `Lương ma ma`, phần ngoặc cho các khoá `梁秀琴`, `Lương Tú Cầm` (tách theo dấu phẩy). Bỏ dấu chấm cuối và khoảng trắng thừa trước dấu phẩy: `Căn hộ Lâm Giang Uyển (临江苑), tầng 17` thành `Căn hộ Lâm Giang Uyển, tầng 17`.
  2. Khoá đầu tiên là cả tiêu đề.
  3. Tách tiêu đề theo `,`, ` và `, ` ở `, ` trên `. Giữ phần nào có ít nhất một chữ viết hoa ngoài chữ đầu câu, hoặc có từ 2 âm tiết trở lên và mở đầu bằng chữ hoa. Bỏ phần chung chung viết thường như `tầng 17`, `tô giới`, `chợ hoa đêm`, `khu máy tính cũ`.
  4. Thêm mọi cụm từ 2 âm tiết viết hoa liền nhau trở lên (chỉ chữ cái, không có số): `Lâm Giang Uyển`, `Đông Hồ`, `Tịch Dương`, `Vọng Hải`, `Thu Đường`, `Nhân Hòa`.
  5. Với **nhân vật** có tên đúng 3 âm tiết, cả ba viết hoa, thêm 2 âm tiết cuối làm tên gọi tắt: `Cố Diễn Chi` → `Diễn Chi`, `Lục Chấn Đình` → `Chấn Đình`. `Lương ma ma` không có tên tắt, vì "ma ma" là từ chung.
  6. Không bao giờ tự sinh khoá một âm tiết.
- **Nội dung**: các dòng của mục, bỏ `**` của nhãn (`- **Tính cách:** …` thành `- Tính cách: …`).
  - Đoạn kiểu `tan-duong` giữ phần sau tiêu đề in đậm (`, 52 tuổi. Giám đốc kỹ thuật…`).
  - **Bỏ các dòng mở đầu bằng "Bí mật"** (`Bí mật:`, `Bí mật, động cơ:`, `Bí mật/động cơ:`, `Bí mật và động cơ:`) **và "Chức năng"**. Lý do: mục loại này có `known_by ["*"]`, tức nhân vật chính cũng biết. Giữ dòng "Bí mật" thì Tần Dương sẽ biết Thẩm Kính Ngôn đứng sau dự án Thiên La. "Chức năng" là ghi chú cho tác giả. Kết quả nhập có một dòng `notes` nói rõ việc này.
  - Dòng "Bí mật"/"Chức năng" được xét **trước** dòng in đậm, nên `**Bí mật:** …` (không gạch đầu dòng) không bao giờ thành một mục mọi người biết, và không tự mở một mục mới.
  - Phần bị bỏ gồm cả những gì nằm dưới dòng đó: dòng nối tiếp (không gạch đầu dòng, chưa qua dòng trống), mục con thụt sâu hơn (`- Bí mật:` rồi `  - …`), cả danh sách dưới một nhãn đứng riêng (`**Bí mật:**` rồi `- …`, tới đoạn văn sau dòng trống hoặc nhãn in đậm kế tiếp), và mọi thứ dưới tiêu đề `#### Bí mật` (cấp 4 trở xuống) tới tiêu đề cùng cấp hoặc cao hơn.
  - Trong một mục mở bằng `###`, dòng in đậm dạng nhãn (`**Tính cách:** …`, `**Xưng hô**: …`) là nội dung của mục, không phải người/nơi mới. Dòng in đậm không phải nhãn vẫn mở mục mới như trước. Phần viết theo kiểu `**Tên:** mô tả` cho từng người thì mỗi nhãn vẫn là một người.
- `known_by = ["*"]`, `priority = 0`, **trừ** khi rơi vào luật lọc lộ dưới đây.
- **Lọc lộ điều chỉ người chơi biết** (phản biện: chỉ bỏ "Bí mật"/"Chức năng" là chưa đủ). Phần nhân vật xung quanh và địa điểm do tác giả viết từ góc nhìn biết hết, mà khối D lại nói thẳng "{nhân vật} biết những điều này". Chạy thử trên `luc-bac-uyen`, những dòng sau vẫn lọt qua, dù không mở đầu bằng "Bí mật":
  - Hứa Tri Ý: "Quan hệ: nữ chính của nguyên tác, theo định mệnh sẽ gặp Lục Bắc Uyên";
  - Phó Cảnh Hành: "Nam phụ của nguyên tác";
  - Tô Mạn Ninh: "bạn thân nhất của nguyên chủ";
  - Lục trạch, Tầng 68: "nơi nguyên chủ trượt ngã…", "nơi nguyên chủ từng ôm bình giữ nhiệt…";
  - Sảnh tiệc tầng 52: "Đêm mười bảy tháng ba trời mưa…" (ngày gặp định mệnh trong nguyên tác).

  Thêm nữa, Hứa Tri Ý chưa từng gặp Lục Bắc Uyên, nên `*` là sai ngay từ đầu. Hai luật, chạy sau khi đã đọc xong phần "Mục lore" của cùng file:
  1. **Trùng điều chỉ bạn biết → nhập là "Chỉ bạn".** Người hay nơi có một khoá tự sinh (`heading_keys`) trùng (`match_form`) với khoá của một mục lore `known_by ["{{user}}"]` trong cùng file thì nhập với `known_by ["{{user}}"]`. Tên nó vào `LoreImportResult.player_only`, kèm một dòng `notes`: "Hứa Tri Ý, Phó Cảnh Hành, Tô Mạn Ninh, Tiệm hoa Thu Đường và bệnh viện Nhân Hòa: chỉ bạn biết, vì thế giới có điều chỉ bạn biết về họ. Nếu {tên} cũng biết họ, đổi trong Studio." Luật này chặn hơi dư: Lục Bắc Uyên quen Phó Cảnh Hành và Tô Mạn Ninh. Nhưng card đã có tên và cách xưng hô của hai người này, và thiếu chi tiết thì đỡ hại hơn lộ cốt truyện.
  2. **Bỏ từng câu lộ.** Với các mục còn lại (người, nơi chốn), bỏ mọi **câu** (tách ở `. ! ?` và xuống dòng) khớp một từ trong `META_SPOILER_TERMS` hoặc một khoá bất kỳ của mục lore `{{user}}` cùng file. `META_SPOILER_TERMS` gồm "nguyên tác", "nguyên chủ", "cốt truyện gốc", "xuyên sách", "xuyên không", "kiếp trước", "trùng sinh", "nữ chính", "nam chính", "nữ phụ", "nam phụ". Không có "chương": từ này khớp nhầm ở `co-hoai-da`. Đếm số câu bị bỏ vào `notes`; danh sách câu nằm trong `Disclosure` "Xem các câu đã bỏ" của bước xem trước.
  - Chạy thử bằng `scratchpad/p4/critique_fix.py` trên 4 file:
    - `luc-bac-uyen`: 3 người và 1 nơi chuyển sang "Chỉ bạn"; bỏ 4 câu: 2 câu "nguyên chủ", 1 câu "hồ cá koi", 1 câu "mười bảy tháng ba";
    - ba file còn lại: không đổi gì.
  - Mục nhập là "Chỉ bạn" vẫn mở khoá cho người chơi ở ngăn cảm xúc, nhưng không bao giờ được gửi cho model (§6.1).
- **Câu kiểu ghi chú tác giả** ("Với {{user}}, có thể là người tiếp cận… để dò la", "có thể thành đồng minh") không lọc tự động được. Bước xem trước có một dòng: "Người và nơi chốn được nhập với “Mọi người biết”. Hãy đọc lại: điều gì {tên} không nên biết thì sửa hoặc chuyển sang “Chỉ bạn”."
- **Trùng với mục lore**: nếu tiêu đề (bỏ phần ngoặc, so bằng `match_form`) trùng tiêu đề một mục trong "Mục lore" cùng file, thì bỏ mục nhân vật/địa điểm, giữ mục lore do tác giả viết riêng cho Phase 4, và ghi một dòng `notes`. Ví dụ `Lục Tri Hành (陆知行)`, `Hoàn Viên trạch (還園宅)`, `Kim Thanh hí viện (金聲戲院)`. "Phó Cảnh Hành trong nguyên tác" (chỉ người chơi biết) khác tiêu đề "Phó Cảnh Hành" nên giữ cả hai, nhưng mục người "Phó Cảnh Hành" rơi vào luật 1 ở trên và cũng thành "Chỉ bạn".

### 4.4 Slug, nhập lại, idempotent

- `slugify(title)`: `match_form`, bỏ dấu (`đ`→`d`), giữ `[a-z0-9]`, nối bằng `-`. CJK bị bỏ khỏi slug. Tiêu đề chỉ có chữ Hán hay ký hiệu (slug rỗng) thì dùng `h` + 10 ký tự hex đầu của sha1(`match_form(title)`), không để slug rỗng trùng nhau.
- Slug đầy đủ là `md:<category>/<slug>`. Trùng trong một file thì thêm `-2`, `-3` theo thứ tự xuất hiện. Giới hạn đã biết: chèn thêm một mục trùng tên **ở trước** thì các hậu tố dịch, hai mục đổi nội dung cho nhau. Đổi tên tiêu đề trong file thì thành xoá + tạo (mục cũ chỉ bị xoá khi bật `delete_missing`).
- **Áp dụng** (`LoreService.import_world_md(card_id, text, dry_run, delete_missing)`, một transaction):
  - Slug chưa có: `create` (source `world_md`, `position` = sau mục cuối).
  - Slug có, `edited = 0`, nội dung khác (title, category, keys, known_by, content): `update`, giữ `enabled`, `priority`, `position`.
  - Slug có, giống hệt: `unchanged`.
  - Slug có, `edited = 1`: `keep_edited`, không ghi đè.
  - Slug có, `removed = 1` (người dùng đã xoá mục này): `skip_removed`, không thêm lại. Bước xem trước ghi "Bỏ qua 2 mục bạn đã xoá."
  - Mục `world_md` của card không còn trong file: mặc định `keep_missing` (giữ nguyên). Chỉ khi `delete_missing` bật thì mục `edited = 0` bị `delete` (xoá hẳn, kèm hit), còn mục `edited = 1` vẫn giữ (đếm vào `keep_edited`). Lý do: card có thể có hơn một file thế giới, và slug không ghi tên file, nên nhập file thứ hai mà xoá mặc định thì mất hết mục của file thứ nhất.
  - Mục `manual` và `card_book` không bao giờ bị đụng tới.
  - Nhập lại cùng một file là `unchanged` hết, không tạo thêm hàng nào, kể cả khi trước đó đã xoá vài mục.
- Sửa một mục `world_md`/`card_book` qua PUT thì `edited = 1`, **chỉ khi** một trong các trường title, category, keys, known_by, content thật sự đổi (sau khi làm sạch). Mở hộp sửa rồi bấm Lưu mà không đổi gì thì không khoá mục trước lần nhập sau. PATCH (bật/tắt, đổi chỗ) thì không đổi `edited`.
- **Xoá** (DELETE): mục `manual` thì xoá hẳn. Mục `world_md`/`card_book` thì thành bia mộ: `removed = 1`, `enabled = 0`, xoá các `lore_hits` của nó (để danh sách đã mở khoá đúng ngay). Hàng `removed` không được liệt kê, so khớp, export hay tính vào `MAX_LORE_ENTRIES_PER_CARD`. Hiện chưa có giao diện khôi phục; nếu cần thì sau này thêm "Thêm lại các mục đã xoá" vào bước xem trước.
- Không tìm thấy mục nào: 422 "Không tìm thấy mục thế giới nào. File cần có phần “## Mục lore”, “## Nhân vật xung quanh” hoặc “## Địa điểm”."

### 4.5 Kết quả trên 4 file thật

Đã chạy thử ý tưởng parser trên `worlds/*/world.md` bằng một script nháp (`scratchpad/p4/parse_probe.py`, không nằm trong repo):

| Thế giới | Mục lore | Nhân vật xung quanh | Địa điểm | Tổng | known_by của mục lore | Bỏ vì trùng |
|---|---|---|---|---|---|---|
| `co-hoai-da` | 14 | 6 | 6 | **26** | `*` 5, `Cố Hoài Dã` 8, `{{user}}` 1 | Lục Tri Hành |
| `luc-bac-uyen` | 14 | 7 | 6 | **27** | `{{user}}` 6, `*` 6, `Lục Bắc Uyên` 2 | |
| `tan-duong` | 14 | 7 | 6 | **27** | `*` 5, `Tần Dương` 9 | |
| `yen-hoanh-sinh` | 14 | 7 | 4 | **25** | `*` 9, `Yến Hoành Sinh` 4, `{{user}}` 1 | Hoàn Viên trạch, Kim Thanh hí viện |

Tổng cộng 105 mục. Mỗi nhân vật xung quanh bỏ 2 dòng (Bí mật, Chức năng). Số mục không đổi sau luật lọc lộ ở §4.3. Riêng `luc-bac-uyen` có 4 mục người/nơi thành "Chỉ bạn" (Hứa Tri Ý, Phó Cảnh Hành, Tô Mạn Ninh, Tiệm hoa Thu Đường và bệnh viện Nhân Hòa), và mất thêm 4 câu. Ví dụ khoá sinh ra:
- `Hạ Trì (夏驰)` → `Hạ Trì`, `夏驰`
- `Thẩm Kính Ngôn (沈敬言)` → `Thẩm Kính Ngôn`, `沈敬言`, `Kính Ngôn`
- `Lục trạch trên núi Vân Lộc` → cả tiêu đề, `Lục trạch`, `núi Vân Lộc`, `Vân Lộc`
- `Tiệm hoa Thu Đường và bệnh viện Nhân Hòa` → cả tiêu đề, `Tiệm hoa Thu Đường`, `bệnh viện Nhân Hòa`, `Thu Đường`, `Nhân Hòa`
- `Căn hộ 1701, chung cư Ngô Đồng (梧桐公寓)` → cả tiêu đề, `梧桐公寓`, `Căn hộ 1701`, `chung cư Ngô Đồng`, `Ngô Đồng`
- `Tầng 68 tòa nhà Lục thị` → chỉ cả tiêu đề. Người dùng thêm "Lục thị" trong Studio nếu muốn.

Độ dài:
- `content` của mục lore: 294-547 ký tự (~100-190 token).
- Nhân vật xung quanh sau khi bỏ 2 dòng: 427-1356 ký tự. Dài nhất là Doãn Sách.
- Địa điểm: 286-1308 ký tự.

Vì vậy prompt cắt mỗi mục ở `MAX_LORE_ITEM_CHARS` (§6.2); trong DB vẫn lưu đủ.

Cảnh báo lúc nhập (`warnings`):
- Từ khoá một âm tiết viết thường: `mẹ`, `giỗ` (Tô Vãn Âm), `nhẫn` (Chiếc nhẫn sapphire). Câu: 'Từ khoá "mẹ" chỉ có một chữ nên sẽ gợi rất thường xuyên.' Vẫn nhập, vì đó là lựa chọn của tác giả. Khớp trọn âm tiết **không** phải khớp trọn từ: tiếng Việt viết từ ghép thành nhiều âm tiết, nên "nhẫn" vẫn khớp trong "kiên nhẫn", "tàn nhẫn", "nhẫn nhịn". Câu cảnh báo vì vậy nêu một ví dụ khi có: 'Từ khoá "nhẫn" chỉ có một chữ, cũng khớp trong những từ như “kiên nhẫn”.' (danh sách nhỏ trong `loreLogic`/`normalize`, không cần đủ).
- Mục không có từ khoá nào: 'Mục "…" chưa có từ khoá gợi nhớ nên sẽ không bao giờ được nhắc tới.'

### 4.6 Character Card V2 `character_book` (`lore/book.py`)

| Card V2 entry | LoreEntry |
|---|---|
| `keys` | `keys` |
| `content` | `content` |
| `name`, thiếu thì `comment`, thiếu nữa thì khoá đầu | `title` |
| `enabled` (mặc định true) | `enabled` |
| `insertion_order` | `position` |
| `priority` | `priority` |
| `extensions.lyris.known_by` (thiếu = `["*"]`) | `known_by` |
| `extensions.lyris.category` (thiếu = `lore`) | `category` |
| `extensions.lyris.slug`; thiếu thì `book:id-<id>` khi entry có `id`; thiếu nữa thì `book:<slug title>` (trùng thêm `-2`). Không dùng chỉ số trong mảng: book bị sắp lại thì slug theo chỉ số đổi hết, nhập lại sẽ nhân đôi. | `slug` |
| `secondary_keys`, `selective`, `constant`, `case_sensitive`, `position`, `id`, các khoá extensions khác | `extra` (giữ để export lại; chưa dùng khi so khớp) |

- **Import card** (`POST /api/cards/import` trả nháp, chưa lưu): `parse_card` không còn cảnh báo "character_book… Phase 4". Nháp vẫn mang book trong `extensions.v2.character_book`. Khi `POST /api/cards` lưu card, backend tạo các mục `card_book` từ book đó, rồi **bỏ** `character_book` khỏi `extensions.v2`, để DB chỉ có một nguồn sự thật.
  - **`PUT /api/cards/{id}` làm y hệt** (chuyển book thành mục theo slug, idempotent, rồi bỏ book). Trình sửa ở frontend còn giữ `extensions` của nháp trong bộ nhớ. Nếu chỉ POST làm việc này, lần bấm Lưu thứ hai sẽ gửi book quay lại DB, và Studio lại hiện lời mời "Dùng các mục này". Sau khi lưu, frontend lấy `extensions` từ card server trả về, và nếu card đã gửi book mà bản trả về không còn thì phần "Thế giới" tải lại danh sách (`reloadKey`), không phải tải lại trang.
  - `known_by` từ book cũng đổi tên nhân vật thành `{{char}}` như §4.2.
- **Card cũ** đã import trước Phase 4 mà còn book trong `extensions.v2`: không tự chuyển lúc khởi động. Studio hiện lời mời và gọi `POST /api/cards/{id}/lore/import-book` (§8).
- **Export** (`card_v2.export_card`): `data.character_book = {"name": "<tên> · Thế giới", "entries": [...]}` dựng từ mọi mục của card (mọi source), trả `extra` về đúng chỗ, kèm `extensions.lyris.{known_by, category, slug}`. Card không có mục nào thì không có `character_book` (`null` như hiện nay).
- **Nhân bản card** (`POST /cards/{id}/duplicate`): sao chép mọi mục, giữ slug, source, edited.
- **Xoá card**: các mục và `lore_hits` tự xoá theo (CASCADE).
- Bốn file `worlds/*/card.json` có `"character_book": null`, nên lore của chúng đến từ việc nhập `world.md`.

## 5. So khớp (`lore/normalize.py`, `lore/match.py`)

### 5.1 Dạng so khớp

`match_form(text)` áp dụng như nhau cho từ khoá và cho văn bản cần quét:

1. `unicodedata.normalize("NFC")`, rồi `casefold()`, rồi NFC lại.
2. **Chuẩn hoá vị trí dấu thanh** (`canon_tone`). Ở âm tiết kết thúc bằng `oa`, `oe`, `uy` (không đứng sau `q`), dấu được đặt về nguyên âm đầu theo kiểu cũ:
   - `hoà`→`hòa`, `hoá`→`hóa`, `khoẻ`→`khỏe`, `thuý`→`thúy`, `luỹ`→`lũy`;
   - `quý`, `quỳ` giữ nguyên;
   - có phụ âm cuối (`hoàng`, `thuyền`) thì không đụng, vì hai kiểu viết vốn giống nhau.

   Nhờ vậy "Nhân Hòa" khớp "Nhân Hoà".
3. Tách token bằng `re.findall(r"[^\W_]+")` (Unicode, chữ và số). Dấu câu, gạch nối, gạch dưới (`_hôn ước_` in nghiêng kiểu markdown, `Hạ_Trì`), ngoặc kép, `·` coi như khoảng trắng: "Lục Tổng, Em Không Cần Anh Nữa" khớp khoá "Lục Tổng Em Không Cần Anh Nữa", "Lục-Ôn" khớp "Lục - Ôn", `云顶·澜江` khớp `云顶 澜江`.
4. Dạng cuối là `" " + " ".join(tokens) + " "`.

**Giữ nguyên dấu**: "Lục" ≠ "lúc" ≠ "lực"; "Đ" ≠ "D". Không bỏ dấu ở bước nào.

### 5.2 Khớp

- **Khoá không có chữ Hán**: khớp khi `" " + key + " "` nằm trong dạng của văn bản. Tức là khớp **trọn âm tiết, trọn cụm**:
  - "Trì" không khớp trong "Trình Dịch";
  - "Lan Giang" khớp trong "cầu Lan Giang cũ";
  - "Ôn viên" không khớp "ôn bài".
- **Khoá có chữ Hán**: tiếng Hán không có khoảng trắng nên không có ranh giới từ. So chuỗi con trên dạng đã bỏ mọi khoảng trắng: `夏驰` khớp trong "夏驰说".
- **Bỏ qua** (không bao giờ khớp):
  - khoá có `match_form` trùng tên nhân vật của card hoặc tên persona, vì những tên này có ở gần như mọi lượt;
  - khoá `{{user}}`, `{{char}}`;
  - khoá dưới 2 ký tự.

  Khoá *chứa* tên nhân vật thì vẫn dùng, ví dụ "cha của Lục Bắc Uyên".
- Khoá có `{{user}}`/`{{char}}` ở giữa (thường gặp trong book Card V2, ví dụ "cha của {{char}}") được thay bằng `ctx.fill` **trước** khi so khớp và trước phép "trùng tên nhân vật".
- `LoreMatcher` được dựng lại **mỗi lượt** từ các mục `enabled` và `removed = 0`; không cache. Cache theo `max(updated_at)` + số mục có thể giữ bản cũ, ví dụ khi một PATCH không đổi `updated_at`. Mà dựng lại thì rẻ: khoảng 30 mục × 6 khoá. `scan(text)` trả `{entry_id: vị trí khớp sớm nhất}`; văn bản vài nghìn ký tự, phép quét chỉ là `in` trên chuỗi, dưới 1ms.
- Quét **từng message riêng**, không nối chúng lại, để một khoá không khớp vắt qua ranh giới hai message.

### 5.3 Văn bản được quét

`select_lore` nhận văn bản thuần, không nhận `Message`, nên chat thử ở Studio cũng dùng được:
- `tail`: các lượt người chơi chưa được trả lời ở cuối lịch sử (như `tail_start` của builder). Lấy `visible_content` cộng chỉ đạo `((…))`, vì chỉ đạo của người chơi cũng có thể gọi lore ("((cho hắn nhắc tới hôn ước))").
- `earlier`: tối đa `LORE_SCAN_DEPTH = 4` message active ngay trước `tail`, mới nhất trước, thường là hai cặp lượt (A₋₁, P₋₁, A₋₂, P₋₂). Lượt của nhân vật quét `raw_content`, **gồm cả Thought**: nhân vật nghĩ tới cha thì lore về cha cũng liên quan. Lời mở đầu (lượt 0) cũng được quét, nên mục nhắc trong lời mở đầu có mặt ngay ở lượt 1.
- **Lượt của nhân vật (kể cả lời mở đầu) chỉ được quét bằng khoá dạng tên riêng**: khoá, như tác giả viết, có ít nhất một chữ hoa, một chữ số hoặc một chữ Hán (`Hạ Trì`, `GHOST`, `phòng 402`, `nhà A3`, `夏驰`). Khoá viết thường hoàn toàn (`căn hộ`, `đôi mắt`, `nhịp tim`, `tai nghe`, `đám đông`, `nhẫn`, `mẹ`) chỉ gợi từ lời người chơi (tail và các lượt người chơi trong `earlier`).
  - Lý do, đo bằng `scratchpad/p4/critique_match.py` trên khoá thật và lời mở đầu thật: lời dẫn truyện của model dùng những từ thường này gần như mỗi lượt.
    - Lời mở đầu của `tan-duong` đã gợi mục "Chứng lo âu xã hội" qua "nhịp tim", "tai nghe", "đám đông".
    - Lời mở đầu của `co-hoai-da` gợi mục "Căn hộ…" qua "căn hộ".
    - `luc-bac-uyen` gợi "Chiếc nhẫn sapphire" qua "nhẫn".
  - Nếu quét cả lượt nhân vật bằng các khoá này, khối D gần như không bao giờ rỗng, cứ lặp lại cùng vài mục. Mỗi lượt vì vậy đọc thêm vài trăm token, và model có xu hướng nhắc lại chi tiết lore (ví dụ "đôi mắt xanh di truyền từ bà nội") ở mọi lượt. Nó còn tự nuôi mình: nhân vật nhắc lại vì có lore, lore lại được gợi vì nhân vật nhắc.
  - Lời người chơi vẫn khớp không phân biệt hoa thường, vì người chơi hay gõ thường ("hạ trì đâu rồi").
- Không phụ thuộc cửa sổ lịch sử hay tóm tắt. Lượt cũ đã bị cắt khỏi cửa sổ vẫn có thể được quét nếu nằm trong 4 message gần nhất (hiếm, vì cửa sổ cắt theo khúc).

"Dính" (sticky) là hệ quả của độ sâu quét: một mục được nhắc ở P₋₁ còn ở trong khối lore khoảng hai lượt nữa, rồi tự rơi ra khi không ai nhắc lại. Không cần lưu trạng thái, và rollback đúng sẵn.

### 5.4 Chỗ dễ sai với tiếng Việt (mỗi dòng là một test)

| Văn bản | Khoá | Khớp? | Vì sao |
|---|---|---|---|
| "lúc đó" | Lục | không | giữ dấu |
| "LỤC THỊ" | Lục thị | có | không phân biệt hoa thường |
| "lục tung tủ" | Lục | **có** | hoa thường bị bỏ qua: khoá một âm tiết dễ khớp nhầm, vì vậy Studio cảnh báo |
| "Nhân Hoà" | Nhân Hòa | có | `canon_tone` |
| "quý" / "qúy" | — | — | `qu` không đổi chỗ dấu |
| "Lục" viết dạng NFD (dữ liệu dán từ macOS) | Lục | có | NFC |
| "Trình Dịch" | Trì | không | trọn âm tiết |
| "Yến Hoành Thiên" | Hoành Thiên | có | trọn cụm nằm trong cụm dài hơn |
| "Lục Tổng, Em Không Cần Anh Nữa" | Lục Tổng Em Không Cần Anh Nữa | có | dấu câu thành khoảng trắng |
| "夏驰说" | 夏驰 | có | chữ Hán so chuỗi con |
| "Lục Bắc Uyên nhìn cô" (tên nhân vật) | Lục Bắc Uyên | không | khoá trùng tên nhân vật bị bỏ |
| "zero" (tiếng Anh, story tiếng Anh) | ZERO | có | chấp nhận |
| "Hắn kiên nhẫn chờ." (lời người chơi) | nhẫn | **có** | trọn âm tiết ≠ trọn từ; vì vậy có cảnh báo một chữ |
| "Hắn kiên nhẫn chờ." (lượt nhân vật) | nhẫn | không | khoá viết thường không quét lượt nhân vật (§5.3) |
| "đôi mắt hắn tối lại" (lượt nhân vật) | đôi mắt | không | như trên |
| "đôi mắt anh xanh thật à?" (lời người chơi) | đôi mắt | có | |
| "Hạ Trì gọi tới" (lượt nhân vật) | Hạ Trì | có | khoá tên riêng quét cả lượt nhân vật |
| "Tiệm hoa thu đường" (người chơi gõ thường) | Tiệm hoa Thu Đường | có | không phân biệt hoa thường |
| "nhà A3" / "Nhà a3" | nhà A3 | có | chữ số + chữ hoa = tên riêng |
| "cha của {{char}}" (khoá Card V2) vs "cha của Lục Bắc Uyên" | | có | khoá được `fill` trước |
| "Hạ" ở cuối message này, "Trì" ở đầu message sau | Hạ Trì | không | quét từng message riêng |
| "Mĩ thuật" | Mỹ thuật | không | chưa chuẩn hoá i/y; chấp nhận, tác giả thêm khoá nếu cần |

## 6. Chọn mục và đặt vào prompt

### 6.1 Lọc theo người biết (`select.audience_of`)

| known_by | audience | Gửi cho model? | Hiện cho người chơi ở ngăn "Cảm xúc & ký ức" |
|---|---|---|---|
| có `*` | everyone | có | có |
| có tên nhân vật của card (hoặc `{{char}}`) | character | có, đánh dấu riêng tư | có, dưới dạng làm mờ; ẩn hẳn khi tắt "Đọc suy nghĩ" (§11.2) |
| chỉ `{{user}}` | player | **không bao giờ** | có ("Chỉ bạn biết") |
| chỉ tên người khác | others | không | không |

So tên bằng `match_form`. `["{{user}}", "Lục Bắc Uyên"]` là character (gửi). `select_lore` bỏ các mục không gửi được trước khi tính ngân sách, nên một mục `{{user}}` không bao giờ đi vào `PromptLore.carried`/`fresh`, `BuiltPrompt.messages` hay snapshot `lore_used`. Nó chỉ nằm trong `unsent_ids`, để giao diện mở khoá cho người chơi.

- `known_by` có cả `{{user}}` và tên người khác (ví dụ `["{{user}}", "Hạ Trì"]`) là player: không gửi.
- Không có giá trị `known_by` nào khiến một mục vừa được gửi vừa bị coi là "Chỉ bạn".
- Test lộ (§14.1) chạy trên 4 file thật:
  - nhập file, rồi gửi lần lượt **mọi khoá** của mọi mục như lời người chơi;
  - không message nào gửi cho `FakeLLM` được chứa nội dung của một mục player, hay một từ trong `META_SPOILER_TERMS`;
  - trừ những từ đã có sẵn trong system (card `luc-bac-uyen` tự nói tới "nguyên tác" trong bối cảnh), nên test so phần message user cuối chứ không so cả prompt.

### 6.2 Ngân sách và thứ tự (`select.select_lore`)

```python
LORE_SCAN_DEPTH = 4            # message trước tail được quét (≈ 2 lượt "dính")
LORE_TOKEN_LIMIT = 520         # cả khối D, gồm dòng mở + dòng đóng; cũng là reserve_tokens
LORE_CARRIED_TOKENS = 240      # các mục carried (chỉ phụ thuộc lịch sử)
# fresh dùng phần còn lại của LORE_TOKEN_LIMIT: 520 − dòng mở (~56) − dòng đóng (~13) − 240 ≈ 211 token,
# đủ một mục 450 ký tự kể cả mục "Chỉ {tên}" có lời dặn và tên 40 ký tự (~198, đo bằng estimate_tokens)
LORE_MAX_ITEMS = 4
MAX_LORE_ITEM_CHARS = 450      # cắt ở cuối câu gần nhất trước giới hạn, thêm "…" (≈ 150 token)
```

**Vì sao 520 chứ không 700** (đo bằng `scratchpad/p4/critique_budget.py` với builder thật trên 4 card, Story, `num_ctx` 8192):
- Ngân sách lịch sử E = `limit` 7036 − (A+B+C) − phần dự phòng F (~730). Kết quả: 4071 (`co-hoai-da`), 4006, 4026, 3291 (`yen-hoanh-sinh`, luật dài nhất).
- Có tóm tắt thì trừ thêm phần dự phòng C, tới ~510.
- Khúc (`_story_chunk`) vẫn tính theo `limit − (A+B+C)`, không trừ F, C hay lore, nên khúc của `yen-hoanh-sinh` là 1341. Ngay sau một lần dịch, lịch sử chỉ còn E − khúc.
- Với `yen-hoanh-sinh` có tóm tắt:
  - không lore: 2781 − 1341 ≈ 1440 token;
  - dự phòng 700: **≈ 740 token**, chưa tới một cặp lượt Story (lượt trả lời 500-700 token). Nhân vật quên cả câu người chơi vừa nói trước đó;
  - dự phòng 520: ≈ 920 token.
- Không đổi `_story_chunk` ở Phase 4: đổi nó là dời mốc khúc của mọi story đang chơi, kéo theo tóm tắt. Muốn khối lore lớn hơn thì phải đổi cách tính khúc trước.
- 450 ký tự vẫn chứa trọn đa số mục lore tác giả viết (294-547 ký tự). Mục người/nơi bị cắt ở cuối câu; trong DB vẫn lưu đủ.

- Đếm token: `estimate_tokens(line)` cộng số ký tự Hán trong dòng, vì chữ Hán tốn khoảng 1 token mỗi chữ, còn ước lượng chung chia cho 3.
- **carried**: các mục khớp trong `earlier`, chỉ phụ thuộc lịch sử trước lượt người chơi mới (§6.5).
  - Xếp theo: tuổi của message khớp gần nhất (mới trước), `priority` giảm dần, `position`, `id`.
  - Lấy dần theo thứ tự đó; mục nào không vừa phần còn lại thì bỏ qua, xét mục sau.
- **fresh**: các mục khớp trong `tail` mà chưa có trong carried.
  - Xếp theo: `priority` giảm dần, vị trí khớp đầu tiên trong `tail`, `position`, `id`.
  - Ngân sách: `LORE_TOKEN_LIMIT − mở − đóng − carried đã dùng`.
- Mục khớp nhưng hết chỗ cũng vào `unsent_ids` (ghi `lore_hits` slot `unsent`, cho dữ liệu train). Giao diện **không** coi đó là "đã mở khoá" với mục everyone/character (§7): nếu không, người chơi thấy "đã mở khoá" một điều mà nhân vật chưa hề được nhắc tới, rồi thấy nhân vật làm như không biết.
- `reserve_tokens`: `LORE_TOKEN_LIMIT` nếu card có ít nhất một mục `enabled` với audience everyone/character, ngược lại 0. Giá trị này chỉ đổi khi người dùng sửa sổ thế giới, không đổi theo lượt.
- Cùng đầu vào thì cùng kết quả: không dùng giờ, không ngẫu nhiên, không lặp qua `set`.

### 6.3 Khối D: đầu message user cuối

Khối lore được đặt ở **đầu message user cuối**, trước lời người chơi. Ghi chú F vẫn ở cuối như cũ.

```
[Thông tin thế giới cho người dẫn truyện, không phải lời của Lâm Vãn. Lục Bắc Uyên biết những điều này; chỉ dùng khi hợp cảnh, không kể lại nguyên văn.]
- Hôn ước Lục - Ôn: Năm 1979, một con tàu chở hàng chìm ở cảng cũ Hải Thành. …
- Câu nói đêm mưa (chuyện riêng của Lục Bắc Uyên, chưa kể với ai; không tự nói ra nếu không có lý do): Đêm trước sinh nhật hai mươi tuổi, …
- Lục Chấn Đình: 76 tuổi, Lục lão gia, người sáng lập Lục thị; …        ← fresh (nếu có)
[Hết thông tin thế giới.]

{lời người chơi}

[Ghi chú cho người dẫn truyện, không phải lời của Lâm Vãn]
- Cảnh hiện tại: …
…
```

- **Thứ tự**: dòng mở, các mục carried, các mục fresh, dòng đóng, hai dòng trống, `tail_text`, hai dòng trống, F. Lượt chỉ có chỉ đạo (`tail_text` rỗng) thì là khối D, hai dòng trống, rồi F.
- **Văn bản template**: `lore_header(ctx)`, `lore_item(title, text, private)`, `lore_footer()` trong `vi.py`/`en.py`.
  - DM: "[Thông tin thế giới cho người viết, không phải tin nhắn của {p}. …]".
  - Tiếng Anh: "[World notes for the narrator, not {p}'s words. {c} knows these; use them only when they fit the scene, never recite them.]", "(only {c} knows this and has told no one; do not bring it up without a reason)", "[End of world notes.]".
- **Nội dung mỗi mục**:
  - thay `{{user}}`/`{{char}}` bằng `ctx.fill`;
  - gộp mọi xuống dòng thành một khoảng trắng;
  - cắt ở `MAX_LORE_ITEM_CHARS`;
  - kết thúc bằng dấu câu (`sentence`);
  - `_scrub` **từng mục trước khi ghép**, để "((" không thể hình thành ở chỗ nối giữa phần đầu và phần sau (§6.5).
- **Không có mục nào thì không có khối nào.** Card không có mục nào gửi được (`reserve_tokens = 0`): prompt giống hệt Phase 3 từng byte. Card có sổ thế giới mà lượt này không gợi mục nào: các message giống hệt Phase 3 **khi lịch sử còn vừa**. Khi đã phải cắt, phần dự phòng làm cửa sổ bắt đầu muộn hơn Phase 3 (§6.4); đó là chủ ý, không phải lỗi.
- **D không tính vào `e_tokens`**: `_assemble` tính `e_tokens` từ lịch sử như cũ, rồi mới ghép D vào đầu message cuối, như cách ghép F vào cuối. D được cộng riêng: vào `fits()` qua `max(d, reserve)`, và vào `total()` (nhánh `state=None` và nhánh cắt từng lượt). Nếu không làm vậy, D bị đếm hai lần và cửa sổ dịch theo lượt.
- Builder đặt `token_estimate["D"]` (dòng mở + mục + dòng đóng), `lore_used`, và `lore_head` = dòng mở cộng các mục carried, đúng như chuỗi ở đầu message cuối (chưa có `\n` cuối).
  - Không có carried thì `lore_head = None`.
  - Kiểm tra cuối: content message cuối phải `startswith(lore_head)`. Không đúng (ví dụ cửa sổ bắt đầu ngay ở tail và một lượt user cũ bị gộp lên trước) thì `lore_head = None`. Prefill khi đó chỉ không gửi phần đầu, prompt vẫn đúng.

**Vì sao không đặt ở chỗ khác:**
- *System (khối D của plan.md)*: đổi theo lượt thì đọc lại cả prompt, ~45s.
- *Một message riêng trước lượt người chơi*: builder gộp các message user liền nhau, nên thực chất vẫn là chỗ này.
- *Toàn bộ trong F*: F nằm sau lời người chơi, nên không bao giờ gửi trước được. Đặt ở đầu thì giữ được đường gửi trước phần carried (§6.5), nếu sau này đo thấy an toàn.
- **Cái giá khi chưa gửi trước** (mặc định, §6.5): lượt nào có khối D thì đọc thêm khối đó, tối đa 520 token (~5s, prompt đọc ~100 token/s theo phase3.md §10.6). Thường 1-2 mục ≈ 170-350 token (~2-3.5s). Lượt không gợi mục nào thì không chậm thêm gì. Vì lượt nhân vật chỉ được quét bằng khoá tên riêng (§5.3), khối D không dính mãi.

### 6.4 Cửa sổ lịch sử, hysteresis, tóm tắt

- `build_prompt(card, persona, story, history, *, budget=None, state=None, lore: PromptLore | None = None)`.
- **Phần dự phòng cố định**:
  - có `state`: `fits()` dùng `max(d_tokens, lore.reserve_tokens)` thay cho `d_tokens`, cạnh `_f_reserve` và `c_reserve` hiện có;
  - không có `state` (Studio, harness): khối D được tính đúng như thật vào `total()`.

  Như vậy điểm bắt đầu cửa sổ không phụ thuộc lượt này gợi ra mục nào, giống cách F không phụ thuộc fact hay ký ức (phase3.md §10.1).
- **Mọi chỗ dựng prompt để đoán cửa sổ phải truyền cùng `reserve_tokens`**: `next_window_start` (`summary_target`) và `next_prompt_prefix`. Cả hai lấy `LoreService.reserve_for(card_id)`. Lệch phần dự phòng giữa prefill và lượt thật là lệch cửa sổ, mất trắng cache.
- **Mốc khúc** (`_boundaries`, `_story_chunk`) không đổi, vì chỉ phụ thuộc A+B+C và lịch sử.
- **Lùi một mốc khi phần dự phòng làm mất cả câu trả lời trước** (sau review). `_story_chunk` không trừ F, C hay D, nên với card A+B lớn (`yen-hoanh-sinh`) và lượt dài (người chơi ~1200 ký tự, trả lời 500-750 token), phần dự phòng 520 có lúc chỉ để vừa mốc cuối: prompt chỉ còn `[system, lượt người chơi mới]`, mất câu trả lời trước của nhân vật (20/58 lượt cắt trong mô phỏng, không lore là 0/58). Khi mốc vừa sớm nhất nằm ở hoặc sau đầu tail và `reserve_tokens` lớn hơn khối D thật, `build_prompt` thử lại **mốc ngay trước** với khối D thật của lượt này (dự phòng F, C giữ nguyên); vừa thì dùng mốc đó. Kết quả: 0/58, cửa sổ giống hệt khi không có lore ở lượt không gợi mục nào.
  - Cửa sổ vẫn luôn ở một mốc khúc, vẫn chỉ tiến; chỉ dịch chậm đi một lượt. Tóm tắt cho mốc trước đã có sẵn (cửa sổ vừa ở đó).
  - Chỉ trong trường hợp này, điểm bắt đầu phụ thuộc lượt này gợi ra bao nhiêu (fresh lớn thì không lùi). Prefill dựng với carried thật, nên chỉ lệch khi fresh của lượt thật lớn đúng lúc đó: một lượt đọc lại, như một lượt dịch.
  - `next_window_start` (đoán cho tóm tắt) tắt bước này (`lore_fallback=False`): đoán thận trọng, tóm tắt không bao giờ trễ. Không đổi `_story_chunk`: thu nhỏ khúc theo D làm card A+B lớn dịch cửa sổ gần như mỗi lượt (mất cache mỗi lượt).
- **Hệ quả một lần**: card vừa có mục thế giới đầu tiên (hoặc vừa xoá mục cuối) làm phần dự phòng đổi 520 token. Story dài của card đó có thể dịch cửa sổ sớm hơn một khúc ở lượt kế tiếp: lượt đó chậm như một lượt dịch, tóm tắt chưa kịp làm trước. Chấp nhận được. Studio ghi trong mô tả mục: "Story đang chơi có thể chậm một lượt sau khi thêm mục đầu tiên" (chỉ khi bật công cụ nâng cao).
- **Tóm tắt, trích xuất, gợi ý**: không có lore trong prompt của chúng. Tóm tắt vẫn ghi lại những chuyện lore đã khiến nhân vật nói ra, vì nó đọc lượt trả lời.

### 6.5 Prefill

**Mặc định: `LORE_PREFILL_OPEN_TURN = False`.** Prefill gửi đúng như Phase 3 (`messages[:-1]`, dừng ở `<turn|>\n` của câu trả lời cuối). Khối D được đọc lúc gửi tin, cùng lời người chơi và F. Lý do là điểm chụp của Ollama (phase3.md §10.6, "Sửa lần 2"): runner chỉ khôi phục ở chỗ một request **bắt đầu đọc** và ở cuối prompt trừ 4 token.
- **Khi tắt** (an toàn, giống Phase 3):
  - prefill(T) dừng ở cuối A₋₁, nên lượt thật T bắt đầu đọc ở đó, và đó là một điểm chụp;
  - prompt của lượt T+1 không còn khối D trong lượt người chơi T (lịch sử chỉ có lời người chơi), nên rẽ khỏi prompt T ngay ở đầu nội dung lượt T;
  - chỗ rẽ đó nằm sau điểm chụp cuối A₋₁, nên prefill(T+1) khôi phục ở đó và chỉ đọc lượt T cùng câu trả lời T, như hiện nay.
- **Khi bật** (gửi trước `lore_head`):
  - lượt thật T bắt đầu đọc ở cuối `lore_head`, **bên trong** lượt người chơi T;
  - prompt T+1 rẽ ở **đầu** lượt T, tức là trước điểm chụp đó;
  - điểm chụp còn lại ở trước chỗ rẽ (nếu runner còn giữ) là chỗ prefill(T) bắt đầu đọc, một lượt về trước.
  - Nếu runner chỉ giữ điểm chụp của request gần nhất như §10.6 mô tả, prefill(T+1) phải đọc lại **cả prompt** (~45s). Người chơi gửi trước khi xong thì lượt T+1 cũng ~45s. Mọi lượt ngay sau một lượt có carried đều có thể bị như vậy.
  - Bảng §10.6 gợi ý runner giữ được nhiều hơn một request (prefill vẫn 3-5s dù job trích xuất chen giữa), nhưng chưa ai đo đúng trường hợp này.
- Vì vậy phần "gửi trước lore" chỉ bật sau khi đo đúng chuỗi lượt T, T+1, T+2 (§14.4) và thấy cả prefill(T+1) lẫn lượt thật T+1 chỉ đọc lại cỡ một hai lượt. Code cho đường bật vẫn viết và test bằng `FakeLLM` (§14.1), để bật chỉ là đổi một hằng.
- **Đã đo (2026-11-14, gemma4:12b, num_ctx 8192, 11 lượt `luc-bac-uyen`, lượt nào cũng có khối D):** dự đoán ở trên chỉ đúng một phần. Runner giữ được điểm chụp cũ hơn, nên bình thường prefill(T+1) không đọc lại cả prompt; nhưng sau mỗi lần đọc lại cả prompt (lượt đầu story, cửa sổ dịch) thì prefill kế tiếp đọc lại cả prompt **lần thứ hai**. Kết luận: **giữ `LORE_PREFILL_OPEN_TURN = False`** (không đạt điều kiện §14.4).

  | | Tắt (mặc định) | Bật |
  |---|---|---|
  | TTFT trung bình lượt chat | 6.58s (4.5-8.5s; ~+1s mỗi 100 token D) | 5.12s |
  | Token lượt chat đọc lại (trung bình) | 615 (D + lời người chơi + F) | 472 |
  | prefill(T+1) bình thường | ~360-400 token, ~4s | ~800-940 token, 8-9s |
  | prefill ngay sau một lần đọc cả prompt | không có | 2895 token / 28.0s (sau lượt 1), 2341 / 23.5s (sau cửa sổ dịch) |

  Bật thì nhanh hơn ~1.5s mỗi lượt, nhưng người chơi gửi trong lúc prefill đọc lại cả prompt lần hai thì lượt đó chờ ~25s.

Khi bật:
- `StateService.next_prompt_prefix(story)` dựng prompt với lượt người chơi giả (trung vị độ dài, như cũ), cùng `PromptLore` thật của lượt sắp tới. Phần carried chỉ phụ thuộc `earlier`, và lượt giả không có từ khoá, nên fresh rỗng.
  - Có `built.lore_head`: trả `messages[:-1] + [ChatTurn(user, lore_head)]`, `open_last=True`.
  - Không có: trả `messages[:-1]` như cũ.
- Khi tắt, `next_prompt_prefix` vẫn phải truyền `reserve_tokens` thật của card (§6.4), chỉ không trả phần mở.
- `render_prefix(renderer, messages, *, open_last=False)`: khi `open_last`, message cuối được render thành `<|turn>user\n{content.lstrip()}` **không** có `<turn|>\n`.
  - Prompt thật render thành `<|turn>user\n{lore_head}\n- …fresh…\n[Hết…]\n\n{lời người chơi}…<turn|>\n…`.
  - Văn bản prefill vì vậy là chuỗi đầu của văn bản thật.
  - Token cuối của prefill có thể được tách khác khi có `\n` nối sau. Điểm chụp "cuối prompt trừ 4 token" của Ollama nằm trước chỗ đó, nên lượt thật vẫn dùng lại gần hết.
- `OllamaClient.prefill_prefix(model, messages, options=, open_last=False)` truyền cờ cho `render_prefix`. Worker gọi với `open_last=built.open_last`.
  - Prefill raw không dùng được (renderer khác, lỗi) thì worker prefill bằng `chat_stream` với `messages[:-1]` nếu `open_last`. `/api/chat` không gửi được lượt còn mở, và gửi lượt đã đóng thì rẽ ngay ở `\n`.
- `FakeLLM.prefill_prefix(..., open_last=False)` ghi `"open_last"` vào `calls`.
- **Sửa sổ thế giới** (tạo, sửa, bật/tắt, xoá, nhập) gọi `JobQueue.lore_changed(card_id)`. Nếu story đang được prefill hoặc đang chờ prefill thuộc card đó, worker huỷ prefill rồi hẹn prefill lại (như `messages_changed`).
  - Prefill đã chạy xong (worker rảnh, trường hợp thường gặp: người chơi sang Studio) mà story đang chơi thuộc card: worker hẹn prefill lại cho story đó (không giành chỗ của một prefill đang chờ cho story khác). Phần dự phòng D đổi 0 ↔ 520 làm cửa sổ đổi, phần đầu đã gửi trước không còn khớp.
  - Cùng lúc đó, nếu cửa sổ mới cần một mốc tóm tắt chưa có (`summary_target` với phần dự phòng mới), worker xếp `summarize` cho câu trả lời cuối, trong lúc người chơi còn ở Studio.
- **Cần đo trên Ollama thật trước khi bật**, khi người dùng cho phép (đang chat thì không đo). Lấy số token đọc lại từ log Ollama (`prompt_eval_count`), không chỉ TTFT:
  - lượt T có carried: đọc lại ≈ 4 token + fresh + lời người chơi + F;
  - **prefill(T+1)** ngay sau đó: đọc lại ≤ ~1500 token (một hai lượt), không phải cả prompt;
  - lượt thật T+1, và lượt T+2 sau hai lượt liền có carried.
  - Không đạt thì giữ `LORE_PREFILL_OPEN_TURN = False`. App vẫn đúng; lượt có khối D đọc thêm tối đa 520 token.
  - Harness đo: 10 lượt `luc-bac-uyen` nhắc "hôn ước", "Lục Chấn Đình", chạy hai lần (hằng bật, hằng tắt), cùng `base.db`, chờ hàng đợi và prefill xong rồi mới gửi lượt sau, như phase3.md §10.6.

### 6.6 Snapshot và ghi lại lượt nào mở mục nào

- `ChatService._build`: `lore = await LoreService.prompt_lore(story, card, persona, history)`. Hàm này đồng bộ; lỗi thì log rồi `None`, không bao giờ chặn lượt chat. Trả kèm `unsent_ids`.
- `_Plan` thêm `lore: PromptLore | None`.
- `_snapshot`: `BuiltPrompt.lore_used` đã nằm trong `model_dump`. Thêm `snapshot["lore_unsent"] = [ids]`, để dữ liệu train Phase 5 dựng lại đúng prompt.
- `_persist` (cả lượt bị ngắt giữa chừng, `aborted`): sau khi ghi message, `repo.record_lore_hits(story_id, message_id, carried/fresh/unsent)`, mỗi mục một hàng (`INSERT OR IGNORE` theo `UNIQUE(message_id, entry_id)`). Lỗi thì log, lượt vẫn lưu. Một mục bị xoá giữa lúc dựng prompt và lúc ghi (FK hỏng) chỉ làm hàng đó bị bỏ qua, không làm hỏng cả lượt: ghi từng hàng, hoặc lọc `entry_id` còn tồn tại trong cùng transaction.

## 7. Rollback

| Thao tác | Kết quả |
|---|---|
| Regenerate | Prompt dựng lại từ đúng lịch sử, nên lore giống lần trước (trừ khi sổ thế giới vừa đổi). Variant mới có `lore_hits` riêng; variant cũ hết active nên hit của nó bị bỏ qua khi đọc. |
| Lật lại variant cũ | Hit của nó active trở lại. |
| Xoá từ một lượt | CASCADE xoá hit của các message bị xoá. |
| Sửa lượt người chơi / lượt nhân vật | Hit của lượt đã sinh giữ nguyên (đó là điều prompt đã dùng). Lượt sau quét chữ đã sửa (carried tính lại), và worker huỷ, hẹn lại prefill như hiện nay. |
| Xoá một mục | Mục tự thêm: CASCADE. Mục từ file/card: thành bia mộ (`removed = 1`) và xoá hit của nó (§4.4). Cả hai trường hợp, mục biến mất khỏi danh sách đã mở. |
| Tắt một mục | Không gợi nữa; hit cũ vẫn hiện trong danh sách đã mở (đã từng mở). |
| Sửa nội dung mục | Danh sách đã mở hiện nội dung mới; snapshot của lượt cũ vẫn giữ nguyên văn đã gửi. |
| "Đọc lại story" (rebuild) | Không đụng lore. Story cũ trước Phase 4 không có hit; danh sách bắt đầu từ lượt kế tiếp. |

Đọc danh sách đã mở (`repo.unlocked_lore(story_id)`):

```sql
SELECT h.entry_id, MIN(m.turn_index), MAX(m.turn_index), COUNT(DISTINCT m.turn_index),
       MAX(h.slot IN ('carried', 'fresh')) AS sent
FROM lore_hits h JOIN messages m ON m.id = h.message_id AND m.is_active = 1
JOIN lore_entries e ON e.id = h.entry_id AND e.removed = 0
WHERE h.story_id = ? GROUP BY h.entry_id
```

Sau đó tính audience từ `known_by`:
- bỏ `others`;
- bỏ everyone/character có `sent = 0` (chỉ khớp mà chưa bao giờ đến được model, §6.2);
- player luôn giữ (slot của nó luôn là `unsent`).

Xếp theo `MAX(turn_index)` giảm dần. `StoryExtras.lore_tags` dùng cùng danh sách này (everyone + player), nên hai chỗ không lệch nhau.

## 8. API (`api/routes_lore.py`; mọi route lọc theo `current_account`)

| Method | Path | Body → Kết quả |
|---|---|---|
| GET | /api/cards/{card_id}/lore | `LoreEntryOut[]` theo `position, id` |
| POST | /api/cards/{card_id}/lore | `LoreEntryIn` → `LoreEntryOut`. Slug `manual:<12 hex>`. 409 khi quá `MAX_LORE_ENTRIES_PER_CARD` |
| PUT | /api/cards/{card_id}/lore/{entry_id} | `LoreEntryIn` → `LoreEntryOut`. Mục `world_md`/`card_book` thì `edited = 1` khi có trường đổi thật (§4.4) |
| PATCH | /api/cards/{card_id}/lore/{entry_id} | `LorePatch` → `LoreEntryOut` (bật/tắt, đổi chỗ); có đổi `updated_at` |
| DELETE | /api/cards/{card_id}/lore/{entry_id} | `{"deleted": 1}`. Mục từ file/card thành bia mộ (§4.4). Mục `removed` coi như không có (404) ở mọi route |
| POST | /api/cards/{card_id}/lore/import | `LoreImportRequest` → `LoreImportResult`. 422 khi không có mục nào hoặc chữ quá dài |
| POST | /api/cards/{card_id}/lore/import-book | `{"dry_run": bool}` → `LoreImportResult` (từ `extensions.v2.character_book`). Xong thì bỏ book khỏi extensions |
| GET | /api/cards/{card_id}/lore/summary | `LoreSummary` (hồ sơ nhân vật; mẫu chưa cài: 404, giao diện ẩn phần này) |
| GET | /api/stories/{story_id}/lore | `StoryLore` |
| (đổi) | GET /api/stories/{id}/extras | `lore_tags`, `lore_available` có dữ liệu |
| (đổi) | POST /api/stories | `show_thoughts?: bool` ở cấp ngoài (không nằm trong `settings`) |
| (đổi) | PATCH /api/stories/{id} | `show_thoughts?: bool` |
| (đổi) | GET /api/stories, GET /api/stories/{id} | `Story.show_thoughts` |
| (đổi) | POST /api/cards, GET /api/cards/{id}/export, POST /api/cards/{id}/duplicate | character_book (§4.6) |
| (đổi) | GET /api/lore/status | §2 |

- **404**: card hoặc story không có, hoặc thuộc account khác. Mục không thuộc card trong path cũng 404.
- **422**: dùng câu tiếng Việt dễ hiểu (`detail`), ví dụ:
  - "Mục thế giới cần có tên."
  - "Mỗi mục có tối đa 32 từ khoá."
  - "Cần chọn ai biết điều này."
  - "File quá lớn (tối đa 500 KB)."
  - "Không tìm thấy mục thế giới nào. File cần có phần “## Mục lore”, “## Nhân vật xung quanh” hoặc “## Địa điểm”."
- **Không khoá story khi sửa lore**: story đang sinh câu trả lời vẫn sửa được. Lượt đang chạy đã dựng prompt xong, lượt sau dùng bản mới.
- **Card mẫu đã cài**: người dùng sở hữu nên sửa được. Mẫu chưa cài không có `card_id`, nên không có route nào áp dụng.

Ví dụ:

```json
// GET /api/stories/12/lore
{"available": true, "can_edit": true, "card_id": 4, "entries": [
  {"entry_id": 31, "title": "Hôn ước Lục - Ôn", "category": "lore", "audience": "everyone",
   "content": "Năm 1979, … ông nội của Ngọc Anh, …", "first_turn": 3, "last_turn": 7, "turns": 3},
  {"entry_id": 26, "title": "Hứa Tri Ý và đêm mười bảy tháng ba", "category": "lore", "audience": "player",
   "content": "Theo nguyên tác, …", "first_turn": 5, "last_turn": 5, "turns": 1},
  {"entry_id": 36, "title": "Câu nói đêm mưa", "category": "lore", "audience": "character",
   "content": "Đêm trước sinh nhật hai mươi tuổi, …", "first_turn": 7, "last_turn": 7, "turns": 1}]}

// POST /api/cards/4/lore/import  {"text": "...", "filename": "world.md", "dry_run": true}
{"dry_run": true, "created": 27, "updated": 0, "unchanged": 0, "kept_edited": 0, "deleted": 0,
 "missing": 0, "skipped_removed": 0,
 "player_only": ["Hứa Tri Ý", "Phó Cảnh Hành", "Tô Mạn Ninh", "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa"],
 "items": [{"slug": "md:lore/tieu-thuyet-luc-tong-em-khong-can-anh-nua", "title": "Tiểu thuyết …", "category": "lore", "action": "create"}, …],
 "notes": ["Không nhập phần Bí mật và Chức năng của 7 nhân vật xung quanh, vì Lục Bắc Uyên không biết những điều đó.",
           "Bỏ 4 câu nhắc tới điều chỉ bạn biết.",
           "Hứa Tri Ý, Phó Cảnh Hành, Tô Mạn Ninh, Tiệm hoa Thu Đường và bệnh viện Nhân Hòa: chỉ bạn biết, vì thế giới có điều chỉ bạn biết về họ. Nếu Lục Bắc Uyên cũng biết họ, đổi trong Studio."],
 "warnings": ["Từ khoá “nhẫn” chỉ có một chữ, cũng khớp trong những từ như “kiên nhẫn”."]}
```

## 9. Giao diện Studio: phần "Thế giới" của trình sửa nhân vật

Tệp: `pages/studio/LorebookSection.tsx`, `LoreEntryDialog.tsx`, `LoreImportDialog.tsx`, `loreLogic.ts` (+ `loreLogic.test.ts`). Gắn vào `CardForm.tsx` ngay trước "Ghi chú của người tạo", `id="sec-world"`. Dùng primitive §11: `Section`, `Card`, `Button`, `Toggle`, `Badge`, `ChipInput`, `TextArea`, `ChoiceGroup`, `Modal`, `EmptyState`, `InlineAlert`, `Skeleton`, `Disclosure`.

**Tiêu đề và gợi ý:**
- "Thế giới"
- Gợi ý: "Người, nơi chốn và chuyện cũ quanh {tên}. Khi story nhắc tới một từ khoá, {tên} sẽ nhớ ra điều đó. Các mục ở đây được lưu ngay, không cần bấm Lưu nhân vật."

**Trạng thái:**

| Trạng thái | Hiện |
|---|---|
| Card chưa lưu (`id` null) | `EmptyState` "Lưu nhân vật trước, rồi thêm thế giới cho {tên}." Không có nút. |
| Đang tải | 3 `Skeleton` hàng 56px; vùng `aria-busy`. |
| Lỗi tải | `InlineAlert` "Không tải được thế giới của {tên}." + "Thử lại" + "Chi tiết". |
| Rỗng | `EmptyState` "Chưa có mục nào. Thêm một mục, hoặc nhập từ file thế giới (như world.md)." Hai nút sm: "Thêm mục" (secondary), "Nhập từ file" (ghost). Nhãn nút không ghi đuôi file. |
| Có book Card V2 chưa dùng | `Notice` "Card này có sẵn {n} mục thế giới từ file gốc." + "Dùng các mục này" (gọi `import-book`, xem trước như nhập file). |
| Có mục | Hàng công cụ (Thêm mục · Nhập từ file · ô "Tìm trong thế giới" khi > 12 mục; ô ẩn đi, ví dụ xoá bớt còn ≤ 12 mục, thì từ khoá cũng thôi lọc), rồi 3 nhóm `Disclosure` có số đếm: "Chuyện và bí mật" (lore), "Người xung quanh" (character), "Nơi chốn" (place). Nhóm rỗng thì ẩn. |

**Một hàng mục** (44px trở lên, chạm cả hàng để sửa):
- Tên mục (15px/500).
- `Badge` ai biết: "Mọi người" (neutral), "Chỉ {tên}" (accent), "Chỉ bạn" (gold), "Người khác" (neutral).
- Dòng phụ 13px `muted`: "Gợi nhớ khi nhắc: hôn ước, đính hôn, Lục Ôn…" (tối đa 3 khoá rồi "…").
- Không có khoá thì dòng phụ màu `warn`: "Chưa có từ khoá gợi nhớ".
- Bên phải là `Toggle` không nhãn hiện, `aria-label` "Dùng mục {tên mục}". PATCH lạc quan; lỗi thì bật lại như cũ và báo một dòng dưới hàng.
- Mục `edited` từ file có chữ nhỏ "Đã sửa", chỉ khi bật công cụ nâng cao.

**Hộp sửa mục** (`Modal md`, sheet từ dưới trên điện thoại; tiêu đề "Mục thế giới" hoặc "Mục mới"):
- `TextField` "Tên mục".
- `ChoiceGroup` "Loại": "Chuyện và bí mật" / "Người" / "Nơi chốn".
- `ChipInput` "Từ khoá gợi nhớ". Gợi ý: "Khi story nhắc đúng một trong các từ này, {tên} sẽ nhớ ra mục này. Có phân biệt dấu: “Lục” khác “lúc”. Tên riêng viết hoa (như “Hạ Trì”) gợi nhớ cả khi {tên} tự nhắc tới; từ thường (như “căn hộ”) chỉ gợi nhớ khi bạn nhắc." Cảnh báo từng khoá ngay dưới ô, 13px `warn`, từ `loreLogic.keyWarnings`:
  - 'Từ khoá "mẹ" chỉ có một chữ nên sẽ gợi rất thường xuyên.' (kèm ví dụ từ ghép nếu có, §4.5)
  - 'Từ khoá "{tên}" là tên nhân vật nên không dùng để gợi nhớ.'
  - Persona không có trong Studio, nên trùng tên persona chỉ được bỏ qua lúc chơi, không cảnh báo ở đây.
- `ChoiceGroup` "Ai biết điều này":
  - "Mọi người" (hint "{tên} và mọi người trong thế giới đều biết.");
  - "Chỉ {tên}" (hint "{tên} biết nhưng giữ trong lòng, không tự kể ra.");
  - "Chỉ bạn" (hint "Chỉ bạn biết. {tên} không bao giờ được đọc điều này.").

  Mục có `known_by` là tên người khác thì có thêm lựa chọn thứ tư, chỉ đọc: "Chỉ {Hạ Trì} biết" (hint "{tên} không biết điều này."). Chọn lựa chọn khác sẽ thay `known_by`.
- `TextArea` "Nội dung", kèm `UserPlaceholderBadge`. Gợi ý: "Viết như một đoạn ghi chú ngắn. Dùng {{user}} cho bạn và {{char}} cho {tên}." Dưới ô: "Dài quá thì {tên} chỉ đọc phần đầu." khi > 450 ký tự (`MAX_LORE_ITEM_CHARS`, lấy từ một hằng chung trong `loreLogic`).
- Mục "Mọi người" hoặc "Chỉ {tên}" mà nội dung có một từ trong `META_SPOILER_TERMS` (như "nguyên tác"): một dòng `warn` dưới ô nội dung, 'Có chữ “nguyên tác”. Nếu đây là điều {tên} không được biết, hãy chọn “Chỉ bạn”.' Chỉ nhắc, không chặn lưu.
- Chỉ khi bật công cụ nâng cao (`useAdvancedTools`): "Độ ưu tiên" (số −100..100), "Người biết" (danh sách thô), nguồn ("Nhập từ file", "Từ card gốc", "Tự thêm"), slug, ước lượng token.
- Chân hộp: "Xoá mục" (danger, hỏi lại ngay tại chỗ: "Xoá “{tên mục}”? Story đã mở mục này sẽ không còn thấy nó." · Giữ lại / Xoá; với mục nhập từ file thêm câu "Nhập lại file sẽ không thêm lại mục này."), "Huỷ" (ghost), "Lưu" (primary). Lỗi lưu: `InlineAlert` trong hộp, hộp vẫn mở.
- Kiểm tra trước khi gửi (`loreLogic.validateEntry`): tên rỗng ("Mục thế giới cần có tên."), quá 32 khoá, nội dung quá 4000 ký tự.

**Nhập file** (`LoreImportDialog`):
1. Nút mở `input type=file accept=".md,text/markdown,text/plain"`. Đọc bằng `File.text()`. Quá 500 KB thì báo ngay, không gửi.
2. Gửi `dry_run: true`. Modal "Nhập thế giới từ {tên file}" khi đang chờ thì có `Spinner` và "Đang đọc file…".
3. Kết quả, chữ từ `loreLogic.importSummaryLines`:
   - "Thêm 27 mục mới."
   - "Cập nhật 3 mục."
   - "Giữ nguyên 2 mục bạn đã sửa."
   - "Bỏ qua 2 mục bạn đã xoá."
   - "Không đổi 20 mục."
   - Khi `missing > 0`: `Toggle` "Xoá 3 mục không còn trong file" (mặc định tắt), hint "Chỉ bật nếu file này thay hẳn file cũ." Bật thì gửi lại `dry_run: true, delete_missing: true` để cập nhật số liệu.
   - Khi `player_only` không rỗng: `Notice` "Chỉ bạn biết: Hứa Tri Ý, Phó Cảnh Hành… vì thế giới có điều chỉ bạn biết về họ. Đổi trong danh sách sau khi nhập nếu {tên} cũng biết họ."
   - Một dòng cố định: "Người và nơi chốn được nhập với “Mọi người biết”. Hãy đọc lại: điều gì {tên} không nên biết thì sửa hoặc chuyển sang “Chỉ bạn”."

   Rồi `notes` và `warnings` (gạch đầu dòng, 13px). Danh sách tên mục theo nhóm nằm trong `Disclosure` "Xem các mục", và các câu đã bỏ nằm trong `Disclosure` "Xem các câu đã bỏ".
4. "Nhập" (primary) gửi lại với `dry_run: false`, đóng hộp, tải lại danh sách, báo "Đã nhập thế giới." (`LiveStatus`). Không có gì thay đổi thì nút là "Đóng" và câu "File này đã được nhập, không có gì mới."
5. Lỗi (422 hoặc mạng): `InlineAlert` + "Chi tiết", nút "Chọn file khác".

**Danh sách Studio** (`CardListPage.tsx`): bỏ thẻ "Wiki & Lorebook" (thư mục `world_wiki` không còn dùng), cùng `describeLoreStatus` và test của nó. Không cần câu thay thế; phần "Thế giới" nằm trong từng nhân vật.

**Xem trước prompt** (chỉ khi bật công cụ nâng cao): `PromptPreviewPanel.BLOCKS` thêm `{key: "D", label: "D · Thế giới", hint: "Mục thế giới được gợi nhớ ở lượt này"}`. Xem trước chỉ có lời mở đầu, nên D thường rỗng. Lời mở đầu của card đã lưu nhắc tới một tên riêng có trong sổ thì D có mặt (carried) ở đầu message user cuối: khi đó message này có nhãn "Khối D + lượt người chơi + khối F" và câu dưới số đếm nói "để thấy khối D và khối F" (`previewLogic.ts`).

**Chat thử ở Studio**: card đã lưu (`card.id`) thì `test-chat` cũng dựng `PromptLore` từ các lượt chat thử, để tác giả thử từ khoá. Không ghi `lore_hits`. Không có giao diện riêng; xem trong "Xem trước" nâng cao.

## 10. Hồ sơ nhân vật (chỉ đọc)

- `CharacterPage.tsx`, tab "Giới thiệu", sau "Bối cảnh": phần "Thế giới". Chỉ hiện khi `LoreSummary.total > 0`.
  - "{total} điều về thế giới của {tên}."
  - "Người quanh {tên}": `Chip` tĩnh với tên các nhân vật xung quanh.
  - "Nơi chốn": `Chip` tĩnh với tên các địa điểm.
  - Chỉ gồm mục category character/place có audience everyone, tối đa 8 mỗi loại, rồi "+N".
- **Không bao giờ** hiện nội dung, tên mục loại "Chuyện và bí mật", hay mục chỉ nhân vật / chỉ người chơi biết. Những tên như "Kết cục của phản diện" hay "Câu nói đêm mưa" tự chúng đã là spoiler.
- Tải song song với card; lỗi hoặc 404 (mẫu chưa cài) thì ẩn phần này, không báo lỗi.
- Logic trong `pages/character/logic.ts` (`worldTeaser(summary, name)`), có test.

## 11. Ngăn "Cảm xúc & ký ức" trong chat

Tệp: `pages/chat/HeartDrawer.tsx`, `pages/chat/useStoryLore.ts`, `pages/chat/loreLogic.ts` (+ test).

### 11.1 Tải dữ liệu

- `useStoryLore(storyId, open, signature)`:
  - gọi `GET /stories/{id}/lore` khi ngăn mở;
  - khi đang mở mà chữ ký `${extras.lore_count}|${extras.lore_tags.join("|")}` đổi (một lượt vừa mở mục mới), hoặc sau thao tác regenerate / lật variant / xoá, thì gọi lại. `lore_tags` không có mục "Chỉ {tên}", nên chỉ dựa vào nó thì mục bí mật vừa mở sẽ không làm ngăn tải lại. `StoryExtras.lore_count: int = 0` là số mục đã mở, mọi audience trừ others;
  - đóng ngăn thì giữ dữ liệu cũ, không hỏi lại;
  - chỉ câu trả lời mới nhất được dùng.
- `/extras` (đã hỏi lại theo `useStoryExtras`) chỉ mang tên mục và `lore_available`, không mang nội dung.

### 11.2 Phần "Thế giới đã mở khoá" (thay phần "Wiki đã mở khoá" rỗng hiện nay)

| Trạng thái | Hiện |
|---|---|
| Đang tải lần đầu | `Skeleton` pill 160×28 ×2 |
| Lỗi | Một dòng 14px "Chưa tải được thế giới." + nút ghost "Thử lại" + `ErrorDetails` |
| Story cũ, có sổ thế giới nhưng chưa có hit nào (nhập sổ sau khi đã chơi) | như "chưa mở mục nào" bên dưới; không dò lại các lượt cũ |
| Card không có mục nào (`available` false) | "{tên} chưa có sổ thế giới." Khi `can_edit`: nút ghost sm "Thêm trong Studio" → `#/studio/{card_id}` (cuộn tới `sec-world`) |
| Có sổ nhưng chưa mở mục nào | "Chưa mở khoá điều gì. Khi story nhắc tới người, nơi chốn hay chuyện cũ trong thế giới của {tên}, chúng sẽ hiện ở đây." |
| Có mục | Danh sách như dưới |

- **Mục mọi người biết và mục chỉ bạn biết**: mỗi mục là một hàng `Disclosure`.
  - Icon `IconSparkles` 15px màu `accent-2`, tên mục, rồi `Badge` "Chỉ bạn biết" (gold) cho audience player.
  - Mở ra là nội dung `font-story` 14px `prose`, cộng nút ghost sm "Xem lúc được nhắc tới lần đầu", nhảy tới `first_turn` bằng cùng cơ chế `jumpPlan` của sheet Sự kiện (kể cả thông báo "Lượt này nằm bên {Story/DM}…").
  - **Không in số lượt**: `turn_index` đếm cả lượt người chơi lẫn nhân vật và bắt đầu từ 0, nên "lượt 7" không khớp với điều người chơi thấy. Sheet Sự kiện cũng không in số lượt.
  - Không dùng emoji ✨, vì lint cấm emoji.
- **Mục chỉ nhân vật biết** (audience character): nhóm riêng phía dưới, tiêu đề phụ "Điều {tên} giữ trong lòng".
  - Mỗi mục là một thẻ giống `ThoughtCard`: viền trái 3px `accent`, **cả tên lẫn nội dung bị làm mờ** (`blur(3px)`, `select-none`), lời mời "Chạm để đọc".
  - Chạm thì hiện rõ (`transition-all duration-300`). Công tắc "Luôn hiện suy nghĩ" (`lyris.revealThoughts`) cũng bỏ mờ ở đây.
  - Screen reader: thẻ mờ có `aria-label` "Một điều {tên} giữ trong lòng, chạm để đọc", và chữ thật chỉ có trong DOM khi đã mở.
  - **Story tắt "Đọc suy nghĩ của nhân vật" (§12) thì nhóm này không hiện, kể cả số đếm.**
- Thứ tự: gợi ra gần nhất trước (theo API).
- `loreLogic.splitUnlocked(entries, showThoughts)` trả `{open, secret}`. `secret` luôn rỗng khi `showThoughts` false. Có test.

## 12. B: Không đọc suy nghĩ

Nhân vật vẫn nghĩ: model vẫn viết `[Thought: …]`, worker vẫn đọc Thought để chấm cảm xúc (phase3.md §5), `raw_content` và `thought` không đổi. Người chơi chỉ không thấy.

### 12.1 Backend

- Migration 0007 thêm `stories.show_thoughts` (§1). `Story.show_thoughts: bool = True`.
- `Repo`:
  - đọc cột với `bool(row["show_thoughts"])`, phòng thủ khi cột chưa có (§1);
  - `create_story` ghi theo story;
  - `update_story` nhận `show_thoughts` (thêm vào `STORY_UPDATABLE_FIELDS`, ghi 0/1).
  - **PATCH chỉ đổi `show_thoughts` thì không đổi `stories.updated_at`.** Hub xếp story theo `MAX(updated_at, message mới nhất)`, nên bật/tắt một công tắc hiển thị trên header sẽ đẩy story lên đầu hub và đổi giờ "lần cuối". Cũng không gọi `mode_changed`/`messages_changed`, và không huỷ prefill (prompt không đổi).
- API:
  - `StoryCreate.show_thoughts: bool | None = None` ở cấp ngoài, cạnh `settings`. Không đặt vào `StorySettings`, vì đó là thiết lập của prompt (xem trước, chat thử), còn đây chỉ là cách hiển thị;
  - `StoryPatch.show_thoughts: bool | None`. `False` vẫn đi qua bộ lọc `v is not None` của `patch_story`;
  - `GET /stories/defaults` không đổi (mặc định luôn là true).
- Prompt, trích xuất, gợi ý, prefill: **không đổi gì**. Có test khẳng định prompt của story `show_thoughts=False` giống hệt story `True`.

### 12.2 Hiển thị

- `lib/storyBlocks.ts`: `visibleBlocks(blocks, showThoughts)` bỏ khối `thought` khi tắt. `StoryReply({segments, streaming, showThoughts = true})` dùng nó trước khi chọn khối mang con trỏ nhấp nháy (caret).
- **Đang stream** (`MessageList` → `StreamingStory`):
  - khối hiện được cuối cùng mang caret. Khi model đang viết một Thought bị ẩn ở giữa hoặc ở cuối lượt (`thought_style` end), caret vẫn nhấp nháy ở đoạn dẫn truyện/thoại cuối, nên người chơi biết nhân vật còn đang viết;
  - chưa có khối nào hiện được (lượt mở đầu bằng Thought) thì hiện `StoryWaiting` (ba chấm), như khi `segments` rỗng;
  - `LiveStatus` không đổi.
- **Lượt đã xong mà chỉ có Thought** (hiếm): một dòng 13px `muted` "Lượt này chỉ có suy nghĩ của {tên}." Hàng thao tác (tạo lại, sửa, xoá…) vẫn ở đó. DM cũng vậy: dòng này thay cho bong bóng "…" (chạm vào vẫn mở hàng thao tác).
- **DM** (`DmThread`): `ThoughtCard compact` dưới bong bóng cũng không render.
- Thẻ suy nghĩ **không có trong DOM**, kể cả bản làm mờ, nên screen reader không đọc được.
- **Sửa một lượt của nhân vật**: ô sửa vẫn chứa nguyên văn kèm `[Thought: …]`, vì sửa phải giữ được Thought. Trên ô có một dòng `muted`: "Bản sửa có cả suy nghĩ của {tên}." Đây là ngoại lệ có chủ ý: người chơi tự mở để sửa.
- **Không áp dụng cho**:
  - chat thử ở Studio (công cụ của tác giả);
  - "Chỉ dẫn diễn xuất" và ký ức trong ngăn cảm xúc (đó là thái độ, không phải lời suy nghĩ).

### 12.3 Chỗ bật/tắt

Một công tắc dùng chung, `Toggle`:
- nhãn "Đọc suy nghĩ của nhân vật";
- description "Tắt thì thẻ suy nghĩ không hiện trong story. {tên} vẫn nghĩ như thường, chỉ là bạn không đọc thấy." (không có tên nhân vật thì dùng "Nhân vật").

Ba chỗ:

1. **Sheet "Bước vào câu chuyện"** (`StartStorySheet`, `Disclosure` "Tuỳ chỉnh story"): ngay dưới "Kiểu suy nghĩ".
   - `StoryDraft.show_thoughts: boolean` (mặc định true; `draftFromDefaults`, `rebaseDraft` giữ giá trị người chơi đã chọn).
   - `createRequest` thêm `show_thoughts: false` chỉ khi tắt.
   - Xem trước lời mở đầu trong sheet cũng theo công tắc.
   - Không mở "Tuỳ chỉnh story" thì không gửi trường này (server mặc định true).
2. **Thiết lập story** (`StorySettingsPanel`): ngay dưới Select "Suy nghĩ của nhân vật ở Story".
   - `StorySettingsForm.show_thoughts`, `formFromStory`, `settingsPatch` (chỉ gửi khi đổi).
   - Lưu cùng nút "Lưu" hiện có.
3. **Menu "Suy nghĩ" trên header chat** (`ThoughtMenu`): công tắc ở trên cùng, lưu ngay qua `patchStory({show_thoughts})` lạc quan (như `thought_style`; server từ chối thì trả lại).
   - Khi tắt: công tắc "Luôn hiện suy nghĩ" bị ẩn (không còn gì để làm mờ). Radio kiểu suy nghĩ vẫn giữ (model vẫn viết Thought), kèm câu "Nhân vật vẫn nghĩ trong lòng theo kiểu này, chỉ là bạn không đọc thấy."
   - Nút header: khi tắt đổi icon thành `IconEyeOff` (thêm vào `components/icons.tsx`, kiểu Lucide `eye-off`), nhãn giữ "Suy nghĩ", `aria-label` "Suy nghĩ (đang ẩn)".
   - Khác với "Luôn hiện suy nghĩ" (lưu theo thiết bị, `localStorage`), công tắc này lưu theo story trên server, nên iPhone và Mac thấy giống nhau.

## 13. Hợp đồng frontend ↔ backend (`frontend/src/types.ts`)

Thêm:

```ts
export type LoreCategory = "lore" | "character" | "place";
export type LoreSource = "manual" | "world_md" | "card_book";
export type LoreAudience = "everyone" | "character" | "player" | "others";

export interface LoreEntry {
  id: number; card_id: number; slug: string; title: string; category: LoreCategory;
  keys: string[]; known_by: string[]; content: string; source: LoreSource; edited: boolean;
  enabled: boolean; priority: number; position: number; extra: Record<string, unknown>;
  created_at: string | null; updated_at: string | null;
  audience: LoreAudience; warnings: string[];          // LoreEntryOut
}
export interface LoreEntryInput {
  title: string; category: LoreCategory; keys: string[]; known_by: string[];
  content: string; enabled: boolean; priority: number;
}
export interface LorePatch { enabled?: boolean; position?: number }
export interface LoreImportRequest { text: string; filename?: string | null; dry_run: boolean; delete_missing?: boolean }
export type LoreImportAction =
  | "create" | "update" | "unchanged" | "keep_edited" | "delete" | "keep_missing" | "skip_removed";
export interface LoreImportResult {
  dry_run: boolean; created: number; updated: number; unchanged: number; kept_edited: number; deleted: number;
  missing: number; skipped_removed: number; player_only: string[]; dropped_sentences: string[];
  items: { slug: string; title: string; category: LoreCategory; action: LoreImportAction }[];
  notes: string[]; warnings: string[];
}
export interface UnlockedLore {
  entry_id: number; title: string; category: LoreCategory; audience: "everyone" | "character" | "player";
  content: string; first_turn: number; last_turn: number; turns: number;
}
export interface StoryLore { available: boolean; can_edit: boolean; card_id: number; entries: UnlockedLore[] }
export interface LoreSummary { total: number; people: string[]; places: string[]; people_more: number; places_more: number }
export interface LoreUse { entry_id: number; title: string; slot: "carried" | "fresh"; tokens: number }
```

Đổi:
- `Story.show_thoughts?: boolean`: tuỳ chọn để server cũ vẫn chạy; thiếu thì coi là `true` (`showThoughtsOf(story)` trong `lib/storyOptions.ts`).
- `StoryPatch.show_thoughts?: boolean`.
- `StoryCreateRequest.show_thoughts?: boolean`.
- `StoryExtras.lore_available?: boolean`, `StoryExtras.lore_count?: number`. `lore_tags` giữ kiểu; sửa chú thích "Phase 4 still empty".
- `BuiltPrompt.lore_used?: LoreUse[]`.
- `StorySettingsForm` (`lib/storyOptions.ts`) và `StoryDraft` (`startLogic.ts`) thêm `show_thoughts: boolean`.
- `chatLogic.normalizeExtras` đọc `lore_available` phòng thủ: thiếu thì false, `lore_count` thiếu thì 0, `lore_tags` tối đa 50 chuỗi.

`api/client.ts` thêm:
- `listLore(cardId)`, `createLore(cardId, body)`, `updateLore(cardId, id, body)`, `patchLore(cardId, id, patch)`, `deleteLore(cardId, id)`;
- `importLore(cardId, req)`, `importCardBook(cardId, dryRun)`, `getLoreSummary(cardId)`;
- `getStoryLore(storyId, signal?)`.

`LoreStatus`/`getLoreStatus` giữ để không vỡ build, nhưng không còn chỗ nào gọi.

## 14. Kiểm tra

### 14.1 Backend (pytest, `backend/.venv/bin/pytest`, DB tạm; không Ollama, dùng `FakeLLM`/`ScriptedLLM`)

- **`tests/test_lore_parse.py`**:
  - 4 file `worlds/*/world.md` thật cho đúng số ở §4.5 (26/27/27/25), đúng phân bố `known_by`, đúng danh sách bỏ vì trùng;
  - đọc được cả `- **keys:**` lẫn `- keys:`, cả `###` lẫn đoạn `**Tên (中文)**`;
  - không còn dòng nào mở đầu "Bí mật"/"Chức năng" trong mục nhân vật xung quanh;
  - (sau review) `**Bí mật:**` không gạch đầu dòng trong mục `###` không thành mục riêng; mục con thụt vào dưới `- Bí mật:`, danh sách dưới nhãn đứng riêng và phần dưới `#### Bí mật` đều bị bỏ; nhãn in đậm khác trong mục `###` là nội dung;
  - khoá sinh ra như các ví dụ ở §4.5; không có khoá một âm tiết tự sinh; `Lương ma ma` không có "ma ma";
  - slug ổn định, trùng thì `-2`;
  - file không có ba phần đó → không có mục;
  - `content` nhiều dòng; thiếu `known_by` → `["*"]` + cảnh báo;
  - `known_by` là tên nhân vật → lưu `{{char}}`; tên lệch → audience others + cảnh báo;
  - **lọc lộ** (§4.3) trên `luc-bac-uyen`: Hứa Tri Ý, Phó Cảnh Hành, Tô Mạn Ninh và "Tiệm hoa Thu Đường và bệnh viện Nhân Hòa" là `["{{user}}"]`. Với cả 4 file, không mục everyone/character nào có một từ trong `META_SPOILER_TERMS` hay một khoá của mục `{{user}}` cùng file. Ba file kia không bị bỏ câu nào;
  - tiêu đề chỉ có chữ Hán → slug `h…` không rỗng.
- **`tests/test_lore_match.py`**: mọi dòng của bảng §5.4; NFC/NFD; `canon_tone` (`hoà/hòa`, `thuý/thúy`, `quý` giữ nguyên, `hoàng` không đổi); khoá chữ Hán; bỏ tên nhân vật và persona; khoá chứa tên nhân vật vẫn khớp; khoá có `{{char}}` được `fill`; khoá viết thường không gợi từ lượt nhân vật, khoá tên riêng thì có; lời mở đầu thật của `tan-duong` không gợi "Chứng lo âu xã hội".
- **`tests/test_lore_select.py`**:
  - mục `{{user}}` không bao giờ vào `carried`/`fresh`, kể cả khi là mục khớp duy nhất (chỉ vào `unsent_ids`);
  - audience character được đánh dấu `private`; `others` không gửi;
  - ngân sách 240 / phần còn lại / 520 và `LORE_MAX_ITEMS`; luôn còn chỗ cho ít nhất một mục fresh có nội dung dài `MAX_LORE_ITEM_CHARS` và tên ≤ 40 ký tự (kể cả mục riêng tư); hết chỗ → `unsent_ids`;
  - thứ tự xác định: chạy 2 lần với dữ liệu xáo trộn cho cùng kết quả;
  - độ sâu quét 4: mục nhắc ở P₋₂ còn, ở P₋₃ rơi ra;
  - không trùng giữa carried và fresh; `reserve_tokens` 0 khi card chỉ có mục `{{user}}`.
- **`tests/test_lore_prompt.py`**:
  - không truyền `lore`, hoặc truyền `PromptLore` rỗng với `reserve_tokens=0`: prompt giống hệt từng byte (cả `test_prompt.py`, `test_prompt_state.py`, `test_window_hysteresis.py` cũ vẫn qua);
  - system message giống hệt giữa các lượt gợi ra mục khác nhau;
  - khối D nằm đầu message user cuối, thứ tự mở → carried → fresh → đóng → lời người chơi → F;
  - `token_estimate["D"]`; `lore_head` đúng là đầu message cuối;
  - lượt chỉ có chỉ đạo;
  - mục có "((" không tạo "((" ở chỗ nối;
  - cửa sổ dịch đúng như khi không có lore khi `reserve_tokens` cố định: 30 lượt, mỗi lượt gợi số mục khác nhau, điểm bắt đầu cửa sổ không đổi giữa các lượt ngoài mốc khúc;
  - D không bị đếm vào `e_tokens` (`token_estimate["E"]` của lượt có D bằng lượt không có D cùng lịch sử);
  - với 4 card thật, Story, có tóm tắt dài nhất: tổng ước lượng ≤ `limit` ở mọi lượt, và ngay sau lần dịch, cửa sổ còn ít nhất một cặp lượt trọn vẹn (ghi số đo vào test để thấy khi ai đó tăng `LORE_TOKEN_LIMIT`).
- **Prefill** (`test_prefill_*`, mở rộng `test_jobs.py` và `test_ollama_client.py`):
  - **mặc định (`LORE_PREFILL_OPEN_TURN = False`)**: 30 lượt có từ khoá rải rác; `next_prompt_prefix(...).messages` bằng đúng `prompt_thật.messages[:-1]` ở mọi lượt, kể cả lượt cửa sổ dịch (phần dự phòng lore được truyền cho cả hai); `open_last` luôn False;
  - **bật hằng** (monkeypatch): 30 lượt cùng độ dài có từ khoá rải rác. Ở mỗi lượt, `render_prefix(gemma4, next_prompt_prefix(...).messages, open_last=True)` phải là chuỗi đầu của `render_prefix(gemma4, prompt_thật.messages)`, kể cả lượt cửa sổ dịch;
  - không có carried → `open_last` False, giống Phase 3;
  - worker gọi `prefill_prefix(..., open_last=True)`; raw lỗi → `chat_stream` với `messages[:-1]`;
  - `lore_changed(card_id)` huỷ và hẹn lại prefill của story thuộc card đó, không đụng story khác; worker rảnh thì hẹn prefill story đang chơi và xếp tóm tắt khi cần (sau review), phần đầu gửi trước khớp prompt thật của lượt sau.
- **`tests/test_lore_api.py`**:
  - CRUD, 404 với account khác và với mục của card khác;
  - kiểm tra dữ liệu và câu 422;
  - PUT mục `world_md` có đổi → `edited`; PUT không đổi gì → không `edited`; PATCH thì không;
  - nhập `dry_run` không ghi gì;
  - nhập rồi nhập lại → toàn `unchanged`, số hàng không đổi;
  - sửa tay rồi nhập lại → `keep_edited`;
  - xoá một mục từ file rồi nhập lại → `skip_removed`, mục không quay lại, không hiện trong GET, không được so khớp;
  - file mới thiếu một mục → mặc định `keep_missing`; với `delete_missing` → `delete` (mục đã sửa thì giữ); mục `manual` không bị đụng;
  - nhập file A rồi file B (khác mục) → mục của A còn nguyên;
  - Card V2 có `character_book`: import → create → các mục `card_book`, book bị bỏ khỏi `extensions.v2`; PUT lại card với book trong `extensions` → không nhân đôi mục, book lại bị bỏ; export → `character_book` dựng lại đủ trường (round-trip `extra`, `known_by`); book bị sắp lại thứ tự → slug không đổi;
  - `import-book` cho card cũ; nhân bản card sao chép mục; xoá card xoá mục và hit;
  - `/lore/summary` chỉ có tên người/nơi everyone;
  - `/stories/{id}/lore` không bao giờ trả audience `others`.
- **`tests/test_lore_e2e.py`** (`ChatService` thật + `FakeLLM`, worker `run_until_idle`):
  - gửi lượt có "hôn ước" → `lore_hits` fresh, snapshot `lore_used`;
  - lượt sau → mục đó thành carried;
  - lượt có "Hứa Tri Ý" (mục `{{user}}`) → nội dung mục **không có trong bất kỳ message nào gửi cho FakeLLM** (kiểm `calls`), nhưng `/lore` trả nó với audience player;
  - **test lộ toàn bộ** (§6.1): nhập `luc-bac-uyen/world.md`, gửi lần lượt mọi khoá của mọi mục làm lời người chơi; message user cuối gửi cho FakeLLM không bao giờ chứa nội dung của mục player hay từ trong `META_SPOILER_TERMS`;
  - mục everyone khớp nhưng hết chỗ (`unsent`) → không có trong `/lore` hay `lore_tags`;
  - regenerate → variant mới có hit riêng; lật lại variant cũ → danh sách đổi theo; xoá từ lượt đó → hit biến mất;
  - lượt bị ngắt giữa chừng rồi lưu → hit ghi một lần (UNIQUE);
  - `/extras.lore_tags` đúng thứ tự; `lore_count` tính cả mục "Chỉ {tên}".
- **Không đọc suy nghĩ**:
  - tạo story `show_thoughts: false`; PATCH qua lại;
  - story cũ (DB dựng ở version 6) đọc ra `true`;
  - `GET /stories` có trường này;
  - prompt của hai story chỉ khác `show_thoughts` giống hệt;
  - PATCH chỉ `show_thoughts` không đổi `updated_at`, không đổi thứ tự `GET /stories`.
- **Migration**: `LATEST = 7`; DB version 6 có dữ liệu → nâng cấp giữ đủ hàng; `PRAGMA foreign_key_check` rỗng; xoá message (`truncate_from`) xoá hit theo CASCADE; `_row_to_story` đọc được hàng không có cột `show_thoughts`.
- Sửa `test_card_v2.py`: không còn cảnh báo "character_book… Phase 4".

### 14.2 Frontend (`npm test`, node:test; `typecheck`; `build`)

- `lib/storyBlocks.test.ts`: `visibleBlocks` bỏ Thought; khối mang caret khi stream đang ở Thought ẩn; chỉ có Thought → rỗng.
- `pages/studio/loreLogic.test.ts`:
  - `audienceOf` / `knownByFor` (giữ tên người khác khi không đổi lựa chọn);
  - `keyWarnings` (một chữ, trùng tên nhân vật, có dấu và không dấu); `contentWarnings` ("nguyên tác" trong mục Mọi người);
  - `importSummaryLines` (số nhiều, 0 thì bỏ dòng, "không có gì mới", "Bỏ qua N mục bạn đã xoá", công tắc xoá mục thiếu chỉ khi `missing > 0`);
  - `groupEntries`, `filterEntries` (không phân biệt hoa thường, giữ dấu);
  - `validateEntry`.
- `pages/chat/loreLogic.test.ts`: `splitUnlocked` (ẩn nhóm bí mật khi tắt suy nghĩ), các câu trạng thái rỗng.
- `pages/character/logic.test.ts`: `worldTeaser` (ẩn khi total 0, "+N").
- `startLogic.test.ts`: `createRequest` có `show_thoughts: false` chỉ khi tắt; `rebaseDraft` giữ lựa chọn.
- `lib/storyOptions.test.ts`: `formFromStory` (thiếu trường → true), `settingsPatch` gửi `show_thoughts` khi đổi.
- `chatLogic.test.ts`: `normalizeExtras` với và không có `lore_available`.
- `friendlyError.test.ts`: thêm các câu 422 mới vào danh sách câu của server.

### 14.3 Chạy thử giao diện

Backend tự chạy ở cổng 8060-8069 trên DB demo tạm trong `scratchpad/p4/`, Ollama trỏ cổng chết. Vite riêng ở cổng 8061. Chrome headless 390×844 và 1280×860, hai theme:
- Studio: nhập `worlds/luc-bac-uyen/world.md` (xem trước có "Chỉ bạn biết: Hứa Tri Ý…" và "Xem các câu đã bỏ" → nhập → nhập lại "không có gì mới"); sửa một mục (cảnh báo từ khoá "mẹ"); tắt/bật; xoá rồi nhập lại (mục không quay lại); card chưa lưu.
- Ngăn cảm xúc: có sổ, chưa mở gì; có mục mọi người, chỉ bạn, bí mật (mờ, chạm để đọc); tắt suy nghĩ → nhóm bí mật biến mất. Dữ liệu stream giả lập bằng cách vá `fetch` như §15 design-impl.
- Story có Thought: bật/tắt "Đọc suy nghĩ" ở menu header, ở thiết lập story và ở sheet bắt đầu; stream giả có Thought ở giữa và ở cuối (caret, ba chấm); DM.
- Hồ sơ nhân vật: phần "Thế giới" chỉ có tên người và nơi chốn.
- `lint.mjs --app` 0 FAIL; `inspect.mjs --app --allow gradient,gradient-text` 0 FAIL.
- Tắt mọi server của mình trước khi xong.

### 14.4 Harness (sau, cần model thật; chỉ chạy khi người dùng tắt app)

`harness/scenarios/lore_*.yaml` trên `luc-bac-uyen`:
- **Có từ khoá**: hỏi về "hôn ước" → câu trả lời đúng năm 1979, con tàu.
- **Không có từ khoá**: câu trả lời không bịa chi tiết lore.
- **Lore bị cấm**: người chơi nhắc "Hứa Tri Ý", "nguyên tác", "Phó Cảnh Hành" → nhân vật không biết cốt truyện gốc, không gọi ai là "nữ chính"/"nam phụ" (LLM judge).
- **Bí mật riêng**: nhắc "đồng hồ của cha" → nhân vật không tự kể câu nói đêm mưa.
- **Lặp lore**: 10 lượt không nhắc từ khoá nào sau khi đã nhắc "đôi mắt" một lần → khối D rỗng từ lượt thứ 3; câu trả lời không nhắc lại "mắt xanh / bà nội" mỗi lượt.
- **Cache** (§6.5), đọc `prompt_eval_count` trong log Ollama: với hằng tắt, lượt có D chỉ đọc lại D + lời người chơi + F; với hằng bật, đo thêm prefill(T+1) và lượt T+1 ngay sau lượt có carried. Chỉ bật hằng khi đường bật không bao giờ đọc lại cả prompt.
  - **Kết quả đo 2026-11-14** (gemma4:12b, num_ctx 8192, đường app thật, 11 lượt mỗi lần, bảng ở §6.5): đường bật đọc lại cả prompt lần thứ hai sau lượt đầu story (2895 token, 28.0s) và sau cửa sổ dịch (2341 token, 23.5s). Không đạt, hằng giữ `False`. Đường tắt: lượt chat chỉ đọc D + lời người chơi + F (trung bình 615 token, TTFT 6.58s), prefill(T+1) ~380 token (~4s).
  - Cùng lần đo: lore khớp đúng (sticky 1-2 lượt, ngân sách carried 240 token có lúc đầy), 0 mục chỉ-`{{user}}` lọt vào prompt (22 snapshot), không lộ cốt truyện. Hai lỗi phụ đã sửa: luật DM trong `extract.py` có nơi mẫu "Nhà {p}" bị model chép nguyên (phase3.md, mục "Ghi chú khi chạy thử với gemma4:12b thật"), và story vừa tạo qua API chưa thành story đang chơi nên prefill sau lời mở đầu vẫn của story cũ (lượt đầu 28.7s → 7.1s sau khi sửa, `JobQueue.story_created(..., focus=True)` → `Worker.on_story_focused`).

## 15. Thứ tự làm (app của người dùng đang chạy với `--reload`)

1. `lore/normalize.py`, `parse.py`, `match.py`, `select.py`, `book.py` + test. Chưa ai import nên app không bị ảnh hưởng.
2. Kiểu ở `models.py`: chỉ thêm, mọi trường mới có mặc định.
3. `templates/{vi,en}.py` (hàm mới), `builder.py` (`lore=None` mặc định giữ đường cũ), `render.py`, `fake.py`, `ollama.py` (`open_last=False` mặc định). Chạy toàn bộ pytest: phải xanh, prompt cũ không đổi byte nào.
4. `0007_lore.sql` rồi `repo.py`. Thứ tự quan trọng, vì `--reload` nạp lại `repo.py` vào app của người dùng ngay khi lưu:
   - a. Viết 0007 ở **ngoài** `migrations/`. Test nó trên DB tạm bằng cách vá `MIGRATIONS_DIR` (§1), kể cả DB version 6 có dữ liệu. Đọc lại một lần cuối: đủ cột `removed`, `UNIQUE`, chỉ mục `message_id`.
   - b. Chép vào `backend/lyris/db/migrations/`, cùng lúc sửa các test đang khẳng định version 6. Từ đây migration là **cuối cùng**, không sửa nữa.
   - c. Lưu một file `.py` vô hại (ví dụ chú thích trong `models.py`) để app tải lại và áp 0007 vào DB thật (đã có bản sao lưu). Xem log uvicorn của app người dùng (chỉ đọc) hoặc `GET /api/health` ở cổng 8000 (chỉ đọc) để chắc app vẫn chạy.
   - d. Sau đó mới sửa `repo.py` (đọc/ghi `show_thoughts`, các hàm `lore_*`). `_row_to_story` vẫn đọc phòng thủ như §1.
5. `LoreService`, `routes_lore.py`, nối vào `app.py`, `ChatService`, `StateService`, worker, `card_v2.py`. Mỗi lần sửa một file thì file đó phải import được ngay. `LORE_PREFILL_OPEN_TURN = False`.
6. Frontend: B trước (nhỏ, độc lập), rồi Studio, rồi ngăn cảm xúc, rồi hồ sơ. Không chạy gì ở 5173/8000. Vite của người dùng nạp lại ngay khi lưu, nên `types.ts` và `api/client.ts` chỉ thêm (trường mới đều tuỳ chọn) trước khi có component dùng chúng.
7. Sửa `worlds/*/README.md`: thay câu "File này không tự đi vào prompt…" bằng mục "Nhập thế giới" (Studio → nhân vật → Thế giới → Nhập từ file → chọn `world.md` → đọc phần xem trước, nhất là danh sách "Chỉ bạn biết" và các câu đã bỏ). Ghi rõ: điều đã chép vào ô bối cảnh của story thì không cần nhập lại.
8. Đo trên Ollama thật (§6.5, §14.4) để cuối, khi người dùng báo tắt app.

## 16. Khác với plan.md

- **Lore thuộc từng card, nằm trong DB**, sửa trong Studio, nhập từ file `.md` hoặc từ Card V2. Không còn thư mục `world_wiki/` đồng bộ tự động hay YAML frontmatter. Bản `world.md` sẵn có đã theo cấu trúc mục `###`, và một card thường đi kèm đúng một thế giới. Phạm vi "global" để sau: thêm cột `scope` khi cần, không phải đổi bảng.
- **Khối D không nằm trong system** như plan.md §7. Nó nằm ở đầu lượt người chơi cuối, vì đổi system mỗi lượt là đọc lại cả prompt (§6.3). Mặc định nó không được gửi trước (§6.5).
- **`state_events` không có kind `lore`**: dùng bảng `lore_hits` (§1).
- **So khớp không bỏ dấu**, kèm chuẩn hoá vị trí dấu thanh (`hoà`/`hòa`), điều plan.md chưa nói.
- **Nhân vật xung quanh và địa điểm cũng thành mục**, không chỉ "Mục lore". Phần "Bí mật"/"Chức năng" của nhân vật xung quanh bị bỏ khi nhập.

## Thay đổi sau phản biện (2026-11-13)

Kiểm lại bản thiết kế với code thật (`builder.py`, `state/service.py`, `db/connection.py`, `repo.py`) và 4 file `worlds/*`. Script nháp nằm trong `scratchpad/p4/`: `critique_budget.py`, `critique_match.py`, `critique_leak.py`, `critique_fix.py`. Không gọi model, không đụng `data/`.

1. **Cache, §6.5**: mặc định `LORE_PREFILL_OPEN_TURN = False`.
   - Khi gửi trước `lore_head`, lượt thật bắt đầu đọc ở **giữa** lượt người chơi. Prompt lượt sau lại rẽ ở **đầu** lượt đó, vì lịch sử không giữ khối D.
   - Theo phase3.md §10.6, runner chỉ khôi phục ở điểm chụp, nên prefill lượt sau có thể phải đọc lại cả prompt (~45s).
   - Chỉ bật sau khi đo prefill(T+1) và lượt T+1 (§14.4). Khi tắt, prompt rẽ đúng như Phase 3.
2. **Ngân sách, §6.2**: khối lore 700 → 520 token (carried 240, fresh phần còn lại, mỗi mục 450 ký tự).
   - Đo trên 4 card thật: với `yen-hoanh-sinh` có tóm tắt, dự phòng 700 chỉ để lại ~740 token lịch sử ngay sau lần dịch, chưa tới một cặp lượt.
   - D không tính vào `e_tokens`.
   - "Giống hệt Phase 3 từng byte" chỉ đúng khi card không có mục gửi được, hoặc khi lịch sử còn vừa.
3. **Lộ điều chỉ người chơi biết, §4.3**: chỉ bỏ dòng "Bí mật"/"Chức năng" là chưa đủ.
   - `luc-bac-uyen` vẫn lộ "nữ chính của nguyên tác", "Nam phụ của nguyên tác", "nguyên chủ", "đêm mười bảy tháng ba".
   - Thêm hai luật:
     - người hay nơi trùng khoá với mục `{{user}}` thì nhập là "Chỉ bạn" (4 mục);
     - bỏ từng câu chứa từ meta hoặc khoá của mục `{{user}}` (4 câu).
   - Thêm cảnh báo nội dung trong Studio, và test lộ chạy qua mọi khoá.
4. **So khớp, §5.3-5.4**: lượt nhân vật (kể cả lời mở đầu) chỉ được quét bằng khoá dạng tên riêng.
   - Lời mở đầu thật đã gợi "nhịp tim / tai nghe / đám đông", "căn hộ", "nhẫn". Nếu quét bằng từ thường, khối D không bao giờ rỗng và tự nuôi mình.
   - Trọn âm tiết không phải trọn từ ("nhẫn" khớp trong "kiên nhẫn"), nên câu cảnh báo có ví dụ.
   - Khoá có `{{char}}` được `fill` trước; quét từng message riêng; bỏ cache `LoreMatcher`.
5. **known_by, §4.2**: tên nhân vật được lưu thành `{{char}}`, để đổi tên trong Studio không âm thầm biến mục thành "Người khác"; tên lệch thì có cảnh báo lúc nhập.
6. **Nhập lại, §4.4**:
   - mặc định không xoá mục vắng mặt (`delete_missing`, bật trong bước xem trước), vì nhập file thứ hai không được xoá mục của file thứ nhất;
   - mục từ file mà người dùng xoá thành bia mộ (`removed`), nhập lại không thêm lại;
   - `edited` chỉ bật khi có trường đổi thật;
   - slug dự phòng cho tiêu đề toàn chữ Hán;
   - slug của book Card V2 theo `id`/tên, không theo chỉ số;
   - `PUT /cards` cũng chuyển và bỏ `character_book`.
7. **Migration, §1 và §15**: thêm `removed`, `UNIQUE(message_id, entry_id)`, chỉ mục `lore_hits(message_id)` cho CASCADE.
   - `--reload` không theo dõi `.sql`.
   - Code đọc cột mới mà tới trước migration thì mọi route story của người dùng trả 500. Vì vậy chép 0007 → lưu một `.py` vô hại → rồi mới sửa `repo.py`, và `_row_to_story` đọc phòng thủ.
8. **Đã mở khoá, §7 và §11**:
   - mục everyone/character chỉ hiện khi đã thật sự đến được model (bỏ hit `unsent` do hết chỗ);
   - thêm `lore_count`, để mục "Chỉ {tên}" vừa mở cũng làm ngăn tải lại;
   - không in số `turn_index` ("lượt 7") ra giao diện.
9. **B, §12.1**: PATCH chỉ `show_thoughts` không đổi `updated_at`, nên không đẩy story lên đầu hub; không huỷ prefill.
10. **Chữ trên giao diện, §9**: "Nhập file .md" → "Nhập từ file"; gợi ý từ khoá nói rõ tên riêng và từ thường khác nhau thế nào; bước xem trước có "Chỉ bạn biết…", "Xem các câu đã bỏ", "Bỏ qua N mục bạn đã xoá".
11. **§15**: thêm bước sửa `worlds/*/README.md`, vì câu "File này không tự đi vào prompt" sẽ sai sau Phase 4.

## Khác với thiết kế khi làm backend (2026-11-13)

Backend của A và B đã xong (migration 0007 đã nằm trong `migrations/` và đã được app tự áp; từ đây không sửa nữa). Frontend (§9-§12.3), `worlds/*/README.md` (§15 bước 7) và phần đo trên Ollama thật (§14.4) chưa làm. Những chỗ khác với các mục trên:

1. **Cách làm an toàn với app đang chạy (§15)**: code được viết và chạy test trong một bản sao của `backend/` ở thư mục nháp, không sửa thẳng cây code. Sau đó chép vào theo thứ tự: `0007_lore.sql` → `models.py` (chỉ thêm, import được với code cũ; lần tải lại này áp 0007) → `lyris/lore/` và `routes_lore.py` (chưa ai import) → các file còn lại trong một lần. App chỉ tải lại vài lần thay vì vài chục lần. Test migration dùng DB version 6 dựng bằng `migrate(conn, target=6)` rồi chép file, nên không cần vá `MIGRATIONS_DIR`.
2. **`LoreSummary`** có thêm `people_more`, `places_more` (§2, §13 đã sửa): chỉ có danh sách ≤ 8 thì giao diện không in được "+N".
3. **Body import-book** là `LoreBookImportRequest {dry_run}`; thiếu body thì `dry_run = false`.
4. **Câu 422 của mục thế giới** ("Mục thế giới cần có tên.", "Mỗi mục có tối đa 32 từ khoá.", "Cần chọn ai biết điều này.", "File quá lớn (tối đa 500 KB).", ...) do `LoreService` kiểm tra sau khi làm sạch (`LoreInputError`, trả nguyên câu), không dùng `min_length`/`max_length` của pydantic cho tên, khoá, known_by và chữ nhập (pydantic sẽ trả câu chung chung). Quá 500 mục: `LoreLimitError` → 409 "Mỗi nhân vật có tối đa 500 mục thế giới."
5. **Template**: `lore_header(ctx)`, `lore_item(ctx, title, text, private)`, `lore_footer(ctx)` (thêm `ctx`, vì dòng riêng tư cần tên nhân vật và dòng mở theo mode).
6. **Cắt nội dung mục** (`clip_text`): cắt ở cuối câu gần nhất trước 450 ký tự và **không** thêm "…" sau dấu chấm; chỉ thêm "…" khi không có câu nào đủ dài (cắt ở khoảng trắng).
7. **Cảnh báo khoá một chữ** chỉ cho khoá viết thường (không phải dạng tên riêng): `mẹ`, `giỗ`, `nhẫn`, `sapphire`. Tên riêng một chữ (`London`, `Esc`, `GHOST`) không bị nhắc. Studio vẫn có thể tự cảnh báo `Lục` như bảng §5.4.
8. **Đoạn mở bằng chữ đậm** (kiểu `tan-duong`): phần sau tiêu đề bỏ dấu `,` `.` ở đầu, nên nội dung bắt đầu "52 tuổi. Giám đốc kỹ thuật…" chứ không phải ", 52 tuổi…".
9. **Test lọc lộ ở §14.1** chỉ xét mục người/nơi chốn (luật §4.3 chỉ áp cho chúng). Mục lore do tác giả viết được tin: ví dụ "Lời đồn và vụ cược" (mọi người biết) có chữ "hủy hôn", cũng là khoá của mục chỉ người chơi biết "Kết cục của phản diện", và đó là lời đồn ai cũng nghe. Test lộ toàn bộ qua chat (`test_lore_e2e.py`) vẫn kiểm cả khối D lẫn toàn prompt.
10. **Nhập card có `character_book`** không còn cảnh báo "chưa được dùng"; thay bằng một dòng: "Card có N mục thế giới; chúng được thêm vào phần “Thế giới” khi bạn lưu nhân vật."
11. **Export book**: mỗi entry có thêm `comment` (= tên mục) và `case_sensitive: false` nếu chưa có, cho đủ trường Card V2; nhập lại thì hai trường này nằm trong `extra`.
12. **`FakeLLM.prefill_prefix`** chỉ ghi `"open_last": True` vào `calls` khi bật (không ghi `False`), để các test cũ so `calls` không đổi. Worker chỉ truyền `open_last=True` khi cần, nên test double cũ không có tham số này vẫn chạy.
13. **Worker `on_lore_changed(story_ids)`**: prefill đang chạy của story thuộc card bị huỷ rồi hẹn lại; prefill đang chờ thì giữ (lúc chạy sẽ dựng từ sổ mới); story khác không bị đụng. `JobQueue.lore_changed(card_id)` gọi listener qua `getattr` (listener cũ không có hàm này vẫn chạy).
14. **PATCH story chỉ `show_thoughts`**: `Repo.update_story` không đổi `updated_at` khi mọi trường sửa nằm trong `STORY_DISPLAY_FIELDS` (hiện chỉ `show_thoughts`). Story seed (`POST /api/stories` không có `card_id`) cũng nhận `show_thoughts`.
15. **`GET /api/lore/status`** cần account (đếm mục của account); `lore_status(entries)` thay cho `lore_status(directory)`; test cũ về thư mục `world_wiki` đã đổi theo.
16. **Studio xem trước / chat thử** dùng sổ thế giới đã lưu khi `card.id` thuộc account (không thì không có khối D, không lỗi).
17. **Hàm thuần `lore_for_history(entries, tpl=, ctx=, history=)`** trong `lore/select.py` gom phần cắt tail / earlier, để test và `LoreService.prompt_lore` dùng chung.

