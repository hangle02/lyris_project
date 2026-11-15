# Bot checks: latest full run (evidence)

Generated from `reports/latest/report.json` (that folder is git-ignored, so this copy keeps the evidence in the repo).

- Run finished: `2026-11-14T16:52:39.677Z` (UTC), scenario `environment/e2e.mjs`, started by `bash verification/verify.sh` (see [verify-2026-11-14.json](verify-2026-11-14.json), `bot.checks = 113`, `bot.failed = []`, `202` s).
- Result: **113/113 checks passed**, 0 failed, infra errors: none.
- Where it runs: headless Chrome driven over the Chrome DevTools Protocol (`environment/bot.mjs` + `environment/e2e.mjs`) against the real backend and frontend on scratch ports with a scratch database and a **fake LLM server** (no Ollama, no real user data). Real-model behaviour is covered separately in [real-model-eval.md](real-model-eval.md).
- The same run saved 119 screenshots in `reports/latest/`; a selection is in [docs/assets/screenshots/](../assets/screenshots/).
- Check names are in Vietnamese, exactly as written in `environment/e2e.mjs` and listed under `## Tests` (`bot: …`) of each feature page in `wiki/features/`. The detail column is the bot's own note, copied as recorded.

| # | Check (as named in `environment/e2e.mjs`) | Result | Detail recorded by the bot |
|---|---|---|---|
| 1 | bot: trang pháp lý mở được khi chưa đăng nhập | pass |  |
| 2 | bot: trang đăng nhập hiện và đăng nhập được | pass |  |
| 3 | bot: chưa đăng nhập thì sang login rồi quay lại | pass | chưa đăng nhập: #/login → sau đăng nhập: #/studio |
| 4 | bot: nút đổi theme và nhớ lựa chọn | pass | light → dark (lưu "dark") → tải lại: dark |
| 5 | bot: chữ tiếng Việt có dấu vẽ bằng đúng ba font tự host, không rơi về font dự phòng | pass | Plus Jakarta Sans, Be Vietnam Pro, Cormorant Garamond: 10 kiểu chữ, mọi chữ có dấu vẽ bằng chính font |
| 6 | bot: sheet tài khoản có quyền riêng tư, chia sẻ dữ liệu, xuất, xoá tài khoản | pass |  |
| 7 | bot: Nâng cao gập, /api/system chỉ gọi khi mở | pass | ban đầu aria-expanded=false, /api/system trước khi mở: 0, sau khi mở: 2 |
| 8 | bot: sheet Tài khoản có đổi mật khẩu và đăng xuất | pass | Mọi điện thoại và máy tính đang đăng nhập @chumay sẽ phải đăng nhập lại, kể cả m |
| 9 | bot: trang giới thiệu có nguồn ảnh | pass | 4 nguồn ảnh |
| 10 | bot: thêm persona | pass | avatar chữ "B" |
| 11 | bot: đổi persona mặc định ở sheet Tài khoản | pass | "Bot Persona Hai" → "Lâm Vãn", sau tải lại aria-checked=true |
| 12 | bot: #/me có số liệu và hai tab | pass | Nhân vật 0 \| Persona 2 |
| 13 | bot: Sửa profile đổi tên ngay, handle sai báo dưới ô | pass | lỗi handle: "Handle không có khoảng trắng." · nút: "Tài khoản: Chủ máy Bot. Mở tài khoản" · không tải lại |
| 14 | bot: profile công khai theo handle | pass |  |
| 15 | bot: Sửa profile đổi giới thiệu, ảnh đại diện, ảnh bìa và #/me hiện đủ | pass | sheet: ảnh đại diện đã lưu, ảnh bìa đã lưu · #/me: giới thiệu có, ảnh đại diện 1, ảnh bìa 1 |
| 16 | bot: sửa và lưu nhân vật ở Studio | pass | "Lạc Dương" → "Lạc Dương Bot" |
| 17 | bot: tắt công cụ nâng cao thì trình sửa không có Xem trước | pass | tab: Hồ sơ, Chat thử |
| 18 | bot: lời nói đặc trưng quá 3 dòng bị chặn | pass | lỗi: "Chưa lưu được" · sau tải lại 0 dòng |
| 19 | bot: rời trình sửa còn thay đổi chưa lưu thì hỏi lại | pass | Huỷ: có hỏi → #/studio/1, ô "Lạc Dương Bot chưa lưu" · OK: có hỏi → #/studio · tên đã lưu "Lạc Dương Bot" |
| 20 | bot: chat thử ở Studio vẫn có suy nghĩ | pass | 3 thẻ suy nghĩ trong chat thử |
| 21 | bot: chat thử có ba chấm rồi trả lời | pass | chấm 156ms → chữ 1143ms |
| 22 | bot: chat thử ở Studio dùng persona mặc định | pass | persona mặc định "Bot Persona Hai" (#2; đầu tiên "Lâm Vãn", mới nhất "Bot Persona Ba") · Thiết lập thử: "Bot Persona Hai · Tiếng Việt · Story · Nam-nữ · Thought lồng" · request gửi persona_id 2 |
| 23 | bot: hồ sơ có phần Thế giới chỉ có tên | pass | tên: Hồ Gươm |
| 24 | bot: sổ thế giới không có chữ lore, keys, token | pass | studio: sạch · hồ sơ: sạch |
| 25 | bot: thêm mục thế giới lưu ngay | pass |  |
| 26 | bot: AI viết nháp mở hộp ý tưởng, lỗi không có chữ kỹ thuật | pass | AI viết nháp nhân vật |
| 27 | bot: AI viết nháp xong thì mở trình sửa với card nháp, chưa lưu | pass | #/studio/new, Tên nhân vật "Mai Chi Nháp" · header "chưa lưu" · chưa có trong /api/cards |
| 28 | bot: nhập card .json mở trình sửa | pass | mở trình sửa, chưa lưu · lưu thành #/studio/2 |
| 29 | bot: công tắc Công cụ nâng cao | pass | bật: có Ước lượng token · tắt: Hồ sơ, Chat thử |
| 30 | bot: công tắc Công khai trong phần Cơ bản, mẫu không có, lưu thì có Người khác thấy gì | pass | mẫu: không có công tắc · nhân vật nhập từ .json: công tắc ở phần 'Cơ bản', lưu xong có 'Người khác thấy gì' |
| 31 | bot: avatar tải lên ở Studio hiện ở Studio, Khám phá, hồ sơ và chat | pass | server: /api/cards/2/avatar?v=card-2-aa815b0d.png · editor 1, studio 1, explore 1, profile 1, chat 1 |
| 32 | bot: Khám phá tải xong, thẻ đều nhau, không tràn ngang 390px | pass | 6 thẻ |
| 33 | bot: chip cảm xúc chỉ giữ nhân vật có tag đó, bấm lại thì lưới như cũ | pass | "Chữa lành": 3 / 6, lưới 3 thẻ đều có tag → bỏ lọc: 6, lưới như cũ (6 thẻ) |
| 34 | bot: lưới Khám phá 2/3/5 cột | pass | 390px: 2 cột, 800px: 3 cột, 1280px: 5 cột |
| 35 | bot: hồ sơ nhân vật chỉ đọc, có nút Bước vào câu chuyện | pass | Hạ Vy · #/character/template/ha-vy |
| 36 | bot: hồ sơ mẫu không có Sửa nhân vật, có thanh dính đáy | pass | thanh dính đáy (cách đáy 0px) |
| 37 | bot: sheet bắt đầu chọn sẵn persona mặc định, Tuỳ chỉnh gập | pass | chọn sẵn: "L Lâm Vãn Nữ · 20 tuổi, sinh viên năm ha" (persona đang dùng: "Lâm Vãn") · Tuỳ chỉnh story aria-expanded=false |
| 38 | bot: bắt đầu story qua sheet và persona, story mở với lời chào | pass | persona đã chọn, lời chào 1235 ký tự |
| 39 | bot: lượt người chơi có lời nói và hành động không bị bọc ngoặc kép ngoài | pass | “Chào cậu, hôm nay trời đẹp quá nhỉ” + 1 đoạn hành động |
| 40 | bot: lời trả lời stream, chấm đang gõ rồi tới chữ | pass | chấm 35ms → chữ 948ms → xong 1838ms |
| 41 | bot: đang sinh có nút Dừng | pass | Dừng có lúc sinh, sinh xong đã ẩn |
| 42 | bot: lúc chờ chỉ có ba chấm, không có chữ | pass | chấm ở 35ms |
| 43 | bot: đang trả lời thì Sửa và Xoá từ đây bị khoá, có lý do (title) | pass | 316 lần soát nút Sửa/Xoá từ đây lúc đang trả lời, đều khoá · title: "Đợi nhân vật trả lời xong (hoặc bấm Dừng) rồi mới làm được." |
| 44 | bot: lượt nhân vật có thẻ thoại, thẻ suy nghĩ, dẫn truyện nghiêng | pass | 1 thẻ thoại, 1 đoạn dẫn truyện nghiêng không viền |
| 45 | bot: chỉ đạo ((...)) hiện thành chip | pass | aria-label đúng · chip: "Chỉ đạo cho nhân vật đang ghen nhưng không nói ra" |
| 46 | bot: thẻ suy nghĩ bị làm mờ, chạm thì hiện | pass | trước: blur(3px), sau: none, aria-pressed=true |
| 47 | bot: Luôn hiện suy nghĩ bỏ làm mờ | pass | 4 thẻ, 0 thẻ còn mờ, lyris.revealThoughts=true |
| 48 | bot: đổi kiểu suy nghĩ ở menu Suy nghĩ | pass | Lồng trong truyện / Một đoạn ở cuối · thought_style inline → end |
| 49 | bot: tắt Đọc suy nghĩ thì ẩn suy nghĩ | pass | thẻ suy nghĩ: 4 → 0 → bật lại 4 |
| 50 | bot: Thiết lập story có đủ ô, Xoá story hỏi lại | pass | có hỏi lại "Xoá vĩnh viễn" · bấm Huỷ: GET /api/stories/3 → 200 |
| 51 | bot: hàng thao tác có Thích, Chê, Sửa, Xoá từ đây hỏi lại | pass | có: Thích, Chê, Sửa, Xoá từ đây |
| 52 | bot: tạo lại ra phiên bản mới | pass | phiên bản 2/2 |
| 53 | bot: sheet báo cáo mở trên một lời trả lời | pass | 7 lý do |
| 54 | bot: nút Thêm 44px, sheet ở điện thoại, popover ở máy tính | pass | nút 44×44, aria-expanded false→true · 390: fixed, cách đáy 0px, nền mờ có · 1280: absolute, phía trên nút |
| 55 | bot: Gửi hình ảnh bị khoá, Sắp có | pass | Gửi hình ảnh · Sắp có · Sắp tới bạn sẽ gửi được ảnh cho nhân vật xem. |
| 56 | bot: menu cộng đi bằng phím, Esc trả focus | pass | Nhận gợi ý → ArrowDown:Xem sự kiện → ArrowDown:Gửi hình ảnh → ArrowUp:Xem sự kiện → Home:Nhận gợi ý → End:Gửi hình ảnh · Esc: menu đóng, focus "Thêm" |
| 57 | bot: menu cộng, Nhận gợi ý hiện gợi ý | pass | 3 gợi ý |
| 58 | bot: chờ gợi ý có Huỷ gợi ý, chạm thẻ là gửi | pass | lúc chờ: ba chấm, có Huỷ gợi ý · gửi "Không có gì đâu, chỉ là nhớ cậu thôi." |
| 59 | bot: menu cộng mở sheet Sự kiện | pass | Dòng thời gian \| Khoảnh khắc |
| 60 | bot: chạm mục dòng thời gian thì nhảy tới lượt | pass | 4 mục Story, chạm "Story · 23:50" → Lượt của Hạ Vy trong màn hình, có focus |
| 61 | bot: ngăn trái tim mở với 6 cảm xúc | pass | Thương mến, Tin cậy, Rung động, Nhung nhớ / Chiếm hữu, Lo sợ mất mát, Khoảng cách |
| 62 | bot: ngăn trái tim có Chỉ dẫn diễn xuất và phần trăm | pass | chỉ dẫn: "Hạ Vy có thiện cảm và bắt đầu tin tưởng Bot Person" · 39% 36% 10% 0% 0% 20% |
| 63 | bot: ngăn trái tim có ký ức và nút Quên, header có cảnh | pass | 5 nút Quên, 5 ký ức có nhãn · header: có nơi chốn · thời gian |
| 64 | bot: chuyển sang DM rồi quay lại Story | pass | 1 tin của nhân vật trong DM, 4 lượt Story khi quay lại |
| 65 | bot: DM có avatar, chân Đã gửi/Đã xem, bong bóng ba chấm | pass | chân: "23:50 • Đã xem" · avatar có · ba chấm cạnh avatar có |
| 66 | bot: lượt mode kia thành một dòng nhãn | pass | nhãn "7 lượt trong truyện" |
| 67 | bot: DM có thẻ suy nghĩ thu gọn | pass | có thẻ suy nghĩ thu gọn |
| 68 | bot: placeholder ô nhập và lượt người chơi căn phải | pass | Story: Nhập lời thoại vào "…" · DM: Nhắn tin… · lề phải 54px, lề trái 70px · avatar bên phải |
| 69 | bot: Đọc suy nghĩ có ở header, sheet bắt đầu, Thiết lập story | pass | header "Suy nghĩ (đang ẩn)": có · DM ẩn thẻ: true · sheet bắt đầu: có · Thiết lập story: có |
| 70 | bot: Tìm story lọc danh sách, xem trước sạch | pass | 3 story · "Hạ Vy": 1 · không khớp: 0 (có câu báo) |
| 71 | bot: nhắc từ khoá thì mục thế giới mở khoá | pass | có phần Thế giới đã mở khoá · có nút Xem lúc được nhắc tới lần đầu |
| 72 | bot: story dài (cửa sổ đã dịch) có Tóm tắt những lượt cũ trong ngăn trái tim | pass | story #4: 13 lượt, 38489 ký tự (~12830 token > num_ctx 8192) · tóm tắt server: "Hai người gặp nhau ở quán trà nhỏ, trêu đùa và hẹn gặp lại." · <details>: có (gập sẵn), mở ra: "Hai người gặp nhau ở quán trà nhỏ, trêu đùa và hẹn gặp lại." |
| 73 | bot: trang quản trị của chủ máy có tài khoản, mã mời, Số liệu | pass |  |
| 74 | bot: chủ máy có mục Báo cáo | pass | Số liệu · Báo cáo |
| 75 | bot: chủ máy tạo mã mời | pass | LYR-987Q-XQ8N-Q5WT · lựa chọn 7 ngày: có |
| 76 | bot: màn desktop 1280px không tràn ngang | pass |  |
| 77 | bot: nhân vật không có thì báo không tìm thấy | pass |  |
| 78 | bot: đã có story thì thanh dính đáy của hồ sơ có Tiếp tục story | pass | Tiếp tục story: cách đáy 0px · Bước vào câu chuyện: cách đáy 0px · bấm Tiếp tục story → #/chat/3 (story của bot: #/chat/3) |
| 79 | bot: link new-story cũ chuyển sang hồ sơ | pass | #/new-story?card=1 → #/character/1, sheet bắt đầu mở |
| 80 | bot: danh sách persona trong sheet bắt đầu là radio thật, mỗi persona có avatar | pass | 2 persona, mỗi dòng input radio cùng name + avatar (0 ảnh, 2 chữ cái) · mũi tên: "Lâm Vãn" → "Bot Persona Hai" → "Lâm Vãn" |
| 81 | bot: link mời điền mã và bỏ mã khỏi URL | pass | ô: LYR-987Q-XQ8N-Q5WT · địa chỉ: #/signup |
| 82 | bot: hub rỗng có Mở Khám phá, khối mời đặt profile | pass | có Mở Khám phá · có khối Đặt tên cho tài khoản |
| 83 | bot: thành viên mở #/admin thì về hub | pass | #/admin → #/ · 0 request /api/admin |
| 84 | bot: tài khoản khác thấy nhân vật được chia sẻ | pass | bởi @chumay → #/u/chumay |
| 85 | bot: nhân vật công khai có dòng bản sao | pass | Bạn chơi với Mộc Lan Nhập như bây giờ. @chumay sửa nhân vật sau này thì story của bạn không đổi. |
| 86 | bot: chưa có persona thì sheet bắt đầu tự mở form Tạo persona mới | pass | 0 persona lúc đầu · form tự mở, 0 radio · tạo "Thành viên Bot": được chọn · Bước vào câu chuyện → #/chat/5 |
| 87 | bot: chọn model của story chỉ có trong Nâng cao của Thiết lập story, chỉ chủ máy thấy | pass | chủ máy: sheet bắt đầu không có model, Thiết lập story chưa có model khi 'Nâng cao' aria-expanded=false, mở ra: ô Model trả lời (bge-m3, gemma4:12b) · thành viên: sheet không có model, Thiết lập story không có 'Nâng cao' hay model |
| 88 | bot: đăng nhập ở #/login thì vào Tương tác, không tự mở story | pass | sau đăng nhập: #/ · 4 story trong danh sách · có nút … Mở tài khoản |
| 89 | bot: mở app lần đầu trong ngày được +60 coin | pass | thông báo: có '+60 coin cho hôm nay' ở #/ · số dư ở #/coins: 360 (cần 360) |
| 90 | bot: gửi một lượt thì ví giảm đúng 6 coin | pass | #/coins: 360 → 354 (giảm 6, cần 6) |
| 91 | bot: chip coin trên header mở Ví coin | pass | chip 'Coin: 354. Mở ví coin' → Ví coin · số dư 354 · Nạp coin · Nhiệm vụ · Lịch sử có 'Quà tạo tài khoản' · tràn ngang 0px (header 0px) |
| 92 | bot: sheet Tài khoản có số coin, chủ máy không tốn coin | pass | thành viên: 'Coin · 354 coin · Mở ví coin' (cần '354 coin' + nút Mở ví coin) · chủ máy: 'Tài khoản quản lý không tốn coin.', header không có nút 'Coin: …' |
| 93 | bot: hết coin thì ô nhập khoá, có Nạp coin và Nhiệm vụ | pass | ô nhập disabled · nút Gửi khoá · có 'Bạn đã hết coin' · Nạp coin → #/coins/top-up · Nhiệm vụ → #/missions · tràn ngang 0px |
| 94 | bot: hết coin thì ô nhập DM cũng khoá | pass | ô 'Tin nhắn cho …' disabled · có 'Bạn đã hết coin' · có Nạp coin · có Nhiệm vụ · tràn ngang 0px |
| 95 | bot: Nạp coin có gói giá chế độ thử và ô mã nạp | pass | tiêu đề 'Nạp coin' · có 'Chế độ thử … chưa bán coin' · 4 thẻ gói · ô 'Mã nạp' có · nút 'Dùng mã' có · hộp gói: 'Giá dự kiến khi Lyris ra mắt', nút [Đóng, Đóng] · tràn ngang 0px / 0px |
| 96 | bot: chủ máy cộng coin cho thành viên có lý do | pass | hàng @hetcoin: '0 coin' → '20 coin' (cần +20) · Nhật ký có 'thử bot' · tràn ngang 0px / 0px |
| 97 | bot: chủ máy tạo mã nạp, thành viên dùng mã thì ví tăng | pass | chủ máy: hộp 'Mã nạp mới' có 'Sao chép mã' · @hetcoin: 'Đã nạp 100 coin.' · #/coins 20 → 120 (cần +100) |
| 98 | bot: Nhiệm vụ hôm nay có ba nhiệm vụ và trần 30 coin | pass | tiêu đề 'Nhiệm vụ hôm nay' · 'Đã nhận 0/30 coin hôm nay' · dòng: Xem quảng cáo 0/3 \| Trò chuyện với 3 nhân vật khác nhau 0/3 \| Gửi 20 lượt 0/20 · nút 'Xem' có · tràn ngang 0px |
| 99 | bot: quảng cáo mẫu đếm ngược rồi nhận 5 coin | pass | hộp: có 'chưa phải quảng cáo thật' · 'Còn 15 giây' · nút 'Nhận 5 coin' khoá lúc đầu · mở khoá khi hết giờ · dòng 0/3 → 1/3 (cần 0/3 → 1/3) · 'Đã nhận 5/30 coin hôm nay' · #/coins 120 → 125 (cần +5) · tràn ngang 0px |
| 100 | bot: bảng Nhân vật hot rỗng thì Khám phá vẫn có dải và nút Xem bảng xếp hạng, bảng mời Mở Studio | pass | dải: 'Nhân vật hot' · 'Chưa có nhân vật nào trên bảng xếp hạng.' · 'Xem bảng xếp hạng' → #/explore/hot · bảng rỗng · 'Mở Studio' → #/studio |
| 101 | bot: trình sửa nhân vật công khai có số người chơi, hạng Nhân vật hot và điều kiện bậc thưởng | pass | dựng sẵn 12 người chơi (hạng 1) · công khai: '12 người chơi · Hạng 1 Nhân vật hot Bậc thưởng tiếp theo: top 10 (+300 coin) Thưởng top 10 chỉ có khi bảng có nhân vật của ít nhất 10 người tạo khác nhau (hiện có 1). Người chơi là tài khoản … |
| 102 | bot: Khám phá không còn khung nổi bật, có dải Nhân vật hot mở bảng xếp hạng | pass | không khung nổi bật · dải: Hạng 1: Hạ Vy Quán Trà, 12 người chơi · thẻ Hạ Vy trong lưới · bấm 'Xem bảng xếp hạng' → #/explore/hot |
| 103 | bot: bảng Nhân vật hot có hạng, ảnh, tên, số người chơi và mở hồ sơ | pass | 'Hạng 1: Hạ Vy Quán Trà, 12 người chơi' (ảnh đã tải) · Cập nhật lúc 23:52 · bấm → #/character/7 "Hạ Vy Quán Trà" · 'Về Khám phá' → #/explore |
| 104 | bot: bảng Nhân vật hot và dải ở Khám phá không tràn ngang 390px, hàng và nút chạm được 44px | pass | sáng: dải 56px, bảng 1 hàng 64px+, nút 147×44 / 44×44 · tối: dải 56px, bảng 1 hàng 64px+, nút 147×44 / 44×44 |
| 105 | bot: tìm 'ha vy' không dấu ra thẻ Hạ Vy, xoá tìm thì lưới như cũ | pass | 'ha vy' → 1 / 6: Hạ Vy (245ms; dải ẩn) · 'Xoá tìm kiếm' → 6, lưới như cũ |
| 106 | bot: tìm không có kết quả thì báo và có nút Xoá tìm kiếm | pass | 'zzqxy': báo không có kết quả, 0 thẻ · 'Xoá tìm kiếm' → lưới như cũ (6 thẻ) · 'ha vy' + chip 'Bí ẩn nội tâm': không có kết quả |
| 107 | bot: ô Tìm nhân vật vừa một dòng 390px, cao 44px, không tràn ngang | pass | sáng: ô cao 44px, placeholder 92/172px, nút × 44×44 · tối: ô cao 44px, placeholder 92/172px, nút × 44×44 |
| 108 | bot: thanh tab 3 tab, ẩn ở màn con | pass | #/=3 #/personas=0 #/studio=3 #/studio/<id>=0 #/character/<id>=0 #/explore=3 #/chat/<id>=0 #/explore/hot=3 |
| 109 | bot: 390px nút dưới lượt chat và nút hộp Xác nhận xoá ≥ 44px | pass | 11 nút (hàng thao tác dưới lượt cuối, hộp Xác nhận xoá) đều ≥ 44px ở 390px |
| 110 | bot: 390px không tràn ngang, nút header và thanh tab ≥ 44px ở #/, #/studio, #/chat | pass | #/, #/studio, #/chat: không tràn; nút header và thanh tab ≥ 44px |
| 111 | bot: không có request ra ngoài | pass | 9473 request, đều tới http://127.0.0.1:8067 |
| 112 | bot: không có lỗi console | pass | 25 lỗi mạng đúng kịch bản (/khong_ton_tai_xyz), (/api/cards/draft), /api/cards/999999, /^\[đăng xuất\] Failed to load resource: the server responded with a status of 401\b/, (/api/cards/2), /^\[coin: đổi tài khoản\] Failed to load resour… |
| 113 | bot: không lộ chữ kỹ thuật trên các trang | pass | 43 màn |
