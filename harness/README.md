# harness/ — chấm hành vi model (bake-off và eval)

Bộ công cụ cho người làm app, không có trong giao diện. Chạy bằng Python của backend, từ thư mục gốc dự án
(không dùng `python3` của hệ thống). Mọi lệnh ở đây gọi Ollama thật: chỉ chạy khi chủ dự án không dùng app (chung GPU, RAM).

```bash
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b                       # mọi kịch bản + judge
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b --no-judge --only f09-cam-xuc
backend/.venv/bin/python harness/bakeoff.py --models gemma4:12b qwen3:8b --limit 3    # so sánh model
```

Kết quả: `harness/results/eval-<thời gian>/report.md` + `raw.json` (bake-off: `harness/results/<thời gian>/speed.md` …).
`verification/verify.sh --real-model` chạy `run_eval.py --no-judge --only <id>…` đúng các kịch bản mà trang tính năng ghi
`- model: <id>` trong `## Tests`, và đọc `raw.json`: mỗi kịch bản phải không có lỗi sinh (`error`) và không có lỗi máy
(`problems`). Chỉ dòng "Đã ghi kết quả vào …" của lượt chạy ngoài cùng được in (lượt chạy lồng và bake-off không in dòng đó).

- **Hạn chung** `--deadline-min` (mặc định 50 phút; verify cắt `run_eval` ở 60 phút): quá hạn thì kịch bản đang chạy và kịch bản
  còn lại thành `error` của riêng từng cái ("hết giờ chung…"), `run_eval` vẫn ghi báo cáo và thoát 0. Nhờ vậy một kịch bản treo
  không làm đỏ mọi tính năng cùng lúc.
- **num_ctx** mặc định 8192 như app (không lấy `LYRIS_NUM_CTX`); số dùng được ghi vào `raw.json` (`num_ctx`).
- Prompt của `reply` / `dm_session` có chỉ dẫn diễn xuất từ 6 chỉ số ban đầu của card (`kinds.fresh_prompt_state`), như
  ChatService với một story mới (chưa có tóm tắt, cảnh, ký ức). Ở `dm_session` chỉ số không đổi giữa các lượt (không chạy trích xuất).
- So khớp cụm (`required_all`, `memory_any`, `facts_any`, `required_any`, `reminders`) theo **nguyên từ**: "Chu" không khớp
  "chuyện"; cụm có chữ hoa (tên riêng) thì phải đúng chữ hoa ("chu đáo" không phải tên "Chu").

## Kịch bản (`harness/scenarios/*.yaml`)

Mỗi file một kịch bản, `id` không trùng. Khoá chung: `id`, `title`, `note`, `kind` (mặc định `reply`), `mode` (`story`/`dm`),
`card` (bộ card trong `harness/cards/`, bỏ trống = seed Lạc Dương). Kịch bản chứng minh một dòng "Model thật" đặt id bắt đầu
bằng mã tính năng (`f09-…`) và chỉ kiểm đúng điều dòng đó nói.

| `kind` | Gọi code app nào | Khoá riêng | Lỗi máy khi |
|---|---|---|---|
| `reply` | `build_prompt` (+ `lore_for_history` nếu có `lore`) rồi stream một câu trả lời | `input`, `history` (mỗi phần tử có thể có `mode: dm`), `checks`, `judge`, `thought_style`, `lore` | vi phạm `checks` (bên dưới) |
| `extract` | `state/extract.extract_turn` (đúng lời gọi của việc nền), xét kết quả sau `validate` | `cases`: `name`, `turn`, `before`, `expect` (`delta: {trust: down}`, `all_zero`, `memory_any`, `facts_any`, `facts_owner: persona\|character`) | chỉ số đổi sai chiều; ký ức / điều đã biết thiếu chi tiết; điều đã biết gán nhầm người |
| `summarize` | `memory/summarize.summarize` | `messages`, `previous`, `required_all` (mỗi mục là chuỗi hoặc list cách viết), `forbidden`, `language` | tóm tắt thiếu chi tiết, sai ngôn ngữ |
| `suggest` | `state/suggest.suggest_replies` hai lần (lần hai `avoid` = lần một, như "Gợi ý khác") | `history`, `language`, `max_overlap` | không đủ 3 gợi ý; sai ngôn ngữ; gửi đi không còn nguyên văn; lần hai trùng ≥ `max_overlap` từ |
| `draft` | `studio/draft.draft_card` | `idea`, `language`, `gender`, `style_profile`, `required_fields`, `forbidden_warnings` | thiếu trường, sai ngôn ngữ, có cảnh báo cấm, card bị lưu |
| `dm_session` | nhiều lượt DM liên tiếp qua `build_prompt`, câu trả lời thật làm lịch sử lượt sau | `history`, `turns`, `checks` (mặc định chỉ kiểm câu rỗng), `max_same_ending`, `ending_words`, `max_same_tail`, `reminders` (nhóm cụm của một lời dặn), `max_same_reminder` | câu kết, N chữ cuối, hoặc cùng một lời dặn (viết kiểu khác) lặp ở quá nhiều lượt |
| `app_ttft` | app thật trong tiến trình (`create_app`, DB tạm, worker + prefill bật) phục vụ qua uvicorn ở cổng 8068 (8069 nếu bận); gửi lượt qua HTTP, đo TTFT phía người chơi (POST tới sự kiện `delta` đầu tiên), chờ việc nền xong | `preload`, `turns`, `max_ttft_s`, `max_median_ttft_s`, `after_shift`, `max_turns`, `probe_chars`, `settle_timeout_s` (mặc định 180), `max_total_s` (mặc định 900) | lượt sau lượt đầu chậm hơn ngưỡng, trung vị quá ngưỡng; không gặp lượt cửa sổ dịch; quá `max_total_s` thì là lỗi của riêng kịch bản này |
| `bakeoff` | đúng lệnh `harness/bakeoff.py` (`main()` với `--models <model> --limit N`), đầu ra của nó được giữ lại | `limit` | thoát khác 0, không in / không ghi bảng có dòng của model, có câu `[LỖI: …]` |
| `nested_eval` | chạy lồng `run_eval` | `ids` (không được là `bakeoff`/`nested_eval`) | thoát khác 0, thiếu `report.md`/`raw.json`, thiếu kịch bản, có lỗi sinh |

`checks` của `reply` / `dm_session` (`harness/checks.py`, chỉ thư viện chuẩn): `thought_count`, `min_thoughts`, `max_thoughts`,
`no_adjacent_thoughts`, `thought_at_end`, `narration_forbidden`, `max_words`, `min_words`, `forbidden_phrases`, `directive_leak`
(mặc định bật), `persona_line` (mặc định bật), `language`, `dialogue_forbidden`, `dialogue_required_any`, `directive_echo` (chép 5
chữ liền nhau của chỉ đạo `((…))`), `say_forbidden` (từ không được nói trong lời thoại; Thought thì được), `forbidden_patterns`
(regex, cả Thought), `required_any` (phải có ít nhất một cụm), `prompt_includes` / `prompt_excludes` (kiểm trên prompt đã dựng).

## Kịch bản theo tính năng

| Tính năng | Kịch bản |
|---|---|
| F03 | `01-mo-dau`, `06-viet-hien-dai`, `07-co-trang`, `08-tieng-anh` |
| F05 | `f05-chi-dao` |
| F07 | `f07-thought-long`, `f07-thought-cuoi` |
| F09 | `f09-cam-xuc` |
| F10 | `f10-ky-uc`, `f10-tom-tat` |
| F12 | `f12-dm-xung-ten` (bộ card `tiem_sach_cu.json`) |
| F13 | `f13-dm-10-luot` |
| F14 | `f14-ttft` (ngưỡng: `wiki/decisions/nguong-ttft-f14.md`) |
| F15 | `f15-goi-y` |
| F17 | `f17-the-gioi` |
| F19 | `f19-viet-nhap` |
| F36 | `f36-bakeoff`, `f36-chay-long` |

Thời gian trên gemma4:12b (khoảng 11 tok/s): một lượt Story ~1 phút; `f09-cam-xuc` ~3 phút; `f13-dm-10-luot` ~2-3 phút;
`f14-ttft` ~7-10 phút (lượt đầu đọc cả prompt, rồi trích xuất, tóm tắt, prefill sau mỗi lượt). Cả bộ một lượt ~40 phút trở lên.

## Test

`backend/tests/test_harness_checks.py` (checks.py, 8 kịch bản gốc, judge) và `backend/tests/test_run_eval_kinds.py` (mọi luật máy
mới, hai chiều đúng/sai, và chạy trọn mọi kịch bản mới với Ollama giả, kể cả app thật trong tiến trình). Không test nào gọi mạng.
