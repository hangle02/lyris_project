# Lyris: triển khai DESIGN.md (Phase 2b)

Nguồn thiết kế: `DESIGN.md` ở gốc repo (do người dùng viết). Tài liệu này ánh xạ thiết kế đó vào code hiện có (Phase 1 + Phase 2). Ở chỗ có xung đột, **DESIGN.md thắng** trừ khi ghi khác bên dưới.

Quyết định của người dùng (2026-11-12):
- App đổi tên **Nora → Lyris** trong code, biến môi trường, file DB, giao diện, tài liệu. **Thư mục repo giữ nguyên `/Users/hanghang/nora`.**
- Thành phần cần dữ liệu của phase sau (ma trận 6 cảm xúc, chỉ dẫn diễn xuất, gợi ý trả lời nhanh, chip cảm xúc/địa điểm, banner "Khoảnh khắc", wiki/lorebook) **dựng khung giao diện ngay**, nối với một endpoint thật đang trả dữ liệu rỗng; phase sau chỉ cần điền dữ liệu.

## 1. Đổi tên (đã làm trước đợt này)

- Package Python `backend/lyris` (trước là `backend/nora`), uvicorn `lyris.api.app:app`.
- Biến môi trường `LYRIS_DB_PATH`, `LYRIS_CHAT_MODEL`, `LYRIS_NUM_CTX`, `LYRIS_AVATARS_DIR`, `LYRIS_DRAFT_MODEL`, `LYRIS_API_URL` (Vite). Tên cũ `NORA_*` vẫn đọc được khi tên mới không đặt.
- DB mặc định `data/lyris.db`; khi khởi động, nếu `lyris.db` chưa có mà `nora.db` có thì đổi tên (kèm `-wal`, `-shm`).
- localStorage `lyris.*` (đọc bản `nora.*` cũ một lần rồi chuyển sang).
- Card export: dữ liệu riêng ở `data.extensions.lyris`; import vẫn đọc `extensions.nora`.

## 2. Theme và token

Giữ **tên token Tailwind hiện có** (mọi component cũ tự đổi màu), đổi giá trị theo theme qua CSS variables, thêm token mới. `html[data-theme="dark"|"light"]`; mặc định theo `prefers-color-scheme`; nút đổi theme lưu `localStorage["lyris.theme"]`; cập nhật `<meta name="theme-color">`. Chuyển theme: `transition-colors duration-500` trên nền và các bề mặt (không transition mọi thuộc tính).

| Token | Dark "Velvet Nocturne" | Light "Rosewater Parchment" | Dùng cho |
|---|---|---|---|
| `bg` | #130D14 | #FAF5EE | nền app |
| `surface` | #1F1521 | #FFFDF9 | card, thẻ thoại, modal |
| `surface-2` | #2A1D2C | #F4ECE4 | ô nhập, chip, toggle chưa chọn |
| `surface-3` | #352536 | #EDE2D8 | hover, đang chọn |
| `glass` | rgba(31,21,33,0.78) | rgba(255,252,249,0.85) | header/pill kính, kèm `backdrop-blur-[16px]` |
| `line` | #382635 | #E8D7CE | viền mảnh |
| `fg` | #FAF2EB | #2D1E24 | chữ chính, lời thoại |
| `prose` | #E9DDE0 | #3A2A31 | thân văn bản dài không nghiêng |
| `muted` | #C2AAB8 | #7D636D | dẫn truyện (nghiêng), phụ đề, giờ |
| `faint` | #8F7789 | #A8929A | gợi ý, placeholder |
| `dialogue` | #FAF2EB | #2D1E24 | chữ trong thẻ thoại |
| `accent` | #E5989B | #C86D7E | nút chính, viền Thought, trạng thái active |
| `accent-strong` | #F0B3B5 | #B05768 | hover của accent |
| `accent-2` | #F3C68F | #C58B52 | điểm nhấn vàng/hổ phách: vai trò nhân vật, chấm sao, trạng thái máy |
| `on-accent` | #1A1018 | #FFFDF9 | chữ trên nền accent / gradient |
| `thought` | #EBC9CF | #8E4A5A | chữ trong thẻ Thought |
| `user` (gradient) | #3D2638 → #291928, viền accent/35 | #C86D7E → #B05768 | bong bóng người chơi (`bg-user-gradient` utility) |
| `user-fg` | #FAF2EB | #FFFFFF | chữ bong bóng người chơi |
| `danger` / `ok` / `warn` | #F08A8A / #7FD1A2 / #F3C68F | #B8434F / #3C8C5E / #B07A2E | |
| `emo-affection` ... | #D86C86, #C58B52, #A864A8, #D15B5B, #6E7BB8, #9E8881 | như dark | 6 chỉ số (Affection, Trust, Attraction, Obsession, Fear, Aversion) |

Gradient thương hiệu: `--grad-orb: linear-gradient(135deg,#C86D7E,#D98A6C,#F3C68F)` (nút giữa, nút gửi); `--grad-wordmark` dark `#F3C68F → #E5989B → #FAF2EB`, light `#9E475B → #C86D7E → #B87D4B`.

Không dùng #000/#FFF thuần cho nền và chữ đọc dài (trừ chữ trên bong bóng người chơi ở light theo DESIGN.md).

## 3. Font (tự host, chạy offline)

Đã cài sẵn (lead): `@fontsource/cormorant-garamond`, `@fontsource/plus-jakarta-sans`, `@fontsource/be-vietnam-pro` (đều có subset `vietnamese`). Import đúng các weight cần trong `main.tsx` (ví dụ `@fontsource/be-vietnam-pro/400.css`, `.../400-italic.css`): Cormorant 600-italic, 700-italic; Plus Jakarta 400, 500, 600, 700 (800 chỉ khi thật dùng); Be Vietnam Pro 300, 400, 400-italic, 500.
- `font-brand` = Cormorant Garamond: chỉ wordmark Lyris và tiêu đề đặc biệt.
- `font-sans` (UI, DM) = Plus Jakarta Sans, fallback -apple-system.
- `font-story` = Be Vietnam Pro, line-height 1.65: văn bản Story Mode, thẻ thoại, Thought.
Kiểm tra dấu tiếng Việt chồng (ư, ơ, ằ, ễ, ỡ...) hiển thị đúng ở cả ba font.

## 4. Logo

- `components/brand/LogoMark.tsx`: SVG hai trang sách cong thành hình trái tim, ngôi sao 4 cánh phát sáng ở giữa; nét 1.8px bo tròn, gradient ấm hai điểm; sao tô vàng hổ phách.
- `components/brand/Wordmark.tsx`: "Lyris" bằng Cormorant Garamond nghiêng đậm; chữ L gradient (`--grad-wordmark`); chữ "ı" không chấm (`ı`) với ngôi sao SVG 4 cánh nhấp nháy nhẹ thay dấu chấm; nét lụa cong bên dưới (SVG, `stroke-linecap="round"`). Có `prefers-reduced-motion`.
- `public/favicon.svg` = LogoMark. `<title>Lyris</title>`, meta `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style=black-translucent`, `apple-mobile-web-app-title=Lyris`.

## 5. Điều hướng (DESIGN.md mục 5)

Routes (hash):
| Route | Màn hình | Thanh tab dưới |
|---|---|---|
| `#/` | Tương Tác, lớp 1: danh sách story | có |
| `#/explore` | Khám Phá | có |
| `#/studio`, `#/studio/new`, `#/studio/<id>` | Studio (danh sách / editor) | có ở danh sách, ẩn ở editor |
| `#/personas` | quản lý persona (mở từ modal Persona & Máy chủ) | ẩn |
| `#/character/<id>`, `#/character/template/<slug>` (`?start=1` mở sẵn sheet) | hồ sơ nhân vật, chỉ xem (§16) | ẩn |
| `#/new-story?card=<id>` | link cũ: chuyển sang `#/character/<id>?start=1`; không có card thì sang Khám phá (§16) | ẩn |
| `#/chat/<id>` | Tương Tác, lớp 2: không gian nhập vai toàn màn hình | ẩn |

`Route` thêm `{name:"hub"}`, `{name:"explore"}`; `#/chat` không id → hub. Mở app: hub (không còn tự nhảy vào story gần nhất; story gần nhất nằm đầu danh sách).

**Header hub** (trang hub/explore/studio list): trái là Wordmark + pill trạng thái máy (`● M2 Local`, chấm nhịp thở xanh khi Ollama sẵn sàng; vàng + chữ "Đang chạy pin" khi máy chạy pin hoặc bật Low Power Mode; đỏ khi không kết nối); phải là nút đổi theme (Sun/Moon) và avatar persona mặc định (mở modal trang 4). Kính mờ, tôn trọng `safe-area-inset-top`.

**Thanh tab nổi** (`components/shell/TabBar.tsx`): cách đáy 16px + safe area, rộng 90% (tối đa 420px), `rounded-full`, kính `blur(20px)`. Trái "Khám Phá" (la bàn), giữa "Tương Tác" là quả cầu gradient `--grad-orb` nhô lên 12px, có bóng phát sáng, icon trái tim đặc; phải "Studio" (lấp lánh). Tab active rõ ràng; nhãn chữ nhỏ dưới icon. Nội dung trang chừa chỗ đáy để không bị thanh che.

Icon: SVG nội bộ trong `components/icons.tsx` (vẽ theo phong cách Lucide: Compass, Heart, Sparkles, Sun, Moon, ChevronLeft, Send, RefreshCw, Star, Search, Settings...). Không thêm thư viện icon.

## 6. Từng trang

### 6.1 Tương Tác, lớp 1 (`pages/hub/HubPage.tsx`)
- Banner chào theo giờ (05-11 "☀️ Nắng lên rồi, hôm nay trò chuyện cùng ai?", 11-14 "🌤️ Trưa rồi, nghỉ tay trò chuyện một chút nhé?", 14-18 "🍂 Chiều dịu dàng, ai đang chờ bạn ghé thăm?", 18-22 "🌙 Tối rồi, kể nhau nghe chuyện hôm nay?", 22-05 "🕯️ Đêm muộn rồi, ai đang thức đợi bạn?").
- Ô tìm kiếm bo 16px: lọc theo tên nhân vật, tiêu đề story, (sau này) địa điểm.
- Thẻ story: ảnh 48x48 `rounded-2xl` (avatar card; không có thì gradient + chữ cái đầu) với huy hiệu góc `STORY`/`DM`; tên nhân vật; giờ hoạt động gần nhất (hôm nay "23:15", hôm qua "Hôm qua", cũ hơn "12/11"); vai trò nhân vật (`card.role`) màu `accent-2`; một dòng xem trước nghiêng của tin gần nhất; hàng chip dưới (cảm xúc nổi trội, địa điểm) chỉ hiện khi `extras` có dữ liệu.
- Nút tạo story mới (→ Khám Phá hoặc `#/new-story`), trạng thái rỗng thân thiện.
- Vuốt/nhấn giữ không bắt buộc; xoá story nằm trong bảng thiết lập story.

### 6.2 Tương Tác, lớp 2: không gian nhập vai (`#/chat/<id>`)
1. **Header kính dính trên**: nút quay lại (ChevronLeft → `#/`), avatar 32px, tên nhân vật, dòng phụ (tiêu đề story; sau này địa điểm/giờ trong truyện), pill chuyển `STORY ⇄ DM`, nút 💭 (kiểu Thought + công tắc "Luôn hiện suy nghĩ"), nút trái tim mở ngăn cảm xúc, nút ⚙ thiết lập story.
2. **Banner "Khoảnh khắc"** dưới header: hiện khi `extras.moment` có dữ liệu (ví dụ "Khoảnh khắc: Đón nhận sự quan tâm dịu dàng từ Hạ Vy • +Thương mến").
3. **Story Mode, mỗi lượt AI ba loại khối** (`lib/storyBlocks.ts`, hàm thuần có test):
   - *Dẫn truyện/hành động*: đoạn văn nghiêng màu `muted`, không khung.
   - *Lời thoại*: thẻ `bg-surface rounded-2xl`, chữ `dialogue` đậm vừa, KHÔNG hiện cặp ngoặc ngoài cùng (người dùng chọn 2026-11-13, khác DESIGN.md: khung đã đánh dấu lời nói; `speechText` trong lib/storyBlocks.ts).
   - *Thẻ Thought "Tiếng Lòng Giấu Kín"*: viền trái 3px `accent`, nền gradient nhẹ; **mặc định làm mờ** (`blur(3px)`, `select-none`) với lời mời "Chạm để lắng nghe"; chạm thì hiện rõ (`transition-all duration-300`), chạm lần nữa mờ lại. Công tắc "Luôn hiện suy nghĩ" (localStorage `lyris.revealThoughts`) bỏ làm mờ.
   - Cách tách đoạn: mỗi dòng/đoạn văn bản được chia thành các đoạn trong và ngoài ngoặc kép (“ ” " « » 「 」). Đoạn trong ngoặc từ 3 từ trở lên thành thẻ thoại; đoạn ngắn hơn (tên riêng, từ trích dẫn) ở lại trong dòng dẫn truyện, hiển thị thẳng không nghiêng. Phần dẫn truyện trước/sau một thẻ thoại trong cùng đoạn thành khối dẫn truyện riêng. `*hành động*` trong lượt AI hiển thị như dẫn truyện. Quy ước (người dùng chọn 2026-11-13): trích dẫn trong dấu sao `*"…"*` là trích dẫn hoặc lời của người khác (NPC), luôn ở lại trong dòng dẫn truyện, chữ đứng, giữ ngoặc; ở lượt của người chơi, mọi `"…"` còn lại là lời thoại của người chơi, thành ô thoại dù ngắn hay dài (`paragraphBlocks(para, 1)`). Bàn phím điện thoại mở ngoặc bằng `”` cũng được nhận (`text.ts parseInline`). Gợi ý ô chat Story: `Nhập lời thoại vào "…"` (ngắn để vừa màn hình điện thoại). Thought giữ đúng vị trí như hiện nay.
   - Lượt người chơi: bong bóng gradient `user`, phải; chỉ đạo `((...))` là chip nhỏ.
   - Variant, sửa, xoá, thích/chê, dừng: giữ nguyên hành vi Phase 1.
4. **DM Mode**: bong bóng `max-w-[80%]`, avatar thật cạnh tin nhân vật, chân tin của người chơi "00:40 • Đã gửi" (tin cuối cùng của người chơi khi đã có trả lời: "00:40 • Đã xem"). Giữ gom nhóm và mốc giờ.
5. **Trạng thái đang sinh**: ngôi sao nhịp thở (hoặc RefreshCw xoay chậm) + chữ nghiêng "{Tên} đang ngập ngừng tìm lời hồi đáp..." kèm đồng hồ đã chờ (giữ thông tin hiện có khi chờ lâu).
6. **Composer**: hàng chip gợi ý trả lời nhanh cuộn ngang phía trên ô nhập (hiện khi `extras.suggestions` có; chạm là gửi ngay). Ô nhập `rounded-2xl` nền `surface-2`, placeholder theo mode, nút gửi gradient `--grad-orb` icon Send; nút Dừng khi đang sinh.

### 6.3 Ngăn trượt "Trái tim": ma trận cảm xúc và wiki (`components/chat/HeartDrawer.tsx`)
Trượt từ phải (mobile: toàn màn hình từ dưới hoặc phải), kính mờ.
- Thẻ "Chỉ dẫn diễn xuất" (`extras.relationship.directive`).
- 6 thanh tiến độ màu cảm xúc (0-100%, `transition-[width] duration-500`): Thương mến, Tin cậy, Rung động, Nhung nhớ/Chiếm hữu, Lo sợ mất mát, Khoảng cách.
- Thẻ wiki/ký ức đã mở khoá (`extras.lore_tags`, dạng "✨ Tiệm Sách Mùa Thu").
- Khi chưa có dữ liệu: các thanh ở 0 mờ, lời giải thích nhẹ nhàng "Lyris chưa theo dõi cảm xúc của câu chuyện này. Ma trận sẽ tự cập nhật khi tính năng trí nhớ & quan hệ được bật." (không nói "Phase 3").

### 6.4 Khám Phá (`pages/explore/ExplorePage.tsx`)
- Thẻ hero "thế giới nổi bật": nền gradient mềm, ảnh/avatar, tiêu đề, mô tả ngắn, nút "Bước Vào Câu Chuyện" (cài template nếu cần rồi tới `#/new-story?card=`).
- Chip lọc "vibe": `✨ Chữa Lành`, `✨ Dịu Dàng`, `✨ Bí Ẩn Nội Tâm`, `✨ Tình Đầu` + các tag có trong card; lọc theo tag (không phân biệt hoa thường, bỏ dấu ✨).
- Lưới 2 cột thẻ dọc `aspect-[3/4]`: ảnh (avatar phủ kín hoặc gradient + chữ cái đầu), tên, vai trò, nút "Trò Chuyện". Gồm card của người dùng và template chưa cài (nhãn "Mẫu").

### 6.5 Studio "Xưởng Dệt Tâm Hồn"
Giữ toàn bộ chức năng Phase 2, đổi sang design mới. Thêm:
- Trường **Vai trò** (`card.role`, ví dụ "Chủ tiệm sách mùa thu") ngay dưới tên.
- **Cảm xúc ban đầu**: 6 thanh trượt 0-100 (mặc định Thương mến 30, Tin cậy 30, Rung động 10, Nhung nhớ 0, Lo sợ 0, Khoảng cách 20), lưu ở `card.extensions.lyris.initial_relationship` (Phase 3 dùng làm điểm khởi đầu).
- Thẻ **Wiki & Lorebook**: trạng thái đồng bộ thư mục `world_wiki/*.md` (lấy từ `GET /api/lore/status`; hiện trả `{enabled:false, entries:0, files:0, last_sync:null}`), chữ "Chưa đồng bộ thế giới nào" khi rỗng.
- Import `.json`/`.png` giữ như Phase 2.

### 6.6 Modal "Persona & Máy chủ M2" (Phase 2c: thành sheet "Tài khoản", `components/shell/AccountSheet.tsx`, xem §13)
Mở từ avatar góc phải header hub.
- **Persona đang dùng**: thẻ persona mặc định cho story mới, đổi nhanh trong danh sách; link "Quản lý persona" → `#/personas`.
- **Máy MacBook M2** (từ `GET /api/system`, làm mới mỗi 10 giây khi mở):
  - huy hiệu kết nối ("Hoạt động êm ái" / "Đang chạy pin, sẽ chậm hơn" / "Không kết nối được Ollama");
  - thanh RAM hợp nhất "9.4 GB / 24 GB";
  - model đang nạp và dung lượng;
  - **chọn model chat mặc định** (danh sách model Ollama thật, lưu bằng `PUT /api/settings`);
  - trạng thái KV cache (`q8_0`) và Flash Attention.

## 7. Backend cho design (`be-design`)

Migration `0004_lyris.sql`:
```sql
ALTER TABLE character_cards ADD COLUMN role TEXT NOT NULL DEFAULT '';
CREATE TABLE app_settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
```
Model (hợp đồng): `CharacterCard.role: str = ""`; `AppSettings {default_persona_id: int|None, default_chat_model: str|None}`; `StoryExtras` (dưới).

Endpoint mới / đổi:
| Method | Path | Trả |
|---|---|---|
| GET | /api/settings | `AppSettings` |
| PUT | /api/settings | `AppSettings` (kiểm tra persona tồn tại; model có trong danh sách Ollama nếu Ollama kết nối được) |
| GET | /api/system | `SystemInfo` (dưới), cache 5 giây |
| GET | /api/stories/{id}/extras | `StoryExtras` (hiện: mọi trường rỗng/null) |
| GET | /api/lore/status | `{enabled: false, files: 0, entries: 0, last_sync: null, dir: "world_wiki"}` |
| GET | /api/templates | `TemplateInfo[]` |
| POST | /api/templates/{slug}/install | `CardOut` (đã cài thì trả card cũ; nhận ra qua `extensions.lyris.template == slug`) |
| PATCH | /api/stories/{id} | thêm `model_name` (phải là model Ollama có thật nếu kết nối được) |

- `StoryOut` thêm: `card_role`, `last_preview` (≤ 140 ký tự, phần hiển thị của message active mới nhất, bỏ Thought và `((...))`, gộp khoảng trắng; null nếu không có), `last_role` (`user`/`assistant`/null), `last_mode`.
- `POST /api/stories` không có `persona_id` → dùng `default_persona_id` (thiếu thì persona đầu tiên). Story mới dùng `default_chat_model` nếu đặt, không thì `Settings.chat_model`. `GET /api/stories/defaults` cho phép thiếu `persona_id` tương tự.
- `SystemInfo`: `{ollama: {reachable, version, error}, models: [{name, size_gb, parameter_size, quantization}], loaded: [{name, size_gb, expires_at}], memory: {total_gb, used_gb}, power: {on_battery: bool|null, low_power_mode: bool|null}, ollama_env: {kv_cache_type, flash_attention, num_parallel, max_loaded_models}, chat_model_default}`. macOS: `sysctl -n hw.memsize`, `vm_stat` (đã dùng = (active + wired + compressed) × page size), `pmset -g batt` / `pmset -g` (lowpowermode), `launchctl getenv OLLAMA_*`. Mọi lệnh có timeout 2 giây và lỗi thì trả null, không bao giờ 500. Ollama: `/api/version`, `/api/tags`, `/api/ps`.
- `StoryExtras`: `{relationship: {affection, trust, attraction, obsession, fear, aversion: int 0-100, directive: str|null} | null, suggestions: string[], moment: {text, effect?} | null, lore_tags: string[], location: string|null, in_world_time: string|null}`.
- `TemplateInfo`: `{slug, featured: bool, vibes: string[], card: CharacterCard (không id), installed_card_id: int|null}`.
- Template trong `backend/lyris/seed/templates/*.json` (mỗi file một card đầy đủ + `featured`, `vibes`). Bộ đầu: **Hạ Vy, chủ tiệm sách mùa thu** (viet_hien_dai, chữa lành, dịu dàng; featured; gác xép mùi gỗ thông, bức thư kẹp trong sách), Trần Minh Khang (viet_hien_dai), Tạ Vân Lan (trung_co_dai), Lạc Dương (trung_hien_dai; trùng seed thì nhận là đã cài), một card tiếng Anh. Văn tiếng Việt tự nhiên, lời mở đầu đúng luật (Thought inline, `{{user}}`, xưng hô chỉ trong thoại/Thought, không "bầu không khí").
- Draft (`studio/draft.py`) điền thêm `role`; `card_v2` export `role` trong `extensions.lyris`.

## 8. Hợp đồng frontend (lead viết trước)

`types.ts`: `CharacterCard.role`, `StoryOut.card_role/last_preview/last_role/last_mode`, `AppSettings`, `SystemInfo`, `StoryExtras`, `RelationshipState`, `TemplateInfo`, `LoreStatus`, `StoryPatch.model_name`. `api/client.ts`: `getSettings, putSettings, getSystem, getStoryExtras, getLoreStatus, listTemplates, installTemplate`.

## 9. Kiểm tra

- `pytest`, `npm test`, `typecheck`, `build` qua hết.
- Ảnh chụp headless Chrome ở 375px (giả lập thiết bị qua CDP, không dùng `--window-size` vì Chrome headless tối thiểu ~500px) và 1280px, **cả hai theme**: hub, chat Story (có Thought mờ và đã mở), chat DM, ngăn trái tim, Khám Phá, Studio danh sách + editor, modal Persona & Máy chủ, tạo story.
- Dấu tiếng Việt hiển thị đúng ở cả ba font.

## 10. Taste: bớt dấu hiệu "AI gen" (skill design-taste-frontend)

Người dùng yêu cầu kết hợp skill `design-taste-frontend` (thư mục `/Users/hanghang/.claude/skills/design-taste-frontend`). Lyris là **app screen** (người ta làm việc/chơi trong đó), nên theo `references/app-screens.md` (§9-§14: type, màu, bề mặt, trạng thái, điện thoại, house rules, tells) và `references/tells.md`. **Không bốc thăm hướng thiết kế** (`draw.mjs --app` chỉ có kiểu dashboard tài chính/analytics, không hợp app nhập vai); hướng thiết kế là DESIGN.md (thương hiệu cố định màu, font), giống trường hợp "existing brand: --keep palette,type" của skill.

**Giữ vì DESIGN.md chỉ định rõ (thương hiệu), nhưng dùng tiết chế và chỉ đúng chỗ:**
- Kính mờ (backdrop blur): chỉ 3 chỗ: header hub, thanh tab nổi, header chat. Không card, không modal nào là kính (modal/ngăn kéo dùng nền `surface` đặc).
- Gradient: chỉ 4 chỗ: quả cầu tab giữa, nút gửi, bong bóng người chơi, chữ L của wordmark. Không gradient ở nền, banner, hero, card, chip, nút khác, chữ khác.
- Thẻ Thought: viền trái 3px `accent` + nền **tint phẳng** (accent khoảng 8% trên `surface`), không gradient (lệch nhẹ DESIGN.md để tránh dấu hiệu; ghi trong báo cáo).
- Ba font, mỗi font một việc cố định (brand chỉ cho wordmark; UI; văn truyện). Không font thứ tư, không monospace.
- Bóng: chỉ trên thứ nổi (thanh tab, quả cầu, modal, ngăn kéo, menu). Card, thẻ story, ô nhập lúc nghỉ: không bóng, tách bằng bước tông màu (`surface` trên `bg`) hoặc viền 1px `line`, không cả hai.

**Bỏ / thay so với ví dụ trong DESIGN.md (ghi rõ trong báo cáo để người dùng có thể khôi phục):**
- Emoji trong banner chào (☀️ 🕯️...) và chip vibe (✨): bỏ emoji, giữ lời. Không emoji trong nav, nhãn, trạng thái rỗng. (Emoji do người chơi/nhân vật viết trong tin nhắn thì giữ nguyên.)
- Chữ hoa giãn cách ("TƯƠNG TÁC", "STORY", "DM" dạng caps tracked): dùng chữ thường câu ("Tương tác", "Story", "DM"); huy hiệu mode trên avatar 11-12px không giãn chữ.
- "Glowing drop shadow" của quả cầu: một bóng mềm màu accent alpha thấp (nó nổi), không vầng sáng nhiều lớp.

**Cấm (như skill), kiểm bằng `lint.mjs --app` và `inspect.mjs --app`:**
- Icon trong ô vuông/tròn tô màu; card trên đầu có icon; hàng card giống hệt nhau làm trang trí.
- Nhãn nhỏ trên tiêu đề (eyebrow/kicker), pill badge trên heading, đánh số 01/02/03, chữ mono, đường kẻ mảnh trang trí, blob/hình trang trí, ngôi sao/lấp lánh rải rác (ngôi sao chỉ ở logo và chỉ báo đang sinh).
- Tiêu đề kiểu landing page: tiêu đề màn hình 20-28px; không chữ nào ≥ 48px ngoài wordmark.
- Hover nâng card lên, bounce, hiệu ứng xuất hiện khi tải trang, shimmer. Chuyển động chỉ là phản hồi (nhấn, hover, focus, mở ngăn kéo/modal) cộng ba vi tương tác DESIGN.md nêu (đổi theme, mở Thought, chỉ báo đang sinh). Có `prefers-reduced-motion`.
- Dữ liệu giả: lorem, "User 1", số liệu phô trương; mọi số thật (RAM, số story, giờ) lấy từ API, chữ số tabular.
- Màu chữ mang nội dung đạt tương phản ≥ 4.5:1 trên nền nó nằm, cả hai theme, kể cả placeholder (tính lại `muted`, `faint` nếu không đạt; giữ tông ấm).
- Một họ bo góc: mềm (card 20px, control 14px hoặc tròn hẳn), bước xuống khi lồng nhau; không trộn 8/12/16 lung tung.

**Trạng thái (skill §11):** rỗng giữ khung + một câu + hành động đầu tiên; đang tải là khung xương đúng kích thước thật, không shimmer; lỗi nằm trong khối bị lỗi kèm "Thử lại"; số 0 in như số 0, thiếu dữ liệu là gạch ngang xám.

**Hình ảnh thật thay cho hình vẽ trang trí:** avatar người dùng tải lên là hình chính. Template đi kèm có thể mang ảnh thật giấy phép mở (tìm bằng `node <skill>/scripts/assets.mjs "<query>"`, tải bằng `--get`, ghi nguồn bằng `--credits`): ảnh **bối cảnh** (tiệm sách mùa thu, phố Sài Gòn mưa, núi mây cổ trang...), tranh/bản khắc cổ cho nhân vật cổ trang; không dùng ảnh người thật làm chân dung nhân vật. Ghi nguồn ở modal "Persona & Máy chủ" (mục "Nguồn ảnh") và trong báo cáo. Không mạng thì dùng avatar chữ cái trên nền phẳng, không vẽ hình trang trí.

**Kiểm tra (bắt buộc, theo skill):** `node <skill>/scripts/lint.mjs --app frontend/src` và `node <skill>/scripts/inspect.mjs --app <url bản build preview>` ở 1440/768/390, cả hai theme; sửa mọi FAIL; WARN chỉ giữ khi giải thích được bằng một câu (ví dụ gradient/kính do DESIGN.md chỉ định: dùng `--allow <rule>` đúng rule đó). Đọc mọi ảnh chụp, trả lời 7 câu hỏi critique ở `app-screens.md` §2.7, sửa 3 lỗi tệ nhất, tối đa 3 vòng.

## 11. Foundation API

Do `fe-foundation` viết (2026-11-12). Đây là bộ nền mà các màn hình (hub, chat, khám phá, studio, modal hệ thống) dùng lại. **Không tự viết lại nút, ô nhập, modal, chip, avatar, icon: import từ đây.** Ảnh chụp kiểm tra cả hai theme ở 390/1440px đã đọc; `lint.mjs --app` cho `components/ui`, `components/brand`, `theme` là 0 FAIL 0 WARN.

### 11.1 Token cuối cùng (Tailwind `bg-*`, `text-*`, `border-*`, `ring-*`; CSS `var(--color-*)`)

Dark là bộ mặc định (`@theme static` trong `index.css`), light ghi đè dưới `:root[data-theme="light"]`. Mọi tên token cũ giữ nguyên nên component cũ tự đổi màu theo theme.

| Token | Dark | Light | Ghi chú |
|---|---|---|---|
| `bg` | #130D14 | #FAF5EE | nền app, cũng là `theme-color` |
| `surface` | #1F1521 | #FFFDF9 | card, thẻ thoại, modal, ngăn kéo |
| `surface-2` | #2A1D2C | #F4ECE4 | ô nhập, chip, nút secondary, toggle tắt |
| `surface-3` | #352536 | #EDE2D8 | hover, đang chọn, nền chữ cái avatar, skeleton |
| `glass` | rgb(31 21 33 / .78) | rgb(255 252 249 / .85) | chỉ dùng qua utility `glass` / `glass-strong` |
| `line` | #382635 | #E8D7CE | viền mảnh, viền ô nhập, kẻ chân modal |
| `line-strong` | #4B3448 | #D8C2B7 | viền control nổi rõ hơn, khung nét đứt của EmptyState |
| `edge` | transparent | #E8D7CE | viền card: dark tách bằng bước tông, light cần viền mảnh |
| `fg` | #FAF2EB | #2D1E24 | chữ chính |
| `prose` | #E9DDE0 | #3A2A31 | thân văn bản dài |
| `muted` | #C2AAB8 | **#6B535D** | dẫn truyện nghiêng, phụ đề, giờ, hint |
| `faint` | **#9C8797** | **#7B626B** | placeholder, ghi chú phụ. **Không đặt trên `surface-3`** |
| `dialogue` | #FAF2EB | #2D1E24 | chữ trong thẻ thoại |
| `thought` | #EBC9CF | #8E4A5A | chữ trong thẻ Thought |
| `accent` | #E5989B | **#A14A5B** | nút chính, viền Thought, focus ring, active |
| `accent-strong` | #F0B3B5 | **#8A3A4D** | hover của accent |
| `accent-2` | #F3C68F | **#875A2B** | vai trò nhân vật, điểm nhấn vàng/hổ phách |
| `on-accent` | #1A1018 | #FFFDF9 | chữ/icon trên nền `accent` |
| `on-orb` | #1A1018 | #1A1018 | icon trên `bg-grad-orb` (trắng không đạt trên đầu vàng) |
| `user` / `user-from` / `user-to` | #291928 / #3D2638 / #291928 | #9E4A5C / **#B45A6C** / #9E4A5C | bong bóng người chơi (`bg-user-gradient`) |
| `user-border` | rgb(229 152 155 / .35) | transparent | `border border-user-border` |
| `user-fg` | #FAF2EB | #FFFFFF | chữ bong bóng người chơi |
| `danger` / `ok` / `warn` | #F08A8A / #7FD1A2 / #F3C68F | **#AB3E49 / #306F4B / #845B22** | |
| `emo-affection, emo-trust, emo-attraction, emo-obsession, emo-fear, emo-aversion` | #D86C86, #C58B52, #A864A8, #D15B5B, #6E7BB8, #9E8881 | như dark | chỉ cho thanh/chấm, không làm màu chữ |
| `scrim` | rgb(8 5 9 / .62) | rgb(45 30 36 / .36) | nền mờ sau modal/ngăn kéo |

Radius (Tailwind): `rounded-card` = 20px, `rounded-control` = 14px, còn lại `rounded-full`. Không dùng 8/12/16 lẻ.

Biến CSS khác: `--brand-rose`, `--brand-gold` (chỉ cho logo, giữ đúng màu DESIGN.md: dark #E5989B/#F3C68F, light #C86D7E/#C58B52), `--grad-wordmark`, `--grad-orb` (#C86D7E → #D98A6C → #F3C68F, cả hai theme), `--grad-user`, `--shadow-float`, `--shadow-orb`, `--font-story`, `--tabbar-height` (64px), `--space-tabbar`.

**Tương phản đo được** (WCAG, script node; mặt nền: `bg`, `surface`, `surface-2`, `glass` trộn trên `bg`, nền Thought = accent 8% trên `surface`; cột cuối là trên `surface-3`). Ngưỡng 4.5:1, mọi dòng đạt:

| Token | Dark: thấp nhất / trên surface-3 | Light: thấp nhất / trên surface-3 |
|---|---|---|
| fg, dialogue | 14.03 / 12.91 | 13.58 / 12.45 |
| prose | 11.75 / 10.81 | 11.55 / 10.59 |
| muted | 7.20 / 6.63 | 5.95 / 5.45 |
| faint | 4.68 / (4.31, không dùng) | 4.73 / (4.33, không dùng) |
| thought | 10.20 / 9.38 | 5.48 / 5.03 |
| accent | 6.88 / 6.33 | 4.93 / 4.52 |
| accent-strong | 8.74 / 8.05 | 6.43 / 5.90 |
| accent-2 | 9.83 / 9.04 | 5.09 / 4.67 |
| danger | 6.44 / 5.93 | 5.11 / 4.68 |
| ok | 8.54 / 7.86 | 5.13 / 4.70 |
| warn | 9.83 / 9.04 | 5.13 / 4.71 |
| user-fg trên gradient | 12.37 → 15.00 | 4.55 → 5.85 |
| on-accent trên accent / accent-strong | 8.22 / 10.45 | 5.67 / 7.40 |
| on-orb trên 3 điểm gradient | 5.25 / 6.90 / 11.74 | như dark |
| chữ Badge (tone trộn 25% fg) trên nền tint 15% | ≥ 4.85 mọi tone, mọi mặt nền | ≥ 4.85 |

**Lệch so với DESIGN.md / bảng §2 (để người dùng biết, có thể khôi phục):** light `accent` #C86D7E → #A14A5B và `accent-strong` #B05768 → #8A3A4D (chữ hồng và nhãn nút trắng không đạt 4.5:1 với màu gốc: 3.0-3.5); light `accent-2` #C58B52 → #875A2B (2.5:1 → 5.1:1); light `muted` #7D636D → #6B535D, `faint` #A8929A → #7B626B (2.5:1); dark `faint` #8F7789 → #9C8797 (3.9:1 trên ô nhập); light `ok/warn/danger` đậm hơn; bong bóng người chơi light #C86D7E→#B05768 → #B45A6C→#9E4A5C (chữ trắng 3.5:1 → 4.55:1). Màu gốc của DESIGN.md vẫn dùng cho logo/favicon (`--brand-*`) và quả cầu (`--grad-orb`). Icon trên quả cầu và nút gửi dùng mực tối `on-orb` thay vì trắng.

### 11.2 Utility CSS mới (`index.css`)

| Class | Tác dụng | Chỉ dùng ở |
|---|---|---|
| `font-sans` | Plus Jakarta Sans (mặc định của `body`) | UI, DM |
| `font-story` | Be Vietnam Pro + `line-height: 1.65` | văn Story, thẻ thoại, Thought. Cần dòng khác thì thêm `leading-*` |
| `font-brand` | Cormorant Garamond (chỉ có 600/700 nghiêng) | chỉ wordmark và tiêu đề chương đặc biệt, luôn kèm `italic` |
| `glass` / `glass-strong` | nền `glass` + blur 16px / 20px | header hub, header chat / thanh tab nổi. Không chỗ nào khác |
| `bg-grad-orb` | gradient quả cầu | nút giữa thanh tab, nút gửi (`IconButton variant="orb"` đã có sẵn) |
| `bg-user-gradient` | gradient bong bóng người chơi | bong bóng người chơi, kèm `text-user-fg border border-user-border` |
| `text-grad-wordmark` | chữ gradient | chỉ chữ L trong `Wordmark` (đã dùng sẵn) |
| `shadow-float` | bóng của thứ nổi | modal, ngăn kéo, menu, thanh tab |
| `shadow-orb` | bóng mềm màu hồng | quả cầu tab giữa, nút gửi |
| `pt-safe`, `pb-safe` | padding = safe-area trên / dưới | header, composer, sheet |
| `pb-tabbar` | padding đáy = 64 + 16 + safe-area + 16px | trang có thanh tab nổi (hub, khám phá, studio danh sách) |
| `animate-breathe` | nhịp thở 3.2s (mờ/to nhẹ), tắt khi reduced-motion | ngôi sao chỉ báo đang sinh, chấm trạng thái máy |
| `dark:` / `light:` | variant theo `html[data-theme]` | chỉnh riêng một theme khi thật cần |
| `prose-story`, `.thought-line`, `typing-dot`, `caret`, `scroll-thin` | giữ cho code cũ; `.thought-line` giờ là viền trái 3px accent + nền tint phẳng, không emoji | |

### 11.3 Theme (`src/theme`)

```ts
import { ThemeProvider, useTheme, ThemeToggle } from "../theme";
type Theme = "dark" | "light";
useTheme(): { theme: Theme; source: "stored" | "system" | "url";
  setTheme(t: Theme): void; toggleTheme(): void; followSystem(): void }
<ThemeToggle size?: "md" | "sm" className?: string />   // nút Sun/Moon cho header, nhãn tiếng Việt
```
- `main.tsx` đã bọc `<App />` trong `ThemeProvider`. Script nội tuyến trong `index.html` đặt `html[data-theme]` và `meta theme-color` trước khi vẽ (không nháy).
- Thứ tự: `?theme=dark|light` trên URL (không lưu; dùng cho ảnh chụp kiểm tra), rồi `localStorage["lyris.theme"]`, rồi `prefers-color-scheme`, mặc định dark. Chưa chọn thì theo hệ thống trực tiếp; đồng bộ giữa các tab.
- Đổi theme: lớp `theme-switching` trên `html` trong 550ms cho mọi màu (nền, viền, chữ, fill) chuyển 500ms; tắt khi reduced-motion. Không cần tự thêm `transition-colors duration-500`.
- Hàm thuần (`theme/theme.ts`, có test): `parseTheme`, `resolveTheme(stored, systemPrefersLight, override?)`, `oppositeTheme`, `themeFromSearch`, `THEME_STORAGE_KEY`, `THEME_META_COLORS`.

### 11.4 Font

`main.tsx` import (tự host, có subset tiếng Việt): Cormorant Garamond 600-italic, 700-italic; Plus Jakarta Sans 400/500/600/700; Be Vietnam Pro 300/400/400-italic/500. Không có 800 và không có Be Vietnam 500-italic: đừng dùng `font-extrabold`, và thẻ thoại đậm vừa (`font-medium`) không nghiêng. Dấu chồng (ư ơ ằ ễ ỡ ặ ữ ỷ) đã kiểm ở cả ba font.

### 11.5 Thương hiệu (`src/components/brand`)

```ts
import { LogoMark, Wordmark } from "../components/brand";
<LogoMark size?: number /*32*/ title?: string /*có thì role=img, không thì trang trí*/ animated?: boolean /*false*/ className?: string />
<Wordmark size?: number /*cỡ chữ px, 28*/ animated?: boolean /*true, sao nhấp nháy nhẹ*/ flourish?: boolean /*true*/ className?: string />
```
- `LogoMark`: hai nửa trái tim là hai trang sách, gáy sách ở giữa, ngôi sao 4 cánh vàng; nét 1.8px không co giãn (lên tới 4px ở cỡ lớn), gradient `--brand-rose → --brand-gold`.
- `Wordmark`: `role="img" aria-label="Lyris"`; L gradient, "ı" có sao, dải lụa bên dưới. Trong header hub đặt cỡ 26-30. Màn hình cần h1 thì bọc: `<h1><Wordmark /></h1>` hoặc thêm h1 ẩn (`sr-only`) tên màn hình.
- `public/favicon.svg` (ô vuông bo #130D14), `public/apple-touch-icon.png` 180px, `public/manifest.webmanifest` (standalone). `index.html`: title Lyris, `apple-mobile-web-app-capable`, `status-bar-style=black-translucent`, `apple-mobile-web-app-title=Lyris`, viewport `viewport-fit=cover`.

### 11.6 Icon (`src/components/icons.tsx`)

Kiểu Lucide, nét 1.75px, `1em`, `currentColor`, `aria-hidden`. Prop: mọi `SVGProps<SVGSVGElement>`; đổi cỡ bằng `text-[18px]` ở cha hoặc `className`.
`IconCompass, IconHeart, IconHeartFilled, IconSparkles, IconSun, IconMoon, IconChevronLeft, IconChevronRight, IconChevronDown, IconSend, IconRefreshCw, IconStar4 ({filled?: boolean = true}), IconSearch, IconSettings, IconPlus, IconX, IconMoreHorizontal, IconImage, IconUpload, IconDownload, IconTrash, IconEdit, IconThumbsUp ({filled?}), IconThumbsDown ({filled?}), IconStop, IconMessageCircle, IconBookOpen, IconUser, IconCpu, IconCheck, IconMapPin, IconClock, IconEye`.
Các tên cũ (`IconRegenerate`, `IconClose`, `IconThumbUp`, `IconThumbDown`) đã bỏ khi tích hợp (không còn ai dùng): dùng `IconRefreshCw`, `IconX`, `IconThumbsUp`, `IconThumbsDown`. `IconSend` giờ là máy bay giấy (Lucide Send). `IconStar4` chỉ cho họ logo và chỉ báo đang sinh.

### 11.7 Primitive (`import { … } from "../components/ui"`)

Chiều cao: `md` = 44px (mặc định, chạm được trên điện thoại), `sm` = 36px (hàng dày, toolbar desktop, header 56px). Một hàng dùng một cỡ.

```ts
// Button: pill, chữ 15px/600 (sm 14px)
<Button variant?: "primary" | "secondary" | "ghost" | "danger" /*"secondary"*/ size?: "md" | "sm"
  loading?: boolean icon?: ReactNode iconEnd?: ReactNode block?: boolean
  {...ButtonHTMLAttributes} />            // forwardRef<HTMLButtonElement>; type mặc định "button"
// primary = nền accent chữ on-accent (một nút primary mỗi màn hình); secondary = surface-2;
// ghost = chữ muted; danger = viền + chữ danger (xoá, đặt cuối, kèm xác nhận nêu tên đối tượng).

<IconButton label: string /*bắt buộc: aria-label + tooltip*/ icon: ReactNode
  variant?: "ghost" | "secondary" | "primary" | "orb" /*"ghost"*/ size?: "md" | "sm"
  pressed?: boolean /*aria-pressed*/ loading?: boolean noTooltip?: boolean
  {...ButtonHTMLAttributes trừ children, aria-label} />   // forwardRef
// Dùng ghost gần như mọi nơi. "orb" chỉ cho nút gửi; "primary"/"secondary" (icon trong vòng tròn tô màu)
// bị inspect.mjs bắt lỗi icon-chips nếu lặp lại: tối đa một cái mỗi màn hình.

<Chip children onClick?: () => void selected?: boolean icon?: ReactNode dotColor?: string /*CSS color*/
  size?: "md" | "sm" /*36 / 28px*/ disabled? title? className? />
// có onClick: nút bật/tắt (aria-pressed), chọn = tint accent 15% + viền accent; không onClick: thẻ tĩnh.
// Chip cảm xúc: <Chip size="sm" dotColor="var(--color-emo-affection)">Thương mến 91%</Chip>
// Chip địa điểm: <Chip size="sm" icon={<IconMapPin />}>Gác xép mùi gỗ thông</Chip>
// Gợi ý trả lời nhanh dài: thêm className="max-w-[80vw]" (chữ tự cắt "…").

<Badge children tone?: "neutral" | "accent" | "gold" | "ok" | "warn" | "danger" solid?: boolean className? />
// 20px, chữ 12px/600, không giãn chữ. solid = nền đặc + vòng 2px màu bg, cho huy hiệu nằm trên ảnh:
// <Avatar shape="portrait" size={48} badge={<Badge solid tone="accent">Story</Badge>} />

<Card padding?: "md" | "sm" | "none" /*20 / 16 / 0px*/ {...HTMLAttributes<HTMLDivElement>} />
// bg-surface rounded-card border-edge, không bóng.

<TextField label: string value: string onChange: (v: string) => void hint?: ReactNode error?: ReactNode
  icon?: ReactNode /*icon trái*/ hideLabel?: boolean className? /*wrapper*/ inputClassName?
  {...InputHTMLAttributes trừ value/onChange/size} />          // forwardRef<HTMLInputElement>
<TextArea label value onChange hint? error? maxHeight?: number /*260*/ hideLabel? className? inputClassName?
  {...TextareaHTMLAttributes trừ value/onChange} />          // forwardRef<HTMLTextAreaElement>, tự cao lên
<Select<T extends string> label value: T onChange: (v: T) => void options: { value: T; label: string; disabled?: boolean }[]
  hint? error? placeholder?: string hideLabel? className? {...SelectHTMLAttributes} />   // select gốc
<Toggle label: string description?: ReactNode checked: boolean onChange: (checked: boolean) => void disabled? className? />
// hàng công tắc: chữ trái, công tắc phải; bật = màu mực fg (không phải accent).
<Field label hint? error? htmlFor? hideLabel? extra?: ReactNode /*bên phải hàng nhãn: bộ đếm, nút nhỏ*/ className? children />   // tự ghép control khác
<ChoiceGroup<T extends string> label options: { value: T; label: string; hint?: string }[] value onChange hint? disabled? />
// nhóm lựa chọn dạng pill xuống dòng (giới tính, ngôn ngữ, kiểu quan hệ...); chọn = tint accent + viền. Khác SegmentedControl (công tắc chế độ Story/DM).
<InlineAlert tone: "error" | "info" text onRetry? retryDisabled? actionLabel? /*"Thử lại"*/ onDismiss? className? />
// thông báo một dòng nằm trong khối bị lỗi (tạo story, khung chat qua Banner).
CONTROL_CLASS: string   // class của mọi ô nhập (44px, bo 14, nền surface-2, viền line, chữ 16px)
// Nhãn luôn ở trên (14px/500), cách control 8px; hint 13px muted; lỗi 13px danger, aria-invalid + aria-describedby tự gắn.
// Ô tìm kiếm hub: <TextField label="Tìm câu chuyện" hideLabel icon={<IconSearch />} placeholder="…" />

<Modal open: boolean onClose: () => void title: string description?: ReactNode children footer?: ReactNode
  size?: "sm" | "md" | "lg" /*400 / 520 / 680px từ 640px*/ hideTitle?: boolean dismissible?: boolean /*true*/
  initialFocusRef?: RefObject<HTMLElement | null> className? />
<Drawer {cùng prop như Modal trừ size} side?: "right" | "left" | "bottom" /*"right"*/ width?: number /*400*/ />
// Portal vào body; nền surface đặc + shadow-float; điện thoại: Modal là sheet từ dưới, Drawer trái/phải
// phủ toàn chiều rộng. Bẫy focus (Tab vòng), Escape đóng cái trên cùng, khoá cuộn trang + #root inert,
// trả focus về chỗ cũ; focus đầu vào control đầu tiên (không phải nút Đóng). Footer: nút size="sm",
// căn phải, ghost trước primary. Chuyển động trượt/mờ 180-260ms, tắt khi reduced-motion.
useOverlay({ open, onClose, panelRef, initialFocusRef?, closeOnEscape? })  // nếu tự dựng lớp phủ khác

<SegmentedControl<T extends string> options: { value: T; label: string; icon?: ReactNode; disabled?: boolean }[]
  value: T onChange: (v: T) => void label: string /*tên nhóm cho screen reader*/ size?: "md" | "sm" disabled? className? />
// radiogroup, phím mũi tên/Home/End; đoạn chọn tô accent. Story/DM trong header chat: size="sm".

<Skeleton width?: number | string height?: number | string shape?: "text" | "block" | "card" | "circle" | "pill"
  lines?: number /*cho shape text*/ className? />
// phẳng, không shimmer, aria-hidden; đặt đúng kích thước thật; vùng cha mang aria-busy="true".

<EmptyState text: string /*một câu*/ action?: ReactNode /*một Button size="sm"*/ framed?: boolean /*true*/ className? />
// khung nét đứt bo 20, căn trái, không hình minh hoạ, không emoji.

<Meter label: string value: number max?: number /*100*/ color?: string /*CSS, mặc định accent*/
  valueText?: string /*mặc định "NN%"*/ empty?: boolean /*thanh ở 0, giá trị "—"*/ hideLabel? className? />
// role="meter", chữ số tabular, width chuyển 500ms. 6 cảm xúc: color={`var(--color-emo-${key})`};
// RAM: <Meter label="Bộ nhớ hợp nhất" value={used} max={total} valueText="9.4 GB / 24 GB" />

<Spinner size?: number /*16*/ label?: string /*có thì role=status*/ className? />
cx(...classes), initialOf(name), portraitRadius(size), meterPercent(value, max)   // hàm thuần (logic.ts, có test)
```

### 11.8 Component cũ đã đổi kiểu (API giữ nguyên, chỉ thêm)

- `Avatar({ name, url?, size? = 28, shape?: "circle" | "portrait" = "circle", fill?: boolean, badge?: ReactNode, className? })`: ảnh hoặc chữ cái đầu màu accent trên nền phẳng `surface-3`. `portrait` bo theo cỡ (48px → 14px, 32px → 10px, ≥ 66px → 20px). `fill` phủ kín khung cha (thẻ 3:4 Khám phá; cha đặt kích thước, bo góc, `overflow-hidden`). `badge` ở góc dưới phải, không bị cắt. `initialOf` vẫn export.
- `Banner` (props như cũ): giờ chỉ là `InlineAlert` đặt trong cột 720px của khung chat.
- `formControls` đã xoá khi tích hợp: `Field`/`TextField`/`TextArea` lấy từ `components/ui`, `Segmented` thành `ChoiceGroup`, `SectionTitle` thành `h2` tại chỗ.
- `PronounFields`: nhãn 14px trên, nút gợi ý là `Button sm secondary`.
- `AutoTextarea`, `characterAvatar.ts`: không đổi.

### 11.9 Quy tắc cho các màn hình kế tiếp

- Bề mặt: card = `Card` (hoặc `rounded-card bg-surface border border-edge`). Không thêm bóng cho thứ nằm yên; không `bg-white/…`, `bg-black/…` (không theo theme): dùng `surface-2/3`, `scrim`.
- Chữ trên nền accent dùng `text-on-accent`, không `text-bg`. Chữ vai trò nhân vật `text-accent-2`. `text-faint` không đặt trên `surface-3`.
- Một nút primary mỗi màn hình; còn lại secondary/ghost. Icon trong nút: ghost. Không icon trong vòng tô màu lặp lại.
- Thang chữ: 12 / 13 / 14 / 15 / 16 / 20 / 24 (tiêu đề màn hình 20-24/600). Không ≥ 48px ngoài wordmark. Số liệu `tabular-nums`.
- Tiêu đề màn hình là `h1` (inspect.mjs FAIL `no-title` nếu thiếu).
- `inspect.mjs` sẽ FAIL `gradient`/`gradient-text` cho 4 chỗ DESIGN.md chỉ định (quả cầu, nút gửi, bong bóng người chơi, chữ L): chạy với `--allow gradient,gradient-text` và ghi lý do; WARN `palette-cream` ở light và `font-count` (3 font) cũng do DESIGN.md. Định nghĩa trong `index.css` đã mang chú thích `taste-skill-ignore` nên `lint.mjs` không bắt.
- Kiểm tra cả hai theme: thêm `?theme=light` / `?theme=dark` vào URL khi chạy `inspect.mjs` (Chrome headless báo hệ thống sáng).

### 11.10 Số liệu "trước" (taste skill, bản build trước đợt này)

- `lint.mjs --app frontend/src`: **13 FAIL, 23 WARN** (FAIL: emoji ×11, micro-label ×2; WARN: glass ×6, shadow ×8, numbering ×2, bounce ×3, mono ×4).
- `inspect.mjs --app` (http://127.0.0.1:5191/, màn hình chat Story): **2 FAIL, 1 WARN**: FAIL `emoji` (💭), `no-title` (không có h1); WARN `palette-cream`. Font: Palatino 95%, -apple-system 5%; cỡ chữ 12/13/14/15/16/17px, thân 17px/1.85; nền #0e0e11. Ảnh: `.taste-skill/before/`.
- Sau nền tảng (cùng màn hình, chưa dựng lại): lint toàn app **11 FAIL, 25 WARN** (mọi FAIL còn lại nằm ở file của người khác: emoji trong Header, NavDrawer, DmThread, MessageList…; micro-label ở StoryPicker); inspect **2 FAIL, 1 WARN** ở cả hai theme (`emoji` 💭 trong Header, `no-title`), font đã thành Be Vietnam Pro 95% + Plus Jakarta Sans 5%, thân 16px/1.65.

## 12. Tích hợp (integrator, 2026-11-13)

**Gộp chỗ trùng, bỏ code chết:**
- `components/ThoughtBlock.tsx` (bọc mỏng `ThoughtCard`) đã xoá; DmThread dùng thẳng `pages/chat/ThoughtCard`. Chỉ còn một bộ dựng Story Mode: `lib/storyBlocks.ts` + `components/Prose.tsx` (`StoryProse` không ai dùng, đã bỏ).
- `components/formControls.tsx` đã xoá (xem 11.8). `pages/studio/ui.tsx` không còn `Field` riêng: dùng `Field` của foundation (thêm prop `extra`).
- Một header trang phụ duy nhất: `components/shell/SubpageHeader` (`backHref, backLabel, title, subtitle?, children? /*hành động*/, width?: "narrow" | "wide" | "fluid"`). `TopBar` trong studio/ui đã bỏ; editor, persona, tạo story dùng chung.
- `InlineError` của NewStoryPage và phần thân `Banner` gộp thành `InlineAlert` (foundation).
- `components/shell/index.ts` giờ được App dùng.

**Nối giữa các phần:**
- Dòng phụ header chat: vai trò nhân vật (`card_role`, màu `accent-2`) rồi địa điểm/giờ trong truyện hoặc tiêu đề story; không lặp khi tiêu đề trùng vai trò (`headerSubtitle` trả `{role, detail}`, có test).
- Chat thử trong editor bắt đầu với persona mặc định (`AppSettings.default_persona_id`), như trang tạo story.
- `npm test` chạy mọi `src/**/*.test.ts` (trước đây chỉ `src/lib`).

**Dữ liệu demo:** `backend/.venv/bin/python scripts/make_demo_db.py <db> <thư mục avatar> [--force]`: cài 4 nhân vật mẫu qua API, 2 persona (Ngọc Anh mặc định, Gia Huy), 4 story (Hạ Vy dài, Story, có Thought, chỉ đạo, 2 phiên bản, một lượt được thích; Trần Minh Khang Story rồi DM; Morwenna tiếng Anh; Tạ Vân Lan cũ 4 ngày), giờ lùi về quá khứ. Không gọi Ollama (LLM giả, OLLAMA_URL cổng chết); từ chối ghi vào `data/`.

**Kiểm tra cuối:** lint toàn app 0 FAIL, 5 WARN (bóng của `shadow-float`/`shadow-orb` cho thứ nổi, `padStart` của giờ, gạch ngang "thiếu dữ liệu"). `inspect.mjs --app --allow gradient,gradient-text` trên 8 màn hình × 2 theme: 0 FAIL; WARN còn lại: `palette-cream`, `font-count` (DESIGN.md), `icon-chips` (ảnh avatar bị đếm là icon), `below-fold` ở editor (form dài cuộn trong khung). Đi qua mọi route bằng Chrome headless ở 390x844 và 1280x860, hai theme, cùng các luồng gửi Story/DM, tạo lại, đổi phiên bản, đổi tên, tìm kiếm, đổi theme, đổi persona/model mặc định, tạo/xoá story, tạo nhân vật, thêm persona: không lỗi console, không request lỗi.


## 12. Bổ sung sau đợt triển khai (2026-11-13)

- Tham số URL chỉ dùng để chụp/kiểm tra giao diện (đặt trong phần search, trước dấu `#`; không lưu, không đổi hash):
  - `?theme=light|dark`: ép theme;
  - `?open=system|heart|settings|profile` (`lib/overlayParam.ts`): mở sẵn lớp phủ. `system` = sheet Tài khoản ở header hub; `heart` = ngăn cảm xúc, `settings` = thiết lập story (trong `#/chat/<id>`); `profile` = sheet sửa profile (trong `#/me`);
  - `?tab=characters|personas` (`initialTab`): tab mở sẵn của trang profile (`#/me`). Giá trị lạ thì bỏ qua.
  - Ví dụ: `http://127.0.0.1:5190/?theme=light&open=heart#/chat/5`, `/?tab=personas#/me`.
- Card có thể đặt đại từ dẫn truyện riêng cho nhân vật: `card.extensions.lyris.narration_character` (chuỗi cho tiếng Việt, hoặc `{vi, en}`). `studio/stories.default_settings` dùng nó trước mặc định của style profile; Studio có ô "Đại từ dẫn truyện cho nhân vật (tuỳ chọn)".
- Style profile thứ năm `trung_dan_quoc` (Dân Quốc: gia/em, tam gia, tiên sinh, tiểu thư; dẫn truyện "hắn"), viết cho thế giới Yến Hoành Sinh trong `worlds/`.
- `worlds/<nhân vật>/`: thế giới, cốt truyện, nhân vật xung quanh, lore (chuẩn bị cho Phase 4) và `card.json` import được của 4 nhân vật người dùng gửi.

## 13. Tích hợp Phase 2c: tài khoản, profile, persona có avatar (integrator, 2026-11-13)

Thiết kế: `docs/accounts.md`. Phần này chỉ ghi chỗ nối giữa các phần và chỗ lệch.
- **Một store tài khoản** `hooks/useAccount.ts` (module-level, `useSyncExternalStore`) cho avatar ở header hub, sheet "Tài khoản" (`components/shell/AccountSheet.tsx`, thay `SystemModal.tsx` đã xoá), trang `#/me` và khối mời ở hub: lưu ở một chỗ thì mọi chỗ đổi ngay, không tải lại. Trang profile và việc mở sheet đọc lại tài khoản (số liệu đổi khi tạo card/story/persona ở chỗ khác).
- **Số nhân vật trên profile** là số nhân vật account tự tạo (lưới tab "Nhân vật": bỏ nhân vật mẫu đã cài). `card_count` của API đếm mọi card account sở hữu (gồm mẫu), nên trong lúc lưới đang tải số này là khung xương, không hiện `card_count` rồi nhảy số.
- **Visibility không bị reset khi lưu card:** `lib/cardForm.toCard` giữ `uid`, `visibility` của card; backend `PUT /api/cards/{id}` giữ visibility đã lưu khi body không có trường này (client cũ, script).
- **Avatar persona** hiện ở: trang Persona, chọn persona khi tạo story, sheet Tài khoản, tab Persona của profile, khối "Persona của bạn" ở Studio, cạnh bong bóng người chơi trong DM. Persona không có ảnh dùng chữ cái đầu như cũ. Ô chọn persona trong "Thiết lập thử" của editor là `select` gốc, không có ảnh.
- **Tác giả:** "bởi @handle" cho nhân vật của account, "Mẫu của Lyris" cho nhân vật mẫu (Khám phá, Studio), kèm "Riêng tư" ở Studio và trên lưới profile.
- **Dữ liệu demo** (`scripts/make_demo_db.py`): tài khoản đã đặt profile (tên giả "Minh Thư", `@minhthu.viet`, giới thiệu, avatar chữ cái), một nhân vật tự tạo riêng tư (Phạm Hoài An, có avatar), 2 persona có avatar chữ cái màu phẳng (Pillow), 4 story (Story và DM). `--fresh-account` giữ tài khoản mặc định chưa đặt tên để xem lời mời ở hub.
- **Kiểm tra:** đi qua mọi route ở 390x844 và 1280x860, hai theme, trên DB tạm: lần đầu (`profile_completed = 0`, khối mời), sửa profile (handle sai báo ngay dưới ô; handle trùng của account thứ hai trả 422 hiện dưới ô; lưu được thì khối mời ẩn, header đổi tên ngay), tải ảnh đại diện và ảnh bìa (2400x900 thành 1333x500), hai tab profile, `#/u/<handle khác>` và `#/u/nobody` (404), persona có avatar, chọn persona khi tạo story, avatar persona trong DM, sheet Tài khoản: không lỗi console, không request lỗi ngoài 422/404 chủ đích, không cuộn ngang. Nâng cấp một bản sao DB Phase 2b (migration 0001-0004 + dữ liệu kiểu demo): sau 0005 mọi card, persona, story thuộc account chủ máy `@ban` (`profile_completed = 0`), có uid 32 hex, riêng tư, và hiện đủ trong app.

## 14. Phase 3: state và trí nhớ trên giao diện (fe, 2026-11-13)

Đặc tả: `docs/phase3.md` §7-§8. Kiểu dữ liệu trong `types.ts` khớp `models.py` (`StoryExtras` thêm `memories`, `pending`, `unprocessed_turns`, `memory_search`, `summary`; `MemoryItem`, `DominantEmotion`; `StoryOut.dominant_emotion`, `StoryOut.location` là tuỳ chọn vì server cũ chưa gửi). Client mới: `api.forgetMemory(storyId, memoryId)` (DELETE, chấp nhận 204), `api.rebuildStoryState(storyId)` → `{queued}`. Mọi đường đọc `/extras` đi qua `chatLogic.normalizeExtras` (đọc phòng thủ, tối đa 3 gợi ý, 50 ký ức, bỏ mục không có id/chữ).

- **`useStoryExtras`** (`pages/chat/useStoryExtras.ts` + `extrasPoller.ts` thuần, có test giờ giả): gọi lại khi một lượt kết thúc (xong hoặc Dừng) và sau mỗi thao tác tin (tạo lại, lật phiên bản, sửa, xoá, thích/chê). Khi `pending` thì hỏi lại mỗi 2 giây; không hỏi khi tab ẩn (hiện lại thì hỏi ngay), không hỏi khi đang stream (worker cũng chờ), dừng khi rời trang; chỉ câu trả lời mới nhất được dùng; lỗi thì giữ dữ liệu cũ và ngừng hỏi đến lần làm mới sau. Gợi ý cũ bị bỏ ngay khi một lượt mới bắt đầu.
- **Ngăn cảm xúc** (`HeartDrawer.tsx`, chữ trong `memoryLogic.ts`): thẻ "Chỉ dẫn diễn xuất" (`relationship.directive`); 6 `Meter` màu DESIGN.md §3.3 (`transition-[width] duration-500`, tắt khi reduced-motion); "Cảnh" (Nơi chốn, Thời gian); "Ký ức": dòng trạng thái "Đang ghi nhớ lượt vừa rồi…" (hoặc "Đang đọc lại story, còn N lượt…") khi `pending`, khối mời "Story này có N lượt chưa được ghi nhớ." + nút "Đọc lại story" khi `unprocessed_turns > 0` và không pending, danh sách ký ức với nhãn nhỏ `Badge` "Sự kiện" (neutral) / "Điều đã biết" (gold, kèm "về {subject}"), nút "Quên" hỏi lại ngay trong dòng ("Quên sự kiện này? {Tên} sẽ không nhắc lại nữa." · Giữ lại / Quên; focus chuyển theo), tóm tắt tự động trong `<details>` "Tóm tắt những lượt cũ"; "Wiki đã mở khoá" giữ trạng thái rỗng (Phase 4); dòng cuối "Tìm ký ức theo từ khoá" / "Tìm ký ức theo nghĩa (bge-m3)". Quên không lạc quan: xoá trên server xong mới bỏ dòng, lỗi hiện ngay dưới dòng; 404 coi như đã quên.
- **Gợi ý trả lời** (`QuickReplies.tsx`, `visibleQuickReplies`): tối đa 3 chip trên ô nhập, cuộn ngang (snap, `scroll-px-4` để chip đầu thẳng hàng ô nhập), 44px trên điện thoại / 36px từ 640px, nền `surface-2` (Pressed Linen). Chạm là gửi bằng đúng đường gửi của ô nhập (`Composer.sendText`), không mở bàn phím. Ẩn khi đang sinh, khi ô nhập có chữ, khi không có gợi ý; không có khung giả lúc chờ.
- **Header chat**: dòng phụ = vai trò (vàng) · "nơi chốn · thời gian" (hoặc tiêu đề story). Sửa lỗi cắt chữ trên desktop: hàng header rộng 960px từ 1024px (cột đọc vẫn 720px), khối tên `flex-1`, vai trò tối đa 45% và cảnh chiếm phần còn lại, mỗi phần tự cắt "…"; trên điện thoại khi có cảnh thì chỉ hiện cảnh (vai trò vẫn trong tooltip và ở hub).
- **Thẻ story ở hub**: chip cảm xúc nổi bật với icon tim đặc màu `emo-*` ("Thương mến 91%", không emoji) và chip nơi chốn, lấy thẳng từ `StoryOut` (`storyChips`), chỉ hiện khi có dữ liệu; một hàng, nơi chốn tự cắt. Hub không còn gọi `/extras` cho từng story. Tìm kiếm ở hub tìm cả nơi chốn.
- **Sheet Tài khoản**: khối máy có dòng "Ký ức" ("Tìm theo từ khoá" / "Tìm theo nghĩa, bge-m3"), đọc từ `SystemInfo.memory_search` và `SystemInfo.embed_model` (thêm ở Phase 3, tuỳ chọn để server cũ vẫn chạy). Khi đang tìm theo từ khoá và Ollama chạy, thêm một dòng nhỏ "Muốn nhân vật tìm ký ức theo nghĩa, chạy `ollama pull bge-m3` trong Terminal." Chữ nằm trong `memorySearchRow` (`components/shell/status.ts`, có test).
- **Việc nhỏ Phase 2c**: nhân vật mẫu không còn "Riêng tư" (`explore/logic.creditLine` / `privateLabelFor`, dùng ở Studio danh sách và editor; Khám phá vốn không hiện); profile bỏ chữ "Riêng tư" lặp ở dòng trên lưới ("Nhân vật bạn tạo, chỉ nằm trên máy này."), nhãn trên từng ô giữ nguyên; New Story với `?card=`: lưới thu về một dòng nhân vật đã chọn + "Đổi nhân vật" (44px trên điện thoại), chọn lại trong lưới thì thu về một dòng, đổi `?card=` cũng thu lại; `detailToText` giữ vị trí lỗi (`loc` bỏ tiền tố `body/query/path`: "Dữ liệu không hợp lệ: handle: …", có test); `Chip` giữ cỡ icon khi chữ bị cắt.
- **Kiểm tra**: `npm test` (183 test), `typecheck`, `build`; `lint.mjs --app frontend/src` 0 FAIL, 5 WARN như trước. Ảnh chụp headless (390x844, 1280x860, hai theme) trên DB demo tạm, qua một proxy thêm dữ liệu Phase 3 mẫu: chat, ngăn cảm xúc (đủ và đang pending), hub, tạo story, Studio; luồng: hỏi lại mỗi 2 giây khi pending, dừng khi tab ẩn, hỏi ngay khi hiện lại, Quên (xác nhận rồi bớt một dòng).

## 15. Phase 3b: góp ý sau khi dùng thử (fe, 2026-11-13)

Đặc tả: `docs/phase3.md` §10. Mục này thay một phần §6.2 (mục 5 và 6), §6.3 (dòng cách tìm ký ức), §6.6 và §14 (dòng "Ký ức", gợi ý tự hiện).

**Thành phần mới (dùng lại, đừng viết lại):**

```ts
<Disclosure title hint? open onToggle children />   // components/ui: hàng 44px có chevron, aria-expanded/controls; nội dung chỉ render khi mở
<ErrorDetails technical />                           // components/ui: <details> "Chi tiết" (44px trên điện thoại), chữ kỹ thuật đã qua plainMessage
<InlineAlert … technical? />                         // thêm "Chi tiết" dưới câu lỗi; Banner truyền qua
<TypingDots />                                       // components/TypingDots: ba chấm nhảy, chỉ để nhìn (aria-hidden)
<LiveStatus text />                                  // components/LiveStatus: role=status sr-only luôn gắn sẵn; đặt/xoá chữ khi bắt đầu/kết thúc
<PlayerStoryTurn text pending? />                    // components/Prose: lượt người chơi ở Story
useAdvancedTools(): [boolean, (on) => void]          // hooks: "lyris.advanced", đồng bộ mọi màn hình và giữa các tab
errorMessage(e) / errorTechnical(e) / friendlyOf(e)  // api/client: câu dễ hiểu / chữ gốc cho "Chi tiết"
```

- CSS mới trong `index.css`:
  - `.typing-bounce`: chấm nhảy 1.2 giây. Khi reduced-motion thì đứng yên, độ mờ 0.8.
  - `.turn-highlight`: viền accent 70%, cách 6px. Dùng cho lượt được chọn từ dòng thời gian.
- `ApiError` có thêm `technical` (lấy từ trường `technical` của body lỗi; lỗi mạng cũng có `technical` riêng). Sự kiện SSE `error` cũng đọc `technical`.
- Tham số chỉ để chụp ảnh: `?open=events` mở sheet Sự kiện trong chat, `?open=about` mở thẳng trang Giới thiệu của sheet Tài khoản.

**Màn hình:**

- **Ô nhập.** Hàng gồm "+" (44px, icon ghost, xoay 45° khi mở), ô nhập, rồi nút gửi.
  - Placeholder ngắn lại cho vừa một dòng trên điện thoại: "Lời nói, \*hành động\*…" / "Nhắn tin…". Nhãn đầy đủ vẫn ở `aria-label`.
  - Menu: `bg-surface`, viền `line`, `shadow-float` (vì nó nổi), bo `rounded-card`. Mỗi mục cao 56px; icon ghost (không đặt trong ô màu); nhãn 15px; dòng phụ 13px `muted`. Mục chưa có thì dùng `Badge` "Sắp có".
  - Vùng gợi ý: hàng "Gợi ý cho bạn" (13px `muted`) + "Gợi ý khác" (ghost, RefreshCw) + nút đóng, rồi `QuickReplies` như §14. Chữ gợi ý hiện qua `InlineText`.
- **Sheet "Sự kiện".**
  - `Modal md`: sheet từ dưới trên điện thoại. Hai tab vẽ giống tab của Studio (gạch dưới màu `fg`); phím mũi tên, Home, End chuyển tab.
  - Mỗi mục là một nút cả khối (nền `surface-2` khi hover hoặc focus), có chữ ẩn "Đi tới lượt này." cho screen reader.
  - Chip cảm xúc là `Chip sm` với `dotColor` lấy từ `var(--color-emo-*)`. Chữ vẫn màu mực, không tô màu theo cảm xúc (§11.1).
- **Lượt người chơi ở Story.**
  - Cột căn phải, rộng tối đa 85%. Avatar persona 28px ở góc trên phải.
  - Lời thoại: `bg-user-gradient border-user-border text-user-fg rounded-card`, Be Vietnam Pro 16px, độ đậm vừa.
  - Dẫn truyện và hành động: 16px nghiêng, màu `muted`, không khung, giống dẫn truyện của nhân vật.
  - Gradient vẫn chỉ nằm ở bong bóng người chơi, đúng chỗ đã cho phép ở §10.
- **Sheet Tài khoản.**
  - Mục "Nâng cao" mở ra hai phần: "Máy MacBook M2" (giữ như §6.6) và "Công cụ" (`Toggle` "Công cụ nâng cao").
  - Link "Giới thiệu & bản quyền ảnh" là chữ 13px gạch chân, nằm giữa, cao 44px.
  - Trang Giới thiệu thay nội dung ngay trong sheet: tiêu đề sheet đổi, có nút "‹ Tài khoản" để quay lại, focus đi theo khi chuyển qua lại.
- **Studio.** Khi công cụ nâng cao tắt:
  - bỏ tab "Xem trước" trên điện thoại;
  - bỏ thanh tab bên phải trên desktop, chỉ còn Chat thử;
  - bỏ dòng thời gian sinh và tốc độ token của chat thử.
- **Đổi câu chữ** (không còn "model", "prompt", "Ollama" ngoài Nâng cao):
  - ghi chú người tạo, nhãn card, gợi ý persona, hộp AI viết nháp;
  - cảnh báo ngôn ngữ khi tạo story và trong thiết lập story;
  - cảnh báo thiếu Thought trong lời mở đầu;
  - tooltip và `aria-label` của avatar ở header hub.

**Kiểm tra:**

- `npm test` (219 test, trước đợt này 190), `typecheck`, `build`.
- `lint.mjs --app frontend/src`: 0 FAIL, 7 WARN. Các WARN gồm bóng, `padStart` của giờ, gạch ngang, như trước; thêm `padStart` của giờ trong `eventsLogic`. Emoji trong test viết bằng `\u{…}`.
- Ảnh chụp headless (390x844, 1280x860, hai theme) trên DB demo tạm, backend ở cổng 8041 với Ollama cổng chết. Riêng gợi ý và luồng stream được giả lập bằng cách vá `fetch` trong trang. Đã chụp:
  - menu "+";
  - gợi ý: đang nghĩ, có kết quả, lỗi kèm "Chi tiết";
  - Sự kiện: hai tab, chạm một mục rồi cuộn tới lượt đó và viền sáng;
  - Tài khoản, Nâng cao, Giới thiệu;
  - ngăn cảm xúc ở trạng thái mời đọc lại;
  - thiết lập story, Khám phá, Studio;
  - ba chấm ở Story và DM, có và không có reduced-motion.

  Không có lỗi console.

## 16. Hồ sơ nhân vật (fe, 2026-11-13)

Góp ý của người dùng: bấm vào nhân vật thì chỉ mở hồ sơ (chỉ xem, không phải form sửa), CTA là "Bước vào câu chuyện", chọn persona sau khi bấm CTA, xưng hô và các thiết lập nằm ở tab phụ, phần nhân vật to ra như một trang profile. Mục này thay một phần §6.4 (thẻ nhân vật, hero) và bỏ màn hình tạo story riêng.

**Route** (`lib/router.ts`, có test):
- `#/character/<cardId>`: card của người dùng (kể cả mẫu đã cài). `#/character/template/<slug>`: mẫu chưa cài; nếu mẫu đã cài thì trang tự `replaceRoute` sang `#/character/<id>` (giữ sheet đang mở).
- `?start=1` mở sẵn sheet "Bước vào câu chuyện", rồi trang bỏ cờ này khỏi hash (tải lại hoặc Back không mở lại). App đặt `key` theo nhân vật, không theo cờ, nên bỏ cờ không dựng lại trang.
- `characterRoute(id, start?)`, `templateRoute(slug, start?)`, `legacyRedirect(route)`.
- `#/new-story?card=<id>` (link cũ) → `#/character/<id>?start=1`. `#/new-story` không card → `#/explore`. `NewStoryPage.tsx` đã xoá: phần thiết lập story chuyển vào sheet.
- Thanh tab ẩn như mọi trang con (giống `#/me`); nút quay lại về Khám phá.

**Ai mở hồ sơ:**
- Khám phá: chạm thẻ nhân vật hoặc thân thẻ nổi bật → hồ sơ. Nút "Bước vào câu chuyện" của thẻ nổi bật → hồ sơ kèm sheet. Khám phá không còn tự cài mẫu (`explore/logic.itemRoute`, `templateEntryRoute`).
- Tab "Nhân vật" của `#/me`: ô nhân vật mở hồ sơ, không còn mở editor.
- Studio vẫn là chỗ làm việc của người tạo: danh sách mở editor; nút "Mở story" ở danh sách và "Mở story mới" trong editor → hồ sơ kèm sheet.
- Nút "Story mới" ở hub → Khám phá.

**Trang** (`pages/character/CharacterPage.tsx`, chữ và dữ liệu trong `pages/character/logic.ts`, có test):
- Ảnh lớn 4:5 (avatar card, không có thì ảnh bối cảnh của mẫu, không có nữa thì chữ cái đầu), `components/CharacterPicture.tsx` dùng chung với Khám phá. Điện thoại: ảnh trên cùng. Từ 768px: hai cột, ảnh trái (dính khi cuộn), nội dung phải, khung 960px (`SubpageHeader width="medium"`).
- Tên bằng `font-brand` nghiêng 36-40px (ngoại lệ có chủ đích của §10, theo DESIGN.md §4 "special headings"), vai trò màu `accent-2`, dòng tác giả ("bởi @handle" / "Mẫu của Lyris"), tag + vibe của mẫu là `Chip` tĩnh.
- Link nhỏ "Sửa nhân vật" (ghost, 44px) → `#/studio/<id>`, chỉ với card của người dùng, không với mẫu.
- "Lời nói đặc trưng": 2-3 thẻ trích dẫn giống thẻ thoại Story (`bg-surface rounded-card`, Be Vietnam Pro 16px).
- Tab "Giới thiệu" (mặc định): Đôi nét, Tính cách, Ngoại hình, Hoàn cảnh, Điều mong muốn, Bối cảnh; `{{char}}` thành tên, `{{user}}` thành "bạn". **Không bao giờ hiện bí mật.**
- Tab "Thiết lập" (chỉ đọc, danh sách `dl`): Xưng hô (tự xưng, gọi bạn là, tên gọi thân mật, với người khác); Giọng kể (văn phong, ngôn ngữ, giới tính, đại từ dẫn truyện, cách nói); "Cảm xúc ban đầu" (6 `Meter` màu §3.3) khi card có `extensions.lyris.initial_relationship`.
- Tab: `role=tablist`, `aria-selected`, phím mũi tên/Home/End.
- "Story của bạn với <tên>": story có card này, mới nhất trước, chạm → chat.
- Không có ô nhập hay khung trông như sửa được.
- Hành động: điện thoại là thanh dính đáy (trên safe area) với "Bước vào câu chuyện" (primary) và "Tiếp tục story" (story mới nhất, nếu có). Desktop: hai nút nằm trong cột phải.
- Không tìm thấy (404 hoặc slug lạ): khung rỗng "Không tìm thấy nhân vật này…" + "Về Khám phá". Lỗi khác: `InlineAlert` kèm "Chi tiết".

**Sheet "Chọn persona"** (`pages/character/StartStorySheet.tsx`, logic thuần `startLogic.ts` có test): `Modal` (sheet từ dưới trên điện thoại).
- Danh sách persona là radio thật (phím mũi tên), có avatar; persona mặc định chọn sẵn.
- "Tạo persona mới" (form nhanh, tự mở khi chưa có persona nào) và link "Quản lý persona".
- `Disclosure` "Tuỳ chỉnh story" (đóng sẵn): tiêu đề, bối cảnh, lời mở đầu (kèm xem trước), ngôn ngữ, chế độ Story/DM, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, kiểu suy nghĩ. Giá trị đầu lấy từ `GET /api/stories/defaults`, đổi persona thì tải lại.
- Nút "Bước vào câu chuyện". Không mở "Tuỳ chỉnh story" thì chỉ gửi `card_id` và `persona_id`, server tự điền mặc định như cũ.
- Mẫu chưa cài: chỉ cài khi thật cần id, tức khi mở "Tuỳ chỉnh story" hoặc khi bấm bắt đầu. Tạo story xong → `#/chat/<id>`. Lỗi viết bằng lời thường, có "Chi tiết".

**Lời nói đặc trưng:** trường tuỳ chọn `extensions.lyris.signature_lines: string[]`, tối đa 3 dòng, mỗi dòng ≤ 140 ký tự.
- Studio: ô "Lời nói đặc trưng (tuỳ chọn)" dưới "Cách nói", mỗi dòng một câu.
  - Khi đang gõ, giữ nguyên các dòng như người dùng nhập. Khi lưu, bỏ ngoặc bao, dòng rỗng và dòng trùng (`lib/cardForm.prepareForSave`).
  - Hơn 3 dòng hoặc một dòng dài quá 140 ký tự thì chặn lưu (`validateCard`).
- Backend: `routes_studio.validate_card` làm sạch dễ dãi (`clean_signature_lines`): giữ chuỗi, cắt 140 ký tự, tối đa 3 dòng, không phải list thì bỏ khoá. Không báo lỗi. Export/import Card V2 giữ nguyên (nằm trong `extensions.lyris.extensions`).
- Card không có trường này thì `lib/signatureLines.pickSignatureLines` tự chọn:
  - lấy lời thoại của nhân vật trong ví dụ thoại (bỏ dòng của `{{user}}`, bỏ nhãn người nói, Thought, `*hành động*`);
  - thiếu thì lấy lời trong ngoặc ở lời mở đầu, chỉ khi đoạn đó nói về nhân vật (có tên, hoặc đứng ngay sau đoạn có tên, hoặc mở đầu bằng đại từ);
  - chọn các câu khác nhau, ≥ 3 chữ, dài gần 70 ký tự nhất, giữ thứ tự trong card. Câu dài quá 140 ký tự thì cắt ở cuối câu.
- AI viết nháp chưa sinh trường này (để không đổi prompt nháp); ví dụ thoại đã đủ cho phần tự chọn.

**Kiểm tra:**
- `npm test`: 259 test.
- `typecheck`, `build`.
- `pytest`: thêm `tests/test_signature_lines.py`.
- `lint.mjs --app`: 0 FAIL, 7 WARN (như trước).
- `inspect.mjs --app` trên hồ sơ, hai theme: 0 FAIL, chỉ WARN `palette-cream`.
- Đi luồng trên Chrome headless (390x844, 1280x860, hai theme), DB demo tạm:
  - Khám phá → hồ sơ (card mẫu đã cài, card tự tạo, mẫu chưa cài) → hai tab → sheet → "Tuỳ chỉnh story" (mẫu được cài lúc này) → tạo story → vào chat;
  - CTA của thẻ nổi bật mở hồ sơ kèm sheet; `#/new-story?card=4` chuyển hướng và mở sheet;
  - Studio vẫn mở editor; `#/character/999` báo không tìm thấy.

## 17. Phase 4: lorebook và tuỳ chọn suy nghĩ (fe, 2026-11-14)

Đặc tả: `docs/phase4.md` §9-§13. Backend đã xong trước đợt này. Mục này ghi phần giao diện. Trên màn hình không có chữ "lore", "keys", "known_by", "token" (trừ khi bật công cụ nâng cao): dùng "Thế giới", "Mục thế giới", "Từ khoá gợi nhớ", "Ai biết điều này".

**Thành phần mới (dùng lại, đừng viết lại):**

```ts
ShowThoughtsContext                       // components/showThoughts.ts: true mặc định; ChatPage đặt theo Story.show_thoughts
<StoryReply segments streaming? showThoughts? />   // components/Prose: tắt thì không render thẻ suy nghĩ
visibleBlocks(blocks, showThoughts), onlyHiddenThoughts(blocks, showThoughts)   // lib/storyBlocks
showThoughtsOf(story), SHOW_THOUGHTS_LABEL, showThoughtsHint(name)               // lib/storyOptions
IconEyeOff                                // components/icons (Lucide eye-off)
<LorebookSection cardId characterName extensions onBookUsed />   // pages/studio: phần "Thế giới" của trình sửa
<LoreEntryDialog />, <LoreImportDialog />                        // pages/studio: hộp sửa mục, bước xem trước khi nhập
useStoryLore(storyId, open, signature)   // pages/chat: GET /stories/{id}/lore cho ngăn cảm xúc
api.listLore / createLore / updateLore / patchLore / deleteLore / importLore / importCardBook / getLoreSummary / getStoryLore
```

Chữ và logic thuần nằm trong `pages/studio/loreLogic.ts`, `pages/chat/loreLogic.ts`, `pages/character/logic.ts` (`worldTeaser`), đều có test.

**B. "Đọc suy nghĩ của nhân vật"** (yêu cầu của người dùng: thêm lựa chọn không đọc suy nghĩ)

- Một `Toggle` dùng chung, nhãn "Đọc suy nghĩ của nhân vật", mô tả "Tắt thì thẻ suy nghĩ không hiện trong story. {tên} vẫn nghĩ như thường, chỉ là bạn không đọc thấy." Có ở ba chỗ:
  - sheet "Bước vào câu chuyện", trong "Tuỳ chỉnh story", ngay dưới kiểu suy nghĩ. Xem trước lời mở đầu trong sheet theo công tắc. `createRequest` chỉ gửi `show_thoughts: false` khi tắt; đổi persona giữ lựa chọn này;
  - "Thiết lập story", ngay dưới kiểu suy nghĩ, lưu cùng nút "Lưu" (`settingsPatch` chỉ gửi khi đổi; không hiện câu "Áp dụng từ lượt trả lời sau");
  - menu "Suy nghĩ" trên header chat, trên cùng, lưu ngay (lạc quan, server từ chối thì trả lại; chỉ trả lại đúng khoá của lần lưu đó, nên đổi kiểu suy nghĩ bị từ chối không bật lại "Đọc suy nghĩ" vừa tắt). Lúc đang lưu, công tắc là `aria-disabled` (`Toggle busy`), không `disabled`, để không mất focus bàn phím. Công tắc này không khoá Story/DM và dùng được cả khi nhân vật đang trả lời (chỉ là cách hiển thị). Khi tắt: ẩn "Luôn hiện suy nghĩ", kiểu suy nghĩ vẫn chọn được kèm câu "Nhân vật vẫn nghĩ trong lòng theo kiểu này, chỉ là bạn không đọc thấy."; nút header đổi sang `IconEyeOff`, `aria-label` "Suy nghĩ (đang ẩn)".
- Khi tắt, thẻ suy nghĩ **không có trong DOM** (không phải bản làm mờ): Story, DM (`ThoughtCard compact`), và lúc stream. Lúc stream, khối hiện được cuối cùng mang con trỏ; lượt mở đầu bằng suy nghĩ thì giữ ba chấm tới khi có dẫn truyện hoặc lời thoại. Lượt chỉ có suy nghĩ: một dòng 13px `muted` "Lượt này chỉ có suy nghĩ của {tên}." và hàng thao tác vẫn ở đó (DM: dòng này thay cho bong bóng "…"). Ô sửa một lượt của nhân vật vẫn chứa nguyên văn kèm `[Thought: …]`, trên ô có dòng "Bản sửa có cả suy nghĩ của {tên}."
- Chat thử ở Studio và các bản xem trước không đổi (context mặc định là true).

**A. Studio: phần "Thế giới"** (`id="sec-world"`, trước "Ghi chú của người tạo"; truyền vào `CardForm` qua prop `world`)

- Gợi ý dưới tiêu đề nói rõ các mục được lưu ngay, không cần bấm Lưu nhân vật.
- Trạng thái:
  - card chưa lưu: "Lưu nhân vật trước, rồi thêm thế giới cho {tên}.";
  - đang tải: 3 khung 56px;
  - lỗi: `InlineAlert` "Không tải được thế giới của {tên}." + "Thử lại" + "Chi tiết";
  - rỗng: `EmptyState` với "Thêm mục" (secondary) và "Nhập từ file" (ghost);
  - card cũ còn book Card V2: `Notice` "Card này có sẵn {n} mục thế giới từ file gốc." + "Dùng các mục này" (xem trước như nhập file). Dùng xong thì trình sửa bỏ book khỏi bản card trong bộ nhớ, để lần Lưu sau không gửi lại. Bấm "Lưu nhân vật" mà chưa bấm "Dùng các mục này" thì server cũng chuyển book thành mục; danh sách tải lại ngay.
- Có mục: hàng công cụ (ô "Tìm trong thế giới" khi hơn 12 mục; tìm không phân biệt hoa thường, giữ dấu; ô ẩn đi thì từ khoá thôi lọc), rồi 3 nhóm `Disclosure` có số đếm ("Chuyện và bí mật" mở sẵn, "Người xung quanh", "Nơi chốn"). Khi đang tìm, mọi nhóm mở.
- Một hàng: cả hàng là nút mở hộp sửa (cao từ 44px); tên 15px/500; `Badge` "Mọi người" / "Chỉ {tên}" (accent) / "Chỉ bạn" (gold) / "Người khác"; dòng phụ "Gợi nhớ khi nhắc: a, b, c…" hoặc "Chưa có từ khoá gợi nhớ" màu `warn`. Bên phải là công tắc không nhãn hiện, `aria-label` "Dùng mục {tên mục}", đổi lạc quan; lỗi thì trả lại và báo một dòng dưới hàng. "Đã sửa" chỉ hiện khi bật công cụ nâng cao.
- Hộp sửa (`Modal md`, sheet từ dưới trên điện thoại): "Tên mục", "Loại", "Từ khoá gợi nhớ" (cảnh báo từng khoá ngay dưới ô: khoá một chữ, khoá là tên nhân vật), "Ai biết điều này" (thêm lựa chọn chỉ đọc "Chỉ {người khác} biết" khi mục đang như vậy), "Nội dung" (nút "+ {{user}}"; cảnh báo chữ như "nguyên tác" khi nhân vật được đọc mục; "Dài quá thì {tên} chỉ đọc phần đầu." khi quá 450 ký tự). Nâng cao: độ ưu tiên, danh sách "người biết" thô, nguồn, slug, ước lượng. Chân hộp: "Xoá mục" (hỏi lại ngay trong chân hộp, focus vào "Giữ lại") · "Huỷ" · "Lưu". Lỗi server hiện trong hộp, hộp vẫn mở.
- Nhập file: input ẩn `accept=".md,.markdown,.txt,text/markdown,text/plain"`; quá 500 KB thì báo ngay trong hộp, không gửi. Hộp "Nhập thế giới từ {tên file}": "Đang đọc file…", rồi các dòng số liệu, công tắc "Xoá N mục không còn trong file" (chỉ khi có; bật thì xem trước lại), khung "Chỉ bạn biết: …", dòng nhắc đọc lại, ghi chú và cảnh báo của server (bỏ câu đã hiện ở trên), `Disclosure` "Xem các mục" và "Xem các câu đã bỏ". "Nhập" ghi thật, đóng hộp, tải lại danh sách, hiện "Đã nhập thế giới." (thấy được và qua `LiveStatus`). Không có gì mới: chỉ "File này đã được nhập, không có gì mới." (kèm "Bỏ qua N mục bạn đã xoá." nếu có) và nút "Đóng". Lỗi: `InlineAlert` + "Chi tiết", nút "Chọn file khác".
- `#/studio/<id>?section=world` cuộn tới phần này rồi bỏ cờ khỏi địa chỉ (link "Thêm trong Studio" của ngăn cảm xúc).
- Danh sách Studio bỏ thẻ "Wiki & Lorebook" (`describeLoreStatus` và test của nó đã xoá). Xem trước prompt (nâng cao) có dòng "D · Thế giới"; khi có D, message user cuối có nhãn "Khối D + lượt người chơi + khối F".

**A. Ngăn "Cảm xúc & ký ức": "Thế giới đã mở khoá"** (thay "Wiki đã mở khoá")

- Tải khi ngăn mở; đang mở mà chữ ký `lore_count|lore_tags` đổi thì tải lại; đóng ngăn thì giữ dữ liệu cũ. `normalizeExtras` đọc `lore_available`, `lore_count` phòng thủ; `lore_tags` tối đa 50.
- Mục mọi người biết và mục "Chỉ bạn biết" (`Badge` gold): hàng gập có `IconSparkles` màu `accent-2`; mở ra là nội dung (`font-story` 14px) và nút "Xem lúc được nhắc tới lần đầu". Nút này đóng ngăn rồi nhảy tới lượt bằng `jumpPlan` như sheet Sự kiện (chế độ của lượt lấy từ danh sách tin đã tải). Không in số lượt.
- "Điều {tên} giữ trong lòng": thẻ như `ThoughtCard`, tên và nội dung bị làm mờ, "Chạm để đọc". Chữ thật chỉ có trong DOM khi đã mở (lúc mờ là một câu thay thế, `aria-hidden`). "Luôn hiện suy nghĩ" cũng bỏ mờ ở đây. Story tắt "Đọc suy nghĩ của nhân vật" thì cả nhóm biến mất, không còn số đếm.
- Câu trạng thái: "{tên} chưa có sổ thế giới." (kèm "Thêm trong Studio" khi card là của bạn), "Chưa mở khoá điều gì. Khi story nhắc tới người, nơi chốn hay chuyện cũ trong thế giới của {tên}, chúng sẽ hiện ở đây.", lỗi "Chưa tải được thế giới." + "Thử lại" + "Chi tiết". Đang tải lần đầu: hai khung pill 160×28.

**A. Hồ sơ nhân vật:** cuối tab "Giới thiệu" có phần "Thế giới" khi card có mục: "{N} điều về thế giới của {tên}.", rồi "Người quanh {tên}" và "Nơi chốn" là `Chip` tĩnh, tối đa 8 tên mỗi nhóm rồi "+N". Không có nội dung, không có tên mục loại "Chuyện và bí mật". Lỗi hoặc 404 (mẫu chưa cài) thì ẩn phần này.

**Kiểm tra:**
- `npm test`: 297 test (trước đợt này 267; thêm 31, bỏ 1 test của `describeLoreStatus`). `typecheck`, `build` qua.
- `lint.mjs --app frontend/src`: 0 FAIL, 7 WARN (như trước).
- Chạy thử trên DB demo tạm trong `scratchpad/p4/fe/`: backend ở cổng 8063 (Ollama trỏ cổng chết) và Vite ở 8068. Chrome headless 390×844 và 1280×860, hai theme. Đã chạy qua:
  - Studio: nhập `worlds/luc-bac-uyen/world.md` (xem trước có "Chỉ bạn biết: Hứa Tri Ý…", "Xem các câu đã bỏ"; nhập; xoá hết rồi nhập lại thì "Bỏ qua 27 mục bạn đã xoá", "không có gì mới");
  - bật/tắt một mục, sửa tên (mục thành "đã sửa"), xoá, thêm mục mới với khoá "mẹ" và chữ "nguyên tác" (hiện hai cảnh báo); card chưa có mục;
  - ngăn cảm xúc với dữ liệu giả (vá `fetch`): mục mọi người biết, chỉ bạn biết, bí mật (mờ, chạm để đọc), rồi tắt suy nghĩ thì nhóm bí mật biến mất;
  - Story có Thought: menu header bật/tắt, thiết lập story, sheet bắt đầu; stream giả (vá `fetch`) có Thought ở đầu (ba chấm) và ở cuối (con trỏ nằm ở lời thoại);
  - hồ sơ nhân vật có phần "Thế giới".

  Không có lỗi console, không có request lỗi ngoài 422 cố ý.

## 18. Phase 4b: đăng nhập và tài khoản (fe, 2026-11-14)

Đặc tả: `docs/auth.md` §7 (và §12, §13 mục 34-48 cho chỗ khác thiết kế). Backend xong ở hai giai đoạn trước. Trên màn hình không có chữ "token", "cookie", "phiên", "model", "Ollama", "HTTP"; dùng "đăng nhập", "thiết bị", "story".

**Thành phần và hàm mới (dùng lại, đừng viết lại):**

```ts
// lib (thuần, có test)
gateOf(state, route) -> "setup" | "login" | "signup" | "forceChange" | "app"      // lib/auth
safeNext / rememberNext / takeNext ("lyris.next"), isAccountDataKey, clearAccountData, accountSwitch,
signalsAuth(path, status, code), AUTH_EVENT = "lyris:auth", ACCOUNT_KEY = "lyris.accountId"
normalizeCode, formatInvite, groupCode, inviteLink                                // lib/inviteCode (cùng bảng ca thử với pytest)
passwordError, confirmError, newPasswordErrors, PASSWORD_* (chữ §7.4)             // lib/passwordRules
copyText(text)                                                                    // lib/clipboard (Clipboard API, không thì execCommand)
// store
useAuth(), useAuthAccount(), useIsOwner(), applyAuth(state, {next, navigate}), refreshAuth(), signOut(everywhere?), startAuth()   // hooks/useAuth
// UI
<AuthLayout title intro?>  <PasswordField …TextField trừ type/>  <AuthLink lead href>  <AuthSplash error? onRetry?>   // pages/auth
<ChangePasswordForm currentLabel submitLabel handle onDone? secondary? />                                           // pages/auth
<TextField trailing?: ReactNode />        // components/ui: một nút nhỏ ở đầu phải trong ô (Hiện/Ẩn)
<PublicPreviewDialog open cardId onClose />   // pages/character: "Người khác thấy gì"
api.authMe / setupOwner / login / signup / logout / logoutAll / changePassword,
api.listAdminAccounts / resetAccountPassword / disableAccount / enableAccount / listInvites / createInvite / revokeInvite,
api.listPublicCards / getPublicCard;  ApiError.code;  CSRF_HEADER
```

**Client (`api/client.ts`).** Mọi request (`request`, `upload`, `streamChat`) gửi `X-Lyris: 1` và `credentials: "same-origin"`. `ApiError` có thêm `code` (đọc từ body lỗi). 401, 403 `password_change_required` và 409 `setup_required` (trừ các route `/auth/*`) phát `lyris:auth`; cổng hỏi lại `/auth/me`. Câu dự phòng khi body không có chữ: 401 "Bạn cần đăng nhập.", 403 "Bạn không làm được việc này. Hãy tải lại trang.", 429 "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại.". Sự kiện SSE `waiting` được nhận.

**Cổng (`App.tsx`).** Mở app: một lần `/api/auth/me` trước khi vẽ route; trong lúc chờ là nền `bg` + wordmark (không spinner); backend không trả lời thì một câu thường + "Thử lại". Sau đó: `setup_required` → trang thiết lập (bất kể hash); chưa đăng nhập → `#/login` (hash đang mở được nhớ ở `sessionStorage["lyris.next"]`, đăng nhập xong quay lại; `#/signup` giữ nguyên); `must_change_password` → màn đổi mật khẩu bắt buộc; còn lại như cũ, `#/login`/`#/signup` khi đã đăng nhập về hub, `#/admin` của thành viên về hub.

**Dữ liệu tạm theo tài khoản.** `localStorage["lyris.accountId"]` nhớ ai dùng trình duyệt này. Đăng xuất, đăng xuất mọi thiết bị, hay một tài khoản khác đăng nhập (cùng tab hoặc tab khác, qua sự kiện `storage`): xoá `lyris.draft.*`, `lyris.lastStoryId`, `lyris.studio.*`, `lyris.next` ở cả `localStorage` và `sessionStorage`, đặt hash về `#/` (hoặc `#/login` khi đăng xuất) rồi `location.reload()`. Giữ `lyris.theme`, `lyris.advanced`, `lyris.revealThoughts`. Khoá mới chứa dữ liệu của tài khoản phải thêm vào `isAccountDataKey` (ghi chú nằm ngay đó).

**Màn hình (390px trước; cột giữa tối đa 400px, lề 20px; wordmark 34 + tagline DESIGN.md 14px `muted`; h1 24px):**
- **Đăng nhập** (`pages/auth/LoginPage`): "Tên đăng nhập" (placeholder "@handle", `autocomplete=username`, không viết hoa/tự sửa), "Mật khẩu" với nút ghost "Hiện"/"Ẩn" trong ô, nút primary cả hàng, lỗi của server là `InlineAlert` dưới nút. Bị đăng xuất giữa chừng: `InlineAlert` info "Bạn đã bị đăng xuất. Hãy đăng nhập lại." ở đầu. Cuối: "Có mã mời? **Tạo tài khoản**" và "Quên mật khẩu? Hãy nhờ chủ máy đặt lại." (chữ thường).
- **Tạo tài khoản** (`SignupPage`): câu riêng tư của §7.3; "Mã mời" (điền từ `?code=`, rồi `replaceState` về `#/signup`; `autocapitalize=characters`), "Tên hiển thị", "Tên đăng nhập" (luật handle kiểm ngay khi rời ô, như trang profile), "Mật khẩu" (hint "Ít nhất 8 ký tự."), "Nhập lại mật khẩu". Lỗi server có tên trường (mã mời, handle trùng, mật khẩu) hiện dưới đúng ô (`authFieldOf`). Xong: hub của thành viên mới (khối trống "Chưa có story nào…" + "Mở Khám phá").
- **Thiết lập chủ máy** (`SetupPage`): "Mã thiết lập" (hint "12 ký tự, ví dụ 7KQ2-M9XD-4TPA."), mật khẩu mới + nhập lại; DB mới tinh thì thêm tên và handle. Nút "Lưu và vào Lyris". Không bao giờ hiện handle chủ máy.
- **Đổi mật khẩu bắt buộc** (`ForcePasswordPage`): "Mật khẩu tạm", "Mật khẩu mới", "Nhập lại mật khẩu"; primary "Lưu mật khẩu", ghost "Đăng xuất".
- **Sheet Tài khoản**: dưới khối tài khoản hai nút ghost "Đổi mật khẩu" (mở màn đổi mật khẩu ngay trong sheet, nút "‹ Tài khoản"; lưu xong về màn chính với dòng "Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất.") và, với chủ máy, "Quản lý tài khoản". Trước link "Giới thiệu": secondary "Đăng xuất", ghost "Đăng xuất mọi thiết bị" (hỏi lại ngay trong sheet: "Mọi điện thoại và máy tính đang đăng nhập @{handle} sẽ phải đăng nhập lại, kể cả máy này."). Thành viên: "Nâng cao" chỉ còn "Công cụ"; "Thiết lập story" không có chọn model.
- **Quản lý tài khoản** (`pages/admin/AdminPage`, `#/admin`, chữ trong `pages/admin/logic.ts`): header có nút quay lại. "Mã mời": primary "Tạo mã mời" → `Modal sm` ("Ghi chú" hint "Chỉ bạn thấy.", `ChoiceGroup` "Hết hạn sau" 1/7/30 ngày) → mã 20px `tabular-nums` chọn được cả khối, secondary "Sao chép mã", ghost "Sao chép liên kết" (nút đổi chữ thành "Đã sao chép" 2 giây), "Mã chỉ hiện một lần và dùng được một lần."; danh sách "…{hint}" + `Badge` (Còn hiệu lực `ok`; Đã dùng bởi @x / Hết hạn / Đã huỷ `neutral`) + ghi chú · "Hết hạn {ngày}", mã còn hiệu lực có ghost "Huỷ" (xác nhận). "Thành viên": `Avatar` 40, tên, badge "Chủ máy" `gold` / "Tạm khoá" `danger` / "Chờ đổi mật khẩu" `warn`, @handle, "Vào lần cuối {thời gian tương đối} · {n} thiết bị"; nút "…" (trừ hàng chủ máy) mở sheet nhỏ: "Đặt lại mật khẩu" (xác nhận → mật khẩu tạm 20px + "Sao chép" + câu §7.3), "Tạm khoá" (danger, xác nhận) / "Mở khoá". Đang tải: khung xương; lỗi: `InlineAlert` + "Thử lại"; chưa có mã: `EmptyState`.
- **Studio**: trong "Cơ bản", ngay dưới tên/vai trò, khung `surface-2` có `Toggle` "Công khai" và câu mô tả của §7.3 (không hứa "không thấy bí mật"), lưu cùng nút "Lưu". Tắt khi bản đã lưu đang công khai: dòng `warn` "Story mà người khác đã bắt đầu vẫn tiếp tục với {tên} như lúc họ bắt đầu.". Bản đã lưu công khai: ghost "Người khác thấy gì" mở `PublicPreviewDialog`. Ẩn với nhân vật mẫu. Dòng phụ của header ghi "Riêng tư"/"Công khai"; thẻ danh sách Studio có `Badge` "Riêng tư" (neutral) hoặc "Công khai" (accent). Chữ trong `pages/studio/shareLogic.ts`.
- **Khám phá**: phần "Nhân vật được chia sẻ" sau lưới "Nhân vật" (cùng thẻ 4:3, "bởi @handle"), theo bộ lọc cảm xúc; không có thì không hiện gì (`explore/logic.sharedItems`: bỏ card của chính mình, mới sửa trước).
- **Hồ sơ nhân vật**: `getCard` 404 thì `getPublicCard` (`character/logic.cardFromPublic` để các phần cũ dùng lại; phần người khác không nhận được thì tự ẩn). Không có "Sửa nhân vật"; "bởi @handle" là link tới `#/u/{handle}`; sheet "Bước vào câu chuyện" có dòng 13px "Bạn chơi với {tên} như bây giờ. @{handle} sửa nhân vật sau này thì story của bạn không đổi.". Bản sao (header chat giờ là link tới hồ sơ): không có nút bắt đầu, còn "Tiếp tục story".
- **Chat**: khi cổng sinh đầy (SSE `waiting`), dưới ba chấm có dòng 13px `muted` "Có người khác đang trò chuyện. {Tên} sẽ trả lời ngay sau." (Story, DM và chat thử ở Studio; `chatLogic.waitingLine`). Các câu bận khác (409, quá 120 giây) là câu của server, hiện như lỗi thường với "Thử lại".

**Sửa sau phản biện lần 2 (2026-11-14, `docs/auth.md` §13 mục 55-60):**
- `lib/auth`: `rememberNext` gặp hub thì xoá `lyris.next` cũ; `signalsAuth` phát cho 401 của `/auth/change-password` (các route `/auth/*` khác vẫn không); `withAccountProfile(state, account)` (thuần). `hooks/useAuth.syncAuthProfile(account)`, gọi từ `useAccount.setAccount`: đổi @handle/tên/ảnh ở "Sửa profile" thì cổng thấy ngay.
- `lib/leaveGuard` (`allowForcedLeave`, `isForcedLeave`): `resetBrowser` bật trước khi tải lại; `useUnsavedGuard` không hỏi "Rời trang?" khi cờ bật. Trang mới có `beforeunload` riêng phải kiểm cờ này.
- Modal "Mật khẩu tạm" `dismissible={false}`; modal mã mời `dismissible={!sending && !created}` (bí mật chỉ hiện một lần: không đóng bằng chạm nền hay Escape). "Sao chép liên kết" thất bại thì hiện liên kết (13px, khung `surface-2`, `select-all`) dưới hai nút.
- Chạm 44px trên điện thoại: nút "Hiện"/"Ẩn" của `PasswordField` và hai nút xác nhận "Đăng xuất mọi thiết bị" thêm `max-sm:h-11`. Câu "Tạo một persona để bước vào story." ở sheet bắt đầu story. `copyWords.test.ts` quét "câu chuyện" ngoài CTA.
- Server có thể trả 503 `code: "busy"` "Lyris đang bận. Hãy thử lại sau giây lát." ở đăng nhập, tạo tài khoản, thiết lập, đổi/đặt lại mật khẩu (hàng chờ băm đầy); form hiện như lỗi chung.
- `npm test` 358.

**Kiểm tra:**
- `npm test`: 346 test (trước đợt này 309), `typecheck`, `build` qua; `pytest` vẫn 1407 passed, 71 skipped. `lint.mjs --app frontend/src`: 0 FAIL, 8 WARN (thêm một `padStart` của ngày ở `pages/admin/logic.ts`). Test mới: `lib/auth`, `lib/inviteCode` (đọc `inviteCode.cases.json` dùng chung với pytest), `lib/passwordRules`, `lib/router` (3 route mới), `api/client` (header `X-Lyris` + cookie trên mọi kiểu request, `lyris:auth` khi 401 / đổi mật khẩu bắt buộc nhưng không khi form đăng nhập sai hay `owner_only`, `waiting` qua SSE, 429), `pages/auth/logic`, `pages/admin/logic`, `pages/studio/shareLogic`, `explore/logic.sharedItems`, `character/logic.cardFromPublic`, `chatLogic.waitingLine`, `cardForm.isDirty` với `visibility`, nhãn "Công khai" của profile.
- Chạy thật trên bản sao DB demo trong `scratchpad/p4b/fe3/` (backend 8063 `--no-proxy-headers`, Ollama cổng chết, Vite 8068 proxy tới đó): thiết lập chủ máy bằng mã in ra log, tạo mã mời, tạo tài khoản bằng mã viết thường, bật công khai (card mẫu bị 422 đúng câu), thành viên thấy `/public-cards`, `getCard` 404 rồi `/public`, bắt đầu story từ nhân vật công khai (bản sao, `can_start` false), đặt lại mật khẩu (phiên cũ 401, đăng nhập bằng mật khẩu tạm thì 403 `password_change_required`, đổi xong 200), tạm khoá/mở khoá; Chrome headless 390x844 và 1280x860, hai theme: thiết lập chủ máy (DB thứ hai, backend 8064 + Vite 8069, cả khi mở `#/chat/3`), đăng nhập, tạo tài khoản (mã bị bỏ khỏi địa chỉ), Quản lý tài khoản (tạo mã, sao chép, menu thành viên, đặt lại mật khẩu, mật khẩu tạm), màn đổi mật khẩu bắt buộc (đổi xong vào hub), sheet Tài khoản của chủ máy và thành viên, Studio danh sách và trình sửa, Khám phá của thành viên, hồ sơ công khai và hồ sơ bản sao, chat của thành viên. Luồng: đang ở `#/studio` mà chưa đăng nhập thì sang `#/login` và đăng nhập xong quay lại `#/studio`; server xoá phiên giữa chừng thì request sau đưa về đăng nhập với câu "Bạn đã bị đăng xuất"; tài khoản khác đăng nhập trên cùng tab thì bản nháp của người trước bị xoá, theme giữ, tải lại ở hub; thành viên mở `#/admin` về hub mà không gọi `/api/admin`; "Đăng xuất" trong sheet về `#/login` và quên `lyris.accountId`. Không lỗi console, không cuộn ngang, không request lỗi ngoài 404 chủ đích của `getCard` (hồ sơ nhân vật của người khác).

### Lưới Khám phá: ô luôn bằng nhau (người dùng chọn 2026-11-14)
- Mọi ô nhân vật cùng một kích thước ở mọi độ rộng và mọi mục (`GRID = grid-cols-2 / sm:grid-cols-3 / lg:grid-cols-5`, cố định). Hàng cuối thiếu ô thì để trống, không kéo giãn ô cuối sang hai cột, không đổi số cột theo số nhân vật (đã bỏ `desktopColumns` và kiểu ô "wide").
- Các ô trong cùng một hàng cao bằng nhau (`li` là flex, thẻ `a` lấp đầy).
- Nhân vật ở khung nổi bật không lặp lại trong lưới (trừ khi đang lọc theo cảm xúc); khung nổi bật dùng ảnh của nhân vật đã thêm (`heroImageUrl`, `withoutHero`).
