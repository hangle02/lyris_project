# Ngưỡng TTFT của F14: trung vị ≤ 5 giây, mỗi lượt ≤ 6 giây

- **Ngày:** 2026-11-14 · **Ai quyết:** AI đề xuất, chủ dự án đồng ý cùng ngày ([raw](../raw/2026-11-14-po-quyet-harness.md)).
  Lần `verify.sh --real-model` đầu tiên đo được khoảng 4 giây.

## Bối cảnh

F14 hứa "TTFT các lượt sau lượt đầu khoảng 4-5 giây, kể cả lượt cửa sổ dịch". Kịch bản `f14-ttft` cần một con số cụ thể để
máy chấm đậu/rớt.

## Lựa chọn

- Đo qua **app thật** trong tiến trình (`create_app`, DB tạm, Ollama thật, worker trích xuất + tóm tắt + prefill raw như khi chạy
  app), story seed được nạp sẵn lịch sử tới gần mốc cửa sổ dịch; gửi lượt qua HTTP như giao diện, chờ việc nền và prefill xong mới
  gửi lượt sau (đúng cách đo ở docs/phase3.md §10.6).
- Lượt sống đầu tiên không tính (đọc cả prompt). **Trung vị** các lượt sau ≤ **5,0 giây** ("khoảng 4-5 giây") và **mọi** lượt sau
  ≤ **6,0 giây**; kịch bản phải gặp ít nhất một lượt cửa sổ dịch và đo thêm ít nhất một lượt sau đó (tối đa 7 lượt sống), không thì
  đỏ vì chưa đo được điều dòng Done when nói. (Rà soát 2026-11-14: chỉ có mốc 6 giây thì mọi lượt 5,9 giây vẫn xanh, tức nới
  "khoảng 4-5 giây"; nên thêm trung vị.)
- TTFT đo **phía người chơi**: app được phục vụ qua uvicorn ở cổng test 8068 (8069 nếu bận), đo từ lúc gửi POST tới sự kiện `delta`
  đầu tiên có chữ, nên gồm cả dựng prompt, tìm ký ức, chọn mục thế giới, chờ khoá. Số OllamaClient tự đo vẫn ghi kèm để đối chiếu.
- Giới hạn thời gian: mỗi lần chờ việc nền tối đa 180 giây, cả kịch bản tối đa 900 giây; quá thì là lỗi của riêng `f14-ttft`
  (không kéo cả lượt `run_eval` quá 60 phút làm mọi tính năng đỏ).

## Vì sao

- Số đo thật (docs/phase3.md §10.6, prefill raw, không sổ thế giới): mọi lượt sau lượt đầu 4,2-5,3 giây, kể cả hai lượt cửa sổ dịch.
- Có sổ thế giới (docs/phase4.md §6.5): trung bình 6,58 giây (4,5-8,5 giây, ~+1 giây mỗi 100 token khối D). Story seed của kịch bản
  không có mục thế giới, nên dùng mốc không lore.
- 6,0 giây = số đo cao nhất 5,3 giây cộng ~13% cho dao động lấy mẫu và máy. 5,0 giây cho **từng** lượt sẽ đỏ cả khi máy chạy đúng
  như đã đo (có lượt 5,3 giây), nên 5,0 giây là mốc của trung vị, không phải của từng lượt.
- Số cũ đo ở OllamaClient; đo phía người chơi chậm hơn một chút (dựng prompt, tìm ký ức). Nếu lần chạy thật đầu tiên đỏ chỉ vì phần
  chênh này thì hỏi PO trước khi đổi ngưỡng.

## Đã cân nhắc

- 5,5 giây (sát số đo hơn): dễ đỏ do dao động, mỗi lần đỏ ăn một lượt trong 3 lượt đỏ của tính năng.
- 8,5 giây (mức có sổ thế giới): quá lỏng với story không có lore.
- Thêm luật số token đọc lại (`prompt_eval_count` ≤ ~1500): chưa chắc nghĩa của số này ở mọi bản Ollama; chỉ ghi vào báo cáo để đọc.

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §10.6 (bảng "Prefill raw (mới)"), [docs/phase4.md](../../docs/phase4.md) §6.5
- Kịch bản: [harness/scenarios/17-f14-ttft.yaml](../../harness/scenarios/17-f14-ttft.yaml)
