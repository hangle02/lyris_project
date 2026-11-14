# 8 phần một Wiki app phải có

Dùng để **hỏi lại khi một ý tưởng mới còn thiếu**. Khi chủ dự án đưa một ý tưởng (một tính năng, một màn hình, một thay đổi), đi qua 8 phần dưới đây. Phần nào chưa trả lời được từ `raw/`, code hay `docs/` thì hỏi lại bằng đúng các câu gợi ý, trước khi viết trang `features/` hay `screens/` và trước khi code.

Cách dùng:
1. Ghi ý tưởng nguyên văn vào `raw/YYYY-MM-DD-<chủ-đề>.md`.
2. Đánh dấu từng phần: có rồi / thiếu / không áp dụng.
3. Hỏi lại các phần thiếu, gom thành một lượt hỏi ngắn (tối đa 3-4 câu, câu quan trọng trước).
4. Câu trả lời cũng ghi vào `raw/` (file mới có ngày), rồi mới viết trang wiki và cập nhật `index.md`, `log.md`.

Không đoán thay chủ dự án ở các phần 1, 2, 3 và 7. Phần 5, 6, 8 có thể đề xuất trước rồi xin xác nhận. Chủ dự án không có mặt thì tạm chọn cách hợp lý, ghi vào `decisions/` với chữ "(tạm chọn)" và thêm câu hỏi vào `memory/po-questions.md`; không bỏ trống, không đoán im lặng.

**Kiểm tự động:** `bash verification/plan-check.sh` kiểm phần máy kiểm được của checklist này trên cả wiki (không cần AI): mỗi trang `features/F<NN>-<slug>.md` có dòng đầu `# F<NN> — …`, có Giai đoạn, "Done when" có dòng Unit / Bot / Model thật và không có `[x]`, "Tests" chỉ trỏ tới test có thật; có trang màn hình, có style; không còn chỗ đánh dấu việc chưa viết. Thoát 0 là 🟢 đủ để build; khác 0 thì in ra phần còn thiếu. Phần cần người trả lời (ý tưởng, vòng trải nghiệm, phong cách) vẫn phải hỏi lại theo các câu bên dưới.

---

## 1. Ý tưởng và người dùng

**Phải có:** app hoặc tính năng này là gì, cho ai (chủ máy, người được mời, hay cả hai), giải quyết điều gì, khác WHIF ở đâu.

**Hỏi lại khi thiếu:**
- Ai sẽ dùng cái này: chỉ bạn, hay cả người được mời?
- Bạn đang gặp chuyện gì khiến muốn có nó? Có ví dụ một lần chơi cụ thể không?
- WHIF làm việc này thế nào, và bạn muốn giống hay khác chỗ nào?

**Lyris đang có:** [overview.md](overview.md) (Lyris là gì, cho ai, khác WHIF), [raw/2026-11-12-plan-goc.md](raw/2026-11-12-plan-goc.md), [docs/plan.md](../docs/plan.md) §1.

## 2. Vòng trải nghiệm chính

**Phải có:** đường đi của người chơi từ lúc mở app tới lúc chơi và quay lại; tính năng mới nằm ở bước nào của vòng đó.

**Hỏi lại khi thiếu:**
- Người chơi bắt đầu từ đâu (Khám phá, hồ sơ nhân vật, trong chat, Studio)?
- Bấm gì, thấy gì ngay sau đó, và kết thúc ở đâu?
- Nó xảy ra mỗi lượt chat, mỗi story, hay chỉ thỉnh thoảng?

**Lyris đang có:** vòng Khám phá → hồ sơ nhân vật → Bước vào câu chuyện → chat Story/DM → ngăn trái tim, ở [overview.md](overview.md) "Trải nghiệm chính".

## 3. Tính năng và "Done when"

**Phải có:** mỗi tính năng một trang `features/F<NN>-<slug>.md` (định dạng ở [README.md](README.md) mục "Trang tính năng"), có Giai đoạn (Đã có / Kế hoạch), cách hoạt động, danh sách **"Done when"** gồm các dòng `Unit:` (test nào phải qua), `Bot:` (bấm gì → thấy gì trên trình duyệt, chạy với LLM giả) và `Model thật:` (chỉ kiểm được với model thật), và mục **"Tests"** trỏ tới test có thật. Trạng thái ⏳ / 🟡 / ✅ / ⛔ không ghi ở đây mà ở `memory/features.json`.

**Hỏi lại khi thiếu:**
- Làm xong thì bạn thử thế nào để biết nó đúng? Mô tả một lần thử.
- Có gì nó **không** được làm? (Ví dụ: không tự hiện, không viết thay người chơi.)
- Mặc định bật hay tắt? Người chơi tắt được ở đâu?
- Phải xong ngay, hay làm bản nhỏ trước rồi thêm sau?

**Lyris đang có:** [features/](features/), tiến độ theo phase ở [overview.md](overview.md), chi tiết ở [docs/phase1.md](../docs/phase1.md) đến [docs/phase4.md](../docs/phase4.md), [docs/auth.md](../docs/auth.md).

## 4. Màn hình và điều hướng

**Phải có:** mỗi màn hình một trang trong `screens/`: route (`#/...`), vào từ đâu, ra đi đâu, có thanh tab hay không, những gì hiện trên đó, trạng thái rỗng / đang tải / lỗi.

**Hỏi lại khi thiếu:**
- Cái này nằm ở màn hình nào có sẵn, hay cần màn hình mới?
- Mở bằng nút nào? Trên điện thoại nút đó nằm ở đâu?
- Đây là trang riêng, sheet trượt từ dưới, hay một mục trong menu "+"?
- Khi chưa có dữ liệu thì màn hình nói gì?

**Lyris đang có:** [screens/](screens/), bảng route ở [docs/design-impl.md](../docs/design-impl.md) §5 và §16, ba tab (Khám phá, Tương tác, Studio) ở [design/style.md](design/style.md) §6.

## 5. Dữ liệu và tài khoản

**Phải có:** cần lưu gì, ở bảng nào, thuộc tài khoản nào; ai thấy được (riêng tư, công khai, nhân vật mẫu); nâng cấp DB cũ có mất gì không; regenerate, sửa, xoá một lượt có làm hỏng nó không.

**Hỏi lại khi thiếu:**
- Cái này của riêng một story, của một nhân vật, hay của cả tài khoản?
- Người được mời có thấy không? Chủ nhân vật công khai sửa thì story của người khác có đổi không?
- Xoá story hay xoá nhân vật thì nó đi đâu?
- Có cần đưa vào dữ liệu train sau này không?

**Lyris đang có:** [docs/plan.md](../docs/plan.md) §6, [docs/accounts.md](../docs/accounts.md), [docs/auth.md](../docs/auth.md) §2 và §4, migration `backend/lyris/db/migrations/`, [decisions/](decisions/).

## 6. Model / AI và giới hạn phần cứng

**Phải có:** tính năng có gọi model không, gọi lúc nào (trong lượt chat hay việc nền), thêm bao nhiêu token vào prompt và đặt ở khối nào, làm chậm lượt chat bao nhiêu, có phá cache prompt không; harness kiểm gì.

Giới hạn hiện tại: MacBook M2 24GB, một model `gemma4:12b` (khoảng 16GB khi nạp), context 8,192 token, tối đa 2 lượt sinh cùng lúc. Một lời gọi trích xuất mất 15-35 giây. Lượt trả lời của nhân vật luôn được ưu tiên.

**Hỏi lại khi thiếu:**
- Nó cần có ngay trong câu trả lời, hay chờ vài chục giây (chạy nền) cũng được?
- Nếu làm chậm lượt chat thêm vài giây thì bạn có chấp nhận không?
- Nhân vật có được biết điều này không, hay chỉ người chơi thấy?
- Model trả sai thì nên hiện gì?

**Lyris đang có:** [overview.md](overview.md) "Chạy ở đâu", [docs/plan.md](../docs/plan.md) §3, §7, §9, [docs/phase3.md](../docs/phase3.md) §0, [docs/phase4.md](../docs/phase4.md) §0, `harness/`.

## 7. Phong cách thiết kế

**Phải có:** dùng thành phần nào có sẵn, màu và chữ nào, trông thế nào ở 390px và cả hai theme; chữ trên giao diện bằng tiếng Việt; không lộ chữ kỹ thuật.

**Hỏi lại khi thiếu:**
- Có ảnh chụp hay app nào làm giống cái bạn muốn không?
- Cái này nên nổi bật hay kín đáo (nằm trong "Nâng cao")?
- Chữ trên nút bạn muốn gọi là gì?

**Lyris đang có:** [design/README.md](design/README.md) (nguyên tắc), [design/style.md](design/style.md) (màu, chữ, thành phần), [raw/DESIGN.md](raw/DESIGN.md), [design/assets.md](design/assets.md), [design/credits.md](design/credits.md).

## 8. Kiểm tra và tiêu chí xong

**Phải có:** lệnh kiểm tra phải qua, điều cần thử tay (trên Mac và iPhone, 390px trước), chỗ phải tắt app của chủ dự án trước khi làm (migration, đổi model), và cách quay lại nếu hỏng (sao lưu `data/lyris.db`).

Lệnh thường dùng:
- Cổng chấm: `bash verification/verify.sh F<NN>` (chạy Tests của trang, typecheck, build, bot; chỉ nó chuyển 🟡 → ✅). Dòng "Model thật" chỉ chấm khi thêm `--real-model`.
- Wiki đủ để build chưa: `bash verification/plan-check.sh`.
- Backend: `backend/.venv/bin/pytest`.
- Frontend: `npm test`, `npm run typecheck`, `npm run build` (trong `frontend/`).
- Thiết kế: `lint.mjs --app` và `inspect.mjs --app` của skill `design-taste-frontend` ([design/README.md](design/README.md) §11).
- Hành vi model: `backend/.venv/bin/python harness/run_eval.py` (cần Ollama, chỉ chạy khi chủ dự án không dùng app).

**Hỏi lại khi thiếu:**
- Bạn đang mở app không? Có cần tắt để làm phần này không?
- Bạn muốn tự thử trên điện thoại trước khi coi là xong không?
- Có story nào cụ thể bạn muốn dùng để thử?

**Lyris đang có:** mục "Kiểm tra" ở cuối mỗi phase trong [docs/plan.md](../docs/plan.md) §10, [docs/auth.md](../docs/auth.md) §8, [docs/phase4.md](../docs/phase4.md) §14, bài học ở [learned.md](learned.md).
