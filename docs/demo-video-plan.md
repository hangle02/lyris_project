# Video demo Lyris trên nền nhạc "Gasoline": kế hoạch và kịch bản (bản 3, chờ duyệt)

> Không lời đọc. **Tính năng là chính, câu chuyện là sợi chỉ nối.** Video đi qua các tính năng trong README theo
> đúng hành trình của người dùng: *chọn hoặc tạo nhân vật → chọn mình là ai → nhân vật phản ứng thật (kịch tính lẫn
> dịu dàng) → bạn điều chỉnh mọi thứ → chia sẻ, an toàn, riêng tư.* Bản có lời đọc vẫn ở [demo-script.md](demo-script.md).

## 1. Nhạc (đã chốt)

`demo-video/public/music/gasoline-loop-v4.wav`, tách từ `~/Downloads/example.MP4`, lặp ba lần theo ô nhịp và chèn thêm
bốn câu nhạc trước phần kết (cảnh "Thưởng sáng tác", "Mọi màn hình" và cảnh "Sắp có"), dài **2:22**. Khoảng 98 BPM: mỗi phách 0,61 giây,
mỗi câu nhạc (8 phách) 4,88 giây. Mốc phách nằm ở `demo-video/src/music.json` (video và script quay dùng chung).

**Cách dựng các cảnh app (bản hiện tại):** màn hình app được **dựng lại bằng code** (animation: gõ chữ, chữ stream,
cuộn, sheet trượt, chạm) theo đúng giao diện app thật, nhưng **toàn bộ chữ là nội dung thật** app và model đã trả ra
trong lần quay (`demo-video/src/content.ts`, lấy từ DB demo). Clip quay màn hình vẫn giữ trong `public/clips/` nhưng
không dùng (trông như ảnh chụp màn hình).

Bản quyền: bài hát có bản quyền, lấy từ video của người khác. Link chính trong README là **Google Drive**; YouTube có thể
tắt tiếng hoặc chặn. Clip mẫu chỉ là cảm hứng về nhịp và kiểu chữ, không dùng lại hình của tác giả.

## 2. Phong cách

**Hình app giữ nguyên thiết kế của app.** Không đổi màu, không đổi font, không vẽ đè lên giao diện. Mọi thứ thêm vào
(nền, chữ, khung, hiệu ứng) đều dùng token trong [wiki/design/style.md](../wiki/design/style.md).

| Thành phần | Làm thế nào |
|---|---|
| Nền video | Theo theme của cảnh: tối `#130D14` Velvet Mulberry với quầng sáng nến; sáng `#FAF5EE` Silk Parchment ở phần chữa lành. Đổi theme thì nền đổi trong 500ms, như vặn đèn |
| Khung điện thoại | App quay 390 × 844 trong khung bo 48px, viền `line`, bóng `shadow-float`. Lệch phải, chữ bên trái |
| Chữ hai dòng | Dòng 1: `Be Vietnam Pro` 400, màu `fg`. Dòng 2 (chữ nhấn): `Cormorant Garamond` nghiêng 700, tô `accent` hoặc `accent-2`, quầng sáng nhẹ cùng màu. Hiện bằng **mờ → rõ** đúng phách |
| Dòng tiếng Anh | `Plus Jakarta Sans` 500, màu `muted`, nhỏ, dưới dòng 2 |
| Nhãn phần | Góc trên trái: `Lyris — 01 · Chọn` / `02 · Sống` / `03 · Làm chủ` |
| Nhãn tính năng | Viên chip kiểu `Chip` của app (`surface-2`, viền `line`) hiện cạnh chỗ đang bấm, ví dụ `Nhận gợi ý` |
| Màu theo cảm xúc | Cảnh kịch tính nhấn đỏ Chiếm hữu `#D15B5B`; cảnh chữa lành nhấn vàng nến `#F3C68F` và Thương mến `#D86C86` |

**Bộ hiệu ứng cho đoạn đặc sắc** (dùng có chọn lọc, khoảng 1–2 lần mỗi câu nhạc):

| Hiệu ứng | Dùng ở đâu |
|---|---|
| **Phóng to** 1,6–2,2× vào đúng chi tiết rồi thu về | thẻ suy nghĩ, vạch cảm xúc, chữ nhân vật nhắc lại ký ức, nút lật phiên bản |
| **Rọi sáng**: phần còn lại của màn tối đi 55 %, chi tiết chính sáng lên, viền `accent` mảnh quanh nó | ô "Thế giới đã mở khoá", chip gợi ý, công tắc trong Thiết lập story |
| **Thẻ suy nghĩ hết mờ đúng phách mạnh** | chữ ký của video, xuất hiện ở cả cảnh kịch tính lẫn dịu dàng |
| **Nhấn nhịp**: phóng 1,00 → 1,04 trong 2 khung hình, loé `accent` 8 % | lúc bấm gửi, lúc mở ngăn trái tim |
| **Tách lớp**: kéo một khối (thẻ thoại, bong bóng DM) ra khỏi màn điện thoại, phóng lớn bên cạnh | câu thoại đẹp nhất của mỗi nhân vật |

**Trung thực.** Câu trả lời của nhân vật là model thật trong app. Chỉ tua đoạn chờ, có chip nhỏ "tua nhanh ·
fast-forward" ở góc. Thao tác tay (cuộn, gõ) được tăng tốc vừa phải. Chữ chú thích ở cảnh có câu trả lời thật viết sau
khi quay, theo đúng những gì model trả lời; cột "Chữ" dưới đây là bản dự kiến.

## 3. Kịch bản

Mỗi dòng là một câu nhạc (8 phách, 4,88 giây). Chữ: dòng 1 / **dòng 2** · *English*.

### Phần 1 · Chọn (0:00–0:42,7)

| # | Thời điểm | Hình | Chữ | Tính năng |
|---|---|---|---|---|
| 1.1 | 0:00–0:03,7 | Trang sách mở, 5 tiếng dồn của dạo đầu = 5 trang lật. Người đọc là một bóng mờ **đứng bên ngoài khung trang**, như nhìn qua lớp kính | Bình thường, bạn đứng ngoài câu chuyện. / **Chỉ đọc.** · *Usually, you stand outside the story. You just read.* | |
| 1.2 | 0:03,7–0:08,6 | Đúng phách mạnh đầu câu nhạc, **tấm kính vỡ** (bụi vàng); chữ trên trang **biến thành màn Story của Lyris**: đoạn dẫn truyện nghiêng, thẻ thoại, thẻ suy nghĩ mờ. Phách 3.5, một **bong bóng của người chơi** trượt vào từ bên phải: bạn đã ở trong truyện | Với Lyris, / **bạn là một phần của câu chuyện.** · *With Lyris, you become part of the story.* | |
| 1.3 | 0:08,6–0:13,5 | Đúng phách mạnh, cuốn sách tan hẳn, **logo + wordmark Lyris phóng to giữa màn** trên nền trống. Phách 2: nhãn **AI ROLEPLAY APP**; phách 3: tagline. Giữ ở giữa tới hết câu nhạc rồi phóng nhẹ, tan thẳng vào cảnh 1.4 (không thu về góc) | AI ROLEPLAY APP · *Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại.* | |
| 1.4 | 0:13,5–0:18,4 | Khung điện thoại vào. **Khám phá**: thẻ nổi bật; chạm lần lượt chip vibe **Chữa lành → Tình đầu → Bí ẩn**, lưới thẻ bằng nhau lọc lại theo phách | Chọn nhân vật theo cảm xúc bạn cần. · *Pick a character by the feeling you need.* | Khám phá, vibe |
| 1.5 | 0:18,4–0:23,2 | Chạm **Lục Bắc Uyên** → hồ sơ (ảnh 4:5, tên Cormorant, câu nói đặc trưng). Tách lớp câu nói đặc trưng ra bên cạnh | Mỗi nhân vật có giọng nói, quá khứ / **và cả một thế giới.** · *Each has a voice, a past, and a whole world.* | Hồ sơ nhân vật |
| 1.6 | 0:23,2–0:28,1 | **Studio** → **AI viết nháp**: gõ một dòng *"Chủ tiệm sách cũ trên gác xép, dịu dàng, hay pha trà gừng cho người thức khuya"* → form tự điền (tên **Hạ Vy**, tính cách, câu nói đặc trưng, xưng hô) | Hoặc tự tạo, chỉ từ một dòng ý tưởng. · *Or create your own from a single line.* | Studio, AI viết nháp |
| 1.7 | 0:28,1–0:33,0 | Studio tiếp: tải ảnh đại diện; **Sổ thế giới** của Lục Bắc Uyên (nhân vật phụ, nơi chốn, mục lore) với nhãn **ai biết**: mọi người / chỉ nhân vật / chỉ bạn. Rọi sáng nhãn "chỉ bạn". Nút nhập/xuất card | Thêm thế giới, bí mật, / **và ai được biết điều gì.** · *Add a world, its secrets, and who knows what.* | Sổ thế giới, nhập/xuất card |
| 1.8 | 0:33,0–0:42,7 | **Persona**: ba thẻ persona lật theo phách (*Ôn Nhiên*, tiểu thư xuyên sách · *Lâm An*, nhân viên văn phòng hay thức khuya · *Tiểu Mãn*, hoạ sĩ màu nước). Sheet **Bước vào câu chuyện**: chọn persona, **Kiểu quan hệ** (Ngôn tình / Đam mỹ / Bách hợp / Không lãng mạn), xưng hô → bấm **"Bước vào câu chuyện"** đúng phách cuối | Bạn không cần chỉ là bạn. / **Hôm nay, bạn muốn là ai?** · *You don't have to be just you. Who will you be today?* | Persona, thiết lập story, bắt đầu story |

### Phần 2 · Sống (0:42,7–1:21,7): nhân vật phản ứng thật, kịch tính rồi dịu dàng

| # | Thời điểm | Hình | Chữ | Tính năng |
|---|---|---|---|---|
| 2.1 | 0:42,7–0:47,6 | Theme tối. Lời mở đầu của Lục Bắc Uyên (đêm đính hôn, hộp nhẫn sapphire). Phóng vào thẻ suy nghĩ mờ "Chạm để lắng nghe" → chạm đúng phách: *"Lần này định diễn tới bao giờ?"* | Nghe điều nhân vật / **không bao giờ nói ra.** · *Hear what they never say out loud.* | Story, thẻ suy nghĩ |
| 2.2 | 0:47,6–0:52,5 | Story đã chơi sẵn: gõ `"Tối qua anh nói chuyện với Phó Cảnh Hành rất lâu." *Tôi đặt ly trà xuống.*`. Chip chú thích: `"…" lời bạn · *…* hành động` → gửi | Bạn viết phần của bạn. / **AI không bao giờ nói thay bạn.** · *You write your part. The AI never speaks for you.* | Lượt người chơi |
| 2.3 | 0:52,5–0:57,4 | Câu trả lời thật: hắn điềm tĩnh hỏi lại *"Em biết tôi nói với cậu ấy?"*; thẻ suy nghĩ hết mờ: *"Em ấy đang quan sát tôi kỹ hơn tôi tưởng."* | Ngoài mặt điềm tĩnh, / **trong lòng thì không.** · *Calm on the surface. Not inside.* | Story |
| 2.4 | 0:57,4–1:02,3 | Ngăn **trái tim**: phóng vào 6 vạch cảm xúc. Cuộn xuống, rọi sáng **"Thế giới đã mở khoá"** (có mục Phó Cảnh Hành) | Hắn cảm thấy gì, nhớ gì, / **và thế giới đã mở ra tới đâu.** · *What he feels, what he remembers, how much of the world has opened.* | 6 cảm xúc, ký ức, sổ thế giới |
| 2.5 | 1:02,3–1:07,1 | Nút **Mặt trời**: app và nền video chuyển sang **Rosewater Parchment**, như bật đèn sáng | Trải qua mọi cung bậc, từ kịch tính nghẹt thở / **đến xoa dịu tâm hồn.** · *Every shade of feeling, from breathless drama to comfort for the soul.* | Theme sáng/tối |
| 2.6 | 1:07,1–1:12,0 | Story với **Hạ Vy** (nhân vật mẫu chủ tiệm sách cũ ở Đà Lạt), persona Lâm An. Thẻ suy nghĩ hết mờ: *"Ánh mắt của cậu ấy lúc say sưa đọc sách trông buồn lắm."* | Có người nhận ra / **nỗi buồn bạn chưa nói.** · *Someone sees the sadness you haven't said.* | Nhân vật dịu dàng |
| 2.7 | 1:12,0–1:16,9 | Công tắc **Story / DM** → DM: Lâm An nhắn `Mai mình mang bánh hạt dẻ qua tiệm nhé.`; Hạ Vy nhắn lại, chân tin "Đã xem". Tách lớp bong bóng | Nhắn tin cũng là / **một phần của câu chuyện.** · *Texting is part of the same story.* | DM, chung dòng thời gian |
| 2.8 | 1:16,9–1:21,7 | Về **Story**: `*Chiều hôm sau, tôi đẩy cửa tiệm sách.*` → Hạ Vy nhắc đúng bánh hạt dẻ (phóng vào, gạch chân vàng). Ngăn trái tim: **Thương mến ↑** | Hẹn qua tin nhắn. / **Cô ấy vẫn nhớ.** · *A promise by text. She still remembers.* | Trí nhớ, cảm xúc |

### Phần 3 · Làm chủ (1:21,6–2:07,2)

| # | Thời điểm | Hình | Chữ | Tính năng |
|---|---|---|---|---|
| 3.1 | 1:21,7–1:26,6 | Về theme tối. Dưới một câu trả lời: **"Tạo lại câu trả lời"** → bản mới chạy; lật phiên bản 1 ⇄ 2 ⇄ 3 theo phách (phóng vào số phiên bản); bấm **Thích** | Chưa ưng? / **Viết lại, chọn bản bạn thích.** · *Not quite right? Rewrite it and keep the one you like.* | Tạo lại, phiên bản, thích/chê |
| 3.2 | 1:26,6–1:31,5 | Gõ chỉ đạo ẩn `((Hắn kể về người cha))` → chip chỉ đạo nhỏ trong lượt; câu trả lời đi theo hướng đó. Lướt nhanh **Sửa** và **Xoá từ đây** | Đạo diễn câu chuyện / **mà nhân vật không hề biết.** · *Direct the scene without the character knowing.* | Chỉ đạo ẩn, sửa, xoá |
| 3.3 | 1:31,5–1:36,4 | Nút **"+"** → **Nhận gợi ý** → ba thẻ gợi ý (rọi sáng), chạm một thẻ. Rồi **"+" → Sự kiện**: dòng thời gian các mốc của story | Bí ý tưởng? Xin gợi ý. / **Nhìn lại cả hành trình.** · *Stuck? Ask for ideas. Look back on the whole journey.* | Menu "+", gợi ý, sự kiện |
| 3.4 | 1:36,4–1:41,3 | **Thiết lập story**: rọi sáng công tắc **"Đọc suy nghĩ của nhân vật"** và **"Luôn hiện suy nghĩ"**, đổi văn phong và xưng hô | Mỗi câu chuyện / **chỉnh theo cách của bạn.** · *Tune every story your way.* | Thiết lập story, công tắc suy nghĩ |
| 3.5 | 1:41,3–1:46,1 | Tab **Tương tác**: danh sách story với nhiều nhân vật và persona khác nhau (Lục Bắc Uyên, Hạ Vy, Cố Hoài Dã, Tần Dương…), huy hiệu Story/DM, ô tìm kiếm | Mỗi nhân vật, mỗi persona, / **một câu chuyện riêng.** · *Every character, every persona, its own story.* | Danh sách story |
| 3.6 | 1:46,1–1:51,0 | **Đăng nhập, tạo tài khoản dễ dàng** (bản app chạy trên server, không cần mã mời): màn đăng nhập → "Tạo tài khoản" → điền tên, tên đăng nhập, mật khẩu, đồng ý Điều khoản → vào app, chip coin đếm lên **360** với lời chào "+300 coin quà tạo tài khoản", "+60 coin cho hôm nay" | Tạo tài khoản trong vài giây, / **là bước vào câu chuyện.** · *Sign up in seconds, then step into a story.* | Đăng nhập, tạo tài khoản, quà 300 coin |
| 3.7 | 1:51,0–1:55,9 | **Coin** (docs/coins.md): chạm chip coin → **Ví coin** (số dư, "Mỗi câu trả lời của nhân vật tốn 6 coin.", lịch sử trừ theo nhân vật, +60 đăng nhập hôm nay) → **Nhiệm vụ hôm nay** (tối đa 30 coin/ngày) → **Nạp coin** (gói 100 / 550 / 1.200 / 2.500 coin, "Giá dự kiến") | Mỗi câu trả lời 6 coin. / **Mỗi ngày tặng thêm 60.** · *Each reply costs 6 coins. 60 free coins every day.* | Ví coin, nhiệm vụ hằng ngày, nạp coin |
| 3.8 | 1:55,9–2:00,8 | **Thưởng sáng tác** (F44 làm lại + F46, đang làm; tên nhân vật khác và số người chơi là minh hoạ): bảng **Nhân vật hot** ("Xếp theo tổng số người chơi. Cập nhật mỗi giờ.", rọi sáng câu thưởng top 100/50/10 = 100/200/300 coin). Nhân vật của bạn (Tần Dương, dòng ghim ở đáy, hạng 12) — lần cập nhật kế tiếp **leo lên hạng 7**, các hạng dưới dời xuống → thẻ **+300 coin · Tần Dương vào top 10 Nhân vật hot** trượt lên, số dư đếm 318 → 618 | Sáng tác nhân vật được nhiều người chơi, / **bạn kiếm thêm coin.** · *Create a character people love, and earn coins.* | Thưởng sáng tác, Nhân vật hot, Top 100 · 50 · 10 |
| 3.9 | 2:00,8–2:05,4 | **Mọi màn hình:** cửa sổ trình duyệt máy tính (story Lục Bắc Uyên, 1440 × 900), máy tính bảng (Khám phá lưới 3 cột, 834 × 1194), điện thoại (story Hạ Vy) lần lượt hiện theo phách | Điện thoại, máy tính bảng, máy tính. / **Câu chuyện đi theo bạn.** · *Phone, tablet, desktop. Your story goes with you.* | Giao diện đáp ứng |
| 3.10 | 2:05,6–2:15,4 | **Sắp có · Coming soon** (tính năng tương lai, ghi rõ trên màn). Phần 1: Hạ Vy **gọi điện** — bắt máy, sóng âm, phụ đề kèm sắc thái giọng ("dịu dàng", "khẽ cười"). Phần 2: màn **Tender Moment** riêng (đầu màn có nhãn "Tender Moment" và sóng âm, không có công tắc Story/DM) — chip âm thanh (mưa trên mái tôn, rót trà, bước chân), lời thoại có giọng đọc, giữ micro để **nói bằng giọng thật** rồi gửi thành tin nhắn thoại | Nghe giọng nhân vật, / **trò chuyện không ngắt quãng.** → Tender Moment: hòa vào cùng một không gian / **với âm thanh sống động.** | Gọi điện, giọng nhân vật, không ngắt quãng · Tender Moment, âm thanh sống động, nói bằng giọng thật |
| 3.11 | 2:15,4–2:21,8 | Trang sách của cảnh 1.2, lần này có bong bóng của người chơi. Câu chốt, logo hiện ở góc rồi **phóng ra giữa màn**, phía sau mờ đi; ghi công nhóm chữ nhỏ ở mép dưới; cả màn tối dần theo nhạc fade | Đừng chỉ đọc câu chuyện. / **Bước vào nó.** · *Don't just read the story. Step into it.* · **Lyris** · Team 12 (tên và mã số thành viên) | |

Ở cảnh 1.3, tên app chiếm trọn một câu nhạc: logo + wordmark **phóng to giữa màn** (cuốn sách tan hẳn) kèm dòng giới thiệu, rồi tan thẳng vào cảnh app.

### Độ phủ tính năng (theo bảng "Core features" của README)

| Tính năng trong README | Cảnh |
|---|---|
| Story and DM modes | 2.1–2.3, 2.6–2.8 |
| Player stays the author | 2.2, 3.2 |
| Six-emotion relationship | 2.4, 2.8 |
| Memory | 2.4, 2.8 |
| Lorebook | 1.7, 2.4 |
| Character Studio | 1.6–1.7, 3.6 |
| Explore and profile | 1.4–1.5 |
| On-demand helpers | 3.3 |
| Accounts | 3.6 |
| Fast on modest hardware | Không quay riêng (tua nhanh vẫn ghi rõ) |
| No technical noise | 3.7 (mục "Nâng cao"), cả video không có chữ kỹ thuật |
| Safety and privacy | 3.7 |
| Usage analytics | 3.7 |
| Persona, thiết lập story, theme | 1.8, 2.5, 3.4 |

## 4. Quay tự động

Không quay tay. `demo-video/recorder/record.mjs` tự dựng dữ liệu demo, tự bấm trong app và quay từng cảnh:

```bash
node demo-video/recorder/record.mjs --fake        # chạy thử với LLM giả của bot (không gọi Ollama)
node demo-video/recorder/record.mjs               # model thật (gemma4:12b) — chỉ khi chủ dự án không dùng app
node demo-video/recorder/record.mjs 2.2 2.4       # quay lại vài cảnh (dữ liệu demo được giữ)
```

- **Máy:** backend thật (`recorder/demo-server.py`) cổng 8068 + Vite 8069, DB riêng `reports/demo-video/`
  (tài khoản trung tính `@lyris_demo`). Không đụng `data/`, không đụng 8000/5173. Chrome headless 390 × 844, độ nét ×3.
- **Dữ liệu demo** (tạo qua API, không quay): nhập 4 nhân vật trong `worlds/` kèm `world.md`; cài nhân vật mẫu **Hạ Vy**
  (chủ tiệm sách cũ ở Đà Lạt, vibe Chữa lành / Dịu dàng — nhân vật dịu dàng của phần 2); persona Ôn Nhiên, Lâm An,
  Tiểu Mãn; **story A** (Lục Bắc Uyên + Ôn Nhiên, lời mở đầu "Đêm giao thừa", chơi sẵn 4 lượt); **story B**
  (Hạ Vy + Lâm An, chơi sẵn 3 lượt); 3 story phụ cho danh sách Tương tác. Story C (đêm đính hôn) được tạo ngay trong
  cảnh 1.8.
- **Khớp nhịp:** lúc quay, script đánh dấu mốc (chạm, gửi, chữ đầu tiên, trả lời xong…). Mỗi cảnh khai báo mốc nào rơi
  vào phách nào; giữa hai mốc thời gian được co giãn (`recorder/clip.mjs`). Đoạn chờ model bị nén ≥ 1,8 lần tự hiện
  chip "tua nhanh". Script cũng ghi vị trí phần tử (thẻ suy nghĩ, vạch cảm xúc…) để zoom / rọi sáng trúng chỗ.
- **Kết quả:** `demo-video/public/clips/<cảnh>.mp4` + `<cảnh>.fx.json`. Video dùng clip thật cho cảnh nào có clip,
  cảnh nào thiếu thì hiện màn giả lập.
- **Chỗ đổi so với kịch bản trên:** cảnh 2.6–2.8 dùng nhân vật mẫu Hạ Vy (không phải nhân vật tạo ở 1.6); cảnh 1.6
  tạo một thủ thư thư viện đêm; cảnh 3.2 dùng "Xoá từ đây" → Huỷ (ô Sửa của lượt AI hiện chữ thô); cảnh 3.6 bật
  Công khai cho Lục Bắc Uyên.

Cảnh 1.1–1.3, 3.8 và mọi chữ, khung, hiệu ứng làm bằng code (Remotion), không cần quay.

## 5. Dựng và xuất

```bash
cd demo-video
npm run studio     # xem và chỉnh trong trình duyệt
npm run render     # xuất out/lyris-demo.mp4 (1080p, 2:07)
```

`npm run clips` (tự chạy trước studio/render) quét `public/clips/` và ghi `src/clips.generated.ts`.
Chữ chú thích của cảnh có câu trả lời thật (2.3, 2.6) viết lại theo đúng câu model trả lời sau khi quay.
Xong thì đăng Drive và dán link vào mục "Demo video" của README (phần tiếng Anh và tiếng Việt).

## 6. Cài đặt

| Thứ | Trạng thái |
|---|---|
| Node 22, Chrome, Ollama + `gemma4:12b` | ✅ có sẵn |
| ffmpeg, aubio | ✅ đã cài (`brew install ffmpeg aubio`) |
| Nhạc | ✅ `demo-video/public/music/` (không đưa vào git) |
| Remotion 4 | ✅ trong `demo-video/` (`package.json` riêng, không đụng `frontend/`) |
