# Lyris là gì

Lyris là app nhập vai với nhân vật AI, kiểu WHIF, chạy hoàn toàn trên một máy Mac ở nhà. Bạn chọn một nhân vật (hoặc tự tạo), bước vào một story với nhân vật đó và trò chuyện. AI dẫn truyện và đóng vai nhân vật; chỉ bạn điều khiển persona của mình.

Khẩu hiệu (DESIGN.md): *"Nơi những tâm hồn trang sách bước ra sưởi ấm thực tại"*. Cảm giác muốn có: lãng mạn, chữa lành, gần gũi nhưng bí ẩn, như đọc tiểu thuyết dưới ánh nến.

Tên cũ là Nora. Đổi thành Lyris ngày 2026-11-12; thư mục repo vẫn là `nora`.

Ý tưởng gốc: [raw/2026-11-12-plan-goc.md](raw/2026-11-12-plan-goc.md). Kế hoạch đầy đủ: [docs/plan.md](../docs/plan.md).

## Cho ai

- **Chủ máy:** người sở hữu máy Mac. Tài khoản đầu tiên, giữ mọi dữ liệu cũ, là người duy nhất tạo mã mời, đặt lại mật khẩu và xem thông tin máy.
- **Người được mời:** bạn bè có mã mời do chủ máy tạo. Mỗi người có persona, nhân vật, story riêng. Không ai đọc được story của người khác, kể cả chủ máy (trong app).
- Người lạ cùng Wi-Fi không tự tạo được tài khoản.

Chi tiết: [docs/accounts.md](../docs/accounts.md), [docs/auth.md](../docs/auth.md).

## Chạy ở đâu

| Phần | Hiện tại |
|---|---|
| Máy | MacBook Apple M2 (không phải M2 Pro), RAM 24GB |
| Model | `gemma4:12b` qua Ollama, context 8,192 token. Việc nền (trích xuất cảm xúc, ký ức, tóm tắt) dùng chính model chat, vì nạp thêm model thứ hai sẽ tràn RAM |
| Tìm ký ức | Theo từ khoá; nếu máy có `bge-m3` thì tìm thêm theo nghĩa |
| Backend | FastAPI + một file SQLite (`data/lyris.db`), chỉ nghe ở `127.0.0.1:8000` |
| Frontend | React + Vite + Tailwind, ưu tiên điện thoại |
| Mở từ điện thoại | Cùng Wi-Fi, qua Vite cổng 5173 (`scripts/dev.sh`) |
| Mở từ xa | Sau này qua Tailscale Serve (Phase 6, chưa làm) |

Mọi story và chat chỉ nằm trên máy Mac. Không gửi gì ra ngoài.

## Trải nghiệm chính

1. **[Khám phá](screens/explore.md)** (tab trái): thẻ nhân vật nổi bật, lọc theo cảm xúc ("Chữa lành", "Dịu dàng", "Bí ẩn nội tâm", "Tình đầu"), lưới thẻ nhân vật bằng nhau, phần "Nhân vật được chia sẻ" từ tài khoản khác.
2. **[Hồ sơ nhân vật](screens/character-profile.md)**: ảnh lớn, tên, vai trò, tag, "Lời nói đặc trưng", tab "Giới thiệu" và "Thiết lập" (chỉ xem, không sửa). Không bao giờ hiện bí mật của nhân vật.
3. **[Bước vào câu chuyện](screens/start-story-sheet.md)**: sheet chọn persona. Mở "Tuỳ chỉnh story" để đổi bối cảnh, lời mở đầu, ngôn ngữ, Story/DM, kiểu quan hệ, ngôi kể, đại từ dẫn truyện, kiểu suy nghĩ, có đọc suy nghĩ hay không.
4. **[Chat](screens/chat-story.md)**, hai chế độ chung một dòng thời gian:
   - **[Story](features/F01-che-do-story.md)**: văn tiểu thuyết. Dẫn truyện nghiêng không khung, lời thoại trong thẻ, suy nghĩ của nhân vật trong thẻ làm mờ "Chạm để lắng nghe".
   - **[DM](features/F02-che-do-dm.md)**: giao diện nhắn tin, bong bóng, avatar, mốc giờ.
   - [Nút "+"](features/F16-menu-cong.md) ở ô chat: "Nhận gợi ý" (chỉ khi bấm), "Xem sự kiện", "Gửi hình ảnh" (Sắp có).
5. **Ngăn trái tim** trong chat ([cảm xúc](features/F09-ma-tran-cam-xuc.md), [trí nhớ](features/F10-tri-nho.md), [sổ thế giới](features/F17-so-the-gioi.md)): chỉ dẫn diễn xuất, 6 thanh cảm xúc, nơi chốn và thời gian, ký ức (quên được), "Thế giới đã mở khoá".
6. **[Tương tác](screens/hub.md)** (tab giữa): danh sách story đang chơi. **[Studio](features/F18-xuong-nhan-vat.md)** (tab phải): tạo và sửa nhân vật, sổ thế giới, bật "Công khai".

## Khác WHIF ở đâu

Lấy từ góp ý của chủ dự án trong `raw/`:

- **AI không viết thay người chơi.** Nhân vật phản ứng với hành động bạn viết (ví dụ "run rẩy"), được tả thêm trạng thái nhỏ nó nhìn thấy, nhưng không viết lời, hành động hay quyết định mới cho persona. ([raw](raw/2026-11-12-quyen-cua-nguoi-choi.md), [quyết định](decisions/nguoi-choi-la-tac-gia.md))
- **Bám sát lượt của bạn.** WHIF hay trả lời lệch, bỏ qua điều người dùng viết. Ghi chú cuối prompt (khối F), ngay trước câu trả lời, dặn nhân vật tiếp nối trực tiếp từ đúng lời nói, hành động bạn vừa viết, không đổi cảnh. Bạn còn chỉ đạo được nhân vật bằng `((...))` ([tính năng](features/F05-chi-dao-an.md)).
- **Xưng hô theo bối cảnh.** Nhân vật tên kiểu Trung thì nói kiểu Trung (ta/ngươi, gia/em...), kiểu Việt thì anh/em, tớ/cậu. Xưng hô chỉ dùng trong lời thoại và suy nghĩ; dẫn truyện dùng đại từ riêng. ([raw](raw/2026-11-12-nhan-vat-va-xung-ho.md), [quyết định](decisions/van-phong-theo-boi-canh.md))
- **Story và DM tách khung nhưng chung trí nhớ.** Nói tên trong DM thì sang Story nhân vật vẫn biết. ([raw](raw/2026-11-13-loi-thoai-va-dm-story.md), [quyết định](decisions/story-dm-chung-dong-thoi-gian.md))
- **Suy nghĩ rải trong truyện**, không chỉ ở cuối lượt; tắt được hẳn. ([raw](raw/2026-11-13-khong-doc-suy-nghi.md), [quyết định](decisions/thought-rai-giua-truyen.md), [quyết định](decisions/tuy-chon-doc-suy-nghi.md))
- **Cảm xúc tăng và giảm** theo việc bạn làm (thân với người khác thì chiếm hữu tăng, tin cậy giảm). ([raw](raw/2026-11-13-cam-xuc-tang-giam.md), [quyết định](decisions/cam-xuc-tang-giam.md))
- **Gợi ý chỉ khi bấm**, không tự hiện ([quyết định](decisions/goi-y-chi-khi-bam.md)).
- **Không có chữ kỹ thuật** trên giao diện: không model, Ollama, token, trạng thái máy; chờ thì là ba chấm nhảy. Phần kỹ thuật nằm trong "Nâng cao" ([quyết định](decisions/an-chu-ky-thuat.md)).
- **Chạy local, riêng tư**, sau này tự fine-tune model trên chính chat của mình ([quyết định](decisions/lam-app-truoc-fine-tune-sau.md)).

## Tiến độ theo phase

Theo [docs/plan.md](../docs/plan.md) §10 và code hiện có (DB thật đang ở migration 8).

| Phase | Nội dung | Trạng thái | Ghi chú |
|---|---|---|---|
| 0 | Chọn model, chứng minh đường train | Một phần | Đã chọn `gemma4:12b`. Train thử LoRA 12B không vừa 24GB; bước fuse và `ollama create` chưa kiểm chứng. Hoãn fine-tune |
| 1 | Bản chơi được tối thiểu | Đã xong | [phase1.md](../docs/phase1.md) |
| 2 | Studio và story | Đã xong | [phase2.md](../docs/phase2.md) |
| 2b | Thiết kế Lyris theo DESIGN.md | Đã xong | [design-impl.md](../docs/design-impl.md) |
| 2c | Tài khoản, profile, persona | Đã xong | [accounts.md](../docs/accounts.md) |
| 3 (và 3b) | Cảm xúc, ký ức, gợi ý, sự kiện | Đã xong | [phase3.md](../docs/phase3.md) |
| 4 | Sổ thế giới, tuỳ chọn không đọc suy nghĩ | Đã xong | Kịch bản harness cho sổ thế giới trên model thật chưa chạy. [phase4.md](../docs/phase4.md) |
| 4b | Đăng nhập, mã mời, nhiều tài khoản | Đã xong | [auth.md](../docs/auth.md) |
| 5 | Tự train model | Chưa làm | Chỉ có thử nghiệm nhỏ ở `training/toy/` |
| 6 | Dùng trên iPhone từ xa | Một phần | Có PWA manifest, icon, mở qua Wi-Fi. Cookie `Secure` khi qua HTTPS đã có trong code nhưng chưa thử. Chưa có Tailscale Serve, `allowedHosts` cho *.ts.net, chặn Mac ngủ |
| 7 | Cộng đồng (bình luận, đăng ảnh, chia sẻ ra ngoài máy) | Chưa làm | Cần plan riêng. Chia sẻ trong một máy đã có ở 4b |
| 8 | Director, nhiều nhân vật, NPC, quest (tuỳ chọn) | Chưa làm | |

## Nhân vật hiện có

- Nhân vật mẫu: Hạ Vy (nổi bật), Trần Minh Khang, Tạ Vân Lan, Lạc Dương, Morwenna Penrose (tiếng Anh). File: `backend/lyris/seed/templates/`.
- Nhân vật chủ dự án gửi, có thế giới riêng trong `worlds/`: Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương. ([raw](raw/2026-11-12-bon-nhan-vat-va-the-gioi.md))

## Kiểm tra và tiêu chí xong

Mỗi tính năng (F01–F41) có "Done when" gồm dòng Unit, Bot và Model thật, và mục "Tests" trỏ tới test có thật. Một tính năng chỉ là ✅ khi `verification/verify.sh` chạy xanh: test trong "Tests" (`backend/.venv/bin/pytest`, `npm test`), typecheck, build, và bot trình duyệt trên server LLM giả. Dòng Model thật chỉ chấm khi chạy thêm `--real-model` (cần Ollama). Trạng thái nằm ở `memory/features.json`, không ghi trong wiki. Luật đầy đủ: [README.md](README.md) mục "Trang tính năng".

## Đọc tiếp

- [features/](features/): từng tính năng `F<NN>-<slug>.md`, có "Done when" và "Tests".
- [screens/](screens/): từng màn hình.
- [decisions/](decisions/): lựa chọn quan trọng và lý do.
- [design/README.md](design/README.md): nguyên tắc thiết kế. [design/style.md](design/style.md): màu, chữ, thành phần.
- [plan-checklist.md](plan-checklist.md): 8 phần một ý tưởng phải có trước khi làm.
- [index.md](index.md): mọi trang.
