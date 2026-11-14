# Lưu sự kiện trong app, gửi thêm PostHog khi có khoá

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng

## Bối cảnh

Đề bài của Apero yêu cầu sản phẩm có theo dõi sự kiện để phân tích dữ liệu ở Round 2. Phải chọn nơi lưu sự kiện: chỉ trong DB của app, chỉ trên một dịch vụ phân tích, hay cả hai. Story của Lyris là riêng tư.

## Lựa chọn

Lưu mọi sự kiện trong DB SQLite của app (180 ngày). Khi đặt `LYRIS_POSTHOG_KEY`, gửi thêm sang PostHog bằng một tác vụ nền. **Không bao giờ** gửi chữ của story, nhân vật, persona hay bất kỳ chữ tự do nào vào số liệu; không gửi IP. Người dùng tắt được; tắt thì xoá sự kiện đã lưu của tài khoản.

## Vì sao

- DB của app luôn có dữ liệu, kể cả khi chưa có khoá PostHog hay mất mạng; chủ máy xem số liệu ngay trong app và xuất CSV/JSONL cho Apero.
- PostHog cho biểu đồ, phễu, giữ chân mà không phải tự làm.
- Không chữ, không IP: số liệu không lộ được story riêng tư, và giảm việc phải làm về quyền riêng tư khi dữ liệu ra nước ngoài.

## Đã cân nhắc

- Chỉ PostHog: mất dữ liệu khi chưa cấu hình, phụ thuộc dịch vụ ngoài.
- Chỉ DB của app: phải tự làm mọi biểu đồ.
- Gửi PostHog từ trình duyệt bằng SDK của họ: bị trình chặn quảng cáo chặn, khó giữ luật "không chữ", thêm cookie bên thứ ba.

## Nguồn

- Quyết định của chủ dự án khi rà soát ra mắt, 2026-11-14 (ghi ở [docs/compliance.md §0](../../docs/compliance.md)); chi tiết: [docs/tracking-plan.md](../../docs/tracking-plan.md).
