# F52 — Hàng đợi việc nền trên Postgres

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Không có màn hình mới ("Xem sự kiện", ngăn trái tim vẫn hiện "đang ghi nhớ" như bây giờ).

## Là gì

Việc nền (trích xuất cảm xúc/ký ức/cảnh, tóm tắt, embed, prefill, bảng xếp hạng, đối soát thanh toán, gửi PostHog, dọn
dẹp) chạy trên nhiều worker riêng, lấy job từ chính bảng `jobs` ở Postgres bằng `FOR UPDATE SKIP LOCKED`. Không thêm
broker ([quyết định](../decisions/hang-doi-postgres.md)). Thiết kế: [docs/server.md §7](../../docs/server.md).

## Hoạt động thế nào

- `JobBackend` có hai bản: worker asyncio trong tiến trình (bản tự chạy, như `jobs/worker.py`) và worker pod (bản host).
- Bảng `jobs` thêm `account_id`, `priority`, `run_after`, `lease_until`, `worker_id`, `payload`.
- Job được xếp trong cùng transaction với việc lưu câu trả lời.
- Worker chết: job `running` quá `lease_until` quay về `queued`.
- **Ít nhất một lần, không phải đúng một lần:** worker chậm có thể làm job chạy hai lần; hoàn tất có fence
  (`WHERE id AND worker_id AND attempts`), mọi handler idempotent. `run_after NOT NULL DEFAULT now()`.
- Lấy job xen kẽ theo tài khoản (docs/auth.md §5.3); mỗi tài khoản tối đa 50 job đang chờ.
- Việc định kỳ chỉ do worker giữ dòng `leader_lease` xếp (một leader), mỗi việc có khoá duy nhất `(kind, slot)` theo khung
  giờ. Không dùng khoá phiên `pg_try_advisory_lock`: qua PgBouncer chế độ transaction nó không đúng.
- Kênh `LISTEN` của mỗi worker nối thẳng Postgres (không qua PgBouncer); mất kênh thì poll mỗi 2 giây.
- Test pooler cần `pgbouncer` chạy thẳng trên Mac (không Docker); khi làm F52 thêm kiểm vào `environment/doctor.mjs`,
  thiếu thì là lỗi `infra`, không skip.

## Done when

- [ ] Unit: 4 worker chạy song song trên 200 job (không ai chậm) → mỗi job chạy đúng 1 lần (`test_pg_jobs_skip_locked_exactly_once`).
- [ ] Unit: worker A lấy job rồi chậm quá hạn lease, worker B lấy lại và hoàn tất; A hoàn tất sau → câu `UPDATE` hoàn tất của A khớp 0 dòng, kết quả của A bị bỏ, job có đúng 1 kết quả (của B) (`test_job_at_least_once_completion_fenced`).
- [ ] Unit: xếp job không ghi `run_after` → cột có giá trị `now()` và job được lấy ngay; ghi `NULL` → lỗi `NOT NULL` (`test_job_run_after_defaults_now`).
- [ ] Unit: rollback transaction lưu câu trả lời → không còn job trích xuất nào của lượt đó (`test_job_enqueued_in_same_transaction`).
- [ ] Unit: worker ngừng gia hạn → job `running` về `queued` sau 90 s (đồng hồ giả), chạy lại, `attempts` = 2 (`test_job_lease_expiry_requeues`).
- [ ] Unit: tài khoản A có 100 job chờ, tài khoản B xếp 1 job sau đó → job của B chạy trong 2 job đầu tiên (`test_claim_interleaves_accounts`).
- [ ] Unit: tài khoản đã có 50 job `queued` gọi `POST /api/stories/{id}/state/rebuild` → 409 (`test_job_quota_per_account`).
- [ ] Unit: 3 worker cùng chạy 60 s (đồng hồ giả) → `posthog_flush` được xếp đúng 6 lần, chỉ bởi 1 worker (`test_scheduler_single_leader`).
- [ ] Unit: 3 worker nối Postgres qua một pooler chế độ transaction (PgBouncer tạm trên unix socket) → vẫn đúng 1 leader; leader ngừng gia hạn → worker khác thành leader sau ≤ 30 s, không có khung giờ nào bị xếp hai lần (`test_scheduler_leader_survives_pooler`).
- [ ] Unit: các test hiện có trong `backend/tests/test_jobs.py` xanh trên cả hai bản `JobBackend` (`test_jobs_contract_both_backends`).
- [ ] Bot: trên Postgres với worker chạy ở tiến trình riêng, sau 2 lượt chat ở `#/chat/{id}`, "Xem sự kiện" (menu "+") có ít nhất 1 dòng thời gian.

## Tests

- `backend/tests/test_pg_jobs.py::test_pg_jobs_skip_locked_exactly_once`
- `backend/tests/test_pg_jobs.py::test_job_at_least_once_completion_fenced`
- `backend/tests/test_pg_jobs.py::test_job_run_after_defaults_now`
- `backend/tests/test_pg_jobs.py::test_job_enqueued_in_same_transaction`
- `backend/tests/test_pg_jobs.py::test_job_lease_expiry_requeues`
- `backend/tests/test_pg_jobs.py::test_claim_interleaves_accounts`
- `backend/tests/test_pg_jobs.py::test_job_quota_per_account`
- `backend/tests/test_scheduler.py::test_scheduler_single_leader`
- `backend/tests/test_scheduler.py::test_scheduler_leader_survives_pooler`
- `backend/tests/test_pg_jobs.py::test_jobs_contract_both_backends`
- bot: ghi nhớ chạy bằng worker riêng

## Liên quan

- **Tài liệu:** [docs/server.md §7](../../docs/server.md), [docs/phase3.md §4, §10.6](../../docs/phase3.md), [docs/auth.md §5.2, §5.3](../../docs/auth.md)
- **Code hiện tại:** [`jobs/queue.py`](../../backend/lyris/jobs/queue.py), [`jobs/worker.py`](../../backend/lyris/jobs/worker.py), [`analytics/forwarder.py`](../../backend/lyris/analytics/forwarder.py)
- **Quyết định:** [hang-doi-postgres](../decisions/hang-doi-postgres.md), [viec-nen-dung-model-chat](../decisions/viec-nen-dung-model-chat.md)
