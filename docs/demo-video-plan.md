# Video demo Lyris trên nền nhạc "Gasoline": kế hoạch và kịch bản (bản 3, chờ duyệt)

> Không lời đọc. **Tính năng là chính, câu chuyện là sợi chỉ nối.** Video đi qua các tính năng trong README theo
> đúng hành trình của người dùng: *chọn hoặc tạo nhân vật → chọn mình là ai → nhân vật phản ứng thật (kịch tính lẫn
> dịu dàng) → bạn điều chỉnh mọi thứ → chia sẻ, an toàn, riêng tư.* Bản có lời đọc vẫn ở [demo-script.md](demo-script.md).

## 1. Nhạc (đã chốt)

`demo-video/public/music/gasoline-draft-loop.wav`, tách từ `~/Downloads/example.MP4`, lặp ba lần theo ô nhịp, dài
**2:02**. Khoảng 98 BPM: mỗi phách 0,61 giây, mỗi câu nhạc (8 phách) 4,88 giây. Ba lượt nhạc là ba phần của video;
chỗ nối ở 0:42,7 và 1:21,7.

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
| 1.1 | 0:00–0:03,7 | Một cuốn sách khép. 5 tiếng dồn của dạo đầu = 5 trang lật | — | |
| 1.2 | 0:03,7–0:08,6 | Trang sách mở, chữ tiểu thuyết in đều. Người đọc là một bóng mờ **đứng bên ngoài khung trang**, như nhìn qua lớp kính | Bình thường, bạn đứng ngoài câu chuyện. / **Chỉ đọc.** · *Usually, you stand outside the story. You just read.* | |
| 1.3 | 0:08,6–0:13,5 | Chữ trên trang **biến thành màn Story của Lyris**: đoạn dẫn truyện nghiêng, thẻ thoại, thẻ suy nghĩ mờ. Đúng phách mạnh, một **bong bóng của người chơi** trượt vào từ bên phải: bạn đã ở trong truyện. Logo + wordmark Lyris hiện | Với Lyris, / **bạn là một phần của câu chuyện.** · *With Lyris, you become part of the story.* | |
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
| 2.3 | 0:52,5–0:57,4 | Câu trả lời thật: dẫn truyện, thẻ thoại (tách lớp), thẻ suy nghĩ hết mờ | *(viết sau khi quay, ví dụ)* Hắn ghen, / **nhưng không chịu nhận.** · *He's jealous, and won't admit it.* | Story |
| 2.4 | 0:57,4–1:02,3 | Ngăn **trái tim**: phóng vào vạch, **Nhung nhớ / Chiếm hữu ↑** (đỏ), **Tin cậy ↓**. Cuộn xuống, rọi sáng **"Thế giới đã mở khoá"**: *Phó Cảnh Hành trong nguyên tác* | Cảm xúc lên và xuống / **theo từng việc bạn làm.** · *Feelings rise and fall with everything you do.* | 6 cảm xúc, ký ức, sổ thế giới |
| 2.5 | 1:02,3–1:07,1 | Nút **Mặt trời**: app và nền video chuyển sang **Rosewater Parchment**, như bật đèn sáng | Không chỉ giông bão. / **Có cả những nơi để nghỉ chân.** · *Not just storms. Places to rest, too.* | Theme sáng/tối |
| 2.6 | 1:07,1–1:12,0 | Story với **Hạ Vy** (nhân vật vừa tạo ở 1.6), persona Lâm An. Gác xép, trà gừng, mưa. Thẻ suy nghĩ dịu dàng hết mờ | *(viết sau khi quay, ví dụ)* Có người chỉ mong / **bạn được ngủ ngon.** · *Someone just hopes you sleep well tonight.* | Story, nhân vật tự tạo |
| 2.7 | 1:12,0–1:16,9 | Công tắc **Story / DM** → DM: Lâm An nhắn `Mai mình mang bánh hạt dẻ qua tiệm nhé.`; Hạ Vy nhắn lại, chân tin "Đã xem". Tách lớp bong bóng | Nhắn tin cũng là / **một phần của câu chuyện.** · *Texting is part of the same story.* | DM, chung dòng thời gian |
| 2.8 | 1:16,9–1:21,7 | Về **Story**: `*Chiều hôm sau, tôi đẩy cửa tiệm sách.*` → Hạ Vy nhắc đúng bánh hạt dẻ (phóng vào, gạch chân vàng). Ngăn trái tim: **Thương mến ↑** | Hẹn qua tin nhắn. / **Cô ấy vẫn nhớ.** · *A promise by text. She still remembers.* | Trí nhớ, cảm xúc |

### Phần 3 · Làm chủ (1:21,7–2:02,4)

| # | Thời điểm | Hình | Chữ | Tính năng |
|---|---|---|---|---|
| 3.1 | 1:21,7–1:26,6 | Về theme tối. Dưới một câu trả lời: **"Tạo lại câu trả lời"** → bản mới chạy; lật phiên bản 1 ⇄ 2 ⇄ 3 theo phách (phóng vào số phiên bản); bấm **Thích** | Chưa ưng? / **Viết lại, chọn bản bạn thích.** · *Not quite right? Rewrite it and keep the one you like.* | Tạo lại, phiên bản, thích/chê |
| 3.2 | 1:26,6–1:31,5 | Gõ chỉ đạo ẩn `((Hắn kể về người cha))` → chip chỉ đạo nhỏ trong lượt; câu trả lời đi theo hướng đó. Lướt nhanh **Sửa** và **Xoá từ đây** | Đạo diễn câu chuyện / **mà nhân vật không hề biết.** · *Direct the scene without the character knowing.* | Chỉ đạo ẩn, sửa, xoá |
| 3.3 | 1:31,5–1:36,4 | Nút **"+"** → **Nhận gợi ý** → ba thẻ gợi ý (rọi sáng), chạm một thẻ. Rồi **"+" → Sự kiện**: dòng thời gian các mốc của story | Bí ý tưởng? Xin gợi ý. / **Nhìn lại cả hành trình.** · *Stuck? Ask for ideas. Look back on the whole journey.* | Menu "+", gợi ý, sự kiện |
| 3.4 | 1:36,4–1:41,3 | **Thiết lập story**: rọi sáng công tắc **"Đọc suy nghĩ của nhân vật"** và **"Luôn hiện suy nghĩ"**, đổi văn phong và xưng hô | Mỗi câu chuyện / **chỉnh theo cách của bạn.** · *Tune every story your way.* | Thiết lập story, công tắc suy nghĩ |
| 3.5 | 1:41,3–1:46,1 | Tab **Tương tác**: danh sách story với nhiều nhân vật và persona khác nhau (Lục Bắc Uyên, Hạ Vy, Cố Hoài Dã, Tần Dương…), huy hiệu Story/DM, ô tìm kiếm | Mỗi nhân vật, mỗi persona, / **một câu chuyện riêng.** · *Every character, every persona, its own story.* | Danh sách story |
| 3.6 | 1:46,1–1:51,0 | Studio: bật **Công khai** cho Hạ Vy. Tài khoản → **Tạo mã mời** → cửa sổ thứ hai: đăng ký, đánh dấu đồng ý Điều khoản | Mời bạn bè cùng chơi. / **Story của ai người nấy giữ.** · *Invite friends. Everyone's stories stay private.* | Nhân vật công khai, mã mời, nhiều tài khoản |
| 3.7 | 1:51,0–1:55,9 | Dựng nhanh, mỗi cảnh 2 phách: nút **Báo cáo** dưới câu trả lời · **Tải dữ liệu của tôi** / **Xoá tài khoản** · tab **Số liệu** của chủ máy · mục **Nâng cao** gập sẵn | An toàn · Riêng tư · / **Chạy trên máy của bạn.** · *Safe. Private. Runs on your own machine.* | An toàn, quyền riêng tư, số liệu, ẩn chữ kỹ thuật |
| 3.8 | 1:55,9–2:02,4 | Khung điện thoại lùi ra; màn Story mờ dần thành **trang sách** của cảnh 1.2, nhưng lần này có bong bóng của người chơi trên trang. Logo + wordmark, nhạc fade | Đừng chỉ đọc câu chuyện. / **Bước vào nó.** · *Don't just read the story. Step into it.* · **Lyris** · github.com/… | |

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

## 4. Chuẩn bị và danh sách clip

**Chuẩn bị** (DB demo riêng theo [demo-script.md §1–2](demo-script.md), không dùng `data/`; làm nóng model trước khi quay):
- Nhập Lục Bắc Uyên (`worlds/luc-bac-uyen/card.json` + `world.md`), có sẵn Cố Hoài Dã, Tần Dương, Yến Hoành Sinh.
- Tạo Hạ Vy bằng AI viết nháp (chính là clip C04), thêm ảnh đại diện.
- Ba persona: Ôn Nhiên, Lâm An, Tiểu Mãn.
- **Story A**: Lục Bắc Uyên + Ôn Nhiên, chơi sẵn 8–10 lượt, chưa nhắc Phó Cảnh Hành.
- **Story B**: Hạ Vy + Lâm An, chơi sẵn 4–5 lượt dịu dàng, chưa nhắc bánh hạt dẻ.
- Vài story ngắn với Cố Hoài Dã, Tần Dương để danh sách Tương tác trông có người dùng thật.

Chrome, DevTools chế độ thiết bị **390 × 844**, quay 60 fps bằng OBS, mỗi clip một file, thừa đầu và cuối 2 giây.
Cảnh có câu trả lời của model nên quay 2–3 lần rồi chọn lần đẹp nhất.

| Clip | Cảnh | Theme | Nội dung |
|---|---|---|---|
| C01 | 1.4 | tối | Khám phá: chạm chip Chữa lành → Tình đầu → Bí ẩn |
| C02 | 1.5 | tối | Chạm Lục Bắc Uyên → hồ sơ, cuộn chậm |
| C03 | 1.7 | tối | Studio: sửa Lục Bắc Uyên, cuộn tới Sổ thế giới, mở một mục có nhãn "ai biết"; nút nhập/xuất |
| C04 | 1.6 | tối | Studio → AI viết nháp với dòng ý tưởng của Hạ Vy → form tự điền → tải ảnh → lưu |
| C05 | 1.8 | tối | Trang persona (3 thẻ) → hồ sơ Hạ Vy → sheet Bước vào câu chuyện: chọn persona, kiểu quan hệ, xưng hô → bấm nút |
| C06 | 2.1 | tối | Story mới với Lục Bắc Uyên: lời mở đầu hiện hết → chạm thẻ suy nghĩ |
| C07 | 2.2–2.3 | tối | Story A: gửi câu về Phó Cảnh Hành → câu trả lời → chạm thẻ suy nghĩ |
| C08 | 2.4 | tối | Ngăn trái tim story A sau lượt đó, cuộn tới "Thế giới đã mở khoá" (mở lại sau 15–20 giây nếu chưa cập nhật) |
| C09 | 2.5 | tối → sáng | Bấm nút Mặt trời ở header hub |
| C10 | 2.6 | sáng | Story B: một lượt dịu dàng → câu trả lời → chạm thẻ suy nghĩ |
| C11 | 2.7–2.8 | sáng | Story B: Story → DM, nhắn hẹn bánh hạt dẻ, nhận tin; về Story, gửi câu đẩy cửa tiệm sách, nhận câu trả lời; mở ngăn trái tim |
| C12 | 3.1 | tối | Tạo lại câu trả lời → lật phiên bản → Thích |
| C13 | 3.2 | tối | Gửi lượt có `((Hắn kể về người cha))` → câu trả lời; mở menu Sửa / Xoá từ đây rồi huỷ |
| C14 | 3.3 | tối | "+" → Nhận gợi ý → chạm thẻ; "+" → Sự kiện |
| C15 | 3.4 | tối | Thiết lập story: bật/tắt hai công tắc suy nghĩ, đổi văn phong |
| C16 | 3.5 | tối | Tab Tương tác, cuộn danh sách story, gõ thử vào ô tìm kiếm |
| C17 | 3.6 | tối | Bật Công khai cho Hạ Vy; Tạo mã mời; cửa sổ ẩn danh: đăng ký có ô đồng ý |
| C18 | 3.7 | tối | Nút Báo cáo dưới câu trả lời; Tải dữ liệu của tôi / Xoá tài khoản (không bấm xác nhận); tab Số liệu; mở "Nâng cao" |

Cảnh 1.1–1.3, 3.8 và mọi chữ, khung, hiệu ứng mình làm bằng code, không cần quay.

## 5. Cách dựng

Remotion trong thư mục riêng `demo-video/` (React, cùng font `@fontsource` và token màu của app; mọi lần cắt khớp vào
danh sách phách đã đo).

1. **Bạn duyệt kịch bản này.**
2. Mình cài Remotion, dựng phần mở đầu (1.1–1.3), outro (3.8), chữ, nhãn, khung điện thoại, rồi render một
   **animatic** 2:02: chỗ nào cần clip app thì khung giữ chỗ ghi tên clip. Bạn xem nhịp trước khi quay.
3. Bạn quay 18 clip, chép vào `demo-video/public/clips/` (C01.mov … C18.mov).
4. Mình ghép clip, thêm phóng to / rọi sáng / tách lớp, viết chữ theo câu trả lời thật, render 1080p. Bạn góp ý, mình sửa.
5. Bạn đăng Drive; mình cập nhật link ở mục "Demo video" của README (phần tiếng Anh và tiếng Việt).

## 6. Cài đặt

| Thứ | Trạng thái |
|---|---|
| Node 22, Chrome, OBS, Ollama + `gemma4:12b` | ✅ có sẵn |
| ffmpeg, aubio | ✅ đã cài |
| Nhạc | ✅ `demo-video/public/music/` (không đưa vào git) |
| Remotion | ⏳ cài khi bạn duyệt kịch bản, trong `demo-video/` (`package.json` riêng, không đụng `frontend/`) |
