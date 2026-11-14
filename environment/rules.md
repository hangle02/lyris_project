# Luật làm việc của AI trong harness Lyris

Bạn là **Model** (bộ não). Lyris là app nhập vai với nhân vật AI, tiếng Việt trước, chạy hoàn toàn trên một máy Mac
(FastAPI + SQLite ở `backend/`, React + Vite + TS ở `frontend/`, model `gemma4:12b` qua Ollama).
Bạn làm việc bên trong một harness gồm 4 phần:

| Phần | Ở đâu | Bạn dùng thế nào |
|---|---|---|
| ① Wiki | `wiki/` — `features/F<NN>-*.md` (mỗi tính năng một trang, có *Done when* + *Tests*), `screens/`, `decisions/`, `design/`, `learned.md`, `index.md`, `log.md`, `plan-checklist.md`; `raw/` là lời gốc của chủ dự án | ĐỌC trước khi code. Wiki là sự thật: code khác Wiki thì code sai (hoặc sửa trang + ghi lý do nếu chủ dự án đồng ý). |
| ② Environment | `environment/` — `rules.md` (trang này), `bot.mjs` + `e2e.mjs` (bot Chrome trên server LLM giả, cổng 8066/8067), `doctor.mjs` (kiểm máy); quyền trong `.claude/settings.json` | Tự chạy lệnh để kiểm tra, không đoán. Tự NHÌN giao diện bằng `bot.mjs --look`. |
| ③ Verification | `bash verification/verify.sh` (chấm tính năng) · `bash verification/plan-check.sh` (Wiki đủ để build chưa) | Chỉ `verify.sh` được chuyển 🟡 claimed → ✅ passing. |
| ④ Memory | `memory/features.json` (chỉ qua `node memory/features.mjs`), `memory/progress.md`, `memory/po-questions.md`, `wiki/log.md` | Đọc để biết đang ở đâu. **Không sửa tay `features.json`.** |

Cấu hình (stack, thư mục, cổng bot) nằm trong `harness.config`. Thiết kế chi tiết (dài) nằm trong `docs/`; wiki tóm tắt và dẫn link.
Thư mục `harness/` là bộ eval/bake-off model (khác harness này), chạy bằng `backend/.venv/bin/python harness/run_eval.py`.

## Người dùng không cần gõ lệnh /

- Người dùng nói **ý tưởng / tính năng mới** → làm như `.claude/commands/plan.md` (ghi `wiki/raw/`, hỏi lại nếu thiếu, viết trang feature).
- Người dùng trả lời câu hỏi / gõ "ok" sau khi bạn hỏi → làm tiếp bước đó của `.claude/commands/plan.md`.
- Người dùng nói "làm tiếp", "build", "làm đi" khi đã có kế hoạch → làm như `.claude/commands/build.md`
  (trước hết `node memory/features.mjs brief`).
- Người dùng xin **sửa tính năng có sẵn** → sửa trang trong `wiki/features/` trước, `node memory/features.mjs sync`, rồi làm như `/build`.

## Hợp đồng trang tính năng (wiki/features/F<NN>-<slug>.md)

```
# F07 — Tên tính năng
- **Trạng thái:** xem `memory/features.json` · **Phase:** …
- **Giai đoạn:** Đã có | Kế hoạch
- **Màn hình:** …

## Done when
- [ ] Unit: … (chứng minh bằng test có tên)
- [ ] Bot: … (bot trên server LLM giả; nêu route `#/…`, selector, aria-label)
- [ ] Model thật: … kịch bản `07-co-trang` (cần gemma4:12b thật; verify.sh bỏ qua nếu không có --real-model)

## Tests
- backend/tests/test_x.py::test_ten        (hoặc cả file backend/tests/test_x.py)
- frontend/src/…/x.test.ts
- bot: <tên check y hệt trong environment/e2e.mjs>
- model: <id kịch bản trong harness/scenarios/*.yaml>
```

- Không bao giờ tick `[x]`: trạng thái chỉ nằm trong `memory/features.json`.
- "Kế hoạch" luôn ⏳ cho tới khi code có thật và trang đổi sang "Đã có".
- Tính năng có dòng "Model thật" chỉ ✅ được khi chạy `verify.sh --real-model` (chủ dự án không dùng app lúc đó), và mỗi
  dòng đó phải nhắc `id` của một kịch bản `model: <id>` trong `## Tests` — thiếu thì `promote --gate` từ chối.
- Frontend test phải là `*.test.ts` (npm test chỉ chạy đuôi này). Mọi gạch đầu dòng trong Done when phải có ô `[ ]`.

## Chế độ duy nhất: model_led

Harness không xếp việc cho bạn. **Bạn (Model) tự xếp và tự làm**, harness chỉ giữ sổ và chấm:

1. Xem việc: `node memory/features.mjs brief`. Đọc `wiki/learned.md` (bài học cũ) trước khi bắt tay.
2. Tự xếp thứ tự: **phụ thuộc trước → quan trọng trước → theo số F**. Làm được nhiều tính năng liên tiếp trong một lượt.
3. Với mỗi tính năng: đọc trang `wiki/features/F<NN>-*.md` và các trang nó dẫn tới. **Viết test trước** cho từng dòng
   *Done when* (pytest / `node --test` / check trong `environment/e2e.mjs`), ghi tên test vào mục `## Tests`,
   chạy cho ĐỎ, rồi code cho XANH. Xong thì `node memory/features.mjs claim F<NN>` (🟡 = đã làm, **chưa** chứng minh).
4. Báo tiến độ sau mỗi mốc: `node memory/features.mjs note "F07 xong code, đang làm F08"`.
5. Chạy **Verification** cho mọi tính năng đã claim: `bash verification/verify.sh`
   (sửa nhanh thì `--quick` bỏ bộ test đầy đủ, nhưng `--quick` không bao giờ cho ✅). Một lần chạy đầy đủ mất 3–5 phút:
   gọi tool Bash với `timeout: 600000` (hoặc chạy nền), đừng để timeout mặc định 120 giây cắt ngang.
   - 🟢 xanh → verify.sh tự chuyển sang ✅ passing, ghi `wiki/log.md` và `memory/progress.md`.
   - 🔴 đỏ → đọc lỗi, sửa đúng chỗ, chạy lại. **Tối đa 3 lần đỏ cho một tính năng**: lần đỏ thứ 3 thì sổ TỰ chuyển ⛔
     (`memory/features.mjs fail --gate`). Khi đó thêm **một mục bài học** ở cuối `wiki/learned.md`
     (Sai · Vì sao · Luật rút ra · Nguồn) và một dòng `Câu hỏi cho PO: …` trong `memory/po-questions.md`.
     Chỉ PO mở lại: `node memory/features.mjs reopen F<NN> "PO: …"`. `reopen` không xoá số lần đỏ (trừ khi mở ⛔).
     Không chạy verify trên bản sao sổ (`LYRIS_HARNESS_HOME`) để "thử khỏi mất lượt": chế độ đó chỉ để tự kiểm harness.
   - Lỗi đồ nghề (cổng bận, thiếu Chrome/venv/node_modules, Chrome chết) bot ghi `infra` và không tính lần đỏ — sửa máy.
   - ✅ mà test của nó đỏ ở một lần verify sau → verify hạ về ⏳ (hồi quy). Sửa trang (Done when/Tests) sau khi ✅ thì
     `sync` cũng hạ về ⏳ và ghi thay đổi vào `memory/progress.md` để PO thấy.
   - Mã thoát 3 = xanh nhưng còn 🟡 (chạy `--quick`, hoặc cần model thật): chưa phải xong.
6. **Lặp tới khi mọi tính năng "Đã có" ✅ hoặc ⛔ có lý do.** Không kết thúc bằng "chắc là xong".

## Luật

1. **Không bao giờ tự nói "xong"** và không tự đánh dấu passing. Chỉ `verify.sh` xanh mới là xong.
2. **Viết test trước.** Mỗi dòng Done when có test chứng minh, và test đó được ghi trong `## Tests` của trang.
3. **Không sửa test cho xanh**, không nới điều kiện (ghi "4 thẻ" mà chấp nhận 5), không xoá/skip test của tính năng khác.
   Tên check của bot phải nói đúng điều nó kiểm. Không thu hẹp dòng Done when cho khớp app: app sai thì sửa app, Done when
   chưa rõ thì hỏi PO. Test bị skip không phải bằng chứng.
   Dòng `Model thật:` phải nhắc `id` một kịch bản trong `harness/scenarios/` và trang có `- model: <id>` trong `## Tests`
   (kịch bản đó thật sự kiểm điều dòng ấy nói — `--no-judge` chỉ chấm được luật máy, không chấm "giữ giọng", "làm theo").
4. **Không sửa tay:** `wiki/raw/` (lời gốc; chỉ thêm file mới bằng `node environment/raw.mjs`), `memory/features.json`
   (chỉ qua `features.mjs`), `verification/` (giám khảo), `data/` (DB thật).
5. **Không đoán khi Wiki không nói rõ.** Làm theo cách hợp lý nhất, ghi `(tạm chọn)` trong `wiki/decisions/`, và thêm một dòng
   `Câu hỏi cho PO: …` vào `memory/po-questions.md` để chủ dự án quyết.
6. **Luôn trả lời bằng tiếng Việt**, ngắn, dễ hiểu (thuật ngữ kỹ thuật tiếng Anh được). Tài liệu cũng tiếng Việt.

## Luật riêng của dự án Lyris

**Máy và dữ liệu**
- Python **chỉ** qua `backend/.venv/bin/python` (và `backend/.venv/bin/pytest`). Không bao giờ dùng `python3` của hệ thống.
- **Không bao giờ đụng `data/`** (DB thật của người dùng, `data/lyris.db`). Test và bot dùng DB tạm.
- Cổng 8000 (backend) và 5173 (Vite) có thể là app chủ dự án đang chạy: **không bật, không tắt, không gọi**.
  Bot và server test dùng 8066–8069 và phải tắt sau khi xong.
- Không Docker (chạy thẳng trên Mac). Không `ollama pull` / không tải model mới. Không gọi Ollama trừ `verify.sh --real-model`
  (và chỉ khi chủ dự án không dùng app: dùng chung GPU, RAM 24GB).
- `num_ctx` luôn là **8192** (một hằng số cho mọi lời gọi: chat, trích xuất, tóm tắt, gợi ý, prefill) — đổi là phá cache prompt.
- Không thêm thư viện npm/pip mới. Bot dùng WebSocket có sẵn của Node 22 + Chrome DevTools Protocol.
- Không git commit/push trừ khi chủ dự án bảo.

**Chữ trên giao diện** (test `frontend/src/copyWords.test.ts` quét mọi `.tsx`)
- Giao diện gọi là **"story"** (Story mới, Thiết lập story). "câu chuyện" chỉ có trong CTA **"Bước vào câu chuyện"**.
- **Ẩn chữ kỹ thuật:** không hiện model, Ollama, token, credits, RAM, trạng thái máy. Chờ thì ba chấm nhảy. Thông tin máy và công cụ
  nâng cao nằm trong mục **"Nâng cao"** gập sẵn. Lỗi là câu dễ hiểu, chữ gốc dưới "Chi tiết".
- Thẻ thoại ở Story **không hiện cặp ngoặc kép ngoài cùng** (chữ đã lưu giữ nguyên).
- Ở lượt người chơi: `"…"` là lời người chơi (thành thẻ thoại); `*"…"*` là trích dẫn / lời người khác, ở lại trong dẫn truyện.
- Placeholder ngắn, vừa một dòng ở màn **390px** (Story: `Nhập lời thoại vào "…"`, DM: "Nhắn tin…"); nhãn đầy đủ để ở `aria-label`.
- Lưới thẻ: số cột cố định (điện thoại 2, máy tính bảng 3, máy tính 5), các ô trong một hàng **cao bằng nhau**, hàng cuối thiếu thì để trống.
- Người chơi trong prompt và wiki luôn là `{{user}}`. Không ghi tên/email thật của chủ dự án.

## Design — nhìn rồi mới claim

- Trước khi làm giao diện: đọc `wiki/design/README.md`, `wiki/design/style.md` và `DESIGN.md`. Màu và font chỉ lấy từ token có sẵn.
- **Vòng lặp nhìn:** sau khi làm giao diện, chạy `node environment/bot.mjs --look` rồi mở ảnh trong `reports/look/` bằng **Read**.
  Xem ở 390px trước, cả hai theme. Chấm 1–5: (a) nhìn 3 giây biết bấm gì · (b) đúng màu/font `style.md` · (c) chữ rõ, không bị che/cắt,
  không tràn ngang · (d) không lộ chữ kỹ thuật, đúng luật chữ ở trên · (e) trông như app thật. Ý nào < 4 → sửa → chụp lại.
  Ghi điểm: `node memory/features.mjs note "design F07: a5 b4 c5 d5 e4"`.
- Tính năng có giao diện thì thêm check vào `environment/e2e.mjs` (tìm phần tử như người dùng thấy: vai trò, aria-label, chữ trên nút)
  và ghi đúng tên check vào `## Tests` của trang (`bot: …`).

## Đồ nghề — dùng đúng lúc, đừng đoán

| Muốn | Dùng |
|---|---|
| Biết đang ở đâu | `node memory/features.mjs brief` · `list` · `show F07` |
| Máy đủ đồ nghề chưa | `node environment/doctor.mjs` |
| Chạy test một tính năng | `backend/.venv/bin/pytest -q tests/test_x.py::test_y` (trong `backend/`) · `node --experimental-strip-types --test src/…/x.test.ts` (trong `frontend/`) |
| Nhìn giao diện | `node environment/bot.mjs --look` → Read ảnh trong `reports/look/` |
| Bot bấm thử cả app | `node environment/bot.mjs` → `reports/latest/report.html` + ảnh |
| Chấm và chuyển ✅ | `bash verification/verify.sh [F07 …]` (`--quick` khi đang sửa; `--real-model` khi cần model thật) |
| Wiki đủ để build chưa | `bash verification/plan-check.sh` |
| Hành vi model thật | `backend/.venv/bin/python harness/run_eval.py` (cần Ollama; chỉ khi chủ dự án không dùng app) |
| Ghi lời gốc của chủ dự án | `node environment/raw.mjs <chủ-đề> "lời nguyên văn"` (luôn tạo file mới trong `wiki/raw/`) |
| Chạy app cho người dùng | `bash scripts/dev.sh` (cổng 8000/5173; chỉ khi chủ dự án muốn — script tự dừng nếu app đang chạy) |

Không có công cụ nào chạy được thì ghi một dòng vào `memory/progress.md` (`features.mjs note`) và dùng cái còn lại — không bỏ bước nhìn.
