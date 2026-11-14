# ③ VERIFICATION — giám khảo chấm đậu/rớt

Model chỉ được **claim** (🟡). Chỉ hai script ở đây chấm, và chỉ `verify.sh` được chuyển 🟡 → ✅. AI không được sửa thư mục này.

## verify.sh — chấm tính năng

```bash
bash verification/verify.sh                    # chấm mọi tính năng 🟡 claimed + soát hồi quy mọi tính năng ✅
bash verification/verify.sh F07 F08            # chấm đúng mấy tính năng này (F7 cũng được)
bash verification/verify.sh --quick F07        # bỏ bộ test đầy đủ — để sửa nhanh, KHÔNG BAO GIỜ cho ✅ (mã thoát 3)
bash verification/verify.sh --real-model F09   # thêm bước model thật (Ollama + gemma4:12b; chủ dự án không dùng app lúc đó)
```

Một lần chạy đầy đủ mất 3–5 phút (pytest ~45 giây, bot ~90 giây, test tham chiếu, build): gọi tool Bash với
`timeout: 600000` hoặc chạy nền.

| Bước | Kiểm gì |
|---|---|
| S | `node memory/features.mjs sync`: sổ luôn khớp wiki. Trang sai hợp đồng thì dừng đỏ (không tính lần đỏ). ✅ mà Done when/Tests đổi thì về ⏳. |
| 0 | Mỗi tính năng có `## Tests`; mọi tham chiếu tồn tại (file, tên hàm test, kịch bản `model:`); có Done when `Unit:` thì có test unit, có `Bot:` thì có dòng `bot: …`. Tính năng "Kế hoạch", chưa claim hay đang ⛔ thì đỏ. Các tính năng ✅ cũng được kiểm tham chiếu (soát hồi quy). |
| 1 | Chạy đúng các test được tham chiếu: `pytest -v` gộp mọi node id một lần, `node --test` từng file. **Mỗi tham chiếu phải có ít nhất một test thật sự PASSED**: node id cụ thể bị skip/xfail thì đỏ; file mà không test nào qua (rỗng, toàn skip/todo) thì đỏ. Riêng tham chiếu cả file backend được phép có vài test skip có chủ đích (vd `test_isolation_sweep.py`) miễn là có test qua. |
| 2 | Bộ test đầy đủ: `backend/.venv/bin/pytest -q` · `npm test` · `npm run typecheck` · `npm run build`. `--quick` bỏ bước này. Mỗi bộ tối đa 20 phút. |
| 3 | `node environment/bot.mjs --quiet` (tối đa 25 phút). Bot luôn chạy kịch bản chuẩn `environment/e2e.mjs`: verify bỏ `BOT_SCENARIO` khỏi môi trường và đối chiếu `scenario` trong `report.json`. Bot phải xanh, và mọi `bot: <tên>` của tính năng phải có trong `reports/latest/report.json` và xanh. |
| 4 | Dòng `Model thật:` phải nhắc `` `id` `` của một kịch bản `model: <id>` trong Tests (thiếu → tính năng 🟡 "chưa có kịch bản chứng minh", không ✅). Không có `--real-model` → "bỏ qua (cần model thật) — chưa thể ✅". Có `--real-model` và Ollama có `gemma4:12b` → `harness/run_eval.py --no-judge --only <id>…` đúng các kịch bản được tham chiếu; mỗi kịch bản phải không lỗi sinh, không lỗi máy. Không tự bật Ollama, không tải model. |

Kết quả:
- 🟢 → `memory/features.mjs promote F07 --gate` (✅), thêm dòng vào `wiki/log.md` và `memory/progress.md`. `promote` tự từ
  chối nếu sổ khác wiki, đã đỏ 3 lần, hoặc còn dòng `Model thật` chưa có kịch bản.
- 🔴 tính năng 🟡 → `attempts` +1 (`fail --gate "lý do"`). **Lần đỏ thứ 3 thì sổ tự ⛔ blocked**; Model ghi một mục
  `wiki/learned.md` và một `Câu hỏi cho PO`. Chỉ PO mở lại: `reopen F07 "PO: …"`.
- 🔴 tính năng ✅ (test của nó đỏ, hoặc check bot của nó đỏ/mất) → **hạ về ⏳** (`demote --gate`), ghi `progress.md`.
- Lỗi đồ nghề — bot ghi `infra` (cổng bận, thiếu Chrome/venv/node_modules, server không lên, Chrome chết, bot quá giờ),
  thiếu `backend/.venv/bin/pytest`, thiếu `frontend/node_modules`, bộ test treo quá giờ — **không tính lần đỏ**, lý do in đúng.
- Mã thoát: `0` xanh (đã ✅, không hồi quy) · `1` đỏ · `2` sai tham số / cấu hình (vd `LYRIS_HARNESS_HOME` trỏ về repo) ·
  `3` xanh nhưng còn 🟡 (`--quick`, cần model thật, hoặc thiếu kịch bản model thật). `--quick` không bao giờ thoát 0.
- `reports/verify.json`: thời điểm, từng bộ test, bot (kể cả `infra`), model thật (từng kịch bản), từng tính năng
  (ok, lý do, promoted, attempts), danh sách hồi quy.

## plan-check.sh — Wiki đủ để build chưa

```bash
bash verification/plan-check.sh
```

Kiểm: `wiki/overview.md` trả lời đủ 8 phần của `wiki/plan-checklist.md` · mọi trang `features/F<NN>-*.md` đúng hợp đồng
(và qua được bộ đọc của `memory/features.mjs`: gạch đầu dòng Done when thiếu ô `[ ]`, frontend `.test.tsx` đều đỏ) ·
tính năng "Đã có" có ≥ 2 dòng Done when và ≥ 1 tham chiếu Tests: file **và tên hàm test** có thật, `bot: <tên>` có trong
`CHECKS` của `environment/e2e.mjs`, `model: <id>` có trong `harness/scenarios/` · không có dòng Done when mơ hồ (mã `F01`,
`§10.3` hay `()` trơ trọi không tính là cụ thể) · `memory/features.json` khớp wiki · `design/style.md` có ≥ 5 màu và font ·
không còn TODO / `???` (trừ `raw/` và chỗ nhóm điền đã biết). Dòng `!` chỉ là lưu ý (vd dòng `Model thật` chưa có kịch bản).

## Tự kiểm harness trên dữ liệu giả

`LYRIS_HARNESS_HOME=<thư mục KHÁC repo, có wiki/ và memory/>` cho cả `features.mjs`, `verify.sh`, `plan-check.sh` dùng
wiki, sổ và `reports/` ở thư mục đó (code và test vẫn là của repo). So sánh sau khi giải symlink: trỏ về chính repo hay
sổ thật thì verify thoát 2. Chỉ ở chế độ này mới thay được bot bằng `LYRIS_HARNESS_BOT="<lệnh>"` (ngoài chế độ này biến
đó làm verify thoát 2). Chế độ này **không chấm tính năng nào trùng id + tên với sổ thật** (không dùng bản sao sổ để
"thử khỏi mất lượt đỏ"). Sổ thật `memory/features.json` không bị đụng ở chế độ này.
