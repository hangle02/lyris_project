# F51 — Redis và máy chủ API không trạng thái

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Chat Story/DM (`#/chat/{id}`): không đổi chữ; câu trả lời nối tiếp được sau khi rớt mạng.

## Là gì

Mọi thứ hiện nằm trong bộ nhớ của một tiến trình (cổng sinh, khoá story, khoá viết nháp/chat thử, giới hạn sự kiện) chuyển
sang Redis, để chạy nhiều máy chủ API sau một load balancer. App di động đăng nhập bằng token `Bearer` cùng bảng
`sessions`. Thiết kế: [docs/server.md §4, §6, §10](../../docs/server.md).

## Hoạt động thế nào

- Cổng sinh phân tán (Lua trên Redis): mỗi tài khoản 1 lượt, hàng FIFO, quá 120 giây thì báo bận như bây giờ; sự kiện SSE
  `waiting` giữ nguyên. Vé đang chạy và chỗ chờ là phần tử ZSET có hạn nhịp tim (gia hạn mỗi 10 s), `admit.lua` dọn phần
  tử quá hạn trước khi đếm: pod chết không làm rò sức chứa hay kẹt hàng. Sức chứa đếm theo từng replica vLLM.
- Khoá story `lock:story:{id}` có token, TTL 30 giây, gia hạn 10 giây, **chỉ để từ chối sớm**; bảo đảm đúng là fence ở
  Postgres (dòng giữ chỗ `FOR UPDATE`, F50, [quyết định](../decisions/fence-postgres-va-loc-truoc-stream.md)).
- Pod chết giữa lượt: giữ chỗ coin nhả trong ≤ 40 giây (lease 30 s + sweeper mỗi 10 s). Nối lại câu trả lời của pod đã
  chết → sự kiện `error` dễ hiểu thay vì chờ mãi.
- Request có `Authorization: Bearer` bỏ qua cookie và miễn kiểm `Origin` lẫn `Sec-Fetch-Site` (vẫn bắt `X-Lyris`).
- Khoá tài khoản/đăng xuất mọi thiết bị xoá mọi `sess:*` của tài khoản qua `sess_by_acct:{id}`.
- SSE gửi `Cache-Control: no-cache, no-transform`; giới hạn theo IP chỉ là lưới thô ngưỡng cao (CGNAT di động).
- Test cần `redis-server` và Postgres tạm trên Mac (không Docker); khi làm F51 thêm kiểm `redis-server` vào
  `environment/doctor.mjs`, thiếu thì là lỗi `infra`, không skip.
- Delta của mỗi câu trả lời ghi vào Redis Stream `reply:{reply_id}`; client nối lại bằng `Last-Event-ID` ở máy chủ bất kỳ.
  Rớt mạng giữa lượt: câu trả lời vẫn sinh tới hết và được lưu (tạm chọn, chờ PO); chỉ nút "Dừng" mới dừng.
- SSE gửi dòng `: ping` mỗi 15 giây (Cloudflare cắt kết nối im lặng 100 giây).
- Phiên: bảng `sessions` ở Postgres là nguồn sự thật, Redis cache 60 giây; web dùng cookie như bây giờ, app dùng
  `Authorization: Bearer` ([quyết định](../decisions/phien-token-cho-app.md)).
- `client_ip()` tin `CF-Connecting-IP`/`X-Forwarded-For` chỉ từ dải proxy đã khai (`LYRIS_TRUSTED_PROXIES`).

## Done when

- [ ] Unit: `RedisGate` qua đúng các test của `GenerationGate` hiện có: mỗi tài khoản 1 lượt (409), vào trước ra trước, chờ quá 120 s → `GateTimeout` (`test_redis_gate_matches_memory_gate`).
- [ ] Unit: hai `ChatService` (hai "máy chủ") chung Redis + Postgres: gửi lượt vào cùng story ở máy B khi máy A đang sinh → 409 `Busy` (`test_two_pods_story_lock`).
- [ ] Unit: máy A "chết" giữa lượt (huỷ task, không nhả khoá) → sau ≤ 30 s (đồng hồ giả) story mở lại; sau ≤ 40 s giữ chỗ coin nhả lý do `restart`, số dư bằng trước lượt (`test_pod_crash_releases_lock_and_hold`).
- [ ] Unit: một pod chết khi đang chờ trong hàng và một pod chết khi đang giữ vé sinh (không nhả, không gia hạn) → sau ≤ 40 s (đồng hồ giả) một tài khoản thứ ba được nhận ngay, không phải chờ 120 s; số vé đang chạy của replica trở về 0 (`test_redis_gate_dead_waiter_and_dead_runner_do_not_leak`).
- [ ] Unit: replica R1 có `chat_capacity` 2 đã đủ 2 vé, R2 còn trống → lượt thứ 3 của story dính R1 không vượt 2 vé ở R1 (chờ, hoặc tràn sang R2 sau 5 s) (`test_redis_gate_capacity_per_replica`).
- [ ] Unit: khi chờ cổng, stream gửi `: ping` mỗi 15 s trước sự kiện `start`; response SSE có `Cache-Control: no-cache, no-transform` (`test_sse_heartbeat_while_waiting`).
- [ ] Unit: client ngắt kết nối sau delta số 5 → câu trả lời vẫn được lưu; `GET /api/stories/{id}/reply/{reply_id}/events` với `Last-Event-ID: 5` trả delta từ số 6 tới `done` (`test_reply_resume_after_disconnect`).
- [ ] Unit: pod sinh câu trả lời chết sau delta số 3 (Stream không bao giờ có `done`) → nối lại với `Last-Event-ID: 3` nhận sự kiện `error` có câu dễ hiểu sau khi khoá story hết hạn, không treo; số dư bằng trước lượt (`test_reply_resume_after_origin_pod_died`).
- [ ] Unit: `Authorization: Bearer <token>` đăng nhập được như cookie; request Bearer có `Origin: capacitor://localhost` và `Sec-Fetch-Site: cross-site` → 200; request cookie kèm `Sec-Fetch-Site: cross-site` hoặc `Origin` lạ → 403 `csrf`; request có cả Bearer hợp lệ và cookie của tài khoản khác → chạy với tài khoản của Bearer (`test_bearer_token_auth_and_csrf`).
- [ ] Unit: đăng xuất xoá `sess:{hash}` ở Redis; request kế tiếp bằng token cũ → 401; staff khoá tài khoản có 3 phiên đang cache → cả 3 token bị 401 ngay ở request kế tiếp (`test_logout_invalidates_session_cache`).
- [ ] Unit: `client_ip()` chỉ đọc `CF-Connecting-IP` khi peer thuộc dải trong `LYRIS_TRUSTED_PROXIES` (`test_client_ip_behind_cloudflare_and_lb`).
- [ ] Bot: hai tiến trình backend (cổng 8066 và 8068) chung Postgres + Redis tạm, request luân phiên qua proxy ở 8069: gửi lượt chat ở `#/chat/{id}` thấy câu trả lời và chip coin giảm 6.

## Tests

- `backend/tests/test_redis_gate.py::test_redis_gate_matches_memory_gate`
- `backend/tests/test_multi_pod.py::test_two_pods_story_lock`
- `backend/tests/test_multi_pod.py::test_pod_crash_releases_lock_and_hold`
- `backend/tests/test_redis_gate.py::test_redis_gate_dead_waiter_and_dead_runner_do_not_leak`
- `backend/tests/test_redis_gate.py::test_redis_gate_capacity_per_replica`
- `backend/tests/test_sse_resume.py::test_sse_heartbeat_while_waiting`
- `backend/tests/test_sse_resume.py::test_reply_resume_after_disconnect`
- `backend/tests/test_sse_resume.py::test_reply_resume_after_origin_pod_died`
- `backend/tests/test_bearer_auth.py::test_bearer_token_auth_and_csrf`
- `backend/tests/test_bearer_auth.py::test_logout_invalidates_session_cache`
- `backend/tests/test_client_ip_proxies.py::test_client_ip_behind_cloudflare_and_lb`
- bot: chat qua hai backend luân phiên

## Ngoài Done when

Không chặn ✅: bài kiểm "giết pod giữa lượt" và "Redis failover giữa lượt" trên staging với 3 pod thật (G3 trong
[docs/server.md §18](../../docs/server.md)).

## Liên quan

- **Tài liệu:** [docs/server.md §4, §6, §10](../../docs/server.md), [docs/auth.md §3, §5](../../docs/auth.md)
- **Code hiện tại:** [`chat/gate.py`](../../backend/lyris/chat/gate.py), [`chat/service.py`](../../backend/lyris/chat/service.py), [`api/sse.py`](../../backend/lyris/api/sse.py), [`auth/middleware.py`](../../backend/lyris/auth/middleware.py), [`auth/net.py`](../../backend/lyris/auth/net.py)
- **Quyết định:** [phien-token-cho-app](../decisions/phien-token-cho-app.md), [fence-postgres-va-loc-truoc-stream](../decisions/fence-postgres-va-loc-truoc-stream.md), [may-chu-lon-va-app-store](../decisions/may-chu-lon-va-app-store.md)
