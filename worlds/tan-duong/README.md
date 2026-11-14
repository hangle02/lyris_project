# Tần Dương: hướng dẫn dùng

Thư mục gồm:
- `card.json`: card nhân vật (Character Card V2), import vào Lyris Studio.
- `world.md`: tài liệu thế giới đầy đủ (nhân vật phụ, địa điểm, cốt truyện, móc sự kiện, mục lore cho Phase 4). Đọc để biết cách dẫn truyện; app chưa tự đọc file này.

## Import card

1. Mở Studio, bấm **Import**, chọn `worlds/tan-duong/card.json`.
2. Card import không có cảnh báo. Phần "Ngoại hình / Hoàn cảnh / Mục tiêu / Bí mật / Cách nói" ở cuối mô tả được tự tách vào đúng ô, nên ô Mô tả chỉ còn ba câu.
3. Kiểm tra nhanh rồi lưu: style profile `trung_hien_dai`, giới tính nam, ngôn ngữ tiếng Việt, xưng hô `tôi` / `cậu`, không có biệt danh.

## Thiết lập câu chuyện

- **Persona:** giới tính nào cũng được, chỉ cần là người trưởng thành. Mọi lời mở đầu chỉ gọi người chơi là {{user}}. Ô mô tả persona có thể ghi ngành học hoặc nghề nghiệp nếu muốn.
- **Kiểu quan hệ:** chọn tùy ý. Nam-nam hoặc Nam-nữ nếu muốn chuyện tình chậm; Không lãng mạn nếu chỉ muốn tình bạn và mạch giật gân.
- **Ngôi kể:** ngôi thứ ba. Đại từ dẫn truyện cho nhân vật là "anh"; cho người chơi thì theo giới tính persona, hoặc để trống để chỉ dùng tên.
- **Chế độ:** Story để chơi trọn mạch truyện. DM hợp với những đoạn nhắn tin, nhất là khi Tần Dương nói chuyện dưới tên ZERO.
- **Suy nghĩ của nhân vật:** Thought lồng (mặc định). Cả ba lời mở đầu đều viết theo kiểu này.

## Chọn lời mở đầu

| Lựa chọn | Vai của {{user}} | Mở cảnh |
|---|---|---|
| Chính | Bạn cùng lớp năm tư, bị thầy Trịnh ghép cùng nhóm đồ án tốt nghiệp | Phòng 402 nhà A3 sau giờ học, anh mang đề cương sang và nói {{user}} "không cần làm gì" |
| Khác 1 | Hàng xóm mới ở căn 1702 chung cư Ngô Đồng, sinh viên hay đã đi làm đều được | Gần nửa đêm, anh ôm thùng hàng giao nhầm, đứng trước cửa căn 1702 |
| Khác 2 | Người ngồi ở tầng năm thư viện Hải Đại, điện thoại vừa bắt vào wifi giả của MIRAGE | GHOST báo động, anh buộc phải bước tới bảo {{user}} tắt wifi, laptop để lộ biểu tượng số 0 của ZERO |

Mở đầu Chính đi chậm và hợp với mạch tình cảm. Khác 1 hợp với các cảnh đêm khuya, đời thường. Khác 2 đưa thẳng vào mạch giật gân.

## Những chỗ người chơi tự quyết

- Ngành học và năm học của {{user}} (mở đầu Chính mặc định {{user}} học cùng lớp CNTT năm tư).
- Họ của {{user}}: nhân vật phụ gọi "bạn học + họ". Nếu persona không có họ, họ sẽ gọi bằng tên.
- Kiểu quan hệ và tốc độ thân thiết. Card được viết để đi chậm, nên đừng ép Tần Dương mở lòng nhanh.

## Rút gọn card

Card đã được rút gọn để khối nhân vật (khối B của prompt) còn khoảng 1.200 token, giảm từ khoảng 2.000 (đo bằng `build_preview`), vì gemma4:12b hay quên luật khi khối này dài. Card vẫn giữ mọi chi tiết người dùng đưa ra, chỉ viết gọn lại. Ô Mô tả giờ chỉ còn một câu. Lời mở đầu chính và hai lời mở đầu khác đều dưới 200 từ.

Những phần đã chuyển ra khỏi card nằm nguyên trong `world.md` và sẽ thành mục lore ở Phase 4:
- hồ sơ nhân vật phụ;
- địa điểm;
- cốt truyện và móc sự kiện;
- lịch sinh hoạt, thích/ghét, tác nhân gây hoảng và cách tự trấn an;
- mẹ (Hứa Uyển) và bà nội;
- tên cha;
- bốn điều cấm của GHOST.

Muốn thêm chi tiết vào card thì đo lại khối B trước, đừng để vượt 1.200 token.
