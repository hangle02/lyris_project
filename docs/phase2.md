# Phase 2: Character Studio và Story (thiết kế)

Mục tiêu: người dùng tự tạo nhân vật (bằng tay, bằng "AI viết nháp", hoặc import card ngoài), quản lý persona, và mở nhiều story độc lập với bất kỳ cặp nhân vật + persona nào, mỗi story có thiết lập riêng (ngôn ngữ, mode, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, kiểu Thought).

Đọc trước: `docs/plan.md` (mục 6, 7, Phase 2), `docs/phase1.md` (kiến trúc Phase 1). Code Phase 1 đang chạy tốt; không phá hành vi cũ.

## Phạm vi

Có trong Phase 2:
1. CRUD card, persona; tạo/xoá/sửa thiết lập story.
2. Studio: danh sách card, form sửa card (đủ trường), avatar, chọn style profile, trình sửa xưng hô có gợi ý, xem trước prompt và số token, "chat thử" trước khi lưu.
3. Style profile (đến 2026-11-13 có thêm `trung_dan_quoc`, thành năm bộ). Bốn bộ đầu: `trung_hien_dai` (có sẵn, thêm frontmatter), `trung_co_dai`, `viet_hien_dai`, `chung` (trung tính, cho card import hoặc bối cảnh khác; chỉ yêu cầu theo bối cảnh của chính card). Nội dung để người dùng duyệt.
4. "AI viết nháp": một dòng ý tưởng ra card đầy đủ bằng structured output (`gemma4:12b`).
5. Import Character Card V2 (và V1) dạng JSON hoặc PNG; export JSON hoặc PNG; nhân bản; xoá.
6. Tạo story: chọn card, persona, tiêu đề, bối cảnh, lời mở đầu, ngôn ngữ, mode, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, kiểu Thought. Danh sách story; sửa thiết lập; xoá story.
7. Avatar nhân vật hiện trong khung DM và danh sách.
8. Harness: kiểm tra ngôn ngữ và xưng hô trong lời thoại; kịch bản cho card `viet_hien_dai`, `trung_co_dai` và một story tiếng Anh.

Không có (để sau): giao diện song ngữ (chuỗi UI vẫn tiếng Việt, chuyển sang Phase 6), lorebook/`character_book` (Phase 4, chỉ giữ nguyên dữ liệu khi import/export), nhiều nhân vật trong một story.

## Quyết định thiết kế

- **Card không gắn chặt với persona.** Mọi chỗ cần nhắc người chơi trong card (mô tả, lời mở đầu, ví dụ thoại, bối cảnh) dùng `{{user}}`; tên nhân vật có thể viết thẳng hoặc `{{char}}`. Prompt builder đã thay `{{char}}/{{user}}` (`PromptContext.fill`). Khi tạo story, lời mở đầu được thay placeholder theo persona của story trước khi lưu thành message lượt 0. Card seed Lạc Dương giữ nguyên (đã viết thẳng "Lâm Vãn"), không sửa.
- **Card đổi thì mọi story dùng card đó đổi theo** từ lượt sau (như WHIF). `prompt_snapshot` của từng message vẫn giữ đúng prompt đã dùng. Card và persona của một story không đổi được sau khi tạo.
- **Draft và import trả về bản nháp chưa lưu.** Studio mở form với bản nháp; người dùng duyệt (nhất là giới tính, xưng hô, style profile) rồi mới lưu. Ảnh của card PNG import được giữ tạm phía server bằng `avatar_token`, gắn vào card khi lưu.
- **Xoá có ràng buộc.** Xoá card/persona đang có story trả 409 kèm số story; chỉ xoá khi gọi lại với `with_stories=true` (xoá luôn story và message, tức mất dữ liệu train; UI phải cảnh báo rõ).
- **Avatar** được chuẩn hoá bằng Pillow: đọc PNG/JPEG/WebP/GIF (khung đầu), sửa xoay theo EXIF, cắt vừa trong 768x768 (giữ tỉ lệ, không crop), lưu PNG, bỏ metadata. Tối đa 8MB đầu vào. Tên file `card-<id>-<8 hex ngẫu nhiên>.png` (đổi tên mỗi lần upload để trình duyệt không dùng cache cũ).
- **Chat thử** không lưu gì: client giữ cuộc chat trong state và gửi toàn bộ lịch sử mỗi lượt; server dựng prompt bằng đúng `build_prompt` với card chưa lưu.
- **Một lượt sinh tại một thời điểm cho chat thử và viết nháp**: mỗi loại có `asyncio.Lock` riêng; đang bận thì 409. Không chặn chat thường (Ollama có 2 slot).

## Cây file và người phụ trách

```
backend/
  pyproject.toml                    (có sẵn; đã thêm pillow)
  lyris/
    models.py                       (HỢP ĐỒNG, đã cập nhật) CharacterCard thêm scenario, alternate_greetings,
                                    creator_notes, avatar, extensions; StorySettings; StyleProfileInfo
    db/migrations/0003_studio.sql   (HỢP ĐỒNG, có sẵn)
    llm/base.py                     (HỢP ĐỒNG, đã thêm chat_json)
    config.py                       [core] thêm avatars_dir, draft_model
    db/repo.py                      [core] CRUD card/persona, xoá story/card/persona, đếm story, updated_at
    seed/__init__.py                [core] create_default_story giữ nguyên hành vi; dùng chung hàm chèn lời mở đầu
    studio/__init__.py              [core] (rỗng)
    studio/stories.py               [core] story_defaults(), create_story_for(), insert_greeting()
    studio/avatars.py               [core] lưu/chuẩn hoá ảnh, token ảnh tạm, dọn file
    studio/card_v2.py               [cardv2] import/export Character Card V2/V1 (JSON, PNG)
    llm/ollama.py, llm/fake.py      [draft] chat_json
    studio/draft.py                 [draft] AI viết nháp
    prompt/builder.py               [styles] đọc frontmatter style, list_style_profiles()
    prompt/styles/*.md              [styles] 4 profile
    studio/preview.py               [api] dựng prompt xem trước + chat thử (stream, không lưu)
    api/routes.py                   [api] mọi endpoint mới (có thể tách routes_studio.py nếu muốn)
    api/app.py                      [api] đăng ký router, lock, dọn avatar tạm khi khởi động
  tests/
    test_repo.py (thêm), test_studio_stories.py, test_avatars.py   [core]
    test_card_v2.py                 [cardv2]
    test_draft.py, test_ollama_client.py (thêm)   [draft]
    test_styles.py, test_prompt.py (sửa nếu cần)  [styles]
    test_api_studio.py              [api]
harness/
  checks.py, run_eval.py            [harness]
  cards/*.json                      [harness] bộ card + persona + story settings cho kịch bản
  scenarios/06-*.yaml ...           [harness]
frontend/src/
  types.ts, api/client.ts           (HỢP ĐỒNG, đã cập nhật)
  lib/router.ts                     [fe-shell] hash router nhỏ
  App.tsx, components/Header.tsx, components/StoryPicker.tsx      [fe-shell]
  pages/NewStoryPage.tsx, components/StorySettingsPanel.tsx      [fe-shell]
  components/Avatar.tsx             [fe-shell] avatar dùng chung (ảnh hoặc chữ cái đầu)
  components/DmThread.tsx           [fe-shell] dùng Avatar với ảnh thật
  pages/studio/*                    [fe-studio] danh sách card, form card, nháp AI, import, chat thử
  pages/PersonasPage.tsx            [fe-studio]
  lib/cardForm.ts (+ .test.ts)      [fe-studio] logic thuần của form (kiểm tra, chuẩn hoá xưng hô...)
```

Mỗi người phụ trách chỉ tạo/sửa file của mình. Không sửa file HỢP ĐỒNG; thấy sai thì ghi vào báo cáo. Cần thêm hàm ở module người khác thì gọi đúng interface dưới đây.

## Môi trường và luật an toàn

- Backend: `backend/.venv` (Python 3.12). Test: `cd backend && .venv/bin/pytest -q`. Không dùng `python3` hệ thống.
- Frontend: `cd frontend && npm test && npm run typecheck && npm run build`.
- **Người dùng đang chạy app ở cổng 8000 và 5173 với `data/lyris.db`. Không tắt, không khởi động lại, không gọi API ở hai cổng đó, không đụng `data/`.** Muốn chạy thử server thì dùng cổng khác (ví dụ 8020/5190) và `LYRIS_DB_PATH` trong thư mục tạm.
- **Builder không gọi Ollama thật** (dùng FakeLLM / httpx.MockTransport). Chỉ bước tích hợp gọi model thật, tuần tự.
- Không chạy `scripts/ollama-env.sh`, không đụng `data/models`, `.venv-train`, `training/`.

## Interface từng module

### config.py [core]
```python
@dataclass(frozen=True)
class Settings:
    db_path: Path
    ollama_url: str
    chat_model: str
    num_ctx: int
    avatars_dir: Path   # LYRIS_AVATARS_DIR; mặc định <thư mục chứa db>/avatars; với db ":memory:" dùng
                        # <REPO_ROOT>/data/avatars (test luôn truyền Settings riêng với thư mục tạm)
    draft_model: str    # LYRIS_DRAFT_MODEL; mặc định = chat_model
```
Các chỗ đang tạo `Settings(...)` bằng tay (test) phải vẫn chạy: hai trường mới có giá trị mặc định ở dataclass (`avatars_dir` mặc định `REPO_ROOT/"data"/"avatars"`, `draft_model` mặc định `DEFAULT_CHAT_MODEL`).

### db/repo.py [core] (thêm)
```python
def update_card(self, card_id: int, card: CharacterCard) -> CharacterCard     # thay toàn bộ, giữ id; updated_at
def delete_card(self, card_id: int, *, with_stories: bool = False) -> int     # trả số story đã xoá;
    # có story mà with_stories=False -> raise InUse(count). Không xoá file avatar (việc của caller).
def set_card_avatar(self, card_id: int, avatar: str | None) -> CharacterCard
def card_story_count(self, card_id: int) -> int
def card_updated_at(self, card_id: int) -> str | None
def update_persona(self, persona_id: int, p: Persona) -> Persona
def delete_persona(self, persona_id: int, *, with_stories: bool = False) -> int   # InUse như trên
def persona_story_count(self, persona_id: int) -> int
def delete_story(self, story_id: int) -> None        # message/feedback/edit cascade theo FK
def story_updated_at(self, story_id: int) -> str | None   # max(created_at message, story.updated_at)
class InUse(ValueError):
    count: int    # số story đang dùng
```
`list_cards`/`list_personas` sắp theo updated_at mới nhất trước. `list_stories` sắp theo hoạt động gần nhất (message mới nhất hoặc updated_at). Card đọc/ghi đủ cột mới (`alternate_greetings_json`, `extensions_json`...).

### studio/stories.py [core]
```python
def default_settings(card: CharacterCard, persona: Persona, language: Language | None = None) -> StorySettings
    # language: tham số > card.language
    # scenario = card.scenario đã thay {{char}}/{{user}}
    # relationship_type: nam+nữ -> het; nam+nam -> bl; nữ+nữ -> gl; có "other" -> none
    # narration_pronouns: từ StyleProfileInfo.narration[language][gender] của profile card dùng
    #   (thiếu thì: vi male "anh", female "cô", other = tên; en he/she/they). Ngôi thứ ba.
    # mode story, pov third, thought_style inline
def default_title(card: CharacterCard, persona: Persona) -> str     # ví dụ "Lạc Dương & Lâm Vãn"
def create_story_for(repo, card_id, persona_id, *, title=None, greeting_index=0,
                     settings: StorySettings | None = None, model_name: str) -> Story
    # settings None -> default_settings. greeting_index: 0 = greeting, i = alternate_greetings[i-1],
    # -1 = không có lời mở đầu; ngoài phạm vi -> ValueError.
    # Lời mở đầu được fill {{char}}/{{user}} rồi chèn bằng insert_greeting (mode theo settings.mode).
def insert_greeting(repo, story: Story, raw: str) -> Message | None   # split_thought, turn 0; rỗng -> None
```
`seed.create_default_story` giữ nguyên hành vi Phase 1 (dùng `insert_greeting`).

### studio/avatars.py [core]
```python
MAX_AVATAR_BYTES = 8 * 1024 * 1024
class AvatarError(ValueError): ...    # thông điệp tiếng Việt (định dạng không hỗ trợ, quá lớn, ảnh hỏng)
def normalize_image(data: bytes) -> bytes             # -> PNG tối đa 768x768, bỏ metadata
def save_card_avatar(avatars_dir: Path, card_id: int, data: bytes) -> str     # trả tên file mới
def remove_avatar(avatars_dir: Path, name: str | None) -> None                # không lỗi nếu không có
def avatar_path(avatars_dir: Path, name: str) -> Path                         # chặn path traversal
def hold_temp(avatars_dir: Path, data: bytes) -> str          # chuẩn hoá + lưu tmp/<token>.png, trả token
def claim_temp(avatars_dir: Path, token: str, card_id: int) -> str | None     # chuyển thành avatar card; token lạ -> None
def cleanup_temp(avatars_dir: Path, max_age_s: float = 86400) -> int
```

### studio/card_v2.py [cardv2] (hàm thuần, không đụng DB)
```python
@dataclass
class ImportResult:
    card: CharacterCard          # id=None, avatar=None
    warnings: list[str]          # tiếng Việt, ví dụ "Card không ghi giới tính; đoán là nữ từ mô tả, hãy kiểm tra."
    image: bytes | None          # ảnh PNG gốc nếu import từ PNG
class CardImportError(ValueError): ...

def import_card(data: bytes, content_type: str | None, *, styles: list[str]) -> ImportResult
def export_card_json(card: CharacterCard) -> dict          # {"spec": "chara_card_v2", "spec_version": "2.0", "data": {...}}
def export_card_png(card: CharacterCard, image_png: bytes | None) -> bytes   # nhúng tEXt "chara" (base64 JSON V2);
    # không có ảnh -> tạo ảnh 512x512 nền tối với chữ cái đầu (Pillow)
```
Nhận dạng: PNG (chữ ký `\x89PNG`) → đọc chunk `tEXt`/`iTXt` keyword `chara` (base64 JSON; V2 hoặc V1) hoặc `ccv3` (V3, đọc như V2 phần `data`); JSON → V2 (`spec == "chara_card_v2"`), V3 (`spec == "chara_card_v3"`, lấy `data`), hoặc V1 (các trường ở gốc: `name, description, personality, scenario, first_mes, mes_example`).

Ánh xạ V2 → Lyris:
| V2 | Lyris |
|---|---|
| name | name |
| description | description |
| personality | personality |
| scenario | scenario |
| first_mes | greeting |
| alternate_greetings | alternate_greetings |
| mes_example | example_dialogues (chuyển `<START>` thành dòng trống; giữ `{{char}}:`/`{{user}}:`) |
| creator_notes | creator_notes |
| tags | tags |
| extensions.lyris | các trường riêng của Lyris: gender, language, appearance, background, goals, secrets, speech_style, style_profile, address_terms (bản export của Lyris import lại không mất gì) |
| system_prompt, post_history_instructions, character_book, creator, character_version, extensions khác | giữ trong `card.extensions` (khoá `"v2"`) để export lại; không đưa vào prompt; có thì thêm cảnh báo "phần X chưa được dùng" |

Khi card không có `extensions.lyris`:
- gender: đếm đại từ trong description/personality/first_mes (he/him/his/anh ấy/hắn vs she/her/hers/cô ấy/nàng); thắng rõ thì đoán, không thì "other"; luôn cảnh báo.
- language: có chữ tiếng Việt có dấu (ă â đ ê ô ơ ư và các dấu thanh) ở mức đáng kể → "vi", ngược lại "en".
- style_profile: "chung" (nếu có trong `styles`), cảnh báo nên chọn lại.
- address_terms: en → self "I", player "you"; vi → để trống và cảnh báo phải điền.
- Chuỗi rỗng/None chấp nhận; trường sai kiểu → bỏ qua kèm cảnh báo, không crash. File > 8MB hoặc không đọc được → CardImportError (tiếng Việt).

Export: V2 đầy đủ trường bắt buộc của spec (`name, description, personality, scenario, first_mes, mes_example, creator_notes, system_prompt, post_history_instructions, alternate_greetings, character_book, tags, creator, character_version, extensions`), phần riêng của Lyris ở `data.extensions.lyris`, phần giữ lại từ lúc import trả về đúng chỗ cũ. `appearance/background/goals/secrets/speech_style` cũng được nối vào cuối `description` dưới các nhãn ngắn (để app khác vẫn dùng được), nhưng khi import lại bản có `extensions.lyris` thì lấy từ `extensions.lyris`, không nhân đôi.

### llm/ollama.py, llm/fake.py [draft]
`chat_json` theo `LLMClient` (base.py): POST `/api/chat` với `stream: false`, `think: false` (bỏ nếu model báo không hỗ trợ, như chat_stream), `format: schema`, `keep_alive: "30m"`, `options`. done_reason "length" → LLMError("Model viết quá dài, bị cắt giữa chừng. Hãy thử lại."). JSON hỏng → LLMError. FakeLLM: tham số khởi tạo `json_replies: list[dict] | None`, lấy lần lượt; ghi `calls` như chat_stream (thêm khoá `"schema"`).

### studio/draft.py [draft]
```python
DRAFT_SCHEMA: dict             # JSON schema các trường dưới
async def draft_card(llm: LLMClient, model: str, *, idea: str, language: Language,
                     gender: Gender | None, style_profile: str | None,
                     styles: list[StyleProfileInfo]) -> tuple[CharacterCard, list[str]]
class DraftError(ValueError): ...      # ý tưởng rỗng/quá dài (>2000 ký tự)
```
- Schema: `name, gender (enum), language? (không, lấy theo tham số), description, personality, appearance, background, goals, secrets, speech_style, style_profile (enum = tên các profile), self_term, player_term, nicknames (array), others, scenario, greeting, example_dialogues, tags (array)`.
- Prompt (tiếng Việt khi language=vi, tiếng Anh khi en) nêu rõ: mỗi trường 1-3 câu (greeting 120-180 từ); `{{user}}` để chỉ người chơi; greeting ngôi thứ ba, đúng văn phong profile, có 2 dòng `[Thought: ...]` rải giữa (mỗi dòng 2-3 câu), xưng hô của nhân vật chỉ trong lời thoại và Thought, dẫn truyện dùng đại từ; không viết lời hay hành động cho `{{user}}`, kết thúc ở chỗ chờ `{{user}}` đáp; `self_term`/`player_term` là một từ/cụm viết thường, không liệt kê nhiều lựa chọn; tên theo văn hoá của bối cảnh (Hán Việt cho bối cảnh Trung Quốc). Đưa danh sách profile (name, title, description) để model chọn. Có `gender`/`style_profile` từ người dùng thì ép giá trị đó (ghi trong prompt và ghi đè sau khi nhận).
- options: `temperature 0.8, num_predict 2048, num_ctx 8192`.
- Hậu xử lý: trim mọi chuỗi; xưng hô: cắt ở `/`, `,`, ` hoặc `, ` or `, `(`, lấy phần đầu, viết thường chữ đầu (trừ "I" tiếng Anh); nicknames bỏ trùng, tối đa 4; tags tối đa 6, viết thường; style_profile lạ → "chung" + cảnh báo; nếu greeting không có Thought nào → cảnh báo; nếu greeting chứa từ xưng hô (self/player) ngoài ngoặc kép và ngoài Thought → cảnh báo "lời mở đầu dùng xưng hô trong dẫn truyện".
- Trả `CharacterCard(id=None, language=language, ...)` + warnings.

### prompt/builder.py, prompt/styles/ [styles]
Mỗi file `styles/<name>.md` bắt đầu bằng YAML frontmatter:
```yaml
---
title: Ngôn tình Trung Quốc hiện đại
description: Vườn trường, đô thị, tổng tài; tên Hán Việt; tớ/cậu, anh/em.
narration:
  vi: {male: anh, female: cô, other: ""}
  en: {male: he, female: she, other: they}
address_examples:
  - {self: tớ, player: cậu, note: bạn thân, thanh mai trúc mã}
  - {self: anh, player: em, note: người yêu, nam lớn tuổi hơn}
---
```
- `load_style()` bỏ frontmatter (không bao giờ vào prompt); phần còn lại xử lý như cũ. Nội dung prompt của `trung_hien_dai` phải giữ nguyên từng byte (test prompt cũ phải qua).
- `list_style_profiles() -> list[StyleProfileInfo]` (sắp theo tên), `get_style_profile(name) -> StyleProfileInfo` (ValueError nếu không có). File thiếu frontmatter vẫn đọc được (title = name).
- Nội dung các profile mới, viết theo mẫu của `trung_hien_dai.md` (mục `# vi` và `# en`, ngắn, dứt khoát, có câu mẫu):
  - `trung_co_dai`: cổ trang, tiên hiệp, cung đấu. Xưng hô ta/ngươi, ta/nàng, huynh/muội, sư tôn/đồ nhi, công tử/cô nương, bổn vương, tại hạ, thần thiếp...; dẫn truyện thường dùng "hắn"/"y" cho nam, "nàng" cho nữ; từ vựng Hán Việt; tránh đồ vật hiện đại. narration vi: male hắn, female nàng.
  - `viet_hien_dai`: Việt Nam hiện đại. anh/em, tớ/cậu, mình/bạn, tao/mày khi thân hoặc gay gắt; tên người Việt; đời sống Việt (xe máy, cà phê vỉa hè, phở, chợ, Zalo...). Tránh văn dịch Trung ("khóe môi khẽ cong", "đáy mắt"). narration vi: male anh, female cô.
  - `chung`: trung tính. Văn phong, xưng hô, bối cảnh theo đúng mô tả của card và bối cảnh story; không áp đặt quốc gia. Tên giữ nguyên như card viết. narration vi: male anh, female cô; en he/she.
  - `trung_hien_dai`: thêm frontmatter, giữ nguyên phần thân.

### studio/preview.py [api]
```python
def build_preview(card: CharacterCard, persona: Persona, settings: StorySettings, *,
                  budget: PromptBudget, history: list[TestTurn] | None = None) -> BuiltPrompt
    # Story giả (id 0) từ settings; history None -> một lượt user mẫu
    # ("(Lượt mẫu của người chơi)" / "(Sample player turn)") để thấy cả khối F.
    # history có -> chuyển thành Message (user: tách ((...)) như chat thật; assistant: split_thought).
async def test_chat_stream(llm, model, built: BuiltPrompt) -> AsyncIterator[ChatEvent]
    # start {} -> delta {kind, text} (qua ThoughtStreamParser) -> done {raw, visible, thought, stats}
    # LLMError -> error {detail}. Client ngắt -> huỷ request. Không ghi DB.
```

### api [api]
Mọi lỗi trả `{"detail": "..."}` tiếng Việt. `InUse` → 409 "Có N story đang dùng ... Xoá luôn các story đó?". `AvatarError`, `CardImportError`, `DraftError` → 422. Draft/test-chat đang bận → 409.

| Method | Path | Body | Trả về |
|---|---|---|---|
| GET | /api/styles | | `StyleProfileInfo[]` |
| GET | /api/cards | | `CardSummary[]` (description cắt 160 ký tự) |
| POST | /api/cards | `{card, avatar_token?}` | `CardOut` (201 không bắt buộc; 200 cũng được) |
| GET | /api/cards/{id} | | `CardOut` |
| PUT | /api/cards/{id} | `CharacterCard` | `CardOut` (bỏ qua `id` và `avatar` trong body: avatar chỉ đổi qua endpoint avatar) |
| DELETE | /api/cards/{id}?with_stories= | | `{deleted_stories}`; xoá file avatar |
| POST | /api/cards/{id}/duplicate | | `CardOut` (tên + " (bản sao)", copy avatar thành file mới) |
| PUT | /api/cards/{id}/avatar | raw ảnh, Content-Type ảnh | `CardOut` |
| DELETE | /api/cards/{id}/avatar | | `CardOut` |
| GET | /api/cards/{id}/avatar | | file PNG, `Cache-Control: max-age=31536000, immutable` (tên file đổi khi đổi ảnh) |
| GET | /api/cards/{id}/export?format=json\|png | | tải file, `Content-Disposition: attachment; filename*=UTF-8''<tên>.json/.png` |
| POST | /api/cards/import | raw file (JSON/PNG) | `CardDraftResult` (chưa lưu; ảnh PNG giữ tạm → `avatar_token`) |
| POST | /api/cards/draft | `{idea, language, gender?, style_profile?}` | `CardDraftResult` (`avatar_token` null) |
| POST | /api/cards/preview-prompt | `{card, persona_id, settings}` | `{messages, token_estimate, num_ctx}` |
| POST | /api/cards/test-chat | `{card, persona_id, settings, messages}` | SSE: start, delta, done, error |
| GET | /api/personas | | `PersonaOut[]` (thêm `story_count`) |
| POST | /api/personas | `Persona` | `PersonaOut` |
| PUT | /api/personas/{id} | `Persona` | `PersonaOut` |
| DELETE | /api/personas/{id}?with_stories= | | `{deleted_stories}` |
| GET | /api/stories/defaults?card_id=&persona_id=&language= | | `{title, settings}` |
| POST | /api/stories | `{}` / `{title}` (Phase 1: story seed) hoặc `{card_id, persona_id, title?, greeting_index?, settings?}` | `StoryOut` |
| PATCH | /api/stories/{id} | thêm `language, relationship_type, pov, narration_pronouns` | `Story` |
| DELETE | /api/stories/{id} | | `{deleted: 1}` (409 nếu story đang sinh câu trả lời) |

`CardOut` = CharacterCard + `avatar_url` (`/api/cards/{id}/avatar?v=<tên file>` hoặc null) + `story_count` + `updated_at`. `StoryOut` thêm `card_avatar_url`, `updated_at`. `settings` trong POST /api/stories có thể thiếu trường: trộn với `default_settings`. Kiểm tra body card: name không rỗng (≤ 80 ký tự), style_profile phải tồn tại, mỗi trường văn bản ≤ 20,000 ký tự, tags ≤ 20.

### harness [harness]
- `checks.py` thêm:
  - `language: vi|en`. vi: báo lỗi nếu ≥ 3 từ tiếng Anh thông dụng (the, and, you, is, are, what, I'm, don't...) đứng ngoài tên riêng, hoặc tỉ lệ âm tiết có dấu tiếng Việt quá thấp (< 15% số từ, sau khi bỏ tên). en: báo lỗi nếu còn chữ có dấu tiếng Việt sau khi bỏ các tên riêng truyền vào (`names`).
  - `dialogue_forbidden: [..]`: từ không được xuất hiện trong lời thoại (trong ngoặc kép) và Thought, ví dụ card cổ trang cấm "anh", "em", "tớ", "cậu".
  - `dialogue_required_any: [..]`: nếu có lời thoại thì phải có ít nhất một từ trong danh sách (xưng hô của card).
  - So khớp theo từ (biên `\b`, không phân biệt hoa thường, Unicode).
- `run_eval.py`: kịch bản có khoá `card: <file trong harness/cards/>` (JSON gồm `card`, `persona`, `story`: settings); không có thì dùng seed như cũ. `checks` mới thêm vào `_CHECK_KEYS`. `names` cho kiểm tra ngôn ngữ lấy từ card + persona.
- `harness/cards/`: `viet_hien_dai.json` (ví dụ: Trần Minh Khang, 27 tuổi, kiến trúc sư ở Sài Gòn, anh/em, persona nữ "Ngọc Anh"), `trung_co_dai.json` (ví dụ: Tạ Vân Lan, sư tỷ lạnh lùng ở Thanh Vân Tông, ta/đệ hoặc ta/muội tùy persona; persona nam "Lục Trần"), `lac_duong_en.json` (Lạc Dương, story tiếng Anh). Mỗi card có lời mở đầu đúng kiểu Thought inline.
- Kịch bản mới: `06-viet-hien-dai.yaml`, `07-co-trang.yaml`, `08-tieng-anh.yaml` với checks phù hợp (language, dialogue_forbidden/required, narration_forbidden, min/max thoughts, no_adjacent, forbidden_phrases "bầu không khí").
- Test bằng FakeLLM như Phase 1; không gọi model thật.

### Frontend
Hash router (`#/chat/<storyId>`, `#/studio`, `#/studio/new`, `#/studio/<cardId>`, `#/personas`, `#/new-story?card=<id>`). Mặc định `#/chat/<story gần nhất>`. Giao diện tối, mobile-first như Phase 1 (bề ngang 375px không cuộn ngang), chữ ≥ 16px trong ô nhập (iOS không zoom).

[fe-shell]
- `lib/router.ts`: `useRoute()` trả route đã parse; `navigate(path)`. Có test thuần cho hàm parse.
- Header chat: thêm nút menu (☰) mở ngăn điều hướng: Story (danh sách), Studio nhân vật, Persona; giữ Story/DM và 💭. Thêm nút ⚙ mở `StorySettingsPanel` (tiêu đề, bối cảnh, ngôn ngữ, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, kiểu Thought; nút xoá story có xác nhận hai bước). Đổi ngôn ngữ/ngôi kể giữa chừng được phép, có dòng nhắc "áp dụng từ lượt sau".
- `StoryPicker`: mỗi story có avatar, tên nhân vật · persona, thời gian hoạt động; "Tạo story mới" chuyển sang `#/new-story`.
- `NewStoryPage`: chọn card (lưới có avatar; có `?card=` thì chọn sẵn), chọn persona (hoặc tạo nhanh), gọi `storyDefaults` để điền sẵn rồi cho sửa: tiêu đề, bối cảnh, lời mở đầu (greeting / alternate, xem trước), ngôn ngữ (cảnh báo nếu khác ngôn ngữ card), mode, kiểu quan hệ, ngôi kể, đại từ dẫn truyện (gợi ý từ profile), kiểu Thought. Tạo xong → `#/chat/<id>`.
- `Avatar.tsx`: ảnh tròn nếu có url, không thì chữ cái đầu; dùng ở DmThread (thay Avatar nội bộ), StoryPicker, Header.
- Khi chưa có card nào ngoài seed: vẫn chạy như Phase 1.

[fe-studio]
- `pages/studio/CardListPage`: lưới card (avatar, tên, tag, số story); nút "Tạo nhân vật", "AI viết nháp", "Import card"; mỗi card: "Chat" (→ `#/new-story?card=`), "Sửa".
- `pages/studio/CardEditorPage`: form nhóm theo mục (Cơ bản: tên, giới tính, ngôn ngữ, style profile có mô tả, tag; Nhân vật: mô tả, tính cách, ngoại hình, hoàn cảnh, mục tiêu, bí mật, cách nói; Xưng hô: tự xưng, gọi người chơi, tên thân mật dạng chip, với người khác, nút gợi ý từ profile; Mở đầu: bối cảnh mặc định, lời mở đầu, các lời mở đầu khác, ví dụ thoại; Ghi chú người tạo; Avatar: upload/xoá, xem trước). Gợi ý `{{user}}` cạnh các ô có thể nhắc người chơi. Thanh hành động: Lưu, Nhân bản, Xuất JSON/PNG, Xoá (409 → hỏi xoá luôn N story). Cảnh báo khi rời trang chưa lưu. Hiện `warnings` của bản nháp/import ở đầu form.
- Bảng phụ (tab, trên mobile nằm dưới form): **Xem trước prompt** (chọn persona + vài thiết lập; hiện từng khối, số token A/B/C/E/F/total, cảnh báo khi B > 1,200 token) và **Chat thử** (chọn persona, thiết lập; bắt đầu từ lời mở đầu; gửi/stream/dừng/làm lại; hiển thị Thought tại chỗ như chat thật; nút "Xoá cuộc thử"). Chat thử và xem trước dùng card đang sửa (kể cả chưa lưu).
- `AI viết nháp`: hộp thoại nhập ý tưởng (ví dụ gợi ý sẵn), ngôn ngữ, giới tính (tuỳ chọn), style profile (tuỳ chọn hoặc "để AI chọn"); đang chạy hiện đồng hồ và lời nhắc "thường mất 1-2 phút"; có nút huỷ (AbortController). Xong → mở editor với bản nháp chưa lưu.
- Import: chọn file `.json`/`.png` → editor với bản nháp + cảnh báo; lưu thì gửi `avatar_token`.
- `PersonasPage`: danh sách persona (tên, giới tính, mô tả, số story), thêm/sửa/xoá (409 → hỏi xoá luôn story).
- `lib/cardForm.ts` + test: `emptyCard()`, `validateCard(card) -> string[]`, `normalizeTerm()` (giống hậu xử lý draft), `suggestNarration(profile, language, gender)`, `isDirty(a, b)`.

## Kiểm tra cuối Phase 2

1. `cd backend && .venv/bin/pytest -q` qua hết; `cd frontend && npm test && npm run typecheck && npm run build` qua hết.
2. Trên DB tạm, cổng riêng, model thật: tạo card bằng tay; tạo card bằng AI viết nháp; import một card V2 PNG/JSON ngoài (tự tạo file mẫu); export rồi import lại không mất trường; mở story mới với từng card; chat 1 lượt mỗi story.
3. `harness/run_eval.py` chạy đủ 8 kịch bản với `gemma4:12b`; báo cáo lỗi máy.
4. Người dùng: duyệt nội dung 4 style profile; tự tạo 3-5 nhân vật của mình.
