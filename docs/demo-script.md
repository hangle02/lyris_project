# Kịch bản video demo (2 phút 50 giây)

> **English summary.** A 2:50 screen recording of Lyris's core flow on a phone-sized screen: Explore → character
> profile → "Bước vào câu chuyện" → persona → story turns (narration, dialogue cards, a blurred thought tapped
> open) → heart drawer with emotions that moved and a world entry unlocked → switch to DM and back, with the
> character remembering the text → regenerate and flip versions → reply suggestions → 15 s on invites and
> sign-up consent → 15 s on the owner's metrics and reports. Vietnamese voice-over with English subtitles (both
> columns below). Record on a warmed-up model with a story prepared in advance.

Yêu cầu của đề: video 2–3 phút về luồng chính, có link trong README. Bản này dài **2:50**. Mỗi dòng của bảng là một
cảnh: thời điểm, thao tác trên màn hình, lời đọc (tiếng Việt) và phụ đề tiếng Anh (dùng làm phụ đề, hoặc đọc bản
tiếng Anh nếu nhóm muốn).

## 1. Chuẩn bị (trước ngày quay)

1. **Máy và app.** Chạy bản build như production trên một DB riêng cho demo, không dùng DB thật:

   ```bash
   LYRIS_DB_PATH=$HOME/lyris-demo/lyris.db LYRIS_AVATARS_DIR=$HOME/lyris-demo/avatars bash scripts/serve.sh
   ```

   Đặt mật khẩu chủ máy bằng mã in ra Terminal. Tài khoản chủ máy dùng tên trung tính (ví dụ "Lyris Demo",
   `@lyris_demo`), **không dùng tên, handle hay email thật của ai**.
2. **Nhân vật có thế giới.** Studio → nhập `worlds/luc-bac-uyen/card.json`, rồi trong phần "Thế giới" nhập
   `worlds/luc-bac-uyen/world.md`. Bật "Công khai" nếu muốn nhân vật hiện ở cả hai tài khoản.
3. **Persona.** Tạo persona "Ôn Nhiên" (nữ), mô tả: "Người hiện đại xuyên vào tiểu thuyết, biết trước cốt truyện gốc."
4. **Story chuẩn bị sẵn** (gọi là *story A*): bắt đầu story với Lục Bắc Uyên bằng persona trên, chơi 8–10 lượt để có
   ký ức, cảm xúc đã dịch chuyển và một cảnh rõ ràng. Tránh nhắc tới "Phó Cảnh Hành" và "tiệm hoa Thu Đường" (để dành
   mở khoá thế giới khi quay).
5. **Tài khoản thứ hai** trên điện thoại hoặc cửa sổ ẩn danh (dùng ở cảnh mời bạn), để trống.
6. **Tập trước một lần** toàn bộ kịch bản: model 12B không trả lời giống nhau mỗi lần; chọn câu nhập nào cho kết quả
   đẹp thì giữ câu đó.

## 2. Ngay trước khi quay

- **Làm nóng model** 1–2 phút trước: gửi một lượt trong story A rồi xoá ("Xoá từ đây"). Model rời bộ nhớ sau 30 phút
  không dùng; lượt đầu khi nguội mất vài chục giây.
- Không chạy việc nặng khác trên máy (trình duyệt nhiều tab, train, build).
- Màn hình: Chrome DevTools → chế độ thiết bị **390 × 844**, zoom 100 %, theme tối; hoặc quay điện thoại thật qua phản
  chiếu màn hình. Tắt thông báo, ẩn thanh dấu trang.
- Mở sẵn các tab: Khám phá (tài khoản chủ máy), story A, trang đăng ký (tài khoản thứ hai).

## 3. Kịch bản

| Thời điểm | Màn hình và thao tác | Lời đọc (tiếng Việt) | Phụ đề (English) |
|---|---|---|---|
| 0:00–0:10 | Banner Lyris (logo trái tim từ hai trang sách), rồi mở app: tab **Tương tác**. | "Đây là Lyris, nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại." | "This is Lyris, where souls from the pages of a book step out to warm the real world." |
| 0:10–0:22 | Tab **Khám phá**: khung nhân vật nổi bật, chạm chip vibe "Tình đầu", rồi bỏ lọc; cuộn lưới ô bằng nhau. | "Bạn chọn một nhân vật theo cảm xúc mình muốn: chữa lành, tình đầu, bí ẩn..." | "Pick a character by the feeling you want: healing, first love, mystery..." |
| 0:22–0:35 | Chạm **Lục Bắc Uyên** → hồ sơ chỉ đọc (ảnh, giới thiệu, lời nói đặc trưng). Bấm **"Bước vào câu chuyện"**. | "Mỗi nhân vật có hồ sơ và cả một thế giới riêng: nhân vật phụ, nơi chốn, bí mật." | "Every character has a profile and a whole world: side characters, places, secrets." |
| 0:35–0:45 | Sheet chọn persona: chọn **Ôn Nhiên**, chỉ vào dòng nhỏ "Nhân vật do AI đóng vai, có thể sai...". Bấm **"Bước vào câu chuyện"**: lời mở đầu hiện ra. | "Bạn chọn mình sẽ là ai. Lyris luôn nói rõ: nhân vật do AI đóng vai." | "You choose who you are. Lyris always says it plainly: the character is played by AI." |
| 0:45–0:50 | Chuyển sang **story A** (đã chơi sẵn). | "Đây là một story đã đi được một đoạn." | "Here is a story that is already under way." |
| 0:50–1:10 | Gõ: `"Tối qua anh đứng nói chuyện với Phó Cảnh Hành rất lâu." *Tôi đặt ly trà xuống, không nhìn anh.*` → gửi. Ba chấm nhảy, chữ chạy. Chỉ vào: dẫn truyện chữ nghiêng, **ô thoại**, thẻ suy nghĩ mờ **"Chạm để lắng nghe"** → chạm để đọc. | "Bạn viết lời thoại trong ngoặc kép, hành động trong dấu sao. AI chỉ viết cho nhân vật, không bao giờ nói thay bạn. Còn đây là suy nghĩ thật của hắn: chạm để nghe." | "Speech goes in quotes, actions between asterisks. The AI only writes the character, never you. And this is what he really thinks: tap to listen." |
| 1:10–1:30 | Bấm **trái tim** trên header → ngăn "Cảm xúc & ký ức": thanh **Nhung nhớ / Chiếm hữu** tăng, **Tin cậy** giảm; ký ức mới; cuộn xuống **"Thế giới đã mở khoá"**: mục về Phó Cảnh Hành. *(Nếu cảm xúc chưa đổi, đợi 15–20 giây rồi mở lại; cắt đoạn chờ.)* | "Nhắc tới người khác, hắn ghen: chiếm hữu tăng, tin cậy giảm. Cảm xúc lên và xuống theo việc bạn làm. Và một mảnh thế giới vừa mở khoá." | "Mention another man and he gets jealous: possessiveness up, trust down. Feelings rise and fall with what you do. And a piece of the world just unlocked." |
| 1:30–1:50 | Công tắc **Story / DM** → DM. Gõ: `Mai 7 giờ tối gặp em ở tiệm hoa Thu Đường nhé.` → trả lời dạng tin nhắn. Chuyển lại **Story**, gõ `*Bảy giờ tối hôm sau, tôi đẩy cửa tiệm hoa.*` → nhân vật nhắc đúng cuộc hẹn. | "Nhắn tin riêng cũng là một phần của story. Hẹn qua tin nhắn, quay lại story, hắn vẫn nhớ." | "Texting is part of the same story. Make a plan by text, go back to the story, and he still remembers." |
| 1:50–2:05 | Dưới câu trả lời: **"Tạo lại câu trả lời"** → bản mới chạy; bấm phiên bản trước / sau để lật; bấm **Thích**. | "Chưa ưng thì tạo lại, rồi lật qua lại giữa các phiên bản." | "Not quite right? Regenerate, then flip between versions." |
| 2:05–2:20 | Nút **"+"** ở ô nhập → **"Nhận gợi ý"** → ba thẻ gợi ý; chạm một thẻ để gửi. | "Bí ý tưởng? Bấm gợi ý, Lyris đưa ba hướng đi tiếp." | "Stuck? Ask for suggestions and Lyris offers three ways forward." |
| 2:20–2:35 | Avatar → **Tài khoản** → **"Quản lý tài khoản"** → **"Tạo mã mời"**. Cửa sổ thứ hai: trang đăng ký, dán mã, đánh dấu ô **đồng ý Điều khoản và Chính sách**, tạo tài khoản. | "Mời bạn bè bằng mã mời. Mỗi người có story riêng tư của mình, và đồng ý điều khoản trước khi bắt đầu." | "Invite friends with a code. Everyone gets private stories and accepts the terms before starting." |
| 2:35–2:45 | Quay lại tài khoản chủ máy: tab **"Số liệu"** (ô hôm nay / 7 ngày / 30 ngày, phễu, quay lại D1/D7), lướt sang tab **"Báo cáo"**. | "Người vận hành xem số liệu sử dụng và báo cáo nội dung. Số liệu không bao giờ chứa chữ người dùng viết, và ai cũng tắt được." | "Operators see usage numbers and content reports. Analytics never contain anything users write, and anyone can opt out." |
| 2:45–2:50 | Banner Lyris + link repository. | "Lyris. Bước vào câu chuyện của bạn." | "Lyris. Step into your story." |

Tổng lời đọc khoảng 330 chữ tiếng Việt, đọc chậm vừa phải là vừa 2:50.

## 4. Ghi chú khi quay và dựng

- **Không bịa tốc độ.** Được cắt hoặc tua đoạn chờ (ba chấm, việc nền cập nhật cảm xúc), nhưng hiện chữ nhỏ "tua
  nhanh" / "fast-forward" ở góc khi tua, để người xem không hiểu nhầm tốc độ thật.
- **Câu trả lời của model thay đổi mỗi lần.** Nếu một lượt ra không đẹp (lệch vai, quá ngắn), dùng chính "Tạo lại câu
  trả lời" hoặc quay lại cảnh đó; đừng sửa chữ của AI bằng "Sửa" rồi quay như thể AI viết vậy.
- **Không lộ dữ liệu thật:** chỉ dùng DB demo; không quay Terminal có mã thiết lập; thu hồi mã mời đã quay xong (tab
  "Tài khoản" → mã mời → thu hồi).
- **Nội dung an toàn:** giữ cảnh ở mức tình cảm, ghen tuông, không có gì gợi dục; đúng với chính sách mặc định của Lyris.
- **Âm thanh:** thu lời đọc riêng (micro gần, phòng yên), ghép sau; nhạc nền nhỏ, không bản quyền.
- **Phụ đề:** xuất file `.srt` từ cột tiếng Anh (hoặc phụ đề tiếng Việt từ cột lời đọc), bật trong trình phát.
- **Đăng video:** YouTube (Không công khai) hoặc Google Drive (Bất kỳ ai có link đều xem được). Dán link vào mục
  "Demo video" trong README (đang là TODO) và nộp cùng repository.
