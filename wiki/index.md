# Mục lục wiki

Mọi trang trong `wiki/`, mỗi trang một dòng. Thêm trang mới thì thêm dòng ở đây và một dòng ở [log.md](log.md). Cách wiki vận hành: [README.md](README.md).

Trạng thái: **Đã xong** (có trong code), **Một phần** (có code, còn thiếu phần ghi ở trang), **Chưa làm** (mới là kế hoạch).

## Tổng quan

- [README.md](README.md): wiki này vận hành thế nào, ai sửa gì, thêm tính năng ra sao.
- [overview.md](overview.md): Lyris là gì, cho ai, chạy ở đâu, tiến độ từng phase.
- [index.md](index.md): trang này, mọi trang của wiki.
- [log.md](log.md): mỗi thay đổi một dòng, từ 2026-11-12 tới nay.

## Tính năng

Mỗi trang có "Done when". Phase theo [docs/plan.md](../docs/plan.md) §10.

| Trang | Trạng thái | Phase | Mô tả ngắn |
|---|---|---|---|
| [ai-viet-nhap](features/ai-viet-nhap.md) | Đã xong | 2 | Gõ một dòng ý tưởng, AI viết nháp một card đầy đủ để sửa rồi lưu |
| [an-chu-ky-thuat](features/an-chu-ky-thuat.md) | Đã xong | 3b | Không chữ model, Ollama, token trên giao diện; phần máy nằm trong "Nâng cao" |
| [buoc-vao-cau-chuyen](features/buoc-vao-cau-chuyen.md) | Đã xong | 2b | Nút "Bước vào câu chuyện": chọn persona, "Tuỳ chỉnh story" gập sẵn |
| [che-do-dm](features/che-do-dm.md) | Đã xong | 2, 2b | Khung nhắn tin: bong bóng, avatar, mốc giờ; đổi Story ⇄ DM trên header |
| [che-do-story](features/che-do-story.md) | Đã xong | 1, 2, 2b | Trả lời như tiểu thuyết: dẫn truyện, thẻ thoại, thẻ suy nghĩ |
| [chi-dao-an](features/chi-dao-an.md) | Đã xong | 1 | Người chơi ghi chỉ đạo trong ((...)); AI làm theo, giữ giọng nhân vật |
| [chong-lap](features/chong-lap.md) | Một phần | 3 | Dặn model tránh câu kết, câu mở đầu đã dùng gần đây; chưa thử trên model thật |
| [dang-nhap](features/dang-nhap.md) | Đã xong | 4b | Đăng nhập, mã mời, chủ máy; mỗi người chỉ thấy story của mình |
| [danh-sach-story](features/danh-sach-story.md) | Đã xong | 2b | Tab "Tương tác": mọi story, mới nhất trên cùng |
| [dinh-dang-luot-nguoi-choi](features/dinh-dang-luot-nguoi-choi.md) | Đã xong | 3b, 4 | Quy ước gõ "…", *"…"*, *hành động* và cách hiện lượt người chơi |
| [doc-suy-nghi](features/doc-suy-nghi.md) | Đã xong | 4 | Công tắc "Đọc suy nghĩ của nhân vật", lưu theo từng story |
| [dong-thoi-gian-su-kien](features/dong-thoi-gian-su-kien.md) | Đã xong | 3b | Sheet "Sự kiện": lượt có ký ức, cảm xúc, cảnh; chạm để nhảy tới lượt |
| [dung-chung-may](features/dung-chung-may.md) | Đã xong | 4b | Một model cho nhiều tài khoản: tối đa 2 lượt cùng lúc, xếp hàng |
| [giao-dien-theme](features/giao-dien-theme.md) | Đã xong | 2b | Hai theme sáng/tối, font tự host, logo, thanh tab 3 tab |
| [ho-so-nhan-vat](features/ho-so-nhan-vat.md) | Đã xong | 2b | Hồ sơ nhân vật chỉ xem, không bao giờ hiện bí mật |
| [kham-pha](features/kham-pha.md) | Đã xong | 2b, 4b | Trang Khám phá: nhân vật nổi bật, lọc theo cảm xúc, lưới ô bằng nhau |
| [ma-tran-cam-xuc](features/ma-tran-cam-xuc.md) | Đã xong | 3, 3b | Sáu chỉ số cảm xúc, tăng và giảm theo tình huống |
| [menu-cong](features/menu-cong.md) | Đã xong | 3b | Nút "+" ở ô nhập gom các việc phụ |
| [nhan-goi-y](features/nhan-goi-y.md) | Đã xong | 3b | Gợi ý trả lời chỉ sinh khi bấm "Nhận gợi ý" |
| [nhan-vat-cong-khai](features/nhan-vat-cong-khai.md) | Đã xong | 4b | Bật "Công khai" để tài khoản khác bắt đầu story bằng một bản sao |
| [nhap-xuat-card](features/nhap-xuat-card.md) | Đã xong | 2 | Nhập, xuất Character Card V1/V2 (.json, .png) |
| [persona](features/persona.md) | Đã xong | 2, 2c | Một tài khoản nhiều persona; persona dùng khi trò chuyện |
| [quan-ly-tai-khoan](features/quan-ly-tai-khoan.md) | Đã xong | 4b | Trang của chủ máy: mã mời, thành viên, đặt lại mật khẩu, tạm khoá |
| [so-the-gioi](features/so-the-gioi.md) | Đã xong | 4 | Sổ thế giới theo từng nhân vật, mở khi story nhắc từ khoá gợi nhớ |
| [tai-khoan-profile](features/tai-khoan-profile.md) | Đã xong | 2c | Tài khoản và trang profile, tách khỏi persona |
| [tang-toc-prefill](features/tang-toc-prefill.md) | Đã xong | 3b | Cửa sổ lịch sử theo khúc và gửi trước phần đầu prompt khi rảnh |
| [thao-tac-tin-nhan](features/thao-tac-tin-nhan.md) | Đã xong | 1 | Tạo lại, lật phiên bản, sửa, xoá từ đây, thích/chê |
| [the-suy-nghi](features/the-suy-nghi.md) | Đã xong | 1, 2b | Thẻ suy nghĩ làm mờ, "Chạm để lắng nghe", rải giữa truyện |
| [tri-nho](features/tri-nho.md) | Đã xong | 3 | Ký ức, điều đã biết, tóm tắt, cảnh; tìm lại ký ức mỗi lượt |
| [truy-cap-lan](features/truy-cap-lan.md) | Đã xong | 3, 4b | Mở app trên điện thoại cùng Wi-Fi (cổng 5173), vẫn phải đăng nhập |
| [van-phong-xung-ho](features/van-phong-xung-ho.md) | Đã xong | 0-2 | Xưng hô và văn phong theo bối cảnh; thiết lập story |
| [xuong-nhan-vat](features/xuong-nhan-vat.md) | Đã xong | 2, 2b | Studio: tạo, sửa nhân vật, chat thử trước khi lưu |
| [dm-story-chung-dong-thoi-gian](features/dm-story-chung-dong-thoi-gian.md) | Một phần | 3b | Story nhớ điều đã nói qua DM; chưa thử trên model thật |
| [harness-kiem-tra](features/harness-kiem-tra.md) | Một phần | 0, 1, 2 | Bake-off model và chấm hành vi; kịch bản sổ thế giới chưa chạy |
| [iphone-tailscale](features/iphone-tailscale.md) | Một phần | 6 | Có PWA và icon; chưa có Tailscale Serve |
| [cong-dong](features/cong-dong.md) | Chưa làm | 7 | Bình luận, đăng ảnh, chia sẻ ra ngoài máy Mac |
| [dao-dien-khoanh-khac](features/dao-dien-khoanh-khac.md) | Chưa làm | 8 | Đạo diễn nhịp truyện, nhiều nhân vật, Khoảnh khắc |
| [gui-hinh-anh](features/gui-hinh-anh.md) | Chưa làm | chưa xếp | Gửi ảnh trong chat; mục trong menu "+" đang khoá "Sắp có" |
| [tu-train-model](features/tu-train-model.md) | Chưa làm | 5 | Fine-tune LoRA từ chat đã đánh giá, rồi nạp lại vào app |

## Màn hình

| Trang | Đường dẫn | Mô tả ngắn |
|---|---|---|
| [auth-splash](screens/auth-splash.md) | trước mọi đường dẫn | Màn chờ lúc mở app, trong khi hỏi đã đăng nhập chưa |
| [login](screens/login.md) | `#/login` | Đăng nhập bằng @handle và mật khẩu |
| [signup](screens/signup.md) | `#/signup` | Tạo tài khoản bằng mã mời |
| [setup-owner](screens/setup-owner.md) | khi chưa có mật khẩu chủ máy | Chủ máy đặt mật khẩu lần đầu bằng mã in ra Terminal |
| [force-password](screens/force-password.md) | khi phải đổi mật khẩu | Đổi mật khẩu tạm ngay sau khi chủ máy đặt lại |
| [hub](screens/hub.md) | `#/` | Tương tác: danh sách story, mở app là thấy |
| [explore](screens/explore.md) | `#/explore` | Khám phá: nhân vật nổi bật, lọc cảm xúc, lưới nhân vật |
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
| [admin](screens/admin.md) | `#/admin` (chủ máy) | Quản lý tài khoản: mã mời, thành viên |

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

## Bài học

- [learned.md](learned.md): Learned Wiki: mỗi lần sai một mục (sai gì, vì sao, luật rút ra, nguồn); bài mới ghi thêm ở cuối.

## Kế hoạch

- [plan-checklist.md](plan-checklist.md): 8 phần một ý tưởng phải có; dùng để hỏi lại khi ý tưởng còn thiếu.
- Kế hoạch đầy đủ và lộ trình các phase nằm ngoài wiki: [docs/plan.md](../docs/plan.md). Thiết kế chi tiết từng phase: [phase1.md](../docs/phase1.md), [phase2.md](../docs/phase2.md), [design-impl.md](../docs/design-impl.md), [accounts.md](../docs/accounts.md), [phase3.md](../docs/phase3.md), [phase4.md](../docs/phase4.md), [auth.md](../docs/auth.md).
