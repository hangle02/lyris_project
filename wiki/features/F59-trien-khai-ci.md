# F59 — Triển khai, CI/CD và môi trường staging

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Không có màn hình mới.

## Là gì

Ba môi trường (dev, staging, prod), container chỉ ở bản host ([quyết định](../decisions/container-chi-khi-host.md)),
Kubernetes có quản lý + Helm, CI chạy test trên cả SQLite và Postgres, staging tự triển khai, production có canary.
Thiết kế: [docs/server.md §14](../../docs/server.md).

## Hoạt động thế nào

- Mỗi PR: typecheck, pytest hai backend, `npm test`, build, bot e2e trên LLM giả, kiểm migration chỉ thêm.
- Nhánh chính → staging tự động → bot e2e chạy trên staging.
- Production: bấm duyệt, canary 10 % trong 30 phút, rồi 100 %; quay lại bằng ảnh container cũ.
- Tắt êm: SIGTERM → `readyz` 503 → chờ stream đang chạy xong (≤ 150 s) → thoát.
- Bản host thiếu biến bắt buộc thì không khởi động (báo tên biến, không in giá trị).
- Migration chạy như một Job riêng nối thẳng Postgres (không qua PgBouncer), trước khi pod mới nhận request; pod API không
  tự áp migration. Giá trị mới của `coin_ledger.kind` / `release_reason` thêm bằng `INSERT` vào bảng tra, nên luật "chỉ
  thêm" không cần ngoại lệ ([quyết định](../decisions/fence-postgres-va-loc-truoc-stream.md)).
- `verification/verify.sh` vẫn là cổng chấm tính năng, không cần cloud.

## Done when

- [ ] Unit: áp `db/migrations` và `db/migrations_pg` từ 0 rồi áp bản mới lên bản chụp schema: 0 lỗi; migration mới có `DROP`, `RENAME` hay `ALTER … DROP` bị từ chối; migration chỉ có `INSERT INTO coin_kinds …` / `INSERT INTO hold_release_reasons …` (thêm giá trị vào bảng tra) được nhận (`test_migrations_additive_only`).
- [ ] Unit: SIGTERM khi đang stream → `/api/readyz` trả 503 ngay, stream đang chạy kết thúc bằng sự kiện `done`, tiến trình thoát trong ≤ 180 s (`test_graceful_shutdown_drains_streams`).
- [ ] Unit: `.github/workflows/ci.yml` có bước pytest với `LYRIS_TEST_DB=sqlite` và `LYRIS_TEST_DB=postgres`, `npm test`, `npm run typecheck`, `npm run build` và bot e2e (`test_ci_workflow_runs_both_backends`).
- [ ] Unit: `LYRIS_MODE=hosted` thiếu `LYRIS_DB_URL`, `LYRIS_REDIS_URL` hoặc `VLLM_KEY` → backend dừng với thông báo có tên biến và không có giá trị bí mật nào (`test_hosted_config_requires_secrets`).
- [ ] Bot: bot e2e chạy với `LYRIS_BOT_BASE_URL` trỏ staging sau mỗi lần triển khai staging: toàn bộ `CHECKS` xanh.

## Tests

- `backend/tests/test_deploy.py::test_migrations_additive_only`
- `backend/tests/test_deploy.py::test_graceful_shutdown_drains_streams`
- `backend/tests/test_deploy.py::test_ci_workflow_runs_both_backends`
- `backend/tests/test_deploy.py::test_hosted_config_requires_secrets`
- bot: chạy cả bộ check trên staging

## Ngoài Done when

Không chặn ✅: Terraform/Helm cho cloud đã chọn (PO trả lời câu hỏi cloud), diễn tập khôi phục hằng tháng, build app di
động bằng Fastlane/Xcode Cloud.

## Liên quan

- **Tài liệu:** [docs/server.md §14, §18](../../docs/server.md), [docs/deploy.md](../../docs/deploy.md)
- **Quyết định:** [container-chi-khi-host](../decisions/container-chi-khi-host.md), [chua-dung-docker](../decisions/chua-dung-docker.md)
- **Tính năng:** [F36](F36-harness-kiem-tra.md), [F58](F58-quan-sat-slo.md)
