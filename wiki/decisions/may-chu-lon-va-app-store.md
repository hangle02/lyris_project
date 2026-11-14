# Lyris lên máy chủ lớn và App Store: thiết kế bây giờ, code sau khi nộp bài

- **Ngày:** 2026-11-14 · **Ai quyết:** PO chốt (1A, 2A, 4A, 5A); mục 3 PO giao AI chọn

## Bối cảnh

PO muốn Lyris thành app công khai trên máy chủ lớn và App Store ([raw](../raw/2026-11-14-server-lon-appstore.md)). Bản
hiện tại chạy trên một máy (SQLite, Ollama, một tiến trình) và đã qua bộ chấm; hạn nộp bài là 15/11/2026.

## Lựa chọn

- **1A:** viết thiết kế đầy đủ bây giờ ([docs/server.md](../../docs/server.md), F50–F62); code sau khi nộp bài. Bản tự chạy
  giữ nguyên và vẫn phải xanh. README ghi rõ hướng đi.
- **2A:** máy chủ GPU riêng, model mở (`gemma4:12b`, sau này LoRA tự train) qua vLLM ([suy-luan-vllm](suy-luan-vllm.md)).
- **3:** AI chọn Capacitor ([app-di-dong-capacitor](app-di-dong-capacitor.md)).
- **4A:** ~10.000 người dùng/tháng, vài trăm người chat cùng lúc: Postgres, Redis, nhiều máy chủ API không trạng thái,
  hàng đợi việc nền, ảnh trên S3 ([postgres-giu-repo](postgres-giu-repo.md), [hang-doi-postgres](hang-doi-postgres.md)).
- **5A:** Apple IAP trên iOS (Google Play Billing trên Android), VNPay/MoMo trên web, server đối soát vào chung sổ coin
  ([thanh-toan-iap-va-cong-vn](thanh-toan-iap-va-cong-vn.md)).

## Vì sao

PO: "1A … 2A … 3: bạn xem cái nào tối ưu và mượt mà nhất thì chọn 4A … 5A"
([raw](../raw/2026-11-14-server-lon-appstore-tra-loi.md)). Code lại backend một ngày trước hạn nộp có thể làm hỏng bản đã
qua bộ chấm.

## Đã cân nhắc

1B code ngay (rủi ro trước hạn nộp); 2B API của nhà cung cấp AI lớn (phụ thuộc chính sách nội dung); 2C kết hợp; 4B thiết
kế cho 100 nghìn người từ đầu (đắt, chưa cần); 4C nhỏ vài trăm người; 5B chỉ IAP.

## Sau phản biện (2026-11-14)

Bản thiết kế đã qua một vòng phản biện kiến trúc và duyệt App Store/Play; 23 điểm được nhận, sửa lại hoặc bác có lý do
([docs/server.md §21](../../docs/server.md)). Hướng đi PO chốt (1A, 2A, 4A, 5A) và lựa chọn Capacitor không đổi; thay
đổi nằm ở chi tiết (fence coin ở Postgres, cổng Redis không rò, lọc đầu ra trước khi stream, giữ giọng văn khi sang
vLLM, luật "cộng cho chủ giao dịch" của IAP), xem [fence-postgres-va-loc-truoc-stream](fence-postgres-va-loc-truoc-stream.md).

## Nguồn

- [raw/2026-11-14-server-lon-appstore.md](../raw/2026-11-14-server-lon-appstore.md)
- [raw/2026-11-14-server-lon-appstore-tra-loi.md](../raw/2026-11-14-server-lon-appstore-tra-loi.md)
