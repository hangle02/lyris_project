# ② ENVIRONMENT — tay và mắt của AI

| File | Là gì |
|---|---|
| `rules.md` | Luật làm việc của AI (quy trình model_led, luật dự án Lyris, luật chữ giao diện, vòng lặp nhìn). `CLAUDE.md` ở gốc kéo file này vào. |
| `bot.mjs` | "Mắt" của harness: bật backend thật + LLM giả (cổng 8066) và Vite (8067), điều khiển Chrome qua DevTools Protocol, bấm như người dùng điện thoại 390×844, chụp ảnh, ghi `reports/latest/report.{json,html}`. `--quiet` cho verify.sh (luôn chạy `e2e.mjs`, bỏ qua `BOT_SCENARIO`; `report.json` ghi `scenario`), `--look` chỉ chụp các màn chính vào `reports/look/`. Lỗi đồ nghề (cổng bận, thiếu Chrome/venv/node_modules, server không lên, Chrome chết, quá `BOT_TIMEOUT_MS` = 15 phút) → `report.json` có `infra`, mã thoát 2. Mỗi lệnh CDP tối đa 60 giây. Ghi các tiến trình con vào `reports/.bot-pids.json`; lần sau tự dọn nếu lần trước bị giết ngang. Mọi hộp thoại (confirm/beforeunload) được ghi vào `c.dialogs`; `c.answerDialogs(false)` để bấm Huỷ. |
| `e2e.mjs` | Kịch bản của bot: 84 check có tên cố định (`CHECKS`), phủ mọi dòng Bot của các tính năng Đã có. Trang `wiki/features/F<NN>-*.md` tham chiếu đúng tên đó trong `## Tests`. Đi qua: chưa đăng nhập → chủ máy (hub, tài khoản, persona, profile, Studio, Khám phá, story, DM, quản trị) → đăng xuất → link mời → thành viên thứ hai (hub rỗng, chặn `#/admin`, nhân vật được chia sẻ). Lỗi mạng kịch bản cố ý gây ra (AI viết nháp lỗi, nhân vật không tồn tại, đúng lỗi 401 của request đang bay lúc đăng xuất) được ghi rõ và không tính là lỗi console; mọi lỗi khác (kể cả exception lúc đăng xuất) đều đỏ. "Không request ra ngoài" = mọi request chỉ tới origin của app bot (`127.0.0.1:8067`); cổng localhost khác (8000, Ollama 11434) cũng tính là ra ngoài. |
| `fake-server.py` | Backend Lyris thật với LLM giả, DB tạm trong `reports/bot/` (`BOT_DATA_DIR` chỉ được là thư mục bên trong `reports/` hoặc thư mục tạm, không bao giờ là `data/`, repo hay thư mục cha; tự tắt khi bot chết). Có sẵn chủ máy `@chumay` và thành viên `@thanhvien` (chưa đặt profile), cùng mật khẩu `bot mat khau 2026`. Không đụng `data/`, không gọi Ollama. Chạy bằng `backend/.venv/bin/python`. |
| `doctor.mjs` | Kiểm máy: Node ≥ 22, Chrome, `backend/.venv` (Python 3.12, pytest), `frontend/node_modules`, uv (tuỳ chọn), cổng 8066–8069 trống. Mặc định **không** gọi Ollama; `--ollama` mới hỏi Ollama có `gemma4:12b` không (chỉ lưu ý). `--hook` chạy lúc mở phiên Claude (không bao giờ gọi Ollama), chỉ lên tiếng khi có việc cần sửa. |
| `raw.mjs` | Ghi lời gốc của chủ dự án vào một file MỚI `wiki/raw/YYYY-MM-DD-<chủ-đề>.md` (không bao giờ sửa file cũ). `/plan` dùng lệnh này vì quyền sửa `wiki/raw/**` bị chặn. |
| `../.claude/settings.json` | **Tool Calling**: AI được tự chạy lệnh nào, và **không** được sửa file nào (`memory/features.json`, `wiki/raw/**`, `verification/**`). |
| `../harness.config` | `STACK=fullstack`, thư mục backend/frontend, cổng bot. |

```bash
node environment/doctor.mjs           # máy đủ đồ nghề chưa
node environment/bot.mjs              # bot bấm thử cả app, báo cáo có ảnh
node environment/bot.mjs --look       # chỉ chụp các màn chính để AI tự nhìn
```

Gỡ lỗi kịch bản: `BOT_SCENARIO=<file.mjs> node environment/bot.mjs` chạy một kịch bản khác (export `play(c)`); có `--quiet` (cách verify.sh gọi) thì biến này bị bỏ qua. Bot đưa tab lên trước, theo dõi trang bằng MutationObserver (không dùng rAF) và "tải lại" bằng cách đi qua `about:blank` (xem [learned.md](../wiki/learned.md)).

Cổng 8000/5173 là app của chủ dự án (`scripts/dev.sh`): bot và test không bao giờ đụng tới.
