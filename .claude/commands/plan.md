---
description: Ý tưởng mới cho Lyris → Wiki và kế hoạch tính năng (Harness Plan)
argument-hint: <ý tưởng: tính năng, màn hình hay thay đổi bạn muốn>
---

Đọc `environment/rules.md` trước. Trả lời tiếng Việt, ngắn, thân thiện. Ý tưởng của chủ dự án:

$ARGUMENTS

Làm lần lượt. **Không viết code app ở lệnh này.**

1. **Ghi nguyên văn** ý tưởng vào file MỚI trong `wiki/raw/`: `node environment/raw.mjs <chủ-đề-ngắn> "<lời nguyên văn>"`
   (tạo `wiki/raw/YYYY-MM-DD-<chủ-đề>.md` dưới dòng `## <ngày giờ>`). Quyền sửa `wiki/raw/**` bị chặn: không sửa file cũ nào.
2. **Đối chiếu 8 phần** của `wiki/plan-checklist.md` (ý tưởng và người dùng · vòng trải nghiệm chính · tính năng + Done when ·
   màn hình và điều hướng · dữ liệu và tài khoản · model/AI và giới hạn phần cứng · phong cách · kiểm tra và tiêu chí xong).
   Lấy câu trả lời từ `wiki/`, code và `docs/` trước khi hỏi.
   - Nếu còn thiếu phần 1, 2, 3 hoặc 7 (không được đoán thay), hoặc thiếu từ 3 phần trở lên: đưa ra **tối đa 5 câu hỏi**,
     mỗi câu 2–4 lựa chọn A/B/C ngắn, cụ thể, lựa chọn đầu là gợi ý tốt nhất ghi "(gợi ý)".
     Ví dụ: `2. Mở ở đâu? A) Mục mới trong menu "+" ở ô nhập (gợi ý)  B) Nút trên thanh đầu chat  C) Trong "Nâng cao"`
     Kết thúc bằng: "Trả lời kiểu **1A 2C 3B**, thêm ý riêng nếu muốn, hoặc gõ **ok** để lấy hết gợi ý." rồi **dừng**.
   - Khi chủ dự án trả lời (kể cả tin nhắn sau, không có /plan): ghi câu hỏi + câu trả lời vào file MỚI
     (`node environment/raw.mjs <chủ-đề>-tra-loi "…"`; câu không trả lời thì ghi "dùng gợi ý"), rồi làm tiếp bước 3.
   - Ý tưởng đủ rõ thì làm luôn bước 3.
3. **Viết Wiki** (theo `wiki/README.md`):
   - `wiki/features/F<NN>-<slug>.md`, số tiếp theo sau trang lớn nhất, hai chữ số. Đúng hợp đồng trong `environment/rules.md`:
     dòng đầu `# F<NN> — Tên`; `Trạng thái: xem memory/features.json`; `Phase`; **`Giai đoạn: Kế hoạch`** (chưa có code); `Màn hình`.
   - `## Done when`: mỗi dòng `- [ ] Unit: …` / `- [ ] Bot: …` / `- [ ] Model thật: …`, đo được (số, route `#/…`, selector,
     aria-label, tên hàm), không chữ cảm tính ("đẹp", "mượt" mà không có số). Không tick `[x]`.
   - `## Tests`: tên test sẽ viết (`backend/tests/test_x.py::test_y`, `frontend/src/…/x.test.ts`, `bot: <tên check>`).
   - Màn hình mới → `wiki/screens/`; lựa chọn quan trọng → `wiki/decisions/` (ngày, ai quyết, bối cảnh, lựa chọn, vì sao;
     phần tự chọn ghi `(tạm chọn)`). Có giao diện thì theo `wiki/design/style.md` và luật chữ trong `environment/rules.md`.
   - Chỗ chưa rõ: chọn cách hợp lý, thêm `Câu hỏi cho PO: …` vào `memory/po-questions.md`.
   - Cập nhật `wiki/index.md`, thêm một dòng cuối `wiki/log.md` (`- YYYY-MM-DD · việc · [trang](…)`); nếu đổi bức tranh chung thì sửa `wiki/overview.md`.
   - Thiết kế dài (API, migration, prompt) để ở `docs/`, trang wiki dẫn link.
4. Chạy `node memory/features.mjs sync` rồi `bash verification/plan-check.sh`. 🔴 thì bổ sung Wiki rồi chạy lại, tối đa 3 lần.
5. **Trình bày** cho chủ dự án duyệt:
   - Mỗi tính năng một dòng: `F<NN> · tên — điều quan trọng nhất trong Done when`.
   - Màn hình / chữ trên nút sẽ dùng (nếu có giao diện).
   - Các câu hỏi cho PO.
   - Kết quả plan-check (🟢/🔴).
   Kết thúc bằng: "Bạn là PO: muốn sửa gì cứ nói. Ổn rồi thì gõ **/build**."
6. Chủ dự án muốn sửa: sửa trang trong `wiki/features/`, `node memory/features.mjs sync`, chạy lại plan-check.
   Khi bắt đầu làm (ở /build), đổi trang sang `Giai đoạn: Đã có` lúc code đã có thật, rồi `sync`.
