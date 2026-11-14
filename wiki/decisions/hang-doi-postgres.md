# Hàng đợi việc nền trên Postgres (bảng jobs, SKIP LOCKED)

- **Ngày:** 2026-11-14 · **Ai quyết:** AI chọn (tạm chọn, PO đổi được)

## Bối cảnh

PO chốt "hàng đợi việc nền" (4A) nhưng không nói công cụ. Hiện tại bảng `jobs` ở SQLite + một worker asyncio trong tiến
trình, có huỷ job khi message hết active, xen kẽ theo tài khoản, nhường lượt chat ([F52](../features/F52-hang-doi-viec-nen.md)).

## Lựa chọn

Giữ bảng `jobs` ở Postgres, nhiều worker lấy job bằng `FOR UPDATE SKIP LOCKED`, đánh thức bằng `LISTEN/NOTIFY` (kênh
LISTEN nối thẳng Postgres, không qua PgBouncer), lease có hạn; việc định kỳ do một leader giữ dòng `leader_lease` (không
dùng khoá phiên `pg_try_advisory_lock`, vì PgBouncer chế độ transaction làm hỏng khoá phiên). Không Celery, RQ, arq,
Dramatiq.

Ngữ nghĩa là **ít nhất một lần**: hoàn tất job có fence (`WHERE id AND worker_id AND attempts`), mọi handler idempotent,
`run_after NOT NULL DEFAULT now()`. Sửa sau phản biện ([docs/server.md §21](../../docs/server.md)).

## Vì sao

- Job được xếp trong **cùng transaction** với việc lưu câu trả lời: không bao giờ lưu tin mà mất job.
- Giữ nguyên ngữ nghĩa và test của `jobs/queue.py`, `jobs/worker.py`; cùng code chạy ở bản tự chạy.
- Lưu lượng 4A (~4–10 job/giây) rất nhỏ so với sức của Postgres; không thêm broker phải vận hành.

## Đã cân nhắc

Celery/RQ/arq/Dramatiq/SAQ trên Redis (ghi hai nơi, cần outbox, viết lại ngữ nghĩa); hàng đợi của cloud (SQS, Pub/Sub:
khoá vào một cloud). Đổi khi > 500 job/giây kéo dài.

## Nguồn

- [docs/server.md §7](../../docs/server.md)
