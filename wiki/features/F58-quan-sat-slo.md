# F58 — Quan sát hệ thống và SLO

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Quản lý (`#/admin`) → "Số liệu" → mục "Nâng cao" gập sẵn: thời gian chờ chữ đầu tiên của nhân vật.

## Là gì

Log có cấu trúc (không chữ chat), số đo Prometheus, trace OpenTelemetry, cảnh báo và SLO cho bản host. Thiết kế:
[docs/server.md §12](../../docs/server.md).

## Hoạt động thế nào

- SLO: TTFT lượt không chờ hàng p50 ≤ 1,5 s và p95 ≤ 4 s; chữ đầu tiên **hiện** cho người chơi (sau bộ lọc đầu ra theo
  đoạn) p50 ≤ 2,5 s và p95 ≤ 5 s; tốc độ chữ p50 ≥ 25 token/s; lượt phải chờ ≤ 5 % lúc cao điểm; lượt lỗi do hệ thống
  ≤ 0,5 % (kể cả lúc đêm chỉ có 1 replica); API không stream sẵn sàng 99,9 %, p95 ≤ 300 ms; coin của giao dịch đã trả
  99 % trong 60 s.
- Cảnh báo: TTFT p95 > 6 s trong 10 phút, hàng chờ > 20 trong 5 phút, 5xx > 1 % trong 5 phút, sổ coin hoặc nợ coin lệch,
  sao lưu lỗi, báo cáo `minor_safety` quá 24 giờ, giữ chỗ mất trước khi trừ (`lyris_hold_lost_total`) > 0,1 % lượt trong
  1 giờ.
- `/api/healthz` (sống) và `/api/readyz` (Postgres + Redis trả lời trong 200 ms) cho load balancer.
- Giao diện người dùng không có chữ kỹ thuật; số đo chỉ cho người quản lý, trong "Nâng cao".

## Done when

- [ ] Unit: `/metrics` của API có `lyris_reply_ttft_seconds`, `lyris_reply_first_visible_seconds`, `lyris_reply_tokens_per_second`, `lyris_genq_length`, `lyris_jobs_queued`, `lyris_hold_lost_total` (`test_metrics_exposed`).
- [ ] Unit: log JSON của một lượt chat có `request_id` và `story_id`, và không chứa chuỗi nào của tin nhắn đã gửi hay câu trả lời (`test_logs_have_no_chat_text`).
- [ ] Unit: sửa tay một ví lệch 6 coin so với tổng sổ → `ledger_audit` phát cảnh báo `ledger_mismatch` với id ví; sửa tay `debt` của một ví lệch 10 so với `Σ shortfall − Σ |debt_repay|` → cảnh báo `debt_mismatch` (`test_ledger_audit_detects_mismatch`).
- [ ] Unit: `deploy/alerts.yaml` có đủ 7 luật cảnh báo ở trên với đúng ngưỡng (6 s/10 phút, 20/5 phút, 1 %/5 phút, 0,1 %/1 giờ…) (`test_alert_rules_file`).
- [ ] Unit: `/api/healthz` trả 200 không cần đăng nhập và không có tên model hay phiên bản; `/api/readyz` trả 503 khi Redis không trả lời trong 200 ms (`test_health_and_ready`).
- [ ] Bot: `#/admin` → "Số liệu" → mở "Nâng cao": có ô "Chờ chữ đầu tiên (p95)" hiện số giây; phần ngoài "Nâng cao" không có chữ `token`, `GPU`, `vLLM`.

## Tests

- `backend/tests/test_observability.py::test_metrics_exposed`
- `backend/tests/test_observability.py::test_logs_have_no_chat_text`
- `backend/tests/test_observability.py::test_ledger_audit_detects_mismatch`
- `backend/tests/test_observability.py::test_alert_rules_file`
- `backend/tests/test_observability.py::test_health_and_ready`
- bot: số liệu chờ trả lời cho người quản lý

## Liên quan

- **Tài liệu:** [docs/server.md §12](../../docs/server.md), [docs/tracking-plan.md](../../docs/tracking-plan.md), [docs/deploy.md §11](../../docs/deploy.md)
- **Tính năng:** [F34](F34-theo-doi-su-kien.md), [F53](F53-cong-suy-luan-vllm.md)
- **Quyết định:** [nguong-ttft-f14](../decisions/nguong-ttft-f14.md), [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
