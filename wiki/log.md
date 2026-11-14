# Nhật ký thay đổi

Mỗi thay đổi một dòng: `YYYY-MM-DD · việc · trang`.

- **việc**: một câu ngắn, đã làm gì hoặc đã quyết gì.
- **trang**: trang wiki nói về việc đó (nhiều trang thì cách nhau bằng dấu phẩy).
- Dòng mới ghi thêm ở **cuối**. Không sửa dòng cũ; ghi sai thì thêm một dòng sửa.

Các dòng trước "Tạo wiki" được dựng lại từ [docs/plan.md](../docs/plan.md), các mục ghi thay đổi trong `docs/*.md` và lời chủ dự án trong [raw/](raw/). Lúc đó wiki chưa có; cột "trang" là trang wiki hiện mô tả việc đó.

## 2026-11-12

- 2026-11-12 · Viết lại kế hoạch: app nhập vai kiểu WHIF chạy trên MacBook, tự tạo nhân vật, tự train model · [overview](overview.md), [raw](raw/2026-11-12-plan-goc.md)
- 2026-11-12 · Chốt: tự train là LoRA trên một model mở, không train từ đầu · [lora-khong-train-tu-dau](decisions/lora-khong-train-tu-dau.md)
- 2026-11-12 · Chủ dự án chọn fine-tune sau khi có app; cập nhật danh sách model ứng viên · [lam-app-truoc-fine-tune-sau](decisions/lam-app-truoc-fine-tune-sau.md)
- 2026-11-12 · Phase 0: cài Ollama, chạy bake-off 15 câu tiếng Việt; chủ dự án tự chấm điểm · [harness-kiem-tra](features/harness-kiem-tra.md), [raw](raw/2026-11-12-phase0-chon-model.md)
- 2026-11-12 · Nhân vật thử Lạc Dương và persona Lâm Vãn; xưng hô và văn phong theo bối cảnh (Việt, Trung) · [van-phong-theo-boi-canh](decisions/van-phong-theo-boi-canh.md), [raw](raw/2026-11-12-nhan-vat-va-xung-ho.md)
- 2026-11-12 · Thêm giới tính, kiểu quan hệ, ngôi kể vào prompt; xưng hô chỉ trong thoại, dẫn truyện dùng đại từ riêng · [xung-ho-tach-dan-truyen](decisions/xung-ho-tach-dan-truyen.md), [van-phong-xung-ho](features/van-phong-xung-ho.md)
- 2026-11-12 · Chọn gemma4:12b cho chat; xoá qwen3.5:9b và sailor2:8b · [chon-gemma4-12b](decisions/chon-gemma4-12b.md), [learned](learned.md)
- 2026-11-12 · Tiếng Việt là mặc định, có mode tiếng Anh · [tieng-viet-truoc](decisions/tieng-viet-truoc.md)
- 2026-11-12 · Người chơi điều khiển persona; AI không viết thay, phản ứng với mọi điều người chơi viết · [nguoi-choi-la-tac-gia](decisions/nguoi-choi-la-tac-gia.md), [raw](raw/2026-11-12-quyen-cua-nguoi-choi.md)
- 2026-11-12 · Train thử LoRA trên 12B: hết 24GB RAM, 2-3 tok/s; hoãn fine-tune sang Phase 5 · [lam-app-truoc-fine-tune-sau](decisions/lam-app-truoc-fine-tune-sau.md), [tu-train-model](features/tu-train-model.md), [learned](learned.md)
- 2026-11-12 · Chạy thẳng trên Mac, chưa dùng Docker · [chua-dung-docker](decisions/chua-dung-docker.md)
- 2026-11-12 · Phase 1: bản chơi được (chat Story, thẻ suy nghĩ, chỉ đạo ẩn, tạo lại, sửa, xoá, thích/chê) · [che-do-story](features/che-do-story.md), [the-suy-nghi](features/the-suy-nghi.md), [chi-dao-an](features/chi-dao-an.md), [thao-tac-tin-nhan](features/thao-tac-tin-nhan.md)
- 2026-11-12 · Góp ý sau Phase 1: bỏ cụm sáo "bầu không khí", suy nghĩ rải giữa truyện, DM có giao diện nhắn tin · [thought-rai-giua-truyen](decisions/thought-rai-giua-truyen.md), [dm-giao-dien-nhan-tin](decisions/dm-giao-dien-nhan-tin.md), [learned](learned.md), [raw](raw/2026-11-12-gop-y-phase1.md)
- 2026-11-12 · Bắt đầu Phase 2: Studio, AI viết nháp, nhập/xuất Card V2, persona, story, chế độ DM · [xuong-nhan-vat](features/xuong-nhan-vat.md), [ai-viet-nhap](features/ai-viet-nhap.md), [nhap-xuat-card](features/nhap-xuat-card.md), [che-do-dm](features/che-do-dm.md)
- 2026-11-12 · Sửa nhân vật thì mọi story dùng nhân vật đó đổi theo từ lượt sau · [card-doi-story-doi-theo](decisions/card-doi-story-doi-theo.md)
- 2026-11-12 · Chủ dự án gửi DESIGN.md; đổi tên app Nora thành Lyris, thư mục vẫn là nora · [ten-app-lyris](decisions/ten-app-lyris.md), [raw/DESIGN.md](raw/DESIGN.md), [raw](raw/2026-11-12-design-va-ten-lyris.md)
- 2026-11-12 · Theo DESIGN.md nhưng bớt dấu hiệu "AI gen"; dựng khung giao diện trước khi có dữ liệu · [tiet-che-thiet-ke](decisions/tiet-che-thiet-ke.md), [dung-khung-giao-dien-som](decisions/dung-khung-giao-dien-som.md)
- 2026-11-12 · Chủ dự án gửi bốn nhân vật (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương), yêu cầu dựng thế giới · [the-gioi-cho-nhan-vat](decisions/the-gioi-cho-nhan-vat.md), [raw](raw/2026-11-12-bon-nhan-vat-va-the-gioi.md)
- 2026-11-12 · Chọn chữ "Story"; ẩn pill "M2 sẵn sàng"; tách tài khoản và persona · [tach-tai-khoan-persona](decisions/tach-tai-khoan-persona.md), [raw](raw/2026-11-12-story-an-may-tai-khoan-persona.md)

## 2026-11-13

- 2026-11-13 · Phase 2b: giao diện theo DESIGN.md (hai theme, font, logo, 3 tab, hub, Khám phá, chat, Studio) · [giao-dien-theme](features/giao-dien-theme.md), [danh-sach-story](features/danh-sach-story.md), [design/style.md](design/style.md)
- 2026-11-13 · Thêm style profile `trung_dan_quoc` và thư mục `worlds/` cho bốn nhân vật · [van-phong-xung-ho](features/van-phong-xung-ho.md), [the-gioi-cho-nhan-vat](decisions/the-gioi-cho-nhan-vat.md)
- 2026-11-13 · Phase 2c: tài khoản, trang profile, nhiều persona có avatar · [tai-khoan-profile](features/tai-khoan-profile.md), [persona](features/persona.md)
- 2026-11-13 · DM tin nào cũng kết "ngủ sớm đi": thêm chống lặp câu · [chong-lap](features/chong-lap.md), [learned](learned.md), [raw](raw/2026-11-13-phase3-lap-y-va-dien-thoai.md)
- 2026-11-13 · Mở cổng 5173 ra mạng LAN để thử bằng điện thoại · [mo-cong-5173](decisions/mo-cong-5173.md), [truy-cap-lan](features/truy-cap-lan.md)
- 2026-11-13 · Phase 3: cảm xúc, ký ức, điều đã biết, tóm tắt, cảnh; không dùng sqlite-vec · [tri-nho](features/tri-nho.md), [ma-tran-cam-xuc](features/ma-tran-cam-xuc.md), [khong-sqlite-vec](decisions/khong-sqlite-vec.md)
- 2026-11-13 · Việc nền dùng chính model chat; mọi lời gọi dùng cùng num_ctx 8192 · [viec-nen-dung-model-chat](decisions/viec-nen-dung-model-chat.md), [cung-num-ctx](decisions/cung-num-ctx.md)
- 2026-11-13 · Nút "+" ở ô nhập; gợi ý chỉ sinh khi bấm; "Gửi hình ảnh" khoá "Sắp có" · [menu-cong](features/menu-cong.md), [nhan-goi-y](features/nhan-goi-y.md), [goi-y-chi-khi-bam](decisions/goi-y-chi-khi-bam.md), [gui-hinh-anh-chi-la-khung](decisions/gui-hinh-anh-chi-la-khung.md), [raw](raw/2026-11-13-o-chat-goi-y-va-an-ky-thuat.md)
- 2026-11-13 · Phase 3b: ẩn chữ kỹ thuật, ba chấm nhảy, mục "Nâng cao"; trình bày lại lượt người chơi · [an-chu-ky-thuat](features/an-chu-ky-thuat.md), [an-chu-ky-thuat](decisions/an-chu-ky-thuat.md), [dinh-dang-luot-nguoi-choi](features/dinh-dang-luot-nguoi-choi.md)
- 2026-11-13 · Chỉ số cảm xúc tăng và giảm theo tình huống (reason, tone) · [cam-xuc-tang-giam](decisions/cam-xuc-tang-giam.md), [learned](learned.md), [raw](raw/2026-11-13-cam-xuc-tang-giam.md)
- 2026-11-13 · Trích xuất cảm xúc nhanh hơn; lần đo chậm là do máy bận, không phải prompt · [ma-tran-cam-xuc](features/ma-tran-cam-xuc.md), [learned](learned.md)
- 2026-11-13 · Sheet "Sự kiện" gồm lượt của cả Story lẫn DM · [dong-thoi-gian-su-kien](features/dong-thoi-gian-su-kien.md), [su-kien-ca-hai-che-do](decisions/su-kien-ca-hai-che-do.md)
- 2026-11-13 · Thẻ nhân vật ở Khám phá nhỏ lại · [the-kham-pha-nho-lai](decisions/the-kham-pha-nho-lai.md), [kham-pha](features/kham-pha.md), [raw](raw/2026-11-13-kham-pha-va-ho-so-nhan-vat.md)
- 2026-11-13 · Chạm nhân vật mở hồ sơ chỉ đọc; CTA "Bước vào câu chuyện"; chọn persona sau CTA; bỏ trang tạo story riêng · [ho-so-nhan-vat](features/ho-so-nhan-vat.md), [buoc-vao-cau-chuyen](features/buoc-vao-cau-chuyen.md), [ho-so-nhan-vat-chi-doc](decisions/ho-so-nhan-vat-chi-doc.md), [thuat-ngu-story](decisions/thuat-ngu-story.md)
- 2026-11-13 · Chủ dự án gửi thêm ảnh nhân vật · [design/credits.md](design/credits.md), [raw](raw/2026-11-13-kham-pha-va-ho-so-nhan-vat.md)
- 2026-11-13 · Cửa sổ lịch sử cắt theo khúc; gửi trước phần đầu prompt khi rảnh (prefill raw) · [tang-toc-prefill](features/tang-toc-prefill.md), [cua-so-lich-su-theo-khuc](decisions/cua-so-lich-su-theo-khuc.md), [prefill-raw](decisions/prefill-raw.md), [learned](learned.md)
- 2026-11-13 · Thẻ thoại không còn dấu ngoặc ngoài cùng · [the-thoai-khong-ngoac](decisions/the-thoai-khong-ngoac.md), [raw](raw/2026-11-13-loi-thoai-va-dm-story.md)
- 2026-11-13 · Chủ dự án xin tuỳ chọn không đọc suy nghĩ của nhân vật · [tuy-chon-doc-suy-nghi](decisions/tuy-chon-doc-suy-nghi.md), [raw](raw/2026-11-13-khong-doc-suy-nghi.md)
- 2026-11-13 · Story và DM chung một dòng thời gian: lượt DM có nhãn; chưa thử trên model thật · [dm-story-chung-dong-thoi-gian](features/dm-story-chung-dong-thoi-gian.md), [story-dm-chung-dong-thoi-gian](decisions/story-dm-chung-dong-thoi-gian.md)
- 2026-11-13 · Hai câu thoại trong một lượt đều thành thẻ; `*"…"*` là trích dẫn; ô nhập ghi `Nhập lời thoại vào "…"` · [trich-dan-trong-dau-sao](decisions/trich-dan-trong-dau-sao.md), [placeholder-ngan](decisions/placeholder-ngan.md), [dinh-dang-luot-nguoi-choi](features/dinh-dang-luot-nguoi-choi.md)
- 2026-11-13 · Phase 4: thiết kế sổ thế giới, phản biện, làm backend; sổ nằm trong DB theo từng nhân vật, không đặt trong system · [so-the-gioi](features/so-the-gioi.md), [lore-trong-db-theo-card](decisions/lore-trong-db-theo-card.md), [lore-khong-trong-system](decisions/lore-khong-trong-system.md), [learned](learned.md)
- 2026-11-13 · Chủ dự án xin đăng nhập, tạo tài khoản, quản lý nhiều tài khoản; thêm Phase 4b vào plan · [dang-nhap](features/dang-nhap.md), [raw](raw/2026-11-13-dang-nhap-va-tai-khoan.md)

## 2026-11-14

- 2026-11-14 · Phase 4 giao diện: phần "Thế giới" trong Studio, phần thế giới đã mở trong ngăn cảm xúc, công tắc "Đọc suy nghĩ của nhân vật" (có cả trong menu "Suy nghĩ") · [so-the-gioi](features/so-the-gioi.md), [doc-suy-nghi](features/doc-suy-nghi.md), [lorebook-section](screens/lorebook-section.md), [thought-menu](screens/thought-menu.md)
- 2026-11-14 · Bỏ nơi mẫu trong prompt cảnh của DM (model chép nguyên mẫu) · [tri-nho](features/tri-nho.md), [learned](learned.md)
- 2026-11-14 · Chốt Phase 4b: mã mời, chủ máy, nhân vật công khai, chủ máy đặt lại mật khẩu · [dang-ky-bang-ma-moi](decisions/dang-ky-bang-ma-moi.md), [nhan-vat-cong-khai](decisions/nhan-vat-cong-khai.md), [quen-mat-khau](decisions/quen-mat-khau.md)
- 2026-11-14 · Viết thiết kế đăng nhập (docs/auth.md) và phản biện bảo mật lần 1 · [scrypt-va-phien](decisions/scrypt-va-phien.md), [learned](learned.md)
- 2026-11-14 · Phase 4b backend: đăng nhập, tách dữ liệu theo tài khoản, bản sao nhân vật công khai, cổng sinh chung · [dang-nhap](features/dang-nhap.md), [ban-sao-nhan-vat-cong-khai](decisions/ban-sao-nhan-vat-cong-khai.md), [cong-sinh-chung](decisions/cong-sinh-chung.md), [dung-chung-may](features/dung-chung-may.md)
- 2026-11-14 · Chat thật để train chỉ lấy từ tài khoản đã đồng ý (cho Phase 5) · [du-lieu-train-co-dong-y](decisions/du-lieu-train-co-dong-y.md)
- 2026-11-14 · Phase 4b giao diện: đăng nhập, tạo tài khoản, thiết lập chủ máy, quản lý tài khoản, công tắc "Công khai" · [quan-ly-tai-khoan](features/quan-ly-tai-khoan.md), [nhan-vat-cong-khai](features/nhan-vat-cong-khai.md), [login](screens/login.md), [signup](screens/signup.md), [admin](screens/admin.md)
- 2026-11-14 · Phản biện bảo mật lần 2 và sửa theo; test quét chữ "câu chuyện" ngoài CTA · [thuat-ngu-story](decisions/thuat-ngu-story.md), [learned](learned.md)
- 2026-11-14 · Khám phá hiện hai Hạ Vy: nhân vật nổi bật không lặp trong lưới, dùng ảnh của nhân vật đã thêm · [kham-pha](features/kham-pha.md), [learned](learned.md), [raw](raw/2026-11-14-kham-pha-trung-nhan-vat-va-luoi.md)
- 2026-11-14 · Ô nhân vật trong lưới luôn bằng nhau; số cột cố định 2/3/5 · [luoi-o-bang-nhau](decisions/luoi-o-bang-nhau.md), [explore](screens/explore.md), [learned](learned.md)
- 2026-11-14 · Chủ dự án xin wiki dự án theo mẫu · [raw](raw/2026-11-14-wiki-du-an.md)
- 2026-11-14 · Tạo wiki 1-wiki/ · [index.md](index.md)
- 2026-11-14 · Rà soát wiki: sửa endpoint SSE, icon menu Suy nghĩ, chong-lap thành Một phần (chưa thử trên model thật), Phase 6 cookie Secure, câu trích bịa ở tieng-viet-truoc, bỏ đường dẫn có tên máy, thêm route #/new-story vào start-story-sheet · [che-do-story](features/che-do-story.md), [the-suy-nghi](features/the-suy-nghi.md), [chong-lap](features/chong-lap.md), [overview](overview.md), [tieng-viet-truoc](decisions/tieng-viet-truoc.md), [ten-app-lyris](decisions/ten-app-lyris.md), [start-story-sheet](screens/start-story-sheet.md), [learned](learned.md), [index](index.md)
- 2026-11-14 · Đổi tên thư mục 1-wiki/ thành wiki/ (người dùng chọn) · [README.md](README.md)
