<p align="center">
  <img src="docs/assets/lyris-banner.png" alt="Lyris: Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại" width="820">
</p>

# Lyris

> *Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại.*
> Where the souls of storybook pages step out to warm the real world.

**English** · [Tiếng Việt](#tiếng-việt)

---

## English

### Pitch

Lyris is a Vietnamese-first AI roleplay app.  You pick a character, or write your own in the Studio, step into a story with them, and talk. The AI narrates and plays the character. You alone control your persona. The character remembers what happened, including what you said by text message. Their feelings toward you rise and fall with what you do, and they know only what their world allows them to know. Friends can join with an invite code and get their own private stories.

### The problem

- **Roleplay apps write over the player.** Hosted apps such as WHIF often ignore what the player just wrote, act and speak *for* the player's character, and drift off the scene.
- **Vietnamese is an afterthought.** English-trained roleplay models get Vietnamese forms of address wrong (anh/em, tớ/cậu, ta/ngươi), mix in English or Chinese words, and forget the relationship between two characters.

- **Memory is shallow.** Characters forget names, promises and events after a few dozen turns, and their attitude never changes, whatever the player does.

### Target users

- **Readers of Vietnamese romance web fiction** (ngôn tình, đam mỹ, cổ trang, vườn trường) who want to *live inside* a story rather than read it. Mobile-first, mostly evenings.
- **Writers and character creators** who build characters and whole worlds (side characters, places, secrets, plot hooks) and want them played faithfully.

### Core features

| Area | What it does |
|---|---|
| **Story and DM modes** | Story mode reads like a novel: italic narration, speech in dialogue cards, and the character's inner thoughts as blurred cards you tap to read. DM mode looks like a messaging app. Both share one timeline, so a name given by text is known in the story. |
| **Player stays the author** | The AI never writes your dialogue, actions or decisions. It continues directly from what you wrote. Hidden directions to the character go in `((…))`. Your own speech is written in `"…"`, actions in `*…*`, and other people's words in `*"…"*`. |
| **Six-emotion relationship** | Affection, trust, attraction, possessiveness, fear and aversion (0–100) rise *and fall* with your actions. Jealousy lowers trust, an apology lowers aversion, and small talk barely moves anything. The numbers become acting directions for the character and never appear in the prompt as raw numbers. |
| **Memory** | Rolling scene summaries, long-term memories and facts. Search is by keyword, plus by meaning when an embedding model is present. Regenerating, editing or deleting a turn rolls the state back correctly. |
| **Lorebook** | Each character can carry a world: side characters, places and lore entries, imported from a Markdown `world.md`. Entries are triggered by Vietnamese-aware keywords, with diacritics preserved. Each entry says who knows it: everyone, only the character, or only you. Spoilers that only you know never reach the model. |
| **Character Studio** | Create and edit characters, draft one with AI from a one-line idea, set signature lines, set forms of address, upload an avatar, and import or export Character Card V2. |
| **Explore and profile** | Featured character, vibe filters ("Chữa lành", "Tình đầu"…), equal-size character cards, and a read-only profile with "Bước vào câu chuyện". |
| **On-demand helpers** | A "+" menu in the composer: reply suggestions (only when tapped), an event timeline, and image sending (shell). |
| **Accounts** | Owner and invited members, invite codes, password login with scrypt and HttpOnly sessions, an owner-only admin page, and fully private stories. Characters can be made public; others then play their own private copy. |
| **Fast on modest hardware** | Prompt-cache-aware prompt layout and a background "prefill" of the next turn cut the first-token wait on long stories from ~30–47 s to ~5 s on a 12B model. |
| **No technical noise** | No model names, tokens or server status in the UI. Waiting shows typing dots. Technical settings live behind "Nâng cao". |

### Launch channel and business model *(plan, not yet built)*

**Launch channel**
- **Vietnamese roleplay and web-fiction communities:** Facebook groups, TikTok and Discord servers where WHIF and ngôn tình readers gather.
- **Showcase content:** short clips of story mode and the hand-written worlds that already ship (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương).
- **Creator-led discovery:** writers publish public characters, and their followers come to play them.

**Revenue: a coin economy**
- **Chat costs coins:** every chat turn spends a small number of coins.
- **Buying coins:** users top up coins with money.
- **Earning coins without paying:**
  - **Missions:** daily check-ins, finishing a story arc, unlocking story moments.
  - **Creation:** writing characters and worlds, earning when other users play your public characters.

  This rewards the creators who bring players in.
- **Pricing follows real compute cost:** coin prices would follow measured cost per turn (prompt size, reply length).

### Build, run and access

#### Hardware for local AI

Lyris runs a ~12B-parameter instruction model locally through Ollama, with an 8,192-token context. The model and its cache take about 16 GB.

| | Minimum | Recommended |
|---|---|---|
| Memory for the model | 16 GB unified memory or VRAM, running a smaller model (e.g. `gemma4:e4b`) | 24 GB+ unified memory (Apple Silicon) or a 16 GB+ GPU (NVIDIA) for `gemma4:12b` |
| Disk | ~15 GB (model + app) | 30 GB+ if you add an embedding model or fine-tune later |
| OS | macOS on Apple Silicon (tested), Linux with Ollama (expected to work) | |

Speed scales with memory bandwidth. The first reply after starting the app reads the whole story (tens of seconds). Later turns start in about 5 s thanks to prefill.

#### Software

- [Ollama](https://ollama.com) 0.40+
- Python 3.12 with [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 with npm

#### Steps

```bash
# 1. Model
ollama pull gemma4:12b          # chat model (default)
ollama pull bge-m3              # optional: memory search by meaning

# Recommended Ollama settings (set them for the Ollama server, then restart it):
#   OLLAMA_FLASH_ATTENTION=1  OLLAMA_KV_CACHE_TYPE=q8_0  OLLAMA_NUM_PARALLEL=2
#   On macOS, scripts/ollama-env.sh installs these as a LaunchAgent.

# 2. Backend dependencies
cd backend && uv sync && cd ..

# 3. Run backend (127.0.0.1:8000) and frontend (port 5173) together
bash scripts/dev.sh
```

- **First run:** the terminal prints a one-time **setup code** in a box ("Lyris: đặt mật khẩu cho tài khoản chủ máy"). Open http://localhost:5173, paste the code and choose the owner password. If the box is gone, run `bash scripts/lyris-admin.sh setup-code`.
- **Phone or other devices on the same Wi-Fi:** open the LAN address that `dev.sh` prints (`http://<computer-ip>:5173`) and log in. Use `LYRIS_LAN=0` to keep the app on this computer only. Over plain Wi-Fi, traffic is not encrypted. Remote access over HTTPS (Tailscale) is planned.
- **Inviting someone:** go to Tài khoản → Quản lý tài khoản → Tạo mã mời.
- **Forgot the owner password:** run `bash scripts/lyris-admin.sh reset-password <handle>`.

#### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `LYRIS_CHAT_MODEL` | `gemma4:12b` | Chat model, also used for background extraction and summaries. |
| `LYRIS_NUM_CTX` | `8192` | Context window. Keep one value for all calls, because a change makes Ollama reload the model. |
| `LYRIS_EMBED_MODEL` | `bge-m3` if installed | Memory search by meaning. |
| `LYRIS_CHAT_SLOTS` | `2` | Replies generated at once across all accounts. |
| `LYRIS_DB_PATH` | `data/lyris.db` | SQLite database (one file; back it up). |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server. |

#### Tests

```bash
cd backend && .venv/bin/pytest -q                                  # ~1,400 tests
cd frontend && npm test && npm run typecheck && npm run build      # ~360 tests
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b      # model-behaviour scenarios (needs Ollama)
```

#### Repository map

| Path | Contents |
|---|---|
| `backend/lyris/` | FastAPI app: `api/`, `prompt/` (prompt builder, vi/en templates), `state/` (emotions, extraction), `memory/`, `lore/`, `jobs/` (background worker, prefill), `auth/`, `db/` (SQLite and migrations) |
| `frontend/src/` | React app: `pages/` (explore, character, chat, studio, auth, admin), `components/`, `lib/` |
| `worlds/` | Hand-written character worlds (`card.json` and `world.md`) |
| `harness/` | Model bake-off and behaviour checks |
| `training/` | LoRA fine-tuning experiments (planned phase) |
| `docs/` | Phase designs (`plan.md`, `phase1–4.md`, `auth.md`, `design-impl.md`) |
| `wiki/` | Project wiki: original ideas (`raw/`), features with "Done when" lists, screens, decisions, lessons learned |
| `DESIGN.md` | Design system and UI/UX specification |

### AI-native workflow: how Claude built Lyris

Lyris was built in about three days by one product owner working with **Claude Code** (Claude Opus). The owner wrote the vision, the design spec (`DESIGN.md`), the character worlds and every product decision. Claude wrote almost all of the code, tests and design docs. The owner directed and corrected it in plain Vietnamese.

#### How the work was organised

1. **Plan first, as files.** Claude reviewed and rewrote the original plan into `docs/plan.md`. Each phase starts with a design doc (`docs/phase3.md`, `docs/phase4.md`, `docs/auth.md`) that fixes contracts before any code: tables, API payloads, UI copy and test plan.
2. **Multi-agent workflows for every substantial phase.** One phase is a scripted pipeline of sub-agents:
   - design;
   - an *adversarial critique* that edits the design;
   - backend and frontend implementation;
   - review along 3–4 independent lenses (security, data isolation, cache and performance, UX);
   - an *adversarial verifier* for each finding, which tries to refute it before anyone fixes it;
   - a fix stage with regression tests;
   - an end-to-end smoke test on a copy of real data.

   Phase 4 (lorebook) used 22 agents and Phase 4b (accounts) 23, about two hours each.
3. **Measure on the real model, not in theory.** Claims about speed and model behaviour were tested on the local model with timing tables and Ollama cache logs. Before/after scenario tables covered cases such as forgetting a birthday, jealousy and apologies.
4. **Persistent memory of preferences.** Claude keeps short memory notes of standing rules (reply in Vietnamese, say "story" not "câu chuyện", hide technical UI, no quotes in dialogue cards, equal-size grid cards). Corrections then stick across sessions.
5. **A wiki as the source of truth.** `wiki/` keeps the owner's original messages verbatim (`raw/`), a page per feature with a *Done when* checklist checked against the code, a page per decision with its reason, and `learned.md` for mistakes not to repeat.

#### What worked

- **Adversarial review caught real bugs before the user did.** Examples:
  - parallel wrong-password requests that bypassed the login rate limit;
  - a session surviving a password change;
  - side characters' secrets leaking into the lorebook;
  - the background prefill sending a prompt 6 tokens different from the real one, which made it useless.

  Adversarial verifiers filtered out false alarms, so fix stages worked only on confirmed defects.
- **Measuring beat guessing.** Reading Ollama's prefix-cache logs showed exactly why long stories were slow, and led to the "raw prefill" fix: first-token time on window shifts dropped from 26–30 s to about 5 s. A suspected slow-prompt regression (68 s per extraction) turned out to be the machine running at half speed; the fix that followed still cut extraction to about 15 s.
- **Tests as the contract.** About 1,400 backend and 360 frontend tests, including a route-by-route data-isolation sweep across two accounts. Large refactors such as adding login to every route stayed safe.
- **Design docs before code.** Contracts written first let backend and frontend agents work without stepping on each other. A "critique" pass on the design was much cheaper than fixing code later.

#### What didn't work (and what changed)

- **Taste needs the human.** Claude's defaults were often reasonable but not what the owner wanted:
  - the "Bắt đầu story" wording;
  - Explore cards too large;
  - quotes kept inside dialogue cards;
  - a stretched last card in the grid;
  - a placeholder too long for a phone;
  - the featured character listed twice.

  Each correction became a rule in memory or in `wiki/learned.md`.
- **Prompting can't fix everything in a 12B model.** DM replies kept ending with "ngủ sớm đi", and the character sometimes contradicted the lore or forgot a text-message plan. Prompt changes and validation rules reduced these but did not remove them. That is the case for the planned LoRA fine-tune.
- **Shared hardware got in the way.** Real-model tests share one local GPU with the owner's own chatting. The owner had to stop the app during measurements, and long workflows were paused and resumed several times. One measurement was wrong because the machine was under memory pressure.
- **Agents slip on the rules.** Agents occasionally broke house rules, such as calling the system Python instead of the project's virtual environment, or echoing a temporary secret into a log. Explicit hard rules in every agent prompt, plus a review stage, contained this.
- **Cost.** Thorough multi-agent phases are token-heavy (millions of tokens per phase). They pay off for security-sensitive or cross-cutting work; small UI fixes are faster done directly.

---

## Tiếng Việt

### Giới thiệu

Lyris là app nhập vai với nhân vật AI, ưu tiên tiếng Việt. Bạn chọn một nhân vật (hoặc tự viết trong Studio), bước vào một story với nhân vật đó và trò chuyện. AI dẫn truyện và đóng vai nhân vật, còn persona của bạn chỉ bạn điều khiển. Nhân vật nhớ những gì đã xảy ra, kể cả điều bạn nhắn tin. Cảm xúc của họ với bạn tăng hay giảm theo việc bạn làm, và họ chỉ biết những gì thế giới của họ cho phép. 

### Vấn đề

- **App nhập vai viết đè lên người chơi.** Các app chạy trên server như WHIF hay bỏ qua điều người chơi vừa viết, nói và làm thay nhân vật của người chơi, rồi trôi khỏi cảnh.
- **Tiếng Việt bị xem nhẹ.** Model nhập vai huấn luyện bằng tiếng Anh dùng sai xưng hô (anh/em, tớ/cậu, ta/ngươi), chêm chữ Anh hay chữ Trung, và quên quan hệ giữa hai nhân vật.
- **Trí nhớ nông.** Nhân vật quên tên, lời hứa, sự kiện sau vài chục lượt, và thái độ không đổi dù người chơi làm gì.

### Người dùng mục tiêu

- **Người đọc truyện mạng tiếng Việt** (ngôn tình, đam mỹ, cổ trang, vườn trường) muốn *sống trong* câu chuyện thay vì chỉ đọc. Dùng điện thoại là chính, thường vào buổi tối.
- **Người viết và tạo nhân vật**, dựng cả thế giới (nhân vật phụ, nơi chốn, bí mật, móc sự kiện) và muốn nhân vật được đóng đúng.
- **Người thích tự chạy AI**, có máy đủ mạnh, coi trọng riêng tư hơn gói thuê bao.

### Tính năng chính

| Mảng | Làm gì |
|---|---|
| **Chế độ Story và DM** | Story đọc như tiểu thuyết: dẫn truyện chữ nghiêng, lời thoại trong ô thoại, suy nghĩ của nhân vật trong thẻ làm mờ, chạm để đọc. DM giống app nhắn tin. Hai chế độ chung một dòng thời gian: xưng tên qua tin nhắn thì trong story nhân vật vẫn biết. |
| **Người chơi là tác giả** | AI không viết lời, hành động hay quyết định thay bạn, và tiếp nối đúng từ điều bạn vừa viết. Chỉ đạo ngầm cho nhân vật viết trong `((…))`. Lời thoại của bạn viết trong `"…"`, hành động trong `*…*`, lời của người khác trong `*"…"*`. |
| **Sáu chỉ số cảm xúc** | Thương mến, tin cậy, rung động, chiếm hữu, sợ mất, chán ghét (0–100) tăng *và giảm* theo việc bạn làm. Ghen thì tin cậy giảm, xin lỗi thì chán ghét giảm, chuyện thường ngày hầu như không đổi gì. Chỉ số được đổi thành chỉ dẫn diễn xuất cho nhân vật, không bao giờ đưa con số thô vào prompt. |
| **Trí nhớ** | Tóm tắt cảnh theo đợt, ký ức dài hạn và các điều đã biết. Tìm theo từ khoá, và theo nghĩa nếu máy có model embedding. Tạo lại, sửa hay xoá một lượt thì trạng thái cũng lùi lại đúng. |
| **Sổ thế giới (lorebook)** | Mỗi nhân vật mang theo thế giới riêng: nhân vật phụ, nơi chốn, các mục lore, nhập từ file Markdown `world.md`. Mục được gợi ra bằng từ khoá, so khớp đúng tiếng Việt và giữ dấu. Mỗi mục ghi rõ ai biết: mọi người, chỉ nhân vật, hay chỉ bạn. Spoiler chỉ bạn biết không bao giờ tới model. |
| **Studio nhân vật** | Tạo và sửa nhân vật, AI viết nháp từ một dòng ý tưởng, lời nói đặc trưng, xưng hô, ảnh đại diện, nhập và xuất Character Card V2. |
| **Khám phá và hồ sơ** | Nhân vật nổi bật, lọc theo cảm xúc ("Chữa lành", "Tình đầu"…), lưới thẻ đều nhau, hồ sơ chỉ xem với nút "Bước vào câu chuyện". |
| **Trợ giúp khi cần** | Nút "+" ở ô chat: gợi ý trả lời (chỉ khi bấm), dòng thời gian sự kiện, gửi hình ảnh (mới có khung). |
| **Tài khoản** | Chủ máy và thành viên được mời, mã mời, đăng nhập bằng mật khẩu (scrypt, phiên HttpOnly), trang quản lý chỉ chủ máy thấy, story riêng tư hoàn toàn. Nhân vật có thể bật công khai; người khác chơi trên bản sao riêng của họ. |
| **Nhanh trên máy vừa phải** | Prompt được sắp theo cách giữ được cache, và lượt sau được chuẩn bị trước ("prefill") khi bạn đang gõ. Thời gian chờ chữ đầu tiên ở story dài giảm từ khoảng 30–47 giây xuống khoảng 5 giây với model 12B. |
| **Không chữ kỹ thuật** | Giao diện không có tên model, token hay trạng thái máy. Lúc chờ chỉ hiện ba chấm nhảy. Thiết lập kỹ thuật nằm trong "Nâng cao". |

### Kênh ra mắt và mô hình doanh thu *(kế hoạch, chưa làm)*

**Kênh ra mắt**
- **Cộng đồng nhập vai và truyện mạng tiếng Việt:** nhóm Facebook, TikTok, máy chủ Discord, nơi người chơi WHIF và độc giả ngôn tình tụ họp.
- **Nội dung giới thiệu:** clip ngắn về chế độ Story và các thế giới viết tay đã có sẵn (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương).
- **Lan toả nhờ tác giả:** tác giả đăng nhân vật công khai, người theo dõi họ tới chơi.

**Doanh thu: hệ thống coin**
- **Chat tốn coin:** mỗi lượt chat tiêu một lượng coin nhỏ.
- **Nạp coin:** người dùng nạp coin bằng tiền.
- **Kiếm coin không cần trả tiền:**
  - **Làm nhiệm vụ:** điểm danh hằng ngày, đi hết một chặng truyện, mở khoá khoảnh khắc.
  - **Sáng tác:** viết nhân vật và thế giới, nhận coin khi người khác chơi nhân vật công khai của mình.

  Cách này thưởng cho những người mang người chơi tới.
- **Tự chạy trên máy mình vẫn miễn phí:** coin áp dụng cho bản host sẵn, dành cho người không có máy đủ mạnh.
- **Giá theo chi phí thật:** giá coin sẽ bám theo chi phí tính toán đo được cho mỗi lượt (độ dài prompt, độ dài câu trả lời).

### Cài đặt, chạy và truy cập

#### Phần cứng để chạy AI local

Lyris chạy một model khoảng 12 tỷ tham số qua Ollama, context 8.192 token. Model và bộ nhớ đệm chiếm khoảng 16 GB.

| | Tối thiểu | Khuyên dùng |
|---|---|---|
| Bộ nhớ cho model | 16 GB (bộ nhớ hợp nhất hoặc VRAM), dùng model nhỏ hơn (vd. `gemma4:e4b`) | Từ 24 GB bộ nhớ hợp nhất (Apple Silicon) hoặc GPU NVIDIA từ 16 GB cho `gemma4:12b` |
| Ổ đĩa | ~15 GB (model + app) | Từ 30 GB nếu thêm model embedding hoặc fine-tune |
| Hệ điều hành | macOS trên Apple Silicon (đã thử), Linux có Ollama (dự kiến chạy được) | |

Tốc độ tăng theo băng thông bộ nhớ. Lượt trả lời đầu tiên sau khi mở app phải đọc cả story (vài chục giây). Các lượt sau bắt đầu trong khoảng 5 giây nhờ prefill.

#### Phần mềm

- [Ollama](https://ollama.com) 0.40 trở lên
- Python 3.12 và [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 và npm

#### Các bước

```bash
# 1. Model
ollama pull gemma4:12b          # model chat (mặc định)
ollama pull bge-m3              # tuỳ chọn: tìm ký ức theo nghĩa

# Thiết lập Ollama nên dùng (đặt cho server Ollama rồi khởi động lại):
#   OLLAMA_FLASH_ATTENTION=1  OLLAMA_KV_CACHE_TYPE=q8_0  OLLAMA_NUM_PARALLEL=2
#   Trên macOS, scripts/ollama-env.sh cài sẵn các biến này qua LaunchAgent.

# 2. Thư viện backend
cd backend && uv sync && cd ..

# 3. Chạy backend (127.0.0.1:8000) và frontend (cổng 5173) cùng lúc
bash scripts/dev.sh
```

- **Lần đầu chạy:** Terminal in một **mã thiết lập** trong khung "Lyris: đặt mật khẩu cho tài khoản chủ máy". Mở http://localhost:5173, dán mã và đặt mật khẩu chủ máy. Không thấy khung thì chạy `bash scripts/lyris-admin.sh setup-code`.
- **Điện thoại hoặc máy khác cùng Wi-Fi:** mở địa chỉ LAN mà `dev.sh` in ra (`http://<ip-máy>:5173`) rồi đăng nhập. Đặt `LYRIS_LAN=0` nếu chỉ muốn mở trên máy này. Qua Wi-Fi thường, đường truyền chưa được mã hoá; truy cập từ xa qua HTTPS (Tailscale) đang trong kế hoạch.
- **Mời người khác:** vào Tài khoản → Quản lý tài khoản → Tạo mã mời.
- **Quên mật khẩu chủ máy:** chạy `bash scripts/lyris-admin.sh reset-password <handle>`.

Biến môi trường, lệnh chạy test và sơ đồ thư mục: xem các bảng ở phần tiếng Anh phía trên (giống hệt nhau).

### Quy trình làm việc cùng AI: Claude đã xây Lyris thế nào

Lyris được làm trong khoảng ba ngày bởi một người làm sản phẩm cùng **Claude Code** (Claude Opus). Người làm sản phẩm viết tầm nhìn, đặc tả thiết kế (`DESIGN.md`), các thế giới nhân vật và mọi quyết định sản phẩm. Claude viết gần như toàn bộ code, test và tài liệu thiết kế. Người làm sản phẩm chỉ đạo và sửa bằng tiếng Việt thông thường.

#### Cách tổ chức công việc

1. **Lên kế hoạch trước, bằng file.** Claude rà và viết lại plan gốc thành `docs/plan.md`. Mỗi phase bắt đầu bằng một tài liệu thiết kế (`docs/phase3.md`, `docs/phase4.md`, `docs/auth.md`) chốt hợp đồng trước khi viết code: bảng dữ liệu, dữ liệu API, chữ trên giao diện, kế hoạch test.
2. **Workflow nhiều agent cho mỗi phase lớn.** Một phase là một chuỗi agent phụ được viết sẵn:
   - thiết kế;
   - *phản biện* sửa thẳng vào thiết kế;
   - làm backend và frontend;
   - soát lỗi theo 3–4 góc nhìn độc lập (bảo mật, tách dữ liệu, cache và tốc độ, trải nghiệm);
   - mỗi lỗi tìm được có một *người kiểm chứng* cố bác bỏ trước khi sửa;
   - bước sửa kèm test chống lặp lỗi;
   - chạy thử từ đầu đến cuối trên bản sao dữ liệu thật.

   Phase 4 (sổ thế giới) dùng 22 agent, Phase 4b (tài khoản) dùng 23, mỗi phase khoảng hai tiếng.
3. **Đo trên model thật, không đoán.** Mọi nhận định về tốc độ và hành vi model đều được thử trên model local, kèm bảng thời gian và log cache của Ollama. Bảng so trước/sau có các tình huống như quên sinh nhật, ghen, xin lỗi.
4. **Ghi nhớ sở thích lâu dài.** Claude giữ các ghi chú ngắn về quy tắc cố định (trả lời tiếng Việt, gọi "story" thay vì "câu chuyện", giấu chữ kỹ thuật, không để ngoặc trong ô thoại, thẻ lưới đều nhau). Nhờ vậy lời sửa được giữ qua các buổi làm việc.
5. **Wiki là nguồn sự thật.** `wiki/` giữ nguyên văn tin nhắn gốc của người làm sản phẩm (`raw/`), mỗi tính năng một trang kèm danh sách *Done when* đã đối chiếu với code, mỗi quyết định một trang kèm lý do, và `learned.md` ghi những lỗi không được lặp lại.

#### Điều làm tốt

- **Soát lỗi phản biện bắt được lỗi thật trước khi người dùng gặp.** Ví dụ:
  - gửi song song nhiều lần đoán mật khẩu là vượt được giới hạn đăng nhập;
  - phiên đăng nhập vẫn sống sau khi đổi mật khẩu;
  - bí mật của nhân vật phụ lọt vào sổ thế giới;
  - phần chuẩn bị trước lượt sau gửi prompt lệch 6 token so với prompt thật, nên vô dụng.

  Người kiểm chứng loại bỏ các báo động giả, nên bước sửa chỉ làm trên lỗi đã xác nhận.
- **Đo tốt hơn đoán.** Đọc log cache của Ollama cho thấy chính xác vì sao story dài bị chậm, dẫn tới cách sửa "raw prefill": thời gian chờ chữ đầu tiên ở lượt cắt bớt story giảm từ 26–30 giây xuống khoảng 5 giây. Một nghi ngờ prompt chậm đi (68 giây mỗi lần chấm cảm xúc) hoá ra là do máy đang chạy nửa tốc độ; dù vậy, bản sửa sau đó vẫn rút lần chấm xuống khoảng 15 giây.
- **Test là hợp đồng.** Khoảng 1.400 test backend và 360 test frontend, gồm một bài quét từng route để chắc hai tài khoản không đọc được dữ liệu của nhau. Nhờ vậy những thay đổi lớn như thêm đăng nhập vào mọi route vẫn an toàn.
- **Viết thiết kế trước code.** Hợp đồng viết trước giúp agent backend và frontend làm song song mà không giẫm chân nhau. Phản biện trên giấy rẻ hơn nhiều so với sửa code về sau.

#### Điều chưa tốt (và đã đổi gì)

- **Gu thẩm mỹ cần con người.** Mặc định của Claude thường hợp lý nhưng không đúng ý người làm sản phẩm:
  - chữ "Bắt đầu story";
  - thẻ Khám phá quá to;
  - ô thoại còn dấu ngoặc;
  - thẻ cuối trong lưới bị kéo giãn;
  - dòng gợi ý quá dài trên điện thoại;
  - nhân vật nổi bật hiện hai lần.

  Mỗi lần sửa trở thành một quy tắc trong bộ nhớ hoặc trong `wiki/learned.md`.
- **Prompt không sửa được hết cho model 12B.** Tin nhắn DM cứ kết bằng "ngủ sớm đi", và nhân vật thỉnh thoảng nói trái lore hoặc quên hẹn đã nhắn. Sửa prompt và thêm luật kiểm tra giảm được nhưng không hết. Đó là lý do cho kế hoạch fine-tune LoRA.
- **Dùng chung phần cứng gây vướng.** Test trên model thật dùng chung một GPU với lúc người làm sản phẩm đang chat. Người làm sản phẩm phải tắt app khi đo, và các workflow dài phải tạm dừng rồi chạy tiếp nhiều lần. Có một lần số đo sai vì máy đang thiếu RAM.
- **Agent đôi khi trượt quy tắc.** Agent thỉnh thoảng phạm quy tắc chung, như gọi Python hệ thống thay vì môi trường riêng của project, hoặc in lại một mã bí mật tạm thời vào log. Ghi luật cứng trong prompt của mọi agent cộng với bước soát lỗi đã kiềm chế được.
- **Chi phí.** Các phase nhiều agent rất tốn token (hàng triệu token mỗi phase). Đáng làm với phần nhạy cảm về bảo mật hoặc đụng nhiều nơi; sửa giao diện nhỏ thì làm trực tiếp nhanh hơn.
