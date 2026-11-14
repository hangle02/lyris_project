# Lyris: implementation plan (v3.0)


## 1. Lyris là gì

App roleplay local kiểu WHIF, chạy trên một máy Mac. Bạn là chủ máy; từ Phase 4b, người khác vào được bằng tài khoản riêng do bạn mời (mã mời), mỗi người có story riêng tư. Bạn tạo nhân vật (hoặc import), mở một story với nhân vật đó và chat. AI dẫn truyện và đóng vai nhân vật; chỉ bạn điều khiển persona của mình. Tất cả chạy trên MacBook Pro M2 Pro 24GB, dùng từ trình duyệt trên Mac hoặc iPhone qua Tailscale. Model là một base model mở do chính bạn fine-tune bằng LoRA.

Tính năng bản 1:
- **Character Studio**: tạo, sửa, nhân bản, import, export card nhân vật; "AI viết nháp" từ một dòng ý tưởng.
- **Story**: một story = một card + persona của bạn + bối cảnh + ngôn ngữ (Việt hoặc Anh) + mode. Nhiều story tồn tại song song, mỗi story có trí nhớ và quan hệ riêng.
- **Hai mode** chung một dòng thời gian (nhân vật nhớ cả hai) nhưng mỗi mode có khung riêng: Story Mode (văn tiểu thuyết, suy nghĩ `[Thought: ...]` hiện ngay tại chỗ trong truyện) và DM Mode (giao diện nhắn tin: bong bóng, avatar, mốc giờ, nhiều tin ngắn liền nhau). Mỗi khung chỉ hiện tin của mode đó; lượt của mode kia gộp thành một nhãn.
- **Kiểu suy nghĩ** (`stories.thought_style`, chọn bằng nút 💭): `inline` (mặc định, 2-3 Thought rải giữa truyện, mỗi cái 2-3 câu) hoặc `end` (một Thought 2-4 câu ở cuối lượt).
- **Regenerate, sửa, xoá** bất kỳ lượt nào.
- **Người chơi là tác giả**: được viết hành động cho nhân vật AI ngay trong lượt của mình, ghi chỉ đạo ẩn trong `((...))` (ví dụ "((cho Lạc Dương đang ghen nhưng không nói ra))"), hoặc dùng ô "Chỉ đạo" trên giao diện; AI làm theo nhưng giữ giọng nhân vật.
- **Quan hệ** (6 chỉ số 0-100) chuyển thành chỉ dẫn diễn xuất, hiển thị dạng thanh đo.
- **Trí nhớ**: cửa sổ tin gần đây, tóm tắt cảnh, ký ức dài hạn tìm bằng vector, facts.
- **Lorebook**: file Markdown, kích hoạt theo từ khoá.
- **Vòng train**: app lưu mọi prompt, câu trả lời và đánh giá của bạn; pipeline biến chúng cùng dữ liệu synthetic và public thành bản LoRA, rồi nạp lại vào app.
- **Test harness**: kiểm tra format, godmodding, tiếng Việt và xưng hô, tốc độ, so sánh base với bản fine-tune.

Tuỳ chọn về sau: director điều tiết nhịp truyện và mission, cảnh nhiều nhân vật, NPC tự hành, địa điểm và quest.

## 2. Cần chuẩn bị trước khi bắt đầu

**Máy và dung lượng**
- Khoảng 60GB ổ trống: 3-4 model ứng viên (5-9GB mỗi cái), trọng số full-precision của model được chọn (khoảng 16GB), bản MLX 4-bit, bản GGUF, dataset.
- Cắm sạc khi train; đóng các app nặng.

**Phần mềm cài sẵn**
- Xcode Command Line Tools, Homebrew, git.
- Python 3.11+ và `uv` (quản lý môi trường), Node.js 20+ và `pnpm` hoặc `npm`.
- Ollama (app macOS).
- `cmake` (để build llama.cpp dùng cho bước chuyển GGUF).
- Tailscale trên Mac và iPhone (chỉ cần từ Phase 6).

**Tài khoản**
- Hugging Face + access token; chấp nhận điều khoản của các model có cổng (ví dụ Gemma).
- Tài khoản Tailscale (miễn phí).
- Tuỳ chọn: API key của một model lớn để làm "teacher" sinh dữ liệu synthetic ở Phase 5. Nếu muốn hoàn toàn offline thì dùng model local lớn hơn làm teacher, chất lượng thấp hơn.

**Nội dung bạn tự chuẩn bị (quan trọng, mình không làm thay được)**
- 3-5 ý tưởng nhân vật viết tay (tính cách, cách nói, bối cảnh), ít nhất 2 nhân vật tiếng Việt, kèm cặp xưng hô mong muốn (ví dụ anh/em, tớ/cậu, ta/ngươi).
- Persona của bạn (tên, mô tả ngắn).
- 10 câu mở đầu roleplay tiếng Việt và 5 câu tiếng Anh để test model ở Phase 0.
- 2-3 đoạn văn mẫu thể hiện đúng giọng văn bạn thích (dùng làm chuẩn cho dữ liệu synthetic).
- Quyết định về mức độ nội dung (ví dụ có nội dung người lớn hay không), vì nó ảnh hưởng đến việc chọn teacher và dataset public.

## 3. Ngân sách phần cứng (M2 Pro 24GB)

- Inference: một chat model 8-9B ở Q4_K_M (5-7GB) + `bge-m3` (khoảng 1.2GB) + hai slot context 8k. Mục tiêu tổng dưới 10GB; với model 12B (7-8GB) là dưới 12GB.
- Ollama: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=2`, `OLLAMA_MAX_LOADED_MODELS=2`.
- Train: dừng model Ollama trước (`ollama stop`). QLoRA trên model 7-9B 4-bit, batch 1-2, độ dài chuỗi 2048, dự kiến đỉnh 10-14GB. Không train và serve cùng lúc.
- Context 8,192 token, chia ngân sách ở mục 7.

## 4. Tech stack

| Phần | Lựa chọn |
|---|---|
| Inference | Ollama (stream chat + structured output theo JSON schema) |
| Chat model | Chọn ở Phase 0 bằng bake-off tiếng Việt giữa các ứng viên trong bảng "Model ứng viên" bên dưới. |
| Embedding | Mặc định `bge-m3` qua Ollama (đa ngôn ngữ, 1024 chiều); so với `embeddinggemma-2` ở Phase 3. Số chiều là cấu hình, không hard-code. |
| Train | `mlx-lm` (LoRA trên Apple Silicon), llama.cpp để chuyển GGUF |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SSE, một job worker chạy trong tiến trình |
| Lưu trữ | Một file SQLite + `sqlite-vec`; lorebook là Markdown có YAML frontmatter |
| Frontend | React + Vite + Tailwind, PWA mobile-first, giao diện tối |
| Test | `pytest` cho code, `harness/` cho hành vi model |
| Đăng nhập | Tài khoản + mật khẩu (scrypt của Python), cookie phiên HttpOnly, mã mời do chủ máy tạo (Phase 4b, `docs/auth.md`) |
| Truy cập từ xa | Tailscale Serve (HTTPS) + đăng nhập của Phase 4b |

LLM client là một interface nhỏ (`chat_stream`, `chat_json`, `embed`) để có thể thêm backend thứ hai (`mlx_lm.server`) nếu đường GGUF không chạy với model được chọn.

### Model ứng viên (theo thư viện Ollama, tra ngày 2026-11-12)

Chat model, kích thước là bản Q4_K_M:

| Tag Ollama | Kích thước | Vai trò | Ghi chú |
|---|---|---|---|
| `qwen3.5:9b` | 6.6GB | Ứng viên chính cho cả chat và fine-tune | Mới (khoảng 1 tháng), context 256K, đa phương thức. Trang Ollama không nêu danh sách ngôn ngữ; tiếng Việt phải tự test. |
| `gemma4:12b` | 8.0GB (bản `12b-it-qat` 7.2GB) | Ứng viên chất lượng cao nhất cho chat | Mới (khoảng 1 tháng), context 256K. Fine-tune 12B trên 24GB là sát giới hạn, phải đo ở Phase 0. |
| `gemma4:e4b` | 6.6GB (bản `e4b-it-qat` 6.1GB) | Phương án nhẹ; ứng viên cho luồng trích xuất nền | 4.5B tham số hiệu dụng, context 128K. |
| `sailor2:8b` | 5.2GB | Chuyên Đông Nam Á; phương án an toàn cho fine-tune | Model chính thức duy nhất nêu rõ hỗ trợ tiếng Việt. Apache 2.0. Cũ hơn (khoảng 1 năm), nền Qwen2.5 nên các công cụ train hỗ trợ tốt. Context 32K. |
| `qwen3:8b` | 5.2GB | Mốc so sánh | Cũ (khoảng 1 năm), chỉ text. |
| `ministral-3:8b` | 6.0GB | Tuỳ chọn | Apache 2.0; danh sách ngôn ngữ trong readme không có tiếng Việt. |

Không còn trong danh sách: SeaLLMs-v3 (không có trong thư viện chính thức), Gemma 3 (đã có Gemma 4), các bản RP fine-tune nền Mistral-Nemo (Rocinante, Impish, ...; mạnh tiếng Anh, có thể thử riêng cho mode tiếng Anh). Bản cộng đồng `aisingapore/...SEA-LION-v4...` (8B, cho Đông Nam Á) có trên Ollama nhưng chưa được kiểm chứng; thử nếu các ứng viên trên kém tiếng Việt.

Embedding:

| Tag Ollama | Kích thước | Ghi chú |
|---|---|---|
| `bge-m3` | 1.2GB | Mặc định. Hơn 100 ngôn ngữ, context 8K, đã dùng rộng rãi. |
| `embeddinggemma-2` | 0.3-1.3GB tuỳ cỡ | Mới (3 tuần), 768 chiều, hơn 100 ngôn ngữ. So với `bge-m3` trên dữ liệu tiếng Việt của bạn. |
| `qwen3-embedding:0.6b` | 0.6GB | Phương án nhỏ. |

Lưu ý:
- `qwen3.5` và `gemma4` là model đa phương thức và còn mới; việc `mlx-lm` LoRA và bước chuyển GGUF hỗ trợ kiến trúc của chúng chưa được xác minh. Nếu không chạy, fine-tune trên `sailor2:8b` hoặc `qwen3:8b`.
- Ollama hiện có các tag định dạng MLX cho hai họ này (ví dụ `qwen3.5:9b-mlx`, `gemma4:12b-mlx`). Nếu Ollama nạp được model MLX đã fuse thì bỏ được bước chuyển GGUF; thử ở Phase 0.
- Context 256K là mức tối đa của model; app vẫn chạy ở 8,192 token để giữ RAM và tốc độ.
- Licence của Gemma 4 và Qwen3.5 không ghi trên trang Ollama; xem trên Hugging Face trước khi chia sẻ bản fine-tune.

## 5. Cấu trúc repo

```
lyris/
  backend/lyris/
    api/          # FastAPI: characters, stories, chat (SSE), lore, feedback, models
    llm/          # interface client, backend Ollama, parser tách thought khi stream
    prompt/       # prompt builder, ngân sách token, templates_vi/, templates_en/
    state/        # quan hệ, directive mapper, fold/rollback state_events
    memory/       # tóm tắt, ký ức, retrieval
    lore/         # đồng bộ markdown, so khớp từ khoá
    jobs/         # worker trích xuất
    db/           # schema.sql, migrations, queries
  frontend/       # React PWA
  harness/        # run_eval.py, scenarios/*.yaml, checks/
  training/       # build_dataset.py, synth.py, train.sh, deploy.sh, configs/
  world_wiki/     # lorebook markdown
  data/           # lyris.db, datasets/, adapters/ (git-ignore)
  docs/plan.md
```

## 6. Data model

- `character_cards`: id, name, **gender**, avatar_path, language, description, personality, appearance, background, goals, secrets, speech_style, **style_profile** (bộ quy ước văn phong theo bối cảnh, xem mục 7), **address_terms_json** (nhân vật tự xưng và gọi người chơi thế nào, ví dụ `{"self":"anh","player":"em"}`, có thể có biến thể theo giai đoạn quan hệ), greeting, example_dialogues, tags, created_at, updated_at. Import/export theo chuẩn Character Card V2 JSON để dùng được card từ app khác.
- `personas`: id, name, **gender**, description, xưng hô của bạn.
- `stories`: id, card_id, persona_id, title, scenario, language, mode, **relationship_type** (nam-nữ, nam-nam/đam mỹ, nữ-nữ/bách hợp, không lãng mạn), **pov** (ngôi thứ ba, hoặc ngôi thứ nhất của nhân vật), **narration_pronouns_json** (đại từ dẫn truyện, ví dụ `{"character":"anh","player":"cô"}`), model_name, scene_summary, story_clock, created_at.
- `messages`: id, story_id, turn_index, variant_index, is_active, role, visible_content, thought, prompt_snapshot_json, model_name, gen_stats_json, created_at. Regenerate tạo variant mới ở cùng turn_index.
- `state_events`: id, story_id, message_id, kind (`relationship_delta`, `fact_added`, `memory_added`, `summary_updated`, `flag_set`), payload_json. Chỉ ghi thêm. State hiện tại = gộp các event của tin nhắn đang active; tắt một tin nhắn thì hiệu ứng của nó biến mất.
- `relationship_state`: story_id, affection, trust, attraction, obsession, aversion, fear, notes (bản cache của phép gộp trên).
- `memories` (id, story_id, message_id, summary, importance, story_time) + `vec_memories` (sqlite-vec).
- `facts`: id, story_id, message_id, subject, fact_text.
- `lorebook_entries`: id, slug, title, scope (global hoặc card_id), trigger_keys_json, content, known_by_json, updated_at.
- `feedback`: message_id, rating (up/down), edited_content, note.
- `jobs`: id, story_id, message_id, kind, status, error.
- Phase 2c/4b: `accounts` (handle, tên, vai trò chủ máy/thành viên, trạng thái, mật khẩu scrypt), `sessions` (chỉ lưu hash của token), `invites` (mã mời, chỉ lưu hash), `auth_attempts` (giới hạn thử sai). Persona, card, story thuộc một account; card có `visibility` riêng tư/công khai. Chi tiết: `docs/accounts.md`, `docs/auth.md`.

## 7. Luồng xử lý một lượt chat

**Luồng chính (stream):**
1. Lưu tin nhắn của người chơi.
2. Dựng prompt theo thứ tự cố định để phần đầu được cache ổn định:
   - A. Luật hệ thống theo mode và ngôn ngữ (khoảng 400 token)
   - B. Card nhân vật + persona + xưng hô (khoảng 900)
   - C. Bối cảnh + tóm tắt cảnh (khoảng 400)
   - D. Lore được kích hoạt (tối đa 700)
   - E. Tin nhắn gần đây (khoảng 3,500; tin cũ nhất bị loại trước và dồn vào tóm tắt)
   - F. Ghi chú cuối, đặt ngay trước câu trả lời: chỉ dẫn diễn xuất + ký ức và facts truy xuất được + chỉ đạo của người chơi (nếu có) + một dòng nhắc "tiếp nối trực tiếp từ lượt vừa rồi của người chơi" (khoảng 700). Đặt ở cuối vì model chú ý nhất đến phần gần câu trả lời; đây là cách chính để chống lỗi trả lời lệch, bỏ qua những gì người chơi viết.
   - Dành cho câu trả lời: 900.
3. Stream từ Ollama qua SSE. Stop sequence: tên persona kèm dấu hai chấm, `\nPlayer:`, `\nUser:`. Parser tách `[Thought: ...]` khỏi phần hiển thị ngay khi stream. Tag giữ nguyên dạng tiếng Anh này ở cả hai ngôn ngữ để parse thống nhất.
4. Lưu câu trả lời kèm snapshot prompt chính xác và số liệu tốc độ.

**Luồng nền (job worker, slot Ollama thứ hai):**
5. Một lời gọi structured output với prompt nhỏ (lượt vừa rồi + state hiện tại): delta quan hệ (giới hạn ±5 mỗi lượt), facts mới, một ký ức kèm độ quan trọng, ba gợi ý trả lời.
6. Validate bằng Pydantic, ghi `state_events`, embed ký ức, cập nhật cache state.
7. Đẩy sự kiện state qua kênh SSE của story (thanh đo, gợi ý).
8. Mỗi N lượt, làm mới tóm tắt cảnh.

Nếu người chơi gửi tin mới trước khi job xong, câu trả lời dùng state cũ; job vẫn chạy xong và áp dụng sau.

**Directive mapper:** bảng luật Python thuần, từ 6 chỉ số ra một đến hai câu chỉ dẫn diễn xuất bằng ngôn ngữ của story. Với tiếng Việt, nó còn chọn biến thể xưng hô theo giai đoạn quan hệ. Không bao giờ đưa số thô vào prompt.

**Văn phong theo bối cảnh (style profile):** xưng hô và giọng văn đi theo quốc gia và thời đại của câu chuyện, không theo ngôn ngữ hiển thị. Mỗi card có trường `style_profile` chọn một bộ quy ước, ví dụ:
- `viet_hien_dai`: anh/em, tớ/cậu, mình/bạn; chi tiết đời sống Việt Nam.
- `trung_hien_dai` (ngôn tình hiện đại, vườn trường, tổng tài): tớ/cậu, anh/em; tên gọi thân mật kiểu "Vãn Vãn", "A Vãn", "Tiểu Vãn"; "bạn học + họ", "học trưởng", "học tỷ"; tên và địa danh âm Hán Việt.
- `trung_co_dai` (cổ trang, tiên hiệp, cung đấu): ta/ngươi, huynh/muội, sư huynh/sư muội, sư tôn, công tử/cô nương, bệ hạ/thần, bổn vương, tại hạ; từ vựng Hán Việt.
- Các bộ khác thêm dần (Nhật, Hàn, phương Tây, fantasy).

Mỗi profile là một file Markdown trong `backend/lyris/prompt/styles/` gồm quy tắc xưng hô, cách gọi người ngoài, từ vựng nên dùng và nên tránh, kèm vài câu mẫu; nội dung được chèn vào khối B của prompt. Người dùng tự thêm hoặc sửa profile được. "AI viết nháp" đề xuất profile dựa trên tên, bối cảnh và mô tả, nhưng người dùng là người xác nhận, vì chỉ dựa vào tên thì dễ đoán sai (nhiều họ tên dùng chung giữa Việt và Trung). `address_terms_json` của card ghi đè lên mặc định của profile.

**Thiết lập story và hai loại xưng hô:** mỗi story ghi rõ giới tính hai bên, kiểu quan hệ (nam-nữ, đam mỹ, bách hợp, không lãng mạn) và ngôi kể; cả ba được đưa vào khối A của prompt. Prompt tách bạch hai thứ:
- **Xưng hô** (`address_terms_json`): chỉ dùng trong lời thoại và Thought, ví dụ "tớ/cậu".
- **Đại từ dẫn truyện** (`narration_pronouns_json`): dùng trong phần kể, ví dụ ngôi thứ ba gọi nhân vật là "anh"/"hắn"/"y", người chơi là "cô"/"nàng"; ngôi thứ nhất thì nhân vật kể là "tôi"/"ta". Mặc định lấy theo style profile và giới tính, người dùng sửa được.

**So khớp lore:** chuẩn hoá Unicode NFC, không phân biệt hoa thường, so khớp cụm từ trên vài lượt gần nhất, giữ nguyên dấu. Chỉ chèn entry khi `known_by` chứa nhân vật hoặc `*`.

## 8. Tự train model

**Kỳ vọng thực tế:** LoRA với vài nghìn ví dụ dạy model đúng format và gu của bạn (tag thought, không godmodding, làm theo chỉ dẫn diễn xuất, tiếng Việt tự nhiên với xưng hô nhất quán). Nó không làm model thông minh hơn base. Đó là mục tiêu đúng cho dự án này.

**Hướng dữ liệu mình đề xuất (theo giai đoạn):**

1. **Dataset v1, khi chưa có nhiều chat.** Khoảng 3,000 lượt:
   - khoảng 2,000 lượt synthetic tiếng Việt: model teacher mạnh hơn viết roleplay nhiều lượt trên 40-60 card và bối cảnh đa dạng, chia đều cho các style profile, cả hai mode, theo các đoạn văn mẫu bạn chuẩn bị;
   - khoảng 500 lượt synthetic tiếng Anh cho mode tiếng Anh;
   - khoảng 500 lượt từ dataset roleplay/truyện public tiếng Anh, lọc chất lượng và định dạng lại. Dữ liệu roleplay tiếng Việt public tốt rất hiếm, nên phần tiếng Việt dựa vào synthetic. Kiểm tra licence của từng dataset.
   Trước khi train, tự đọc 100 mẫu ngẫu nhiên; nếu kém thì sửa bộ sinh rồi sinh lại.
2. **Từ v2, dùng chat của chính bạn.** Mỗi câu trả lời bạn bấm thích hoặc sửa trở thành ví dụ (bản đã sửa là đáp án). Câu bị chê hoặc bị regenerate bỏ đi thì loại. Ví dụ từ chat của bạn được nhân trọng số 2-3 lần. Train lại khi có thêm vài trăm lượt đã đánh giá.

Nguyên tắc cốt lõi: mọi ví dụ, từ bất kỳ nguồn nào, đều được dựng qua đúng prompt builder của app, nên format lúc train giống hệt lúc inference, kể cả khối chỉ dẫn và lore.

Teacher cấu hình được: API cloud cho tiếng Việt tốt nhất nhưng bước sinh dữ liệu không offline và chịu quy định nội dung của nhà cung cấp; model local lớn hơn (`gemma4:12b`) thì hoàn toàn local nhưng chất lượng thấp hơn.

**Pipeline (`training/`):**
1. `build_dataset.py`: gộp ba nguồn, khử trùng lặp, lọc (Story Mode phải có tag thought, không nói thay người chơi, giới hạn độ dài), chia 90/10, xuất JSONL dạng chat.
2. `train.sh`: `mlx_lm.lora` trên bản MLX 4-bit của base đã chọn. Giá trị khởi điểm: rank 16, 16 layer, learning rate 1e-4, batch 1-2, max sequence 2048, gradient checkpointing, 1-2 epoch. Theo dõi validation loss.
3. `deploy.sh`: fuse adapter (`mlx_lm.fuse`, ưu tiên fuse vào trọng số full-precision), chuyển bằng `convert_hf_to_gguf.py` của llama.cpp, quantize Q4_K_M, `ollama create lyris-vN`.
4. `harness/run_eval.py --models base,lyris-vN`: cùng kịch bản trên cả hai, báo cáo đặt cạnh nhau.
5. Trong app: chọn model cho từng story và A/B mù khi regenerate ("câu nào hay hơn?"), kết quả cũng ghi vào `feedback`.

Đường fuse và chuyển GGUF phụ thuộc việc kiến trúc model được từng công cụ hỗ trợ, nên phải chứng minh bằng một lần chạy nhỏ ở Phase 0 trước khi làm dữ liệu. Phương án dự phòng: serve adapter bằng `mlx_lm.server` qua cùng interface LLM client.

## 9. Test harness

`harness/run_eval.py` chạy các kịch bản YAML trên bất kỳ model nào và báo cáo:
- **Không godmodding**: nhân vật được phản ứng với mọi lời nói, hành động, trạng thái người chơi đã viết (ví dụ "run rẩy") và mô tả lại qua mắt mình; được tả thêm trạng thái nhỏ mà nhân vật nhìn thấy hoặc cảm nhận (má ửng đỏ, tay lạnh, chóp mũi đỏ vì gió) miễn hợp với những gì người chơi viết; nhưng không được viết lời thoại, hành động có chủ đích, suy nghĩ hay quyết định mới cho persona, và phải dừng lượt ở chỗ cần người chơi đáp lại. Máy khó tự phân biệt trạng thái nhỏ được phép với hành động bị cấm, nên kiểm tra này dùng một model chấm (LLM judge) với prompt so sánh câu trả lời với đúng những gì người chơi đã viết, cộng với chấm tay.
- **Bám sát lượt người chơi**: câu trả lời phải tiếp nối đúng hành động, lời nói, hoàn cảnh người chơi vừa viết, và làm theo chỉ đạo `((...))` mà không in lại phần đó (LLM judge + kiểm tra máy rằng `((` không lọt vào câu trả lời).
- **Tuỳ chọn về sau**: một công tắc theo story, "AI được viết tiếp diễn biến nhỏ cho người chơi", cho ai thích kiểu WHIF. Mặc định tắt.
- **Format**: Story Mode có hội thoại và số `[Thought: ...]` đúng theo `thought_style` (inline: 2-4, không hai Thought liền nhau; end: đúng một); DM Mode ngắn gọn.
- **Văn tự nhiên**: không có cụm sáo kiểu "bầu không khí" (`forbidden_phrases`); người đọc tự chấm thêm khi xem báo cáo.
- **Ngôn ngữ**: trả lời đúng ngôn ngữ của story; câu tiếng Việt giữ đúng xưng hô của card.
- **Văn phong**: xưng hô và từ vựng khớp `style_profile` của card (ví dụ card `trung_co_dai` không được dùng "anh/em" hay "tớ/cậu").
- **Ngôi kể và đại từ**: phần dẫn truyện (ngoài ngoặc kép và Thought) không chứa từ xưng hô của lời thoại, dùng đúng đại từ dẫn truyện và giới tính; ngôi thứ ba không có "tôi" trong phần kể.
- **Trích xuất**: structured output parse được ở mọi kịch bản.
- **Tốc độ**: TTFT, token/giây, bộ nhớ đỉnh, và TTFT khi job trích xuất đang chạy.
- **Rollback**: regenerate khôi phục đúng state trước đó (pytest thường).

## 10. Lộ trình triển khai

Mỗi phase kết thúc bằng một thứ chạy được. Không sang phase sau khi phase trước chưa qua bước kiểm tra. Thời lượng là ước lượng thô cho một người làm buổi tối/cuối tuần cùng coding agent.

### Phase 0: Chọn model và chứng minh đường train (2-4 ngày)
- **Chuẩn bị:** toàn bộ phần mềm và tài khoản ở mục 2; 15 câu test; 60GB ổ trống.
- **Việc làm:**
  1. Cài Ollama, đặt biến môi trường ở mục 3, pull các model ứng viên và `bge-m3`.
  2. Viết `harness/bakeoff.py`: chạy 15 câu test qua từng model, lưu câu trả lời, TTFT, token/giây, RAM.
  3. Bạn tự đọc và xếp hạng chất lượng tiếng Việt (tự nhiên, xưng hô, không lẫn tiếng Anh/Trung).
  4. Thử train trên model thắng: 50 vòng LoRA với 20 ví dụ đồ chơi, fuse, chuyển GGUF, `ollama create`, sinh thử.
- **Kết quả:** bảng so sánh model, base model được chọn, đường train-đến-serve đã xác nhận (hoặc đã chuyển sang phương án `mlx_lm.server`).
- **Kiểm tra:** `python harness/bakeoff.py` in bảng; `ollama run lyris-toy` trả lời được.

**Kết quả thực tế (2026-11-12):**
- Máy thật là Apple M2 thường (không phải M2 Pro), 24GB.
- Chấm tiếng Việt (bạn chấm, thang 10): `gemma4:12b` 7.6, `gemma4:e4b` 6.6, `qwen3.5:9b` 5.5 (chèn chữ Hán), `sailor2:8b` khoảng 5.6 (nhầm nhân vật). Tốc độ sinh: 12, 26.6, 15.8, 17.2 tok/s.
- Sau khi thêm giới tính, ngôi kể, đại từ dẫn truyện vào prompt, `gemma4:12b` đạt 0/15 lỗi máy bắt được.
- **Chọn:** `gemma4:12b` cho chat, `gemma4:e4b` cho luồng nền. Đã xoá `qwen3.5:9b`, `sailor2:8b`.
- Trọng số `google/gemma-4-12B-it` (không có cổng, Apache 2.0) đã tải; chuyển MLX 4-bit được (6.3GB); `mlx-lm` 0.32.2 hỗ trợ Gemma 4.
- Template của Gemma 4 chèn khối thought rỗng khi tắt thinking; bản 4-bit dùng để train đã được vá để khớp (bản gốc ở `chat_template.orig.jinja`).
- **Train thử LoRA 12B không vừa RAM:** 16 lớp LoRA, câu tới 1,168 token → dùng hết 24GB, swap 5GB, chỉ 2-3 tok/s (khoảng 1 phút mỗi vòng). Loss vẫn giảm (4.9 → 3.9). Dừng ở vòng khoảng 20; lần 8 lớp chưa chạy xong đã dừng.
- **Quyết định:** hoãn fine-tune, làm app trước với `gemma4:12b` gốc. Bước fuse/`ollama create` chưa kiểm chứng; script sẵn ở `training/toy/deploy_toy.sh`. Khi quay lại Phase 5, thử theo thứ tự: đóng hết app + 8 lớp + `--max-seq-length 1024`; nâng giới hạn RAM GPU (`sudo sysctl iogpu.wired_limit_mb=...`); hoặc train trên `gemma4:e4b`.

### Phase 1: Bản chơi được tối thiểu (khoảng 1 tuần)
- **Chuẩn bị:** một nhân vật tiếng Việt viết tay và persona của bạn.
- **Việc làm:**
  1. Khung backend: FastAPI, SQLite schema (`stories`, `messages`, `feedback`), migrations.
  2. LLM client + backend Ollama; parser tách thought khi stream; stop sequence.
  3. Prompt builder bản đầu (các khối A, B, C, E) với template tiếng Việt.
  4. API chat SSE; regenerate, sửa, xoá; lưu prompt snapshot; nút thích/chê.
  5. Màn hình chat React tối thiểu (bong bóng chat, thought thu gọn được, regenerate).
  6. Harness: 3 kiểm tra đầu (godmodding, format, tốc độ) trên 5 kịch bản.
- **Kết quả:** chat được với một nhân vật cố định trên trình duyệt Mac; mọi lượt đã được lưu cho việc train sau này.
- **Kiểm tra:** `pytest`, `python harness/run_eval.py --model <base>`, chat thử 20 lượt.

### Phase 2: Character Studio và Story (khoảng 1 tuần)
- **Chuẩn bị:** 3-5 ý tưởng nhân vật và các cặp xưng hô.
- **Việc làm:**
  1. Bảng và API cho `character_cards`, `personas`, `stories`.
  2. Giao diện Studio: form sửa card, upload avatar, xem trước prompt và số token, chọn style profile, trình sửa xưng hô.
  2b. Ba style profile đầu tiên (`viet_hien_dai`, `trung_hien_dai`, `trung_co_dai`) do bạn duyệt nội dung.
  3. "AI viết nháp": một dòng ý tưởng ra card đầy đủ bằng structured output.
  4. Import/export Character Card V2 JSON; nhân bản; xoá; "chat thử" trước khi lưu.
  5. Tạo story: chọn card, persona, bối cảnh, ngôn ngữ, mode, kiểu quan hệ, ngôi kể, đại từ dẫn truyện; danh sách story.
  6. Story Mode / DM Mode và template tiếng Anh.
- **Kết quả:** tự tạo nhân vật và mở nhiều story độc lập.
- **Kiểm tra:** tạo một card bằng tay, một card bằng AI, import một card ngoài; harness thêm kiểm tra ngôn ngữ và xưng hô.

### Phase 2b: Thiết kế Lyris (đã làm 2026-11-13)
Triển khai `DESIGN.md` theo `docs/design-impl.md`: hai theme, font, logo, điều hướng 3 tab, hub, Khám phá, không gian chat (3 loại khối, Thought làm mờ), Studio; đổi tên Nora thành Lyris.

### Phase 2c: Account, profile và persona (khoảng 3-5 ngày)
- **Thiết kế:** `docs/accounts.md`.
- **Việc làm:** account (tên hiển thị, @handle, avatar, ảnh bìa, giới thiệu) tách khỏi persona; một account có nhiều persona; mọi persona/card/story thuộc một account và có `uid` để sau này đồng bộ với cộng đồng; trang profile; sheet "Tài khoản" ở header; avatar persona; "bởi @handle" trên thẻ nhân vật.
- **Kiểm tra:** DB cũ nâng cấp không mất gì; đặt tên/handle; tạo nhiều persona có avatar; story mới dùng persona mặc định; export card ghi đúng tác giả.

### Phase 3: State và trí nhớ (1-2 tuần)
- **Chuẩn bị:** không cần gì thêm; nên có vài story dài từ Phase 2 để thử.
- **Việc làm:**
  1. Job worker + bảng `jobs`; lời gọi trích xuất structured output trên slot thứ hai.
  2. `state_events` và phép gộp; rollback khi regenerate/xoá.
  3. Directive mapper (bảng luật tiếng Việt và tiếng Anh) + khối F trong prompt.
  4. Thanh đo quan hệ và gợi ý trả lời trên giao diện, cập nhật qua SSE.
  5. Tóm tắt cảnh định kỳ; ký ức + `bge-m3` + sqlite-vec; retrieval lai (vector + từ khoá).
- **Kết quả:** nhân vật nhớ chuyện cũ, thái độ thay đổi theo quan hệ, regenerate không làm hỏng state.
- **Kiểm tra:** pytest rollback; harness đo TTFT khi đang trích xuất; kịch bản "nhắc lại chuyện 50 lượt trước".

### Phase 4: Lorebook (3-5 ngày)
- **Chuẩn bị:** vài file lore Markdown cho thế giới của bạn trong `world_wiki/`.
- **Việc làm:** script đồng bộ Markdown vào `lorebook_entries`; so khớp từ khoá tiếng Việt; lọc theo `known_by`; khối D trong prompt; trang xem wiki.
- **Kết quả:** nhắc đến một từ khoá thì nhân vật trả lời đúng theo lore, và không biết điều nó không được biết.
- **Kiểm tra:** kịch bản harness có/không có từ khoá; kịch bản lore bị cấm.

### Phase 4b: Đăng nhập và nhiều tài khoản (5-8 ngày, làm ngay sau Phase 4)
- **Thiết kế:** `docs/auth.md`.
- **Quyết định của bạn (2026-11-14):** tạo tài khoản cần mã mời; tài khoản đầu tiên (`@strawber`, chủ mọi dữ liệu hiện có) là chủ máy và là người duy nhất tạo mã mời; story, persona, ký ức, state, lore đã mở luôn riêng tư; nhân vật mặc định riêng tư, chủ nhân vật bật "Công khai" được để người khác thấy ở Khám phá và bắt đầu story riêng (không sửa được); nhân vật mẫu dùng chung; quên mật khẩu thì chủ máy đặt lại, chủ máy quên thì chạy lệnh trên Mac.
- **Chuẩn bị:** Phase 4 xong và đã kiểm tra; tắt app; sao lưu `data/lyris.db`; một trình duyệt riêng tư hoặc một người bạn để thử mã mời; iPhone cùng Wi-Fi.
- **Việc làm:**
  1. Migration `0008_auth.sql`: vai trò, trạng thái, mật khẩu (scrypt) trên `accounts`; bảng `sessions`, `invites`, `auth_attempts`; persona mặc định theo tài khoản; cột bản sao cho nhân vật công khai. Account id nhỏ nhất thành chủ máy.
  2. `backend/lyris/auth/`: băm mật khẩu, phiên (cookie HttpOnly, hạn trượt 30 ngày), mã mời, giới hạn thử sai (kể cả cookie "trình duyệt đã biết" để không ai khoá được bạn ra ngoài), chặn CSRF, IP thật lấy từ phần tử cuối của `X-Forwarded-For` (không dùng `proxy_headers` của uvicorn), mã thiết lập chủ máy in ra Terminal, lệnh trên Mac (`scripts/lyris-admin.sh`: mã thiết lập, đặt lại mật khẩu, mở khoá).
  3. `current_account` đọc cookie phiên thay vì luôn trả chủ máy; mọi route cần đăng nhập trừ 4 route của `/api/auth`; route chỉ chủ máy (`/api/admin/*`, thông tin máy, model).
  4. Rà từng route theo bảng `auth.md` §4.1 (kể cả `/openapi.json`, `/docs` FastAPI tự thêm: tắt); nhân vật công khai: người khác bắt đầu story thì được một bản sao chụp lúc đó (chủ nhân vật sửa, ẩn, xoá cũng không làm hỏng story của họ); hồ sơ, xem trước prompt, chat thử không lộ bí mật và sổ thế giới; bản sao được dọn ở mọi đường xoá story. Trong lúc chơi, nhân vật vẫn có thể tự kể điều mình biết (`auth.md` §4.5).
  5. Chia một model cho nhiều người: tối đa 2 lượt sinh cùng lúc, mỗi tài khoản 1, xếp hàng theo thứ tự đến; việc nền xen kẽ theo tài khoản.
  6. Giao diện: trang đăng nhập, tạo tài khoản (mã mời), thiết lập chủ máy, đổi mật khẩu bắt buộc; sheet Tài khoản thêm đổi mật khẩu, đăng xuất, đăng xuất mọi thiết bị; trang "Quản lý tài khoản" của chủ máy (mã mời, thành viên, đặt lại mật khẩu, tạm khoá); công tắc "Công khai" ở Studio; Khám phá có "Nhân vật được chia sẻ"; đăng xuất hay đổi tài khoản thì xoá bản nháp và dữ liệu tạm của tài khoản cũ trên trình duyệt.
  7. Vite gửi IP thật cho backend và không cho đọc file ngoài `frontend/`; `scripts/dev.sh` chạy uvicorn với `--no-proxy-headers` và nhắc đặt mật khẩu lần đầu.
- **Kết quả:** mở Lyris phải đăng nhập; bạn mời được người khác bằng mã mời; mỗi người chỉ thấy story của mình; nhân vật công khai dùng được ở tài khoản khác; dữ liệu cũ của bạn còn nguyên dưới `@strawber`.
- **Kiểm tra:** pytest (luồng đăng nhập, giới hạn thử sai, IP giả qua 127.0.0.1, CSRF, test quét mọi route với hai tài khoản, luật nhân vật công khai, migration trên bản sao DB version 7); `npm test`; checklist tay ở `auth.md` §8.3 trên Mac và iPhone. Trước khi chạy trên DB thật: kiểm tài khoản id nhỏ nhất đúng là `@strawber`.
- **Phản biện bảo mật:** đã làm (2026-11-14), các thay đổi liệt kê ở `auth.md` §12.

### Phase 5: Train model của bạn (1-2 tuần, phần lớn là làm dữ liệu)
- **Chuẩn bị:** 2-3 đoạn văn mẫu; teacher (API key hoặc model local); quyết định mức nội dung; 40-60 card/bối cảnh cho synthetic (có thể để AI viết nháp rồi bạn duyệt); vài chục lượt chat đã đánh giá từ các phase trước.
- **Việc làm:**
  0. Chat thật chỉ lấy từ tài khoản có `training_opt_in = 1` (mặc định chỉ chủ máy, Phase 4b). Story của thành viên không vào dataset nếu họ chưa đồng ý.
  1. `synth.py`: sinh roleplay nhiều lượt qua prompt builder thật.
  2. Tải, lọc, định dạng lại dataset public.
  3. `build_dataset.py`; đọc tay 100 mẫu.
  4. `train.sh` (chạy qua đêm), `deploy.sh`.
  5. So sánh base với `lyris-v1` bằng harness; chọn model theo story; A/B mù trong app.
- **Kết quả:** `lyris-v1` chạy trong app, có báo cáo so với base.
- **Kiểm tra:** `python harness/run_eval.py --models <base>,lyris-v1`; bản fine-tune phải bằng hoặc hơn base ở godmodding, format, xưng hô, và thắng trong A/B mù của bạn.

### Phase 6: Dùng trên iPhone (2-4 ngày)
- **Chuẩn bị:** Tailscale trên Mac và iPhone, cùng một tài khoản.
- **Việc làm:** PWA manifest và icon; Tailscale Serve cho HTTPS; dùng đăng nhập của Phase 4b (không cần access token riêng): qua HTTPS thì cookie phiên có `Secure` (qua Vite, `X-Forwarded-Proto` thành `"https,http"` nên backend không tự nhận ra, phải chọn cách ở `auth.md` §3.7); kiểm Tailscale Serve có giữ `Host` cho luật chặn CSRF không (§3.3); thêm đúng tên `*.ts.net` vào `allowedHosts` của Vite, không đặt `true`; tinh chỉnh giao diện mobile; chặn Mac ngủ khi đang serve.
- **Kết quả:** cài app lên màn hình chính iPhone và chat từ bất cứ đâu qua Tailscale, đăng nhập một lần cho mỗi thiết bị.
- **Kiểm tra:** chat từ iPhone bằng 4G; truy cập chưa đăng nhập bị từ chối (401); cookie có `Secure` khi qua HTTPS.

### Phase 7: Cộng đồng (lên plan riêng trước khi làm)
Bình luận, đăng ảnh, theo dõi, và chia sẻ nhân vật **ra ngoài máy Mac**, giống phần cộng đồng của WHIF. Phase 4b đã có trên một máy: nhiều tài khoản, đăng nhập, nhân vật "Công khai" cho các tài khoản cùng máy, bản sao khi bắt đầu story. Phase 7 đưa nhân vật công khai lên một máy chủ chung, nên cần: hosting và chi phí, tài khoản trên máy chủ chung nối với tài khoản trên máy (`uid`), handle phải kiểm lại trùng lặp toàn cầu, chính sách nội dung và kiểm duyệt, và nguyên tắc quyền riêng tư: story và chat không bao giờ tự rời máy. Phase 2c đã chuẩn bị `uid`, `account_id`, `visibility`; Phase 4b thêm `origin_card_id`/`origin_account_id` cho bản sao.

### Phase 8 (tuỳ chọn)
Director điều tiết nhịp truyện và mission, cảnh nhiều nhân vật với tri thức riêng từng người, NPC tự hành theo lịch, địa điểm và quest. Lên plan riêng khi tới nơi.

## 11. Quy tắc cho coding agent

1. Làm từng phase một, bắt đầu từ Phase 0.
2. Trình bày cây file và interface của phase trước khi viết code.
3. Code đầy đủ, có type, chạy được; không để placeholder ở logic chính.
4. Cuối mỗi phase đưa đúng các lệnh để kiểm tra.
5. Chuỗi giao diện và prompt template có cả tiếng Việt và tiếng Anh; tiếng Việt là mặc định.

## 12. Điểm chưa xác minh, sẽ xác nhận ở Phase 0

- Chất lượng tiếng Việt của từng model ứng viên: tag và kích thước đã tra trên thư viện Ollama, nhưng chưa model nào được chạy thử.
- `mlx-lm` có LoRA được trên `qwen3.5` và `gemma4` hay không, và Ollama có nạp được model MLX đã fuse hay không.
- `mlx_lm.fuse` + chuyển GGUF bằng llama.cpp có chạy với kiến trúc model được chọn hay không.
- Mức RAM đỉnh khi train và TTFT thực tế với hai slot Ollama trên máy này.
- Các con số thời lượng và số lượng mẫu là ước lượng khởi điểm, không phải cam kết.
