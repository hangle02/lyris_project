# Nguyên tắc thiết kế

Nguồn: [DESIGN.md](../raw/DESIGN.md) (chủ dự án viết), [docs/design-impl.md](../../docs/design-impl.md) §10-11 (luật "taste" khi làm), và góp ý của chủ dự án trong `raw/`. Màu, chữ, thành phần cụ thể: [style.md](style.md).

Chỗ nào xung đột: **lời chủ dự án mới nhất thắng**, rồi tới DESIGN.md, rồi tới luật taste. Mỗi chỗ lệch DESIGN.md phải ghi lại (xem cuối [style.md](style.md)).

## 1. Cảm giác

- Lãng mạn, chữa lành, gần gũi nhưng bí ẩn. Như đọc tiểu thuyết dưới ánh nến (tối) hoặc viết thư tình trên giấy lụa buổi sáng (sáng).
- Không lạnh kiểu sci-fi, không khô kiểu chatbot công cụ.
- Không dùng đen thuần `#000` hay trắng thuần `#FFF` cho nền và chữ đọc dài. Mọi màu ngả ấm.

## 2. Điện thoại trước

- Thiết kế ở **390px trước**, rồi mới 768px và 1280px. Kiểm tra ở cả hai theme.
- Một ngón cái dùng được: thanh tab nổi ở dưới, vùng chạm tối thiểu 44px.
- Tôn trọng vùng an toàn của iPhone (Dynamic Island, thanh Home).
- Không cuộn ngang. Chữ gợi ý phải vừa một dòng trên điện thoại.

## 3. Giấu phần kỹ thuật

Chủ dự án không muốn thấy chữ kỹ thuật ([raw](../raw/2026-11-13-o-chat-goi-y-va-an-ky-thuat.md), [raw](../raw/2026-11-12-story-an-may-tai-khoan-persona.md), [quyết định](../decisions/an-chu-ky-thuat.md)).

- Không có chữ "model", "Ollama", "prompt", "token", "credits", "lore", "cookie", "phiên", "HTTP" trên màn hình thường.
- Không pill trạng thái máy ở header. Thông tin máy, chọn model, công cụ nâng cao nằm trong sheet Tài khoản → "Nâng cao".
- Đang chờ nhân vật trả lời: **ba chấm nhảy**, không chữ "đang suy nghĩ", không đồng hồ.
- Lỗi: một câu dễ hiểu. Chữ gốc để trong "Chi tiết".
- Nguồn ảnh không hiện trên thẻ; gom vào "Giới thiệu & bản quyền ảnh".
- Thuật ngữ thay thế: "Thế giới", "Mục thế giới", "Từ khoá gợi nhớ", "Ai biết điều này", "đăng nhập", "thiết bị".

## 4. Lời thoại và ô nhập

- **Thẻ thoại không có dấu ngoặc.** Khung đã cho biết đó là lời nói ([raw](../raw/2026-11-13-loi-thoai-va-dm-story.md), [quyết định](../decisions/the-thoai-khong-ngoac.md)).
- Người chơi viết `"…"` là lời thoại của mình, thành ô thoại dù ngắn hay dài. Mỗi cặp ngoặc một ô.
- `*"…"*` là trích dẫn hoặc lời của người khác. Nằm trong dòng dẫn truyện, chữ đứng, giữ ngoặc ([quyết định](../decisions/trich-dan-trong-dau-sao.md)).
- Placeholder ngắn: Story `Nhập lời thoại vào "…"`, DM `Nhắn tin…`. Câu đầy đủ để trong `aria-label` ([quyết định](../decisions/placeholder-ngan.md)).
- Gợi ý trả lời chỉ hiện khi người chơi bấm "Nhận gợi ý".

## 5. Lưới và thẻ

- **Ô nhân vật luôn bằng nhau** ở mọi độ rộng và mọi mục. Số cột cố định: 2 (điện thoại), 3 (máy tính bảng), 5 (máy tính). Hàng cuối thiếu thì để trống, không kéo giãn ô ([raw](../raw/2026-11-14-kham-pha-trung-nhan-vat-va-luoi.md), [quyết định](../decisions/luoi-o-bang-nhau.md)).
- Các ô cùng hàng cao bằng nhau.
- Thẻ ở Khám phá nhỏ, vừa đủ đọc thông tin, để không phải cuộn nhiều ([raw](../raw/2026-11-13-kham-pha-va-ho-so-nhan-vat.md), [quyết định](../decisions/the-kham-pha-nho-lai.md)).
- Một nhân vật chỉ hiện một lần trong mỗi lưới. Dải "Nhân vật hot" là danh sách xếp hạng, không phải lưới, nên nhân vật trên dải vẫn có ô trong lưới (2026-11-14: khung nổi bật đã bỏ, [quyết định](../decisions/kham-pha-tim-kiem-bo-khung-noi-bat.md)).
- Bấm thẻ nhân vật mở **hồ sơ chỉ xem**, không mở form sửa, không tạo story ngay ([quyết định](../decisions/ho-so-nhan-vat-chi-doc.md)).

## 6. Chữ trên giao diện

- Tiếng Việt là mặc định. Câu ngắn, cụ thể, giọng thân.
- Dùng "story", không dùng "câu chuyện". Ngoại lệ duy nhất: nút **"Bước vào câu chuyện"** (test `copyWords.test.ts` quét chữ này; [quyết định](../decisions/thuat-ngu-story.md)).
- Viết hoa kiểu câu ("Tương tác", "Story", "DM"), không viết hoa cả chữ, không giãn chữ.
- Không emoji trong điều hướng, nhãn, trạng thái rỗng. Emoji do người chơi hoặc nhân vật viết thì giữ.
- Người chơi trong nội dung nhân vật là `{{user}}`; trên hồ sơ hiện thành "bạn".

## 7. Dùng tiết chế (luật taste, design-impl §10, [quyết định](../decisions/tiet-che-thiet-ke.md))

- **Kính mờ chỉ 3 chỗ:** header hub, thanh tab nổi, header chat.
- **Gradient chỉ 4 chỗ:** quả cầu tab giữa, nút gửi, bong bóng người chơi, chữ L của wordmark.
- **Bóng chỉ cho thứ nổi:** thanh tab, quả cầu, modal, ngăn kéo, menu. Card nằm yên tách bằng bước tông màu hoặc viền 1px, không cả hai.
- **Ba font, mỗi font một việc.** Không font thứ tư, không chữ mono.
- **Một họ bo góc:** card 20px, control 14px, còn lại tròn hẳn.
- **Một nút primary mỗi màn hình.** Còn lại là secondary hoặc ghost.
- Thang chữ 12 / 13 / 14 / 15 / 16 / 20 / 24. Tiêu đề màn hình 20-24px là `h1`. Không chữ nào từ 48px trở lên ngoài wordmark.
- Chữ mang nội dung đạt tương phản ít nhất 4.5:1 ở cả hai theme.

## 8. Những thứ cấm

- Icon trong ô vuông hoặc tròn tô màu lặp lại; card có icon trên đầu.
- Nhãn nhỏ trên tiêu đề, đánh số 01/02/03, đường kẻ trang trí, blob, ngôi sao rải rác (ngôi sao chỉ ở logo và chỉ báo đang chờ).
- Hover nâng card, bounce, hiệu ứng khi tải trang, shimmer.
- Dữ liệu giả: lorem, "User 1", số phô trương. Mọi con số lấy từ API.
- Ảnh người thật làm chân dung nhân vật mẫu. Hình vẽ trang trí thay cho ảnh.

## 9. Trạng thái

- Rỗng: giữ khung, một câu, một hành động đầu tiên.
- Đang tải: khung xương đúng kích thước thật, không shimmer.
- Lỗi: nằm ngay trong khối bị lỗi, có "Thử lại".
- Số 0 in là 0; thiếu dữ liệu là gạch ngang xám.

## 10. Chuyển động

Chỉ là phản hồi (nhấn, focus, mở ngăn kéo) và ba vi tương tác của DESIGN.md: đổi theme (500ms), mở thẻ suy nghĩ (300ms), chỉ báo đang chờ. Luôn có `prefers-reduced-motion`.

## 11. Kiểm tra trước khi xong

- `npm test`, `typecheck`, `build`.
- `node ~/.claude/skills/design-taste-frontend/scripts/lint.mjs --app frontend/src`: 0 FAIL.
- `inspect.mjs --app` ở 1440 / 768 / 390, hai theme (`?theme=light`, `?theme=dark`), cho phép `gradient,gradient-text` vì DESIGN.md chỉ định.
- Đọc ảnh chụp ở 390px, cả hai theme. Không lỗi console, không cuộn ngang.
