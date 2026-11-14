# Cố Hoài Dã (顾淮野)

Thanh mai trúc mã, vườn trường Trung Quốc hiện đại. Hắn tán tỉnh cả thế giới, riêng với {{user}} thì không dám nói một câu thật lòng. Năm học cuối ở Đại học Minh Châu: mùa giải bơi, áp lực kế thừa của Cố gia, và một bí mật giấu mười mấy năm.

Trong thư mục:

- `card.json`: Character Card V2, import thẳng vào Lyris Studio.
- `world.md`: thế giới, nhân vật phụ, địa điểm, cốt truyện, móc sự kiện và các mục lore (để dành cho Phase 4, chưa import được).

## Import card

1. Mở Studio, bấm **Import**, chọn `card.json`.
2. Hộp nháp hiện ra: kiểm tra rồi lưu. Card đã điền sẵn style profile `trung_hien_dai`, xưng hô "tôi"/"cậu" và hai biệt danh "tiểu tổ tông", "Đậu Đinh". Không cần sửa gì.
3. Tùy chọn: gắn ảnh đại diện cho card.

## Persona

- Giới tính: tùy bạn. Mọi chữ trong card đều trung tính với {{user}}.
- Mô tả nên có: chuyên ngành, tính cách, nhà {{user}} ở đâu trong khu Tây Viên (hàng xóm cùng khu, hay dãy nhà cũ phía sau đồi), và {{user}} đang nghĩ gì về hắn. Card không tự gán gia cảnh giàu nghèo cho {{user}}.
- {{user}} là người trưởng thành, sinh viên năm tư, cùng tuổi hoặc xấp xỉ tuổi hắn.

## Thiết lập khi tạo story

| Mục | Nên chọn |
|---|---|
| Chế độ mở đầu | Story |
| Kiểu quan hệ | Nam - nữ nếu persona là nữ, Nam - nam (đam mỹ) nếu persona là nam, hoặc Không lãng mạn |
| Ngôi kể | Ngôi thứ ba (cả ba lời mở đầu đều viết ngôi thứ ba) |
| Đại từ dẫn truyện, ô của Cố Hoài Dã | **hắn** (app gợi ý "anh", hãy sửa lại) |
| Đại từ dẫn truyện, ô của persona | "cô", "anh" hoặc tên persona. Đừng dùng "cậu" hay "tôi", vì đó là xưng hô của hắn trong lời thoại |
| Suy nghĩ của nhân vật | Lồng trong truyện |

Với "Không lãng mạn": tình cảm của hắn vẫn có trong card, narrator sẽ đưa truyện về hướng tình bạn (xem kết "Tình bạn" trong `world.md`).

## Chọn lời mở đầu

| Lời mở đầu | Cảnh | Hợp khi |
|---|---|---|
| Chính | Một giờ sáng, hắn đi tiệc về, mang hoành thánh "tiện đường mua", hỏi {{user}} đang nhắn tin với ai | Muốn bắt đầu từ nhịp sống chung, ghen ngầm nhẹ |
| Khác 1 | Hồ bơi Đông Hồ, {{user}} trên khán đài, ngồi cạnh là học trưởng Lục Tri Hành | Muốn vào thẳng chuyện ghen và mùa giải |
| Khác 2 | Ba giờ sáng, hắn gõ cửa rủ ra biển sau cuộc gọi với ba | Muốn đi vào mặt yếu đuối và áp lực kế thừa |

Ô **Bối cảnh** điền sẵn "đầu tháng Chín". Nếu chọn Khác 1, sửa thành "tháng Mười, trước vòng loại khu vực". Nếu chọn Khác 2, có thể thêm "ngay sau bữa tối Chủ nhật ba hắn ra tối hậu thư".

## Lựa chọn "Lần thứ hai" (tùy chọn)

{{user}} đã sống qua năm học này một lần: năm đó hắn bỏ bơi, sang London, và {{user}} chỉ biết hắn thích mình khi tìm thấy lá thư cũ bốn năm sau. Card không có lời mở đầu riêng cho lựa chọn này. Muốn chơi:

1. Ghi vào mô tả persona: "{{user}} đã sống qua năm tư một lần và nhớ hết; Cố Hoài Dã không biết."
2. Chọn lời mở đầu Chính (hoặc "Không có" rồi tự viết cảnh mở), và sửa Bối cảnh thành "sáng ngày khai giảng năm tư, {{user}} vừa tỉnh dậy với trí nhớ của một năm đã qua".

Chi tiết những gì đã xảy ra năm ấy nằm ở mục lore "Năm đã sống qua" trong `world.md`.

## Mẹo chơi

- Đừng mong hắn tỏ tình sớm. Mỗi câu thật lòng sẽ bị chính hắn chữa thành câu đùa; khoảnh khắc hắn không đùa nữa mới là bước ngoặt.
- Muốn đẩy truyện, dùng một móc sự kiện trong `world.md` qua chỉ đạo `((...))`, ví dụ `((Hạ Trì bày trò thật hay thách ở Lam Hải))`.

## Rút gọn card

Card đã được rút gọn để khối nhân vật trong prompt (khối B) còn khoảng 1.200 token thay vì gần 2.000; với model nhỏ như gemma4:12b, khối nhân vật dài làm model quên luật (2 Thought rải rác, đóng `]`, không tả "bầu không khí", không bịa chi tiết). Mọi điều đã định về Cố Hoài Dã vẫn còn trong card, viết gọn lại. Những chi tiết bị đưa ra khỏi card vẫn nằm nguyên trong `world.md` (sẽ thành lore ở Phase 4): tên khách sạn Vân Đỉnh, ngành Quản trị kinh doanh, kỷ lục 200 mét, các nguyên tắc riêng, lựa chọn du học năm mười tám tuổi, cách hắn xưng hô với ba mẹ, thầy Tần và cách người khác gọi hắn ("Dã ca", "Cố thiếu", "A Dã"...), hồ sơ nhân vật phụ, địa điểm và cốt truyện. Muốn nhắc model một chi tiết trong đó khi chơi, dùng chỉ đạo `((...))`.
