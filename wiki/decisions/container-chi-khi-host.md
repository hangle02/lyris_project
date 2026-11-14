# Container và Kubernetes chỉ cho bản host; máy dev vẫn không Docker

- **Ngày:** 2026-11-14 · **Ai quyết:** AI chọn (tạm chọn, PO đổi được)

## Bối cảnh

Quyết định [chua-dung-docker](chua-dung-docker.md) (người dùng: "chưa cần docker") áp cho máy Mac chạy Lyris. Bản host cần
triển khai lặp lại được trên nhiều máy, nhiều môi trường ([F59](../features/F59-trien-khai-ci.md)).

## Lựa chọn

- Bản host: ảnh container cho API, worker, vLLM; Kubernetes có quản lý của cloud đã chọn; Helm; node GPU riêng.
- Máy dev và bản tự chạy: giữ nguyên, không Docker (backend `.venv`, Ollama, `scripts/dev.sh`).

## Vì sao

Tự co giãn GPU, rolling deploy, canary và ba môi trường giống nhau cần container; máy Mac của người làm thì không.

## Đã cân nhắc

VM + systemd + Ansible (ít thành phần hơn, nhưng co giãn và canary làm tay); Nomad (ít cloud hỗ trợ sẵn).

## Nguồn

- [docs/server.md §14](../../docs/server.md)
