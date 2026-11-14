# Một model chia cho nhiều người: tối đa 2 lượt cùng lúc

- **Ngày:** 2026-11-14 · **Ai quyết:** thiết kế

## Bối cảnh

Một Ollama, OLLAMA_NUM_PARALLEL=2, mọi thứ thiết kế cho một người.

## Lựa chọn

GenerationGate: tối đa 2 lượt sinh trên cả máy (LYRIS_CHAT_SLOTS), mỗi tài khoản 1, xếp hàng vào trước ra trước, chờ quá 120 giây thì bỏ. Việc nền xen kẽ theo tài khoản. Chỉ chủ máy đổi model và xem thông tin máy. Trạng thái: Một phần (chưa đo tốc độ khi hai lượt chạy song song).

## Vì sao

Hai người chat cùng lúc thì không ai phải chờ người kia viết xong. Nạp model thứ hai trên 24GB làm chậm mọi người.

## Đã cân nhắc

LYRIS_CHAT_SLOTS=1 (lần lượt từng người) nếu đo thấy quá chậm; ưu tiên chủ máy.

## Nguồn

- [docs/auth.md](../../docs/auth.md) §1.1, §5
