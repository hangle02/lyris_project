# Văn phong và xưng hô theo bối cảnh của story

- **Ngày:** 2026-11-12 · **Ai quyết:** người dùng

## Bối cảnh

Người dùng: nhân vật nên xưng hô theo đúng quốc gia, hoàn cảnh; tên kiểu Trung thì trò chuyện kiểu Trung.

## Lựa chọn

Mỗi card có style_profile (file Markdown trong backend/lyris/prompt/styles/): viet_hien_dai, trung_hien_dai, trung_co_dai, trung_dan_quoc, chung. Nội dung chèn vào khối B. AI viết nháp đề xuất profile, người dùng xác nhận. address_terms của card ghi đè mặc định.

## Vì sao

Xưng hô và giọng văn đi theo quốc gia và thời đại của story, không theo ngôn ngữ hiển thị. Chỉ dựa vào tên thì dễ đoán sai.

## Đã cân nhắc

Đoán văn phong chỉ từ tên nhân vật.

## Nguồn

- Lời người dùng, 2026-11-12 05:44 (xem [raw/](../raw/))
- [docs/plan.md](../../docs/plan.md) §7
- [docs/phase2.md](../../docs/phase2.md) (style profile)
