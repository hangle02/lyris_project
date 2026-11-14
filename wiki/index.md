# Mục lục wiki

Mọi trang trong `wiki/`, mỗi trang một dòng. Thêm trang mới thì thêm dòng ở đây và một dòng ở [log.md](log.md). Cách wiki vận hành: [README.md](README.md).

Tính năng có mã `F<NN>` (F01, F02, …). Trạng thái (⏳ pending · 🟡 claimed · ✅ passing · ⛔ blocked) **không** ghi trong wiki: nó nằm ở `memory/features.json`, chỉ `verification/verify.sh` chuyển sang ✅. Wiki chỉ ghi **Giai đoạn**: **Đã có** (có trong code) hoặc **Kế hoạch** (chưa làm; luôn ⏳ cho tới khi làm).

## Tổng quan

- [README.md](README.md): wiki này vận hành thế nào, ai sửa gì, thêm tính năng ra sao.
- [overview.md](overview.md): Lyris là gì, cho ai, chạy ở đâu, tiến độ từng phase.
- [index.md](index.md): trang này, mọi trang của wiki.
- [log.md](log.md): mỗi thay đổi một dòng, từ 2026-11-12 tới nay.

## Harness

Wiki là phần ① của harness (theo mẫu mini-harness của Apero); ba phần còn lại ở gốc repo. Cách chạy: [README gốc, mục Harness](../README.md#harness-theo-mẫu-mini-harness-của-apero).

- [../environment/README.md](../environment/README.md): ② luật cho AI, kiểm máy, bot trình duyệt (82 check trong `environment/e2e.mjs`), hướng dẫn `--look` ở [look.md](../environment/look.md).
- [../verification/README.md](../verification/README.md): ③ `verify.sh` (giám khảo) và `plan-check.sh`.
- [../memory/README.md](../memory/README.md): ④ `features.json` (trạng thái), [progress.md](../memory/progress.md), [po-questions.md](../memory/po-questions.md).
- Bảng đếm ngày 2026-11-14: ✅ 24 · 🟡 12 (chờ `--real-model`) · ⏳ 5 (Kế hoạch) · ⛔ 0. Cùng ngày thêm 4 tính năng Kế hoạch về coin (F42–F45), nên Kế hoạch giờ là 9. Mới nhất: `node memory/features.mjs list`.

## Tính năng

Mỗi trang có "Done when" (dòng Unit / Bot / Model thật) và "Tests" (test thật chứng minh các dòng đó). Xếp theo thứ tự: tính năng đã có, lõi trước; kế hoạch ở cuối. Phase theo [docs/plan.md](../docs/plan.md) §10.

| ID | Trang | Giai đoạn | Phase | Mô tả ngắn |
|---|---|---|---|---|
| F01 | [che-do-story](features/F01-che-do-story.md) | Đã có | 1, 2, 2b | Trả lời như tiểu thuyết: dẫn truyện, thẻ thoại, thẻ suy nghĩ |
| F02 | [che-do-dm](features/F02-che-do-dm.md) | Đã có | 2, 2b | Khung nhắn tin: bong bóng, avatar, mốc giờ; đổi Story ⇄ DM trên header |
| F03 | [van-phong-xung-ho](features/F03-van-phong-xung-ho.md) | Đã có | 0-2 | Xưng hô và văn phong theo bối cảnh; thiết lập story |
| F04 | [dinh-dang-luot-nguoi-choi](features/F04-dinh-dang-luot-nguoi-choi.md) | Đã có | 3b, 4 | Quy ước gõ "…", *"…"*, *hành động* và cách hiện lượt người chơi |
| F05 | [chi-dao-an](features/F05-chi-dao-an.md) | Đã có | 1 | Người chơi ghi chỉ đạo trong ((...)); AI làm theo, giữ giọng nhân vật |
| F06 | [thao-tac-tin-nhan](features/F06-thao-tac-tin-nhan.md) | Đã có | 1 | Tạo lại, lật phiên bản, sửa, xoá từ đây, thích/chê |
| F07 | [the-suy-nghi](features/F07-the-suy-nghi.md) | Đã có | 1, 2b | Thẻ suy nghĩ làm mờ, "Chạm để lắng nghe", rải giữa truyện |
| F08 | [doc-suy-nghi](features/F08-doc-suy-nghi.md) | Đã có | 4 (B) | Công tắc "Đọc suy nghĩ của nhân vật", lưu theo từng story |
| F09 | [ma-tran-cam-xuc](features/F09-ma-tran-cam-xuc.md) | Đã có | 3, 3b | Sáu chỉ số cảm xúc, tăng và giảm theo tình huống |
| F10 | [tri-nho](features/F10-tri-nho.md) | Đã có | 3 | Ký ức, điều đã biết, tóm tắt, cảnh; tìm lại ký ức mỗi lượt |
| F11 | [dong-thoi-gian-su-kien](features/F11-dong-thoi-gian-su-kien.md) | Đã có | 3b | Sheet "Sự kiện": lượt có ký ức, cảm xúc, cảnh; chạm để nhảy tới lượt |
| F12 | [dm-story-chung-dong-thoi-gian](features/F12-dm-story-chung-dong-thoi-gian.md) | Đã có | 3b (§10.8) | Story nhớ điều đã nói qua DM; chưa thử trên model thật |
| F13 | [chong-lap](features/F13-chong-lap.md) | Đã có | 3 | Dặn model tránh câu kết, câu mở đầu đã dùng gần đây; chưa thử trên model thật |
| F14 | [tang-toc-prefill](features/F14-tang-toc-prefill.md) | Đã có | 3b (§10.1, §10.6) | Cửa sổ lịch sử theo khúc và gửi trước phần đầu prompt khi rảnh |
| F15 | [nhan-goi-y](features/F15-nhan-goi-y.md) | Đã có | 3b | Gợi ý trả lời chỉ sinh khi bấm "Nhận gợi ý" |
| F16 | [menu-cong](features/F16-menu-cong.md) | Đã có | 3b | Nút "+" ở ô nhập gom các việc phụ |
| F17 | [so-the-gioi](features/F17-so-the-gioi.md) | Đã có | 4 | Sổ thế giới theo từng nhân vật, mở khi story nhắc từ khoá gợi nhớ |
| F18 | [xuong-nhan-vat](features/F18-xuong-nhan-vat.md) | Đã có | 2, 2b | Studio: tạo, sửa nhân vật, chat thử trước khi lưu |
| F19 | [ai-viet-nhap](features/F19-ai-viet-nhap.md) | Đã có | 2 | Gõ một dòng ý tưởng, AI viết nháp một card đầy đủ để sửa rồi lưu |
| F20 | [nhap-xuat-card](features/F20-nhap-xuat-card.md) | Đã có | 2 | Nhập, xuất Character Card V1/V2 (.json, .png) |
| F21 | [persona](features/F21-persona.md) | Đã có | 2, 2c | Một tài khoản nhiều persona; persona dùng khi trò chuyện |
| F22 | [kham-pha](features/F22-kham-pha.md) | Đã có | 2b, 4b | Trang Khám phá: lọc theo cảm xúc, lưới ô bằng nhau, nhân vật được chia sẻ (khung nổi bật bị bỏ: F46) |
| F23 | [ho-so-nhan-vat](features/F23-ho-so-nhan-vat.md) | Đã có | 2b (§16) | Hồ sơ nhân vật chỉ xem, không bao giờ hiện bí mật |
| F24 | [buoc-vao-cau-chuyen](features/F24-buoc-vao-cau-chuyen.md) | Đã có | 2b (§16) | Nút "Bước vào câu chuyện": chọn persona, "Tuỳ chỉnh story" gập sẵn |
| F25 | [danh-sach-story](features/F25-danh-sach-story.md) | Đã có | 2b | Tab "Tương tác": mọi story, mới nhất trên cùng |
| F26 | [giao-dien-theme](features/F26-giao-dien-theme.md) | Đã có | 2b | Hai theme sáng/tối, font tự host, logo, thanh tab 3 tab |
| F27 | [an-chu-ky-thuat](features/F27-an-chu-ky-thuat.md) | Đã có | 3b | Không chữ model, Ollama, token trên giao diện; phần máy nằm trong "Nâng cao" |
| F28 | [tai-khoan-profile](features/F28-tai-khoan-profile.md) | Đã có | 2c | Tài khoản và trang profile, tách khỏi persona |
| F29 | [dang-nhap](features/F29-dang-nhap.md) | Đã có | 4b | Đăng nhập, mã mời, chủ máy; mỗi người chỉ thấy story của mình |
| F30 | [quan-ly-tai-khoan](features/F30-quan-ly-tai-khoan.md) | Đã có | 4b | Trang của chủ máy: mã mời, thành viên, đặt lại mật khẩu, tạm khoá |
| F31 | [nhan-vat-cong-khai](features/F31-nhan-vat-cong-khai.md) | Đã có | 4b | Bật "Công khai" để tài khoản khác bắt đầu story bằng một bản sao |
| F32 | [dung-chung-may](features/F32-dung-chung-may.md) | Đã có | 4b | Một model cho nhiều tài khoản: tối đa 2 lượt cùng lúc, xếp hàng |
| F33 | [truy-cap-lan](features/F33-truy-cap-lan.md) | Đã có | 3, 4b | Mở app trên điện thoại cùng Wi-Fi (cổng 5173), vẫn phải đăng nhập |
| F34 | [theo-doi-su-kien](features/F34-theo-doi-su-kien.md) | Đã có | Ra mắt | 40 sự kiện không chứa chữ người dùng, tab "Số liệu", xuất CSV/JSONL, PostHog khi có khoá; chưa thử với PostHog thật |
| F35 | [quyen-rieng-tu-va-bao-cao](features/F35-quyen-rieng-tu-va-bao-cao.md) | Đã có | Ra mắt | Nội dung an toàn, Điều khoản và Chính sách có đồng ý, "Báo cáo", tải dữ liệu, xoá tài khoản, báo cáo nhân vật công khai; email liên hệ đặt bằng `LYRIS_CONTACT` |
| F36 | [harness-kiem-tra](features/F36-harness-kiem-tra.md) | Đã có | 0, 1, 2 | Bake-off model và chấm hành vi; kịch bản sổ thế giới chưa chạy |
| F37 | [iphone-tailscale](features/F37-iphone-tailscale.md) | Kế hoạch | 6 | Có PWA và icon; chưa có Tailscale Serve |
| F38 | [gui-hinh-anh](features/F38-gui-hinh-anh.md) | Kế hoạch | Chưa xếp phase | Gửi ảnh trong chat; mục trong menu "+" đang khoá "Sắp có" |
| F39 | [cong-dong](features/F39-cong-dong.md) | Kế hoạch | 7 | Bình luận, đăng ảnh, chia sẻ ra ngoài máy Mac |
| F40 | [dao-dien-khoanh-khac](features/F40-dao-dien-khoanh-khac.md) | Kế hoạch | 8 (tuỳ chọn) | Đạo diễn nhịp truyện, nhiều nhân vật, Khoảnh khắc |
| F41 | [tu-train-model](features/F41-tu-train-model.md) | Kế hoạch | 5 | Fine-tune LoRA từ chat đã đánh giá, rồi nạp lại vào app |
| F42 | [vi-coin](features/F42-vi-coin.md) | Đã có | Ra mắt (coin) | Ví coin: mỗi lượt 6 coin (mỗi câu trả lời, kể cả tạo lại và chat thử: tạm chọn), tài khoản mới 300, mỗi ngày +60, hết coin khoá ô nhập; chủ máy không tốn coin |
| F43 | [nap-coin](features/F43-nap-coin.md) | Đã có | Ra mắt (coin) | "Nạp coin" có gói "Giá dự kiến", chế độ thử chưa bán coin: chủ máy tặng mã nạp hoặc cộng/trừ coin có lý do |
| F44 | [thuong-sang-tac](features/F44-thuong-sang-tac.md) | Đã có (làm lại) | Ra mắt (coin) | Nhân vật vào top 100/50/10 "Nhân vật hot" → người tạo +100/+200/+300 coin (mỗi bậc một lần, cộng dồn); công khai lần đầu +50; thay thưởng mốc người chơi |
| F45 | [nhiem-vu-ngay](features/F45-nhiem-vu-ngay.md) | Đã có | Ra mắt (coin) | Nhiệm vụ ngày tối đa 30 coin: quảng cáo mẫu 15 giây, 3 nhân vật, 20 lượt |
| F46 | [bang-xep-hang-nhan-vat-hot](features/F46-bang-xep-hang-nhan-vat-hot.md) | Đã có | Ra mắt (coin) | Bảng "Nhân vật hot" `#/explore/hot`: top 100 theo tổng người chơi, cập nhật mỗi giờ; dải 3 hạng đầu thay khung nổi bật ở Khám phá |
| F47 | [tim-nhan-vat](features/F47-tim-nhan-vat.md) | Đã có | Ra mắt (coin) | Ô "Tìm nhân vật" ở Khám phá: không dấu, tên/vai trò/tag/giới thiệu, debounce 250 ms |

## Màn hình

| Trang | Đường dẫn | Mô tả ngắn |
|---|---|---|
| [auth-splash](screens/auth-splash.md) | trước mọi đường dẫn | Màn chờ lúc mở app, trong khi hỏi đã đăng nhập chưa |
| [login](screens/login.md) | `#/login` | Đăng nhập bằng @handle và mật khẩu |
| [signup](screens/signup.md) | `#/signup` | Tạo tài khoản bằng mã mời |
| [setup-owner](screens/setup-owner.md) | khi chưa có mật khẩu chủ máy | Chủ máy đặt mật khẩu lần đầu bằng mã in ra Terminal |
| [force-password](screens/force-password.md) | khi phải đổi mật khẩu | Đổi mật khẩu tạm ngay sau khi chủ máy đặt lại |
| [hub](screens/hub.md) | `#/` | Tương tác: danh sách story, mở app là thấy |
| [explore](screens/explore.md) | `#/explore` | Khám phá: ô tìm, dải "Nhân vật hot" (thay nhân vật nổi bật), lọc cảm xúc, lưới nhân vật |
| [hot-ranking](screens/hot-ranking.md) | `#/explore/hot` | Bảng "Nhân vật hot": top 100 theo tổng người chơi, cập nhật mỗi giờ |
| [character-profile](screens/character-profile.md) | `#/character/<id>` | Hồ sơ nhân vật chỉ đọc, có CTA "Bước vào câu chuyện" |
| [start-story-sheet](screens/start-story-sheet.md) | trên hồ sơ nhân vật, `#/character/<id>?start=1` (cả link cũ `#/new-story?card=<id>`) | Chọn persona và tuỳ chỉnh story trước khi tạo |
| [chat-story](screens/chat-story.md) | `#/chat/<id>` | Chat chế độ Story: văn tiểu thuyết toàn màn hình |
| [chat-dm](screens/chat-dm.md) | `#/chat/<id>` (DM) | Chat chế độ DM: nhắn tin như trên điện thoại |
| [composer-menu](screens/composer-menu.md) | nút "+" trong chat | Menu "+" và vùng gợi ý trả lời |
| [thought-menu](screens/thought-menu.md) | nút "Suy nghĩ" trong chat | Chọn cách đọc suy nghĩ ngay trong lúc chat |
| [heart-drawer](screens/heart-drawer.md) | nút trái tim trong chat | Ngăn "Cảm xúc & ký ức": chỉ số, cảnh, ký ức, thế giới đã mở |
| [events-sheet](screens/events-sheet.md) | menu "+" > "Xem sự kiện" | Dòng thời gian những gì nhân vật đã ghi nhớ |
| [story-settings](screens/story-settings.md) | nút bánh răng trong chat | Sửa thiết lập story đang chơi, xoá story |
| [studio-list](screens/studio-list.md) | `#/studio` | Studio: danh sách nhân vật, tạo mới, nhập card |
| [draft-dialog](screens/draft-dialog.md) | trên Studio | Hộp "AI viết nháp" một card từ ý tưởng |
| [card-editor](screens/card-editor.md) | `#/studio/<id>` | Trình sửa nhân vật, chat thử, Công khai, xuất, xoá |
| [lorebook-section](screens/lorebook-section.md) | `#/studio/<id>?section=world` | Phần "Thế giới": các mục sổ thế giới của nhân vật |
| [public-preview](screens/public-preview.md) | trong trình sửa | Hộp "Người khác thấy gì" của nhân vật công khai |
| [personas](screens/personas.md) | `#/personas` | Thêm, sửa, xoá persona |
| [account-sheet](screens/account-sheet.md) | avatar trên header | Sheet "Tài khoản": profile, mật khẩu, đăng xuất, "Nâng cao" |
| [profile](screens/profile.md) | `#/me`, `#/u/<handle>` | Trang profile của một tài khoản |
| [edit-profile-sheet](screens/edit-profile-sheet.md) | `#/me` > "Sửa profile" | Đổi tên, @handle, giới thiệu, ảnh đại diện, ảnh bìa |
| [admin](screens/admin.md) | `#/admin` (chủ máy) | Quản lý tài khoản: mã mời, thành viên (Kế hoạch: mục "Coin", "Cộng/trừ coin") |
| [coin-wallet](screens/coin-wallet.md) | `#/coins` (Kế hoạch) | Ví coin: số dư, "Nạp coin", "Nhiệm vụ", lịch sử |
| [top-up](screens/top-up.md) | `#/coins/top-up` (Kế hoạch) | Nạp coin ở chế độ thử: gói giá, ô "Mã nạp" |
| [missions](screens/missions.md) | `#/missions` | Nhiệm vụ hôm nay và hộp "Quảng cáo mẫu" |

## Quyết định

Xếp theo ngày. "Ai quyết": người dùng, thiết kế, hay đo đạc.

| Ngày | Trang | Quyết định | Ai quyết |
|---|---|---|---|
| 2026-11-12 | [lora-khong-train-tu-dau](decisions/lora-khong-train-tu-dau.md) | Tự train nghĩa là LoRA trên model mở, không train từ đầu | thiết kế |
| 2026-11-12 | [lam-app-truoc-fine-tune-sau](decisions/lam-app-truoc-fine-tune-sau.md) | Làm app trước với gemma4:12b gốc, fine-tune sau | người dùng + đo đạc |
| 2026-11-12 | [chon-gemma4-12b](decisions/chon-gemma4-12b.md) | Chọn gemma4:12b làm model chat | đo đạc + người dùng chấm |
| 2026-11-12 | [van-phong-theo-boi-canh](decisions/van-phong-theo-boi-canh.md) | Văn phong và xưng hô theo bối cảnh của story | người dùng |
| 2026-11-12 | [xung-ho-tach-dan-truyen](decisions/xung-ho-tach-dan-truyen.md) | Xưng hô chỉ trong lời thoại; dẫn truyện dùng đại từ riêng | người dùng |
| 2026-11-12 | [tieng-viet-truoc](decisions/tieng-viet-truoc.md) | Tiếng Việt là mặc định, có mode tiếng Anh | người dùng + thiết kế |
| 2026-11-12 | [nguoi-choi-la-tac-gia](decisions/nguoi-choi-la-tac-gia.md) | Người chơi điều khiển persona; AI không godmodding | người dùng |
| 2026-11-12 | [chua-dung-docker](decisions/chua-dung-docker.md) | Chưa dùng Docker | người dùng |
| 2026-11-12 | [thought-rai-giua-truyen](decisions/thought-rai-giua-truyen.md) | Thought rải giữa truyện là mặc định | người dùng |
| 2026-11-12 | [dm-giao-dien-nhan-tin](decisions/dm-giao-dien-nhan-tin.md) | DM có giao diện nhắn tin riêng | người dùng |
| 2026-11-12 | [card-doi-story-doi-theo](decisions/card-doi-story-doi-theo.md) | Sửa nhân vật thì story dùng nhân vật đó đổi theo | thiết kế |
| 2026-11-12 | [ten-app-lyris](decisions/ten-app-lyris.md) | Tên app là Lyris, thư mục vẫn là nora | người dùng |
| 2026-11-12 | [tiet-che-thiet-ke](decisions/tiet-che-thiet-ke.md) | Theo DESIGN.md nhưng bớt dấu hiệu "AI gen" | người dùng + thiết kế |
| 2026-11-12 | [dung-khung-giao-dien-som](decisions/dung-khung-giao-dien-som.md) | Dựng khung giao diện trước khi có dữ liệu | người dùng |
| 2026-11-12 | [the-gioi-cho-nhan-vat](decisions/the-gioi-cho-nhan-vat.md) | Dựng thế giới cho từng nhân vật người dùng gửi | người dùng |
| 2026-11-12 | [tach-tai-khoan-persona](decisions/tach-tai-khoan-persona.md) | Tách tài khoản và persona | người dùng |
| 2026-11-13 | [mo-cong-5173](decisions/mo-cong-5173.md) | Mở Vite ra mạng LAN để thử bằng điện thoại | người dùng |
| 2026-11-13 | [khong-sqlite-vec](decisions/khong-sqlite-vec.md) | Không dùng sqlite-vec; tìm ký ức lai, embedding không bắt buộc | thiết kế |
| 2026-11-13 | [viec-nen-dung-model-chat](decisions/viec-nen-dung-model-chat.md) | Việc nền dùng chính model chat, không dùng e4b | đo đạc |
| 2026-11-13 | [cung-num-ctx](decisions/cung-num-ctx.md) | Mọi lời gọi model chat dùng cùng num_ctx 8192 | đo đạc |
| 2026-11-13 | [menu-cong-o-nhap](decisions/menu-cong-o-nhap.md) | Nút "+" ở ô nhập gom các tuỳ chọn | người dùng |
| 2026-11-13 | [goi-y-chi-khi-bam](decisions/goi-y-chi-khi-bam.md) | Gợi ý trả lời chỉ sinh khi người chơi bấm | người dùng |
| 2026-11-13 | [gui-hinh-anh-chi-la-khung](decisions/gui-hinh-anh-chi-la-khung.md) | Gửi hình ảnh mới chỉ là khung | thiết kế |
| 2026-11-13 | [an-chu-ky-thuat](decisions/an-chu-ky-thuat.md) | Ẩn mọi chữ kỹ thuật trên giao diện | người dùng |
| 2026-11-13 | [cam-xuc-tang-giam](decisions/cam-xuc-tang-giam.md) | Chỉ số cảm xúc phải giảm được | người dùng + đo đạc |
| 2026-11-13 | [the-kham-pha-nho-lai](decisions/the-kham-pha-nho-lai.md) | Thẻ nhân vật ở Khám phá nhỏ lại | người dùng |
| 2026-11-13 | [ho-so-nhan-vat-chi-doc](decisions/ho-so-nhan-vat-chi-doc.md) | Chạm nhân vật mở hồ sơ chỉ đọc, chọn persona sau CTA | người dùng |
| 2026-11-13 | [thuat-ngu-story](decisions/thuat-ngu-story.md) | Giao diện gọi là "story"; CTA là "Bước vào câu chuyện" | người dùng |
| 2026-11-13 | [cua-so-lich-su-theo-khuc](decisions/cua-so-lich-su-theo-khuc.md) | Cắt lịch sử theo khúc, tóm tắt ngay trước lượt dịch | đo đạc + thiết kế |
| 2026-11-13 | [prefill-raw](decisions/prefill-raw.md) | Gửi trước phần đầu prompt khi rảnh (prefill raw) | đo đạc |
| 2026-11-13 | [the-thoai-khong-ngoac](decisions/the-thoai-khong-ngoac.md) | Thẻ thoại không hiện dấu ngoặc ngoài cùng | người dùng |
| 2026-11-13 | [su-kien-ca-hai-che-do](decisions/su-kien-ca-hai-che-do.md) | Sheet "Sự kiện" gồm lượt của cả Story lẫn DM | người dùng + thiết kế |
| 2026-11-13 | [tuy-chon-doc-suy-nghi](decisions/tuy-chon-doc-suy-nghi.md) | Tuỳ chọn không đọc suy nghĩ của nhân vật | người dùng |
| 2026-11-13 | [story-dm-chung-dong-thoi-gian](decisions/story-dm-chung-dong-thoi-gian.md) | Story và DM chung một dòng thời gian, lượt DM có nhãn | người dùng + thiết kế |
| 2026-11-13 | [trich-dan-trong-dau-sao](decisions/trich-dan-trong-dau-sao.md) | `*"…"*` là trích dẫn hoặc lời người khác | người dùng |
| 2026-11-13 | [placeholder-ngan](decisions/placeholder-ngan.md) | Gợi ý trong ô nhập phải ngắn | người dùng |
| 2026-11-13 | [lore-trong-db-theo-card](decisions/lore-trong-db-theo-card.md) | Sổ thế giới thuộc từng nhân vật, nằm trong DB | thiết kế |
| 2026-11-13 | [lore-khong-trong-system](decisions/lore-khong-trong-system.md) | Sổ thế giới không nằm trong system, mặc định không gửi trước | thiết kế + đo đạc |
| 2026-11-14 | [dang-ky-bang-ma-moi](decisions/dang-ky-bang-ma-moi.md) | Tạo tài khoản cần mã mời; tài khoản đầu là chủ máy | người dùng |
| 2026-11-14 | [nhan-vat-cong-khai](decisions/nhan-vat-cong-khai.md) | Story luôn riêng tư; nhân vật có thể bật Công khai | người dùng |
| 2026-11-14 | [quen-mat-khau](decisions/quen-mat-khau.md) | Quên mật khẩu thì chủ máy đặt lại | người dùng |
| 2026-11-14 | [scrypt-va-phien](decisions/scrypt-va-phien.md) | Mật khẩu scrypt, phiên cookie HttpOnly, không thêm thư viện | thiết kế |
| 2026-11-14 | [ban-sao-nhan-vat-cong-khai](decisions/ban-sao-nhan-vat-cong-khai.md) | Bắt đầu story với nhân vật công khai thì chụp một bản sao | thiết kế |
| 2026-11-14 | [cong-sinh-chung](decisions/cong-sinh-chung.md) | Một model chia cho nhiều người: tối đa 2 lượt cùng lúc | thiết kế |
| 2026-11-14 | [du-lieu-train-co-dong-y](decisions/du-lieu-train-co-dong-y.md) | Dữ liệu train chỉ lấy từ tài khoản đã đồng ý | thiết kế |
| 2026-11-14 | [luoi-o-bang-nhau](decisions/luoi-o-bang-nhau.md) | Ô nhân vật trong lưới luôn bằng nhau | người dùng |
| 2026-11-14 | [luu-su-kien-trong-app-va-posthog](decisions/luu-su-kien-trong-app-va-posthog.md) | Sự kiện lưu trong DB của app, gửi thêm PostHog khi có khoá; không bao giờ có chữ người dùng | người dùng |
| 2026-11-14 | [noi-dung-an-toan-chua-cong-tuoi](decisions/noi-dung-an-toan-chua-cong-tuoi.md) | Nội dung mặc định an toàn, chưa có cổng tuổi; chế độ người lớn chỉ là kế hoạch | người dùng |
| 2026-11-14 | [kich-ban-model-that](decisions/kich-ban-model-that.md) | Mỗi dòng "Model thật" có kịch bản luật máy; phần chỉ người chấm được tách ra (tạm chọn) | thiết kế |
| 2026-11-14 | [nguong-ttft-f14](decisions/nguong-ttft-f14.md) | TTFT mỗi lượt sau lượt đầu ≤ 6 giây, đo qua app thật (tạm chọn) | đo đạc |
| 2026-11-14 | [giu-cho-coin-truoc-khi-sinh](decisions/giu-cho-coin-truoc-khi-sinh.md) | Mỗi lượt 6 coin: giữ chỗ trước khi sinh, chỉ trừ khi có chữ, không bao giờ làm mất câu trả lời; ngày theo giờ Việt Nam (phần tạm chọn) | người dùng + thiết kế |
| 2026-11-14 | [chu-may-khong-ton-coin](decisions/chu-may-khong-ton-coin.md) | Chủ máy không tốn coin, không nhận thưởng, không tính là người chơi (phần tạm chọn) | người dùng + thiết kế |
| 2026-11-14 | [nap-coin-che-do-thu](decisions/nap-coin-che-do-thu.md) | Nạp coin chế độ thử: mã nạp và cộng tay, chưa có cổng thanh toán; giá gói tạm chọn | người dùng + thiết kế |
| 2026-11-14 | [moc-nguoi-choi-sang-tac](decisions/moc-nguoi-choi-sang-tac.md) | **Đã thay bởi xep-hang-nhan-vat-hot.** Thưởng mốc 10/50/100 người chơi; người chơi = tài khoản khác có ≥ 3 câu trả lời đã trả coin ở ≥ 2 ngày; trần mốc 10 theo người tạo (tạm chọn) | người dùng + thiết kế |
| 2026-11-14 | [nhiem-vu-va-quang-cao-mau](decisions/nhiem-vu-va-quang-cao-mau.md) | Nhiệm vụ ngày trần 30 coin; quảng cáo mẫu ghi rõ là mẫu, 15 giây kiểm ở server | người dùng + thiết kế |
| 2026-11-14 | [coin-f42-khi-build](decisions/coin-f42-khi-build.md) | Coin F42 khi build: không cộng +60 khi tắt coin, thông báo +60 nhớ theo ngày, route cộng/trừ coin có từ F42, trang tạm Nạp coin/Nhiệm vụ, test F34 so số sự kiện với tracking-plan (tạm chọn) | AI (tạm chọn) |
| 2026-11-14 | [coin-f45-khi-build](decisions/coin-f45-khi-build.md) | Coin F45 khi build: chủ máy/coin tắt 409 `no_missions`, thứ tự kiểm khi nhận quảng cáo, tiến độ theo ngày của giữ chỗ, hộp quảng cáo đóng sau khi nhận, bot chờ 15 giây thật (tạm chọn) | AI (tạm chọn) |
| 2026-11-14 | [coin-ra-soat-2026-11-14](decisions/coin-ra-soat-2026-11-14.md) | Coin sau rà soát đối kháng: tên nhân vật trong lịch sử ví chỉ của chính tài khoản, giữ chỗ kẹt tự nhả, dừng trước chữ đầu tiên không trừ, sổ chặn DELETE (0013), settle_card không làm hỏng việc lưu (tạm chọn) | AI (tạm chọn) |
| 2026-11-14 | [coin-f44-khi-build](decisions/coin-f44-khi-build.md) | Coin F44 khi build: đếm người chơi qua story và bản sao (id nhân vật bị dùng lại), trần mốc 10 đếm trong sổ, settle khi checkin/lưu Công khai/mở khoá, chủ máy và coin tắt không hứa coin, bot dựng người chơi bằng environment/seed-creator-players.py (tạm chọn) | AI (tạm chọn) |
| 2026-11-14 | [xep-hang-nhan-vat-hot](decisions/xep-hang-nhan-vat-hot.md) | Thay thưởng mốc người chơi bằng thưởng bảng "Nhân vật hot" top 100/50/10 (+100/+200/+300, cộng dồn) và +50 công khai lần đầu; bậc top N cần bảng ≥ N nhân vật, trần 600 coin/7 ngày, tính bảng mỗi giờ khi cần (tạm chọn) | người dùng + thiết kế |
| 2026-11-14 | [kham-pha-tim-kiem-bo-khung-noi-bat](decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md) | Khám phá bỏ khung nổi bật Hạ Vy; ô "Tìm nhân vật" không dấu; dải 3 hạng đầu "Nhân vật hot" (tạm chọn) | người dùng + thiết kế |

## Thiết kế

- [design/README.md](design/README.md): nguyên tắc thiết kế, thứ tự ưu tiên khi xung đột.
- [design/style.md](design/style.md): phong cách của Lyris: hai theme, màu, chữ, thành phần, chỗ lệch DESIGN.md.
- [design/assets.md](design/assets.md): nguồn font, icon, ảnh miễn phí dùng được; mọi thứ đi kèm repo, chạy offline.
- [design/credits.md](design/credits.md): ghi công mọi ảnh, font, icon đang có trong app.

## Ý tưởng gốc (raw)

Lời chủ dự án, chép nguyên văn. Không sửa.

- [raw/README.md](raw/README.md): luật của thư mục raw/ (đặt tên file, không sửa).
- [raw/DESIGN.md](raw/DESIGN.md): đặc tả thiết kế Lyris do chủ dự án viết (bản chép).
- [raw/2026-11-12-plan-goc.md](raw/2026-11-12-plan-goc.md): kế hoạch gốc: app kiểu WHIF, tự train model trên MacBook.
- [raw/2026-11-12-phase0-chon-model.md](raw/2026-11-12-phase0-chon-model.md): Phase 0: chọn model, tải trọng số, tạm hoãn fine-tune.
- [raw/2026-11-12-nhan-vat-va-xung-ho.md](raw/2026-11-12-nhan-vat-va-xung-ho.md): nhân vật đầu tiên, xưng hô theo bối cảnh, giới tính, ngôi kể.
- [raw/2026-11-12-quyen-cua-nguoi-choi.md](raw/2026-11-12-quyen-cua-nguoi-choi.md): người chơi điều khiển persona; AI không viết thay, không trả lời lệch.
- [raw/2026-11-12-gop-y-phase1.md](raw/2026-11-12-gop-y-phase1.md): góp ý sau Phase 1: văn tả cảnh, suy nghĩ, tách DM và Story.
- [raw/2026-11-12-design-va-ten-lyris.md](raw/2026-11-12-design-va-ten-lyris.md): gửi DESIGN.md, đổi tên Nora thành Lyris.
- [raw/2026-11-12-bon-nhan-vat-va-the-gioi.md](raw/2026-11-12-bon-nhan-vat-va-the-gioi.md): bốn nhân vật gửi kèm và yêu cầu dựng thế giới.
- [raw/2026-11-12-story-an-may-tai-khoan-persona.md](raw/2026-11-12-story-an-may-tai-khoan-persona.md): chữ Story, ẩn trạng thái máy, tách tài khoản và persona.
- [raw/2026-11-12-trao-doi-ngan.md](raw/2026-11-12-trao-doi-ngan.md): trao đổi ngắn (hỏi tiến độ, tạm dừng, chạy tiếp) từ 2026-11-12 đến 2026-11-13.
- [raw/2026-11-13-phase3-lap-y-va-dien-thoai.md](raw/2026-11-13-phase3-lap-y-va-dien-thoai.md): DM lặp ý, mở cổng cho điện thoại, bắt đầu Phase 3.
- [raw/2026-11-13-o-chat-goi-y-va-an-ky-thuat.md](raw/2026-11-13-o-chat-goi-y-va-an-ky-thuat.md): nút "+" ở ô chat, gợi ý khi bấm, giấu chữ kỹ thuật.
- [raw/2026-11-13-cam-xuc-tang-giam.md](raw/2026-11-13-cam-xuc-tang-giam.md): chỉ số cảm xúc tăng và giảm theo tình huống.
- [raw/2026-11-13-kham-pha-va-ho-so-nhan-vat.md](raw/2026-11-13-kham-pha-va-ho-so-nhan-vat.md): thẻ Khám phá nhỏ lại, hồ sơ nhân vật, "Bước vào câu chuyện", ảnh nhân vật.
- [raw/2026-11-13-khong-doc-suy-nghi.md](raw/2026-11-13-khong-doc-suy-nghi.md): lựa chọn không đọc suy nghĩ của nhân vật.
- [raw/2026-11-13-loi-thoai-va-dm-story.md](raw/2026-11-13-loi-thoai-va-dm-story.md): hiển thị lời thoại, dấu ngoặc, DM và Story chung một mạch.
- [raw/2026-11-13-dang-nhap-va-tai-khoan.md](raw/2026-11-13-dang-nhap-va-tai-khoan.md): đăng nhập, tạo tài khoản, database cho nhiều tài khoản.
- [raw/2026-11-14-kham-pha-trung-nhan-vat-va-luoi.md](raw/2026-11-14-kham-pha-trung-nhan-vat-va-luoi.md): hai Hạ Vy ở Khám phá, ô nhân vật bằng nhau.
- [raw/2026-11-14-wiki-du-an.md](raw/2026-11-14-wiki-du-an.md): yêu cầu dựng wiki dự án theo mẫu.
- [raw/2026-11-14-coin.md](raw/2026-11-14-coin.md): ý tưởng coin: chat tốn coin, nạp tiền, thưởng sáng tác, nhiệm vụ.
- [raw/2026-11-14-coin-tra-loi.md](raw/2026-11-14-coin-tra-loi.md): câu trả lời về coin: 6 coin mỗi lượt, 300 quà, +60 mỗi ngày, nạp chế độ thử, mốc 10/50/100, nhiệm vụ 30 coin/ngày, hết coin khoá ô nhập.
- [raw/2026-11-14-f44-bang-xep-hang.md](raw/2026-11-14-f44-bang-xep-hang.md): đổi F44: thưởng khi nhân vật vào top 100/50/10 "nhân vật hot", làm bảng xếp hạng, thưởng nhỏ khi công khai lần đầu.
- [raw/2026-11-14-f44-bang-xep-hang-tra-loi.md](raw/2026-11-14-f44-bang-xep-hang-tra-loi.md): trả lời 1A 2C 3A 4A 5A; thêm thanh tìm kiếm, bỏ khung Hạ Vy to ở Khám phá.

## Bài học

- [learned.md](learned.md): Learned Wiki: mỗi lần sai một mục (sai gì, vì sao, luật rút ra, nguồn); bài mới ghi thêm ở cuối.

## Kế hoạch

- [plan-checklist.md](plan-checklist.md): 8 phần một ý tưởng phải có; dùng để hỏi lại khi ý tưởng còn thiếu.
- Kế hoạch đầy đủ và lộ trình các phase nằm ngoài wiki: [docs/plan.md](../docs/plan.md). Thiết kế chi tiết từng phase: [phase1.md](../docs/phase1.md), [phase2.md](../docs/phase2.md), [design-impl.md](../docs/design-impl.md), [accounts.md](../docs/accounts.md), [phase3.md](../docs/phase3.md), [phase4.md](../docs/phase4.md), [auth.md](../docs/auth.md).
- Ra mắt: [tracking-plan.md](../docs/tracking-plan.md) (sự kiện, KPI), [compliance.md](../docs/compliance.md) (tuân thủ), [deploy.md](../docs/deploy.md) (chạy production), [demo-script.md](../docs/demo-script.md) (kịch bản video demo), [coins.md](../docs/coins.md) (coin: ví, nạp chế độ thử, thưởng sáng tác, nhiệm vụ; kế hoạch).

## Máy chủ lớn và App Store (kế hoạch, sau khi nộp bài)

- Thiết kế: [docs/server.md](../docs/server.md) (kiến trúc host, Postgres, Redis, hàng đợi, vLLM, S3, thanh toán, app di động, sức chứa và chi phí, kế hoạch chuyển đổi G0–G8, chế độ tự chạy).
- [F50](features/F50-postgres.md) Postgres và chuyển lớp Repo · [F51](features/F51-redis-api-khong-trang-thai.md) Redis và máy chủ API không trạng thái · [F52](features/F52-hang-doi-viec-nen.md) Hàng đợi việc nền trên Postgres · [F53](features/F53-cong-suy-luan-vllm.md) Cổng suy luận vLLM · [F54](features/F54-luu-anh-s3.md) Lưu ảnh trên S3
- [F55](features/F55-app-ios-android.md) App iOS và Android (Capacitor) · [F56](features/F56-iap-google-play.md) Apple IAP và Google Play Billing · [F57](features/F57-vnpay-momo.md) VNPay và MoMo · [F58](features/F58-quan-sat-slo.md) Quan sát và SLO · [F59](features/F59-trien-khai-ci.md) Triển khai, CI/CD, staging
- [F60](features/F60-kiem-duyet-chan.md) Kiểm duyệt và chặn người tạo · [F61](features/F61-dang-ky-cong-khai.md) Đăng ký công khai, email, Apple/Google · [F62](features/F62-nhap-du-lieu-tu-chay.md) Nhập dữ liệu từ Lyris tự chạy
- Quyết định: [may-chu-lon-va-app-store](decisions/may-chu-lon-va-app-store.md) (PO chốt), [app-di-dong-capacitor](decisions/app-di-dong-capacitor.md) (AI chọn), [suy-luan-vllm](decisions/suy-luan-vllm.md), [postgres-giu-repo](decisions/postgres-giu-repo.md), [hang-doi-postgres](decisions/hang-doi-postgres.md), [thanh-toan-iap-va-cong-vn](decisions/thanh-toan-iap-va-cong-vn.md), [phien-token-cho-app](decisions/phien-token-cho-app.md), [container-chi-khi-host](decisions/container-chi-khi-host.md)
- Lời gốc: [raw/2026-11-14-server-lon-appstore.md](raw/2026-11-14-server-lon-appstore.md), [raw/2026-11-14-server-lon-appstore-tra-loi.md](raw/2026-11-14-server-lon-appstore-tra-loi.md)
- Sau phản biện (2026-11-14): [docs/server.md §21](../docs/server.md) (23 điểm nhận/sửa lại/bác kèm lý do), quyết định [fence-postgres-va-loc-truoc-stream](decisions/fence-postgres-va-loc-truoc-stream.md) (AI chọn, tạm chọn)
