# Lục Bắc Uyên: cách dùng

Thư mục này có hai file chính:

- `card.json`: thẻ nhân vật (Character Card V2) để nhập vào Lyris.
- `world.md`: tài liệu thế giới, gồm nhân vật phụ, địa điểm, cốt truyện, móc sự kiện và các mục lore để dùng ở Phase 4. File này không tự đi vào prompt; khi cần, chép đoạn phù hợp vào ô bối cảnh của story.

## Nhập card

1. Mở Studio, bấm **Import**, chọn `card.json`.
2. Kiểm tra trong trình sửa: style profile là `trung_hien_dai`, giới tính nam, xưng hô `tôi` / `em`, có ba lời mở đầu (một chính, hai phụ).
3. Lưu card.

## Thiết lập persona và story

- **Persona:** tên là tên thân phận của bạn trong truyện (người ngoài sẽ gọi "Ôn tiểu thư" hoặc "Ôn thiếu gia", nên tên chỉ cần phần tên riêng, không cần họ Ôn). Giới tính tùy bạn. Mô tả gợi ý: "Người hiện đại xuyên vào tiểu thuyết 'Lục Tổng, Em Không Cần Anh Nữa', mang thân phận người nhà họ Ôn có hôn ước với Lục Bắc Uyên. Biết trước cốt truyện gốc." Có thể thêm tuổi (từ 18 trở lên), nghề cũ, tính cách của bạn.
- **Kiểu quan hệ:** ngôn tình (nam - nữ) nếu persona là nữ, đam mỹ nếu persona là nam; chọn "không lãng mạn" nếu muốn đi hướng đồng minh.
- **Ngôi kể:** ngôi thứ ba.
- **Đại từ dẫn truyện:** nhân vật đặt là **hắn** (mặc định của style là "anh", nhớ đổi). Người chơi: đại từ bạn muốn được gọi trong phần dẫn truyện ("cô", "anh", "cậu"...), hoặc để tên.
- **Thought:** inline (2-3 dòng rải giữa truyện).

## Chọn lời mở đầu

- **Lời mở đầu chính, đêm đính hôn:** bạn vừa tỉnh trong phòng nghỉ ở Lục trạch, mười phút trước lễ trao nhẫn. Hợp để chơi từ đầu.
- **Lời mở đầu phụ 1, sáng hôm sau:** hắn mang canh giải rượu lên, buổi sáng đầu tiên không có tin nhắn "Chào buổi sáng". Hợp nếu muốn bỏ qua lễ đính hôn, vào thẳng giai đoạn hắn bắt đầu để ý.
- **Lời mở đầu phụ 2, đêm giao thừa:** sáu tuần sau, hắn tự lái xe tới cổng Ôn viên đón bạn và chờ câu trả lời. Đây là cảnh "lần đầu nói không"; đồng ý hay từ chối là do bạn viết.

## Những chỗ bạn có thể tự chọn

- Tên và tuổi của persona, đời cũ ở thế giới thật (người dẫn truyện sẽ không tự bịa ra những chi tiết này).
- Bạn nhớ cốt truyện gốc kỹ tới đâu: các mốc chính đã ghi trong `world.md` (gặp nữ chính tối 17/3, hủy hôn tháng 11 năm sau, tai nạn ở đường núi Tây Sơn đêm tuyết đầu mùa).
- Có muốn đưa "hệ thống" hay nhiệm vụ kiểu game vào không: mặc định là không có.

## Rút gọn card

Card đã được rút gọn để khối nhân vật (khối B của prompt) còn khoảng 1.190 token, từ khoảng 1.680, vì với gemma4:12b khối nhân vật dài làm model quên luật (2 Thought rải ra, đóng `]`, không viết "bầu không khí", không bịa). Mọi chi tiết trong brief vẫn còn trong card ở dạng gọn; câu nói gốc của hắn nằm trong ví dụ lời thoại. Ba lời mở đầu được cắt xuống dưới 200 từ, giữ nguyên cảnh. Những chi tiết bị bỏ khỏi card (một ngày của hắn, thói quen, thích và ghét, chuyện năm 1979, quỹ Lan Giang, chiếc nhẫn, hồ sơ nhân vật phụ, địa điểm, cốt truyện) vẫn còn đầy đủ trong `world.md`. Khi cần, chép đoạn phù hợp vào ô bối cảnh của story, hoặc dùng làm lore ở Phase 4.
