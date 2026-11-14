# ④ MEMORY — sổ tay của harness Lyris (model_led)

| File | Là gì |
|---|---|
| `features.json` | Trạng thái từng tính năng: ⏳ pending · 🟡 claimed · ✅ passing · ⛔ blocked. Đồng bộ từ `wiki/features/F<NN>-*.md`. **Không ai sửa tay.** |
| `features.mjs` | Lệnh đọc/ghi sổ. Model dùng: `sync` · `list` · `brief` · `show F07` · `claim F07` · `block F07 "lý do"` · `reopen F07 ["PO: …"]` · `note "…"`. Chỉ `verification/verify.sh` dùng `promote --gate`, `fail --gate` và `demote --gate`. |
| `progress.md` | Nhật ký tiến độ (Model `note`; harness tự ghi khi claim / đỏ / passing / blocked). |
| `po-questions.md` | Câu hỏi AI để lại cho chủ dự án (PO) khi Wiki chưa nói rõ. Mỗi câu một dòng `Câu hỏi cho PO: …`. |

Mỗi mục trong `features.json`:

```json
{ "id": "F07", "title": "…", "page": "wiki/features/F07-….md", "phase": "…", "stage": "built | planned",
  "done": ["Unit: …", "Bot: …", "Model thật: …"], "tests": ["backend/tests/test_x.py::test_y", "frontend/src/…/x.test.ts", "bot: …", "model: 07-co-trang"],
  "state": "pending | claimed | passing | blocked", "attempts": 2, "verified_at": "…", "reason": "…" }
```

- `sync` giữ trạng thái khi **cùng id, cùng tên và cùng nội dung**. Đổi tên = đổi nghĩa → về ⏳. ✅ mà Done when, Tests hay
  Giai đoạn đổi → về ⏳ (✅ chỉ đúng với nội dung đã được chấm); 🟡/⛔ giữ nguyên. Mọi thay đổi Done when/Tests được ghi vào
  `progress.md` để PO thấy. Trang lỗi hợp đồng (kể cả gạch đầu dòng Done when thiếu ô `[ ]`) thì `sync` dừng và in hết lỗi.
- `stage: planned` (trang ghi "Giai đoạn: Kế hoạch") luôn ⏳: không claim, không ✅ được.
- `attempts` = tổng số lần `verify.sh` chấm đỏ tính năng này kể từ lần ✅ hay lần PO mở ⛔ gần nhất (không phải "liên tiếp":
  một lần xanh mà chưa ✅ không xoá). Lần đỏ thứ 3 thì `fail --gate` **tự chuyển ⛔** (lý do = lỗi của lần đó); `promote`
  từ chối khi đã đỏ 3 lần. `reopen` giữ `attempts`; chỉ mở ⛔ (cần câu trả lời của PO: `reopen F07 "PO: …"`) mới xoá.
- `promote --gate` còn từ chối khi sổ khác trang wiki (chưa `sync`) hoặc khi có dòng `Model thật:` chưa nhắc `id` của một
  `model: <id>` trong Tests.
- `demote --gate`: verify thấy test của một tính năng ✅ đỏ (hồi quy) → về ⏳.

🟡 claimed = "Model nói đã làm". ✅ passing = "máy đã chứng minh". Hai thứ này khác nhau.
