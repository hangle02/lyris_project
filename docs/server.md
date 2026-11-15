# Lyris trên máy chủ lớn và App Store (thiết kế, chưa code)

> **English summary.** After the course submission (15 Nov 2026) Lyris becomes a public hosted app on the web,
> the App Store and Google Play. Target (PO 4A): ~10k monthly users, a few hundred people chatting at once, easy
> to scale. Architecture: Cloudflare (TLS, CDN, WAF) → load balancer → N **stateless FastAPI** pods → **Postgres**
> (port of the SQLite migrations, append-only coin ledger kept by triggers + row locks) + **Redis** (session cache,
> distributed generation gate and story locks, rate limits, resumable SSE via Redis Streams) + a **Postgres-backed
> job queue** (`FOR UPDATE SKIP LOCKED`, the current `jobs` table) for extraction/summary/embeddings/ranking/payments
> → an **inference gateway** that routes each story to the same **vLLM** replica (open model `gemma4:12b`, FP8,
> `max-model-len 8192`, automatic prefix caching replaces Ollama raw prefill) → **S3-compatible storage** for images.
> Mobile (AI's choice): **Capacitor** wraps the existing React app with native plugins (StoreKit 2 / Play Billing,
> push, haptics, Keychain, Sign in with Apple), bearer-token auth, assets bundled in the binary. Payments (PO 5A):
> Apple IAP and Google Play Billing in the apps, VNPay/MoMo on the web; every receipt is verified server-side and
> posted idempotently into the same append-only coin ledger; refunds become negative entries. The local-first
> self-host mode (SQLite + Ollama, one process) keeps working behind the same interfaces.

- **Trạng thái:** thiết kế. Không có dòng code nào ở đây được làm trước ngày nộp bài. Bản đang chạy (một máy, SQLite,
  Ollama, [docs/deploy.md](deploy.md)) giữ nguyên và vẫn phải qua `verification/verify.sh`.
- **PO chốt** (2026-11-14, [raw](../wiki/raw/2026-11-14-server-lon-appstore.md),
  [trả lời](../wiki/raw/2026-11-14-server-lon-appstore-tra-loi.md)): 1A viết thiết kế bây giờ, code sau khi nộp ·
  2A máy chủ GPU riêng chạy model mở qua vLLM · 3 AI chọn cách làm app di động · 4A ~10 nghìn người dùng/tháng,
  vài trăm người chat cùng lúc · 5A IAP trên app, VNPay/MoMo trên web, chung một sổ coin.
- **Tính năng:** [F50](../wiki/features/F50-postgres.md) → [F62](../wiki/features/F62-nhap-du-lieu-tu-chay.md)
  (Giai đoạn: Kế hoạch, Phase "Máy chủ (sau khi nộp bài)"). Quyết định: §17.
- Người chơi trong tài liệu là `{{user}}`. Tên miền ví dụ: `lyris.example`, `api.lyris.example`.
- **Đã phản biện** (2026-11-14): 23 điểm kiến trúc và duyệt App Store/Play đã được xét; điểm nào nhận, điểm nào sửa lại
  hay bác (kèm lý do) ghi ở §21. Các mục dưới đây đã là bản sau phản biện.

## Mục lục

1. Mục tiêu và giới hạn · 2. Sơ đồ · 3. Bản đồ thành phần hiện tại → bản host · 4. Edge, API · 5. Postgres ·
6. Redis · 7. Hàng đợi việc nền · 8. Tầng suy luận (vLLM) · 9. Ảnh và kiểm duyệt · 10. Đăng nhập cho web và app ·
11. Thanh toán · 12. Số liệu và quan sát · 13. Bảo mật, quyền riêng tư, nơi lưu dữ liệu · 14. Sao lưu, môi trường,
CI/CD · 15. Sức chứa và chi phí · 16. App di động · 17. Quyết định · 18. Kế hoạch chuyển đổi theo giai đoạn ·
19. Chế độ tự chạy (local-first) · 20. Câu hỏi cho PO · 21. Phản biện đã áp dụng

---

## 1. Mục tiêu và giới hạn

| Mục tiêu (4A) | Con số thiết kế |
|---|---|
| Người dùng mỗi tháng (MAU) | 10.000 (thiết kế để lên 50.000 bằng cách thêm máy, không đổi kiến trúc) |
| Người dùng mỗi ngày (DAU) | ~3.000 (DAU/MAU 30 %) |
| Người đang chat cùng lúc lúc cao điểm (C) | 300 (19:00–24:00 giờ Việt Nam) |
| Một lượt mỗi người | ~75 giây (đọc + viết, docs/deploy.md §9 đo 60–90 giây) |
| Lượt sinh mỗi giây lúc cao điểm (λ = C / 75) | ~4 lượt/giây |
| Lượt mỗi tháng | ~2,7 triệu (3.000 DAU × 30 lượt × 30 ngày) |

Giới hạn giữ nguyên từ bản hiện tại:

- **Một context duy nhất: 8192 token** cho mọi lời gọi model ([cung-num-ctx](../wiki/decisions/cung-num-ctx.md)).
  Trên vLLM là `--max-model-len 8192`; prompt builder (`PromptBudget(num_ctx=8192)`) không đổi.
- Giọng văn và luật nội dung (khối A của system prompt, `prompt/templates/vi.py`) không đổi; model mở (2A).
- Không chữ kỹ thuật trên giao diện; chờ thì ba chấm; bận thì câu dễ hiểu
  ([an-chu-ky-thuat](../wiki/decisions/an-chu-ky-thuat.md), docs/auth.md §5.5).
- Coin: 6 coin mỗi lượt có chữ, giữ chỗ trước khi sinh, lỗi máy không mất coin (docs/coins.md §3).
- Bản tự chạy một máy (SQLite + Ollama) vẫn là chế độ được hỗ trợ (§19).

## 2. Sơ đồ

```
 iOS app (Capacitor)   Android app (Capacitor)   Trình duyệt / PWA
   assets đóng gói        assets đóng gói          lyris.example
        │  Bearer token        │  Bearer token          │  cookie __Host-lyris_session
        └──────────────┬───────┴────────────────────────┘
                       ▼
        Cloudflare: DNS, TLS, CDN (frontend/dist, ảnh công khai), WAF, chống DDoS, Turnstile
                       │  (SSE đi thẳng, có nhịp ": ping" mỗi 15 s)
                       ▼
        Load balancer L7 (idle timeout ≥ 300 s, health /api/healthz)
                       │
     ┌─────────────────┼──────────────────┐
     ▼                 ▼                  ▼
  API pod 1         API pod 2   …      API pod N        FastAPI, 1 tiến trình/pod, không trạng thái
     │  ▲               │                  │            (chat stream, coin, auth, studio, admin)
     │  └── Redis ◄─────┴──────────────────┘            phiên cache, cổng sinh, khoá story, rate limit,
     │      (Streams cho SSE nối lại, pub/sub)          hàng chờ lượt chat, cache
     │
     ├──► PgBouncer ──► Postgres (chính + standby, PITR)    dữ liệu, sổ coin, bảng jobs
     │   (transaction mode)  ▲   ▲
     │                       │   └── nối thẳng, không qua PgBouncer: Job migration, kênh LISTEN của worker
     │                       │ FOR UPDATE SKIP LOCKED
     │                  Worker pods (việc nền: trích xuất, tóm tắt, embed, prefill,
     │                  bảng xếp hạng, đối soát thanh toán, PostHog, dọn dẹp) + scheduler (dòng leader_lease)
     │                       │
     ├──► Inference gateway (thư viện trong API + worker; định tuyến dính theo story)
     │        ├──► vLLM replica A (GPU)  gemma4:12b FP8, max-model-len 8192, prefix caching
     │        ├──► vLLM replica B (GPU)
     │        └──► embed server (bge-m3)
     │
     ├──► Object storage S3 (avatars/, banners/, imports/) ── CDN (ảnh công khai) / URL ký (ảnh riêng)
     │
     └──► Bên ngoài: App Store Server API + Notifications V2, Google Play Developer API + RTDN (Pub/Sub),
          VNPay (IPN), MoMo (IPN), APNs/FCM (push), PostHog (số liệu, tuỳ chọn), email giao dịch
```

Mọi thứ trừ Cloudflare và dịch vụ bên ngoài nằm trong một mạng riêng (VPC). Chỉ load balancer có IP công khai.
vLLM, Postgres, Redis không bao giờ mở ra Internet.

## 3. Bản đồ: thành phần hiện tại → bản host

| Hiện tại (code thật) | Vì sao không chạy được nhiều máy | Bản host | Tính năng |
|---|---|---|---|
| `db/connection.py`: một `sqlite3` dùng chung, WAL, `busy_timeout` | Một file trên một máy | Postgres qua `psycopg` 3 + pool, PgBouncer | [F50](../wiki/features/F50-postgres.md) |
| `db/migrations/0001…0014` theo `PRAGMA user_version` | Cú pháp SQLite (FTS5, `strftime`, trigger `RAISE(ABORT)`) | Thư mục `db/migrations_pg/` song song, bảng `schema_migrations`; áp bằng một Job riêng nối thẳng Postgres (không qua PgBouncer) dưới `pg_advisory_lock` | F50 |
| `db/repo.py` (2.342 dòng), **một kết nối dùng chung** khoá bằng `threading.RLock`, `Repo.transaction()` = `BEGIN IMMEDIATE`; `coins/*`, `auth/*` nhận thẳng `sqlite3.Connection` (18 module `import sqlite3`, 21 chỗ `lastrowid`, 10 chỗ bắt lỗi `sqlite3.*`, 14 chỗ `BEGIN IMMEDIATE`) | Khoá trong tiến trình; một kết nối thì mỗi pod chạy tuần tự từng lệnh DB | Giữ một lớp `Repo`, thêm lớp dialect (`?`→`%s`, `strftime`→`now()`, `json_extract`→`jsonb`, `INSERT OR IGNORE`→`ON CONFLICT DO NOTHING`, `RETURNING id` thay `lastrowid`, ánh xạ lỗi); **kết nối lấy từ pool cho mỗi đơn vị công việc** (§5.5) | F50 |
| `coins/ledger.py` `post()`, `coins/holds.py` (BEGIN IMMEDIATE, chỉ mục một giữ chỗ mở) | Dựa vào SQLite tuần tự hoá mọi ghi | `SELECT … FROM coin_wallets WHERE account_id = %s FOR UPDATE` rồi kiểm và ghi; trigger chỉ thêm bằng PL/pgSQL; quyền DB thu hồi `UPDATE/DELETE` | F50 |
| `coins.release_stale()` lúc khởi động nhả MỌI giữ chỗ `held` | Pod mới khởi động sẽ nhả giữ chỗ của pod khác đang stream | Cột `lease_until` (30 s), pod đang sinh gia hạn mỗi 10 s; `hold_sweeper` mỗi 10 s nhả giữ chỗ hết hạn (lý do `restart`) → nhả trong **≤ 40 s** | F50, F51 |
| `auth/store.py` bảng `sessions` (sha256 token), cookie `HttpOnly` | Chạy được, nhưng mỗi request một lần đọc DB | Giữ bảng `sessions` ở Postgres (thu hồi được), cache Redis 60 s; app di động gửi `Authorization: Bearer` | F51 |
| `auth/middleware.py` CSRF: `X-Lyris: 1`, `Origin` = `Host`, từ chối `Sec-Fetch-Site: cross-site` | App Capacitor có origin `capacitor://localhost`, mọi request tới `api.lyris.example` là cross-site | Cookie: giữ luật cũ. Có `Authorization: Bearer` → **bỏ qua cookie hoàn toàn** và miễn cả kiểm `Origin` lẫn `Sec-Fetch-Site` (không có credential tự gửi thì không có CSRF), vẫn bắt `X-Lyris` | F51, F55 |
| `auth/ratelimit.py` (bảng `auth_attempts`, giữ chỗ trong BEGIN IMMEDIATE) | Đúng nhờ khoá ghi của SQLite | Giữ bảng (để kiểm toán), tuần tự hoá bằng `pg_advisory_xact_lock(hashtext(khoá))`; giới hạn chung theo IP/tài khoản ở Redis | F50, F51 |
| `auth/net.py` `client_ip()`: tin phần tử cuối `X-Forwarded-For` từ 127.0.0.1 | Sau Cloudflare + LB có hai chặng | `LYRIS_TRUSTED_PROXIES` (dải IP của LB) + `CF-Connecting-IP` chỉ khi peer là dải IP Cloudflare | F51 |
| `chat/gate.py` `GenerationGate` (asyncio, `LYRIS_CHAT_SLOTS`) | Mỗi pod một cổng riêng | Cổng phân tán ở Redis (Lua): vé đang chạy và chỗ trong hàng là phần tử có hạn nhịp tim (pod chết không làm rò chỗ), sức chứa đếm **theo từng replica**; giữ luật "mỗi tài khoản 1 lượt", FIFO, 120 s, sự kiện `waiting` | F51, F53 |
| `ChatService._locks` (asyncio.Lock mỗi story) | Như trên | Khoá Redis `lock:story:{id}` có token + TTL 30 s + nhịp tim **để tối ưu**; khoá thật (fence) là dòng giữ chỗ coin ở Postgres, khoá `FOR UPDATE` trong transaction lưu (§4.3) | F51 |
| `app.state.draft_lock`, `test_chat_lock`, `template_lock` (một khoá cho cả máy) | Như trên; và ở quy mô lớn không cần khoá cả máy | Bỏ khoá cả máy; dùng luật "mỗi tài khoản 1 lượt sinh" của cổng Redis | F51 |
| `api/sse.py` stream gắn với kết nối HTTP | Mất mạng di động hay app vào nền là mất câu trả lời | Lượt sinh tách khỏi kết nối, ghi delta vào Redis Stream `reply:{id}`; nối lại bằng `Last-Event-ID` ở pod bất kỳ | F51 |
| `jobs/queue.py` + `jobs/worker.py` (một asyncio task, bảng `jobs`, nhường lượt chat) | Một worker trong tiến trình API | Cùng bảng `jobs` ở Postgres, nhiều worker pod, `FOR UPDATE SKIP LOCKED`, `lease_until`, `priority`; nhường lượt chat bằng ưu tiên của vLLM | [F52](../wiki/features/F52-hang-doi-viec-nen.md) |
| `Worker.prefill` + `OllamaClient.prefill_prefix` (`/api/generate raw`, docs/phase3.md §10.6) | Cache prompt của một Ollama chỉ giữ một story | vLLM Automatic Prefix Caching + định tuyến dính theo story; prefill giữ nguyên ý tưởng (gửi phần đầu, `max_tokens=1`) tới đúng replica | [F53](../wiki/features/F53-cong-suy-luan-vllm.md) |
| `llm/base.py` `LLMClient` (Protocol), `llm/ollama.py`, `llm/fake.py` | (đã là giao diện) | Thêm `VllmClient` thoả cùng Protocol; `llm/render.py` dựng prompt một lần cho cả prefill và lượt thật | F53 |
| Embedding `bge-m3` qua Ollama, vector BLOB, cosine bằng Python, FTS5 | Đọc mọi vector của story qua mạng mỗi lượt | `pgvector` (`vector(1024)`) + `tsvector('simple')` có GIN; embed server riêng | F50, F53 |
| `studio/avatars.py` ghi PNG vào `LYRIS_AVATARS_DIR`; `/api/cards/{id}/avatar?v=` đọc file | Ổ đĩa của một máy | `BlobStore` (filesystem | S3). Route cũ giữ nguyên, trả `302` tới URL CDN (công khai) hoặc URL ký 5 phút (riêng) | [F54](../wiki/features/F54-luu-anh-s3.md) |
| `analytics/forwarder.py` (asyncio task, outbox trong DB) | Mỗi pod một forwarder chạy trùng | Việc định kỳ trong worker, khoá leader; outbox giữ nguyên ở Postgres | F52, [F58](../wiki/features/F58-quan-sat-slo.md) |
| `_auth_cleanup_loop`, `cleanup_temp`, `drop_orphan_copies` trong lifespan | Chạy ở mọi pod | Việc định kỳ của scheduler (một leader) | F52 |
| `system.py` `SystemMonitor` (đo máy + Ollama cho "Nâng cao") | Không còn "máy của chủ" | Chỉ ở chế độ tự chạy; bản host đọc số đo từ Prometheus cho trang quản trị | F58 |
| Vai trò `owner` (chủ máy), mã mời, "nhờ người quản lý đặt lại mật khẩu" | Một chủ máy cho một máy | Vai trò `staff` (nhiều người, MFA, nhật ký), đăng ký mở (cờ `LYRIS_SIGNUP=open|invite`), khôi phục qua email đã xác minh, Sign in with Apple/Google | [F61](../wiki/features/F61-dang-ky-cong-khai.md) |
| `compliance/account_data.py` xoá trong một transaction, xoá file sau commit | File ảnh trên máy | Xoá object S3 bằng job; thu hồi token Sign in with Apple; dữ liệu trong bản sao lưu tự hết sau 35 ngày | F54, F61 |
| `compliance/reports.py` báo cáo + "Ẩn nhân vật" | Đủ cho một máy | Thêm lọc đầu ra, chặn người dùng, hàng duyệt ảnh (App Store 1.2) | [F60](../wiki/features/F60-kiem-duyet-chan.md) |
| `coins/topup.py` mã nạp (chế độ thử, `test_mode: true`) | — | Thêm `payment_receipts`, `payment_orders`; kind sổ `purchase`, `purchase_refund`, `debt_repay` thêm bằng `INSERT` vào bảng tra `coin_kinds` (chỉ ở Postgres, §5.2) | [F56](../wiki/features/F56-iap-google-play.md), [F57](../wiki/features/F57-vnpay-momo.md) |
| `coins/missions.py` "Quảng cáo mẫu" (F45) thưởng coin | Nội dung giữ chỗ trong bản phát hành (App Store 2.1) | Ẩn ở bản host và app (`LYRIS_SAMPLE_ADS=off`); quảng cáo thật là quyết định riêng của PO (§20) | F55 |
| Caddy + systemd + một uvicorn (`docs/deploy.md`) | Một máy | Container (chỉ ở bản host), Kubernetes có quản lý, Helm, ba môi trường | [F59](../wiki/features/F59-trien-khai-ci.md) |
| PWA `manifest.webmanifest`, hash router `#/…`, `fetch("/api…")` tương đối | — | Giữ cho web; app Capacitor đóng gói `frontend/dist`, `API_BASE` tuyệt đối | [F55](../wiki/features/F55-app-ios-android.md) |

## 4. Edge và API

### 4.1 Edge (Cloudflare) và TLS

- DNS, chứng chỉ (Cloudflare edge + chứng chỉ origin giữa Cloudflare và LB, chế độ "Full (strict)"), HTTP/2 và HTTP/3.
- **CDN:** `frontend/dist` (`/assets/*` immutable, `index.html` `no-cache`), ảnh công khai (`img.lyris.example`).
- **WAF:** bộ luật có quản lý + luật riêng. Giới hạn theo IP chỉ là lưới thô với ngưỡng cao (`/api/auth/*` 120
  request/phút/IP), vì nhà mạng di động Việt Nam dùng NAT chung (CGNAT): hàng trăm người có thể cùng một IP. Giới hạn
  chính tính theo tài khoản / thiết bị / @handle đang thử (docs/auth.md §3.4, §6). `/api/payments/*/ipn` chỉ nhận dải IP
  của cổng thanh toán (VNPay, MoMo công bố) và luôn kiểm chữ ký ở app (dải IP chỉ là lớp thêm).
- **Turnstile** (CAPTCHA không gây khó chịu) ở đăng ký trên web (F61).
- **SSE qua Cloudflare:** proxy cắt kết nối không có byte nào trong 100 giây. Lượt chat có thể chờ cổng tới 120 giây
  trước sự kiện `start`, nên server gửi dòng chú thích `: ping` mỗi 15 giây (SSE bỏ qua dòng chú thích; `lib/sse.ts`
  đã bỏ qua đúng). Response SSE gửi `Cache-Control: no-cache, no-transform` và `X-Accel-Buffering: no`; luật nén
  (Compression Rules) của Cloudflare tắt cho `text/event-stream`, để proxy không gom hay nén delta.

### 4.2 API pods (FastAPI, không trạng thái)

- Một tiến trình uvicorn mỗi pod (`--workers 1`, như bây giờ), nhiều pod. Tối thiểu 3 pod ở 2 vùng sẵn sàng (zone).
  Một pod async giữ được hàng trăm kết nối SSE; giới hạn thật là GPU, không phải API.
- **Không trạng thái:** mọi thứ hiện nằm trong bộ nhớ tiến trình (bảng §3) chuyển sang Redis hoặc Postgres. Pod chết
  thì không mất gì ngoài các stream đang chạy trên nó; giữ chỗ coin của các stream đó được nhả khi hết lease (≤ 40 s:
  lease 30 s + sweeper mỗi 10 s).
- **Gọi DB:** `Repo` vẫn đồng bộ (sync) ở giai đoạn đầu để không viết lại 2.342 dòng; route đồng bộ chạy trong threadpool
  của FastAPI, chỗ nóng trong `ChatService` gọi qua `anyio.to_thread.run_sync`. Mỗi lời gọi mượn một kết nối từ pool
  (§5.5), nên các request của một pod chạy song song thật. Cỡ cố định mỗi pod: limiter thread của anyio 40 (mặc định),
  pool psycopg `min 4 / max 20`; tổng `max × số pod` ≤ `default_pool_size` của PgBouncer. Bản async là việc sau, không
  chặn ra mắt.
- **Health:** `/api/healthz` (sống, không cần đăng nhập, không lộ gì) và `/api/readyz` (Postgres + Redis trả lời trong
  200 ms). `/api/health` cũ vẫn cần đăng nhập.
- **Tắt êm (deploy):** nhận SIGTERM → `readyz` trả 503 → LB ngừng gửi request mới → chờ stream đang chạy xong (tối đa
  150 s = 120 s chờ cổng + một câu trả lời) → thoát. `terminationGracePeriodSeconds: 180`.
- **Phiên bản API:** app trên điện thoại cũ vẫn gọi API mới. Mọi thay đổi API là thêm trường (additive); bỏ trường cần
  hai bản phát hành. `GET /api/app/config` trả `min_supported_version` cho app di động (quá cũ thì màn "Cập nhật Lyris").

### 4.3 Lượt chat trên nhiều pod (thứ tự mới của `ChatService._run`)

1. Kiểm phiên, story thuộc tài khoản (như bây giờ).
2. **Cổng Redis** `reserve(account_id)`: tài khoản đang có lượt sinh khác → 409 như bây giờ (câu của docs/auth.md §5.5).
3. **Khoá story Redis** `lock:story:{id}` (token ngẫu nhiên, TTL 30 s, gia hạn mỗi 10 s). Không lấy được → 409 `Busy`.
   Khoá này chỉ để từ chối sớm và rẻ; nó **không** phải bảo đảm đúng (Redis failover sao chép không đồng bộ có thể làm
   mất khoá). Bảo đảm thật là bước 4 và bước 7.
4. Giữ chỗ coin `open_hold` (Postgres, khoá dòng ví) với `lease_until = now() + 30 s`. Thiếu coin → 402 trước byte SSE đầu.
   Chỉ mục duy nhất "một giữ chỗ mở mỗi tài khoản" là khoá thật: hai pod không thể cùng sinh cho một tài khoản.
5. Lưu lượt người chơi; tạo `reply_id`; trả SSE. Hết chỗ → sự kiện `waiting`, chờ FIFO trong hàng Redis (§6.3), quá
   120 s → `error` (câu cũ), nhả giữ chỗ lý do `queue_timeout`.
6. Gateway chọn replica (§8.4), stream. Delta đi qua **bộ lọc đầu ra theo đoạn** (§13, F60) trước khi tới client: chữ
   được gom tới hết câu (hoặc 24 token, cái nào tới trước), bộ phân loại chấm đoạn đó (~30–80 ms trên GPU), `safe` thì
   gửi cho client và `XADD reply:{reply_id}`; `unsafe` thì không gửi đoạn đó, dừng sinh, gửi câu lảng trong vai. Client
   không bao giờ nhận chữ bị gắn `unsafe`.
7. Một transaction: `SELECT … FROM coin_holds WHERE id = %s FOR UPDATE` (**fence**) → lưu câu trả lời → trừ coin → xếp
   job. Giữ chỗ còn `held` → `charge_hold` như cũ. Giữ chỗ đã bị `hold_sweeper` nhả (pod chậm vì GC hay Postgres chập
   chờn, lỡ hạn lease) → vẫn lưu câu trả lời (người chơi đã thấy nó trên màn) và trừ thẳng bằng `post()` với cùng
   `idem_key = chat:{hold_id}` nếu `số dư − giữ chỗ mở khác ≥ giá`; không đủ thì lưu không trừ, đếm
   `lyris_hold_lost_total` và cảnh báo khi > 0,1 % lượt. Sweeper cũng khoá dòng bằng `FOR UPDATE SKIP LOCKED`, nên không
   bao giờ nhả một giữ chỗ đang được trừ. Câu trả lời chỉ ghi khi tin cha của nó vẫn là cuối nhánh đang active (kiểm
   trong cùng transaction), để pod "sống lại" sau khi mất khoá không ghi đè lượt mới hơn.
8. Xếp job trích xuất trong cùng transaction (hàng đợi trong Postgres, §7) → không có chuyện lưu được tin mà mất job.
9. `finally`: nhả khoá story, nhả vé cổng, nhả giữ chỗ nếu chưa trừ.

**Ngắt kết nối (tạm chọn, đổi so với bây giờ):** client rớt mạng hay app vào nền thì lượt sinh **vẫn chạy tới hết**
(tối đa một câu trả lời), câu trả lời được lưu và trừ coin như bình thường; client mở lại thì nối tiếp bằng
`GET /api/stories/{id}/reply/{reply_id}/events` với `Last-Event-ID`, hoặc thấy câu trả lời đã lưu. Chỉ nút "Dừng"
(`POST /api/stories/{id}/stop`) mới dừng sinh. Lý do: trên điện thoại, mất kết nối 2 giây khi đi thang máy không được
làm mất câu trả lời đã trả coin. Bản tự chạy giữ hành vi cũ (ngắt = dừng). Câu hỏi cho PO ở §20.

**Nối lại khi pod gốc đã chết:** stream `reply:{id}` không bao giờ có `done`. Endpoint nối lại đọc Stream với chờ chặn
tối đa 15 s mỗi vòng; Stream không có mục mới **và** khoá story đã hết hạn **và** không có câu trả lời đã lưu cho
`reply_id` → gửi `error` (câu "Lượt này bị gián đoạn, bạn gửi lại nhé.") rồi đóng; giữ chỗ coin của lượt đó do sweeper
nhả (người chơi không mất coin). Test `test_reply_resume_after_origin_pod_died`.

## 5. Postgres

### 5.1 Chọn gì

- Postgres 16+ có quản lý (managed), một bản chính + một standby đồng bộ ở zone khác, PITR 35 ngày.
- Cỡ khởi đầu: 4 vCPU, 16 GB RAM, 200 GB SSD; PgBouncer **≥ 1.21** chế độ transaction (pool 100 kết nối thật cho 10+ pod).
- **Chế độ transaction của PgBouncer làm hỏng mọi thứ gắn với phiên**, nên:
  - Khoá phiên (`pg_advisory_lock`) chỉ dùng ở Job migration, chạy như một Kubernetes Job **nối thẳng** Postgres.
  - Leader của scheduler không dùng khoá phiên mà dùng dòng `leader_lease(name primary key, holder, until)` (§7.3):
    chạy được qua PgBouncer.
  - `LISTEN/NOTIFY`: mỗi worker giữ **một** kết nối thẳng riêng chỉ để `LISTEN jobs_ready` (NOTIFY gửi qua PgBouncer
    vẫn được). Mất kênh này thì worker vẫn poll mỗi 2 s.
  - Prepared statement: pool của app đặt `prepare_threshold=None` (psycopg 3 mặc định tự prepare sau 5 lần), hoặc bật
    `max_prepared_statements` của PgBouncer ≥ 1.21. Chọn cái thứ nhất (đơn giản, không phụ thuộc bản PgBouncer).
  - `pg_advisory_xact_lock` (khoá theo transaction) vẫn đúng qua PgBouncer, dùng cho `auth/ratelimit.py` (§5.3).
- Phần mở rộng: `pgvector` (ký ức theo nghĩa), `pg_trgm` (tìm nhân vật theo tên, tuỳ chọn), `citext` (handle).
- **Không ORM.** Giữ SQL tay trong `Repo` (đã có test bao quanh từng hàm), thêm một lớp dialect nhỏ. Viết lại bằng ORM là
  rủi ro lớn nhất có thể tránh ([quyết định](../wiki/decisions/postgres-giu-repo.md)).

### 5.2 Chuyển schema (từ `0001_init.sql` … `0014`)

Một file nền `db/migrations_pg/0001_baseline.sql` tương đương trạng thái SQLite sau migration mới nhất, rồi các file sau
đi song song: mỗi migration SQLite mới phải có bản Postgres cùng số (test `test_pg_and_sqlite_migrations_in_lockstep`).

| SQLite | Postgres |
|---|---|
| `INTEGER PRIMARY KEY` | `BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` (id tăng dần như cũ; `BY DEFAULT` để công cụ nhập F62 và sửa dữ liệu ghi được id, sau đó `setval`) |
| thời gian `TEXT` ISO (`strftime('%Y-%m-%dT%H:%M:%fZ','now')`) | `timestamptz(3) DEFAULT now()` (mili giây như chuỗi cũ, để con trỏ phân trang theo thời gian khớp); lớp dialect trả chuỗi ISO giống hệt cho code cũ |
| `coin_day TEXT 'YYYY-MM-DD'` giờ Việt Nam | `date`, tính bằng `(now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date`; psycopg trả `datetime.date` nên lớp dialect đổi về `str` `YYYY-MM-DD` |
| `accounts.handle … COLLATE NOCASE` (0005, 0008) | `handle citext UNIQUE` (hoặc chỉ mục duy nhất trên `lower(handle)`); mọi `WHERE handle = ?` giữ không phân biệt hoa thường |
| JSON trong `TEXT` (`value_json`, `extensions`, `payload`) | `jsonb` |
| `BLOB` (`token_hash`, `code_hash`) | `bytea` |
| `memories.embedding BLOB` float32 | `vector(1024)` (pgvector) + `embed_model text` |
| `memories_fts` FTS5 `remove_diacritics 0` + 3 trigger | cột sinh `tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED` + GIN. Cấu hình `simple` giữ dấu tiếng Việt như FTS5 hiện tại. Thứ hạng `bm25` và `ts_rank` khác nhau: chỉ so **tập** kết quả có dung sai, không so thứ tự |
| `CHECK (kind IN (…))` của `coin_ledger.kind`, `coin_holds.release_reason` | **bảng tra** `coin_kinds(kind text primary key)`, `hold_release_reasons(reason text primary key)` + khoá ngoại. Thêm giá trị = `INSERT` (chỉ thêm, qua được `test_migrations_additive_only`); baseline đã có sẵn `purchase`, `purchase_refund`, `debt_repay`, `queue_full`, `content_filtered`. Các `CHECK` khác (không bao giờ thêm giá trị) giữ `CHECK` |
| Chỉ mục một phần `WHERE status = 'held'` | giống hệt |
| `ON DELETE CASCADE / SET NULL` | giống hệt |
| `PRAGMA user_version` | bảng `schema_migrations(version int primary key, applied_at timestamptz)` |

**Sổ coin chỉ thêm** (0012, 0013) bằng ba lớp:

```sql
CREATE FUNCTION coin_ledger_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    -- Chỉ cascade khi xoá tài khoản: lúc trigger RI chạy, dòng accounts đã bị xoá.
    IF EXISTS (SELECT 1 FROM accounts WHERE id = OLD.account_id) THEN
      RAISE EXCEPTION 'coin_ledger chỉ thêm, không sửa';
    END IF;
    RETURN OLD;
  END IF;
  -- UPDATE: chỉ cho actor_id đổi thành NULL (ON DELETE SET NULL của người quản lý bị xoá).
  IF (NEW.actor_id IS NOT NULL AND NEW.actor_id IS DISTINCT FROM OLD.actor_id)
     OR (NEW.id, NEW.account_id, NEW.delta, NEW.balance_after, NEW.kind, NEW.idem_key, NEW.coin_day, NEW.created_at)
        IS DISTINCT FROM (OLD.id, OLD.account_id, OLD.delta, OLD.balance_after, OLD.kind, OLD.idem_key, OLD.coin_day, OLD.created_at)
     /* …và mọi cột tham chiếu còn lại, như 0012 */ THEN
    RAISE EXCEPTION 'coin_ledger chỉ thêm, không sửa';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER coin_ledger_guard BEFORE UPDATE OR DELETE ON coin_ledger
  FOR EACH ROW EXECUTE FUNCTION coin_ledger_guard();
REVOKE UPDATE, DELETE, TRUNCATE ON coin_ledger FROM lyris_app;   -- vai trò app; cascade chạy bằng quyền chủ bảng
```

`balance >= 0` và `balance_after >= 0` giữ bằng `CHECK`. Một việc nền hằng đêm so `coin_wallets.balance` với
`SUM(delta)` của sổ cho mọi ví, và `coin_wallets.debt` với `Σ shortfall` (cột của `payment_receipts`, §11.2) `− Σ` dòng
`debt_repay`; lệch một đồng là cảnh báo trang (page) người trực (§12.4).

**SQLite (bản tự chạy) không đổi `CHECK`:** SQLite không sửa được `CHECK` nếu không dựng lại bảng, mà dựng lại
`coin_ledger` (có trigger chỉ thêm) là rủi ro không cần. Các kind và lý do mới chỉ dùng ở bản host (thanh toán thật,
lọc đầu ra, báo bận sớm); bản tự chạy không bao giờ ghi chúng (báo bận vẫn là `queue_timeout` như bây giờ).
`KINDS` và `RELEASE_REASONS` trong code lấy theo dialect. Không cần ngoại lệ nào cho luật "migration chỉ thêm".

### 5.3 Transaction thay cho `BEGIN IMMEDIATE`

SQLite tuần tự hoá mọi ghi nên code hiện tại đúng "miễn phí". Trên Postgres (mức `READ COMMITTED` mặc định):

| Chỗ | Cách giữ đúng |
|---|---|
| `ledger.post()` | `INSERT … ON CONFLICT (idem_key) DO NOTHING RETURNING id` trước; không có dòng → đọc dòng cũ so nội dung (`IdemConflict` như cũ). Ví: `UPDATE coin_wallets SET balance = balance + %s WHERE account_id = %s AND balance + %s >= 0 RETURNING balance` (một câu, nguyên tử; 0 dòng → `InsufficientCoins`) |
| `holds.open_hold()` | `SELECT balance FROM coin_wallets WHERE account_id = %s FOR UPDATE` → tính số dư − giữ chỗ mở ≥ giá → `INSERT … RETURNING id` giữ chỗ; chỉ mục một phần chặn giữ chỗ thứ hai (bắt `UniqueViolation` → `HoldBusy`) |
| `charge_hold`, `release_hold` | `SELECT … FROM coin_holds WHERE id = %s FOR UPDATE` (fence, §4.3 bước 7) rồi `UPDATE … WHERE id = %s AND status = 'held'` |
| `hold_sweeper` | `SELECT id FROM coin_holds WHERE status = 'held' AND lease_until < now() FOR UPDATE SKIP LOCKED` → nhả `restart` |
| Hoàn tiền khi đang có giữ chỗ mở | Khoá ví → trừ tối đa `balance − Σ giữ chỗ mở`, phần thiếu vào `debt` (§11.1), để bất biến "số dư − giữ chỗ ≥ 0" không vỡ và `charge_hold` của lượt đang chạy không bị `InsufficientCoins` |
| `auth/ratelimit.py` giữ chỗ lần thử | `pg_advisory_xact_lock(hashtext('auth:' || kind || ':' || khoá))` đầu transaction (khoá theo transaction: đúng qua PgBouncer), rồi đếm + ghi như cũ |
| Quà đăng nhập ngày, nhiệm vụ, mốc sáng tác | Đã dùng `idem_key` duy nhất → `ON CONFLICT` |
| `claim_next_job` | `FOR UPDATE SKIP LOCKED` (§7) |
| Migration | Job riêng nối thẳng Postgres; `pg_advisory_lock(7130)` quanh cả lượt áp; đọc lại `schema_migrations` sau khi có khoá (cùng ý với `_apply` hiện tại). Pod API không tự áp migration |
| Xoá tài khoản (`account_data.py`) | Một transaction như cũ; thêm `SELECT … FROM accounts WHERE id = %s FOR UPDATE` để không chạy song song với nạp coin |

Deadlock: mọi transaction khoá theo một thứ tự cố định (ví → giữ chỗ → story). Lỗi `40P01`/`40001` được thử lại tối đa
3 lần trong `Repo.transaction()`.

### 5.4 Kích thước

~2,7 triệu lượt/tháng × 2 tin × ~5 KB (chữ + snapshot state) ≈ 27 GB/tháng cho `messages`. Năm đầu < 400 GB, vẫn một
máy. Khi `messages` vượt 500 GB: chia partition theo tháng của `created_at` (story cũ ít đọc). `analytics_events` giữ
180 ngày như bây giờ (xoá theo lô hằng đêm).

### 5.5 Mô hình kết nối (phạm vi thật của F50)

"Giữ `Repo`" không có nghĩa là chỉ sửa `repo.py`. Code hiện tại giả định **một** kết nối `sqlite3` dùng chung:

| Hiện tại | Bản Postgres |
|---|---|
| `Repo.conn` một kết nối, mọi method khoá `threading.RLock` | `Repo` giữ một pool (`psycopg_pool.ConnectionPool`); mỗi đơn vị công việc (một request, một job, một lượt chat) mượn một kết nối và gắn vào `contextvar`. `Repo.transaction()` mượn kết nối từ pool (hoặc dùng kết nối đang gắn), commit/rollback, trả lại. Bản SQLite giữ đúng cách cũ sau cùng giao diện |
| `coins/*`, `auth/*` nhận `sqlite3.Connection` (18 module `import sqlite3`) | Nhận một kiểu `DbConn` (Protocol nhỏ: `execute`, `fetchone`, `fetchall`, `rowcount`), hai bản cài đặt |
| `cur.lastrowid` (21 chỗ) | `INSERT … RETURNING id` (lớp dialect thêm vào câu SQL) |
| bắt `sqlite3.IntegrityError` / `OperationalError` (10 chỗ) | Lớp dialect ánh xạ sang `DbIntegrityError` / `DbBusy` chung (`UniqueViolation`, `40P01`, `40001`…) |
| `BEGIN IMMEDIATE` (14 chỗ) | `Repo.transaction()` + khoá dòng theo §5.3 |

Ước lượng: F50 là việc lớn nhất của cả kế hoạch (khoảng 3–4 tuần cho một người + AI), không phải "thêm lớp dialect".

## 6. Redis

Một Redis có quản lý (2 GB, bản sao, không cần lưu bền: mất Redis chỉ làm mọi người đăng nhập lại cache và hàng chờ
bắt đầu lại). Khoá theo tiền tố:

| Khoá | Dùng cho | TTL |
|---|---|---|
| `sess:{token_hash}` | cache phiên → `{account_id, role, status, expires_at}`; xoá khi đăng xuất, đổi mật khẩu, khoá tài khoản | 60 s |
| `sess_by_acct:{account_id}` (set) | mọi `token_hash` đang cache của một tài khoản, để khoá tài khoản / "đăng xuất mọi thiết bị" xoá hết `sess:*` của nó ngay | 60 s, gia hạn khi thêm |
| `gen:acct:{account_id}` | "tài khoản đang có một lượt sinh" (thay `GenerationGate._busy`) | 30 s, gia hạn mỗi 10 s |
| `lock:story:{story_id}` | khoá story khi sinh (thay `ChatService._locks`); chỉ để tối ưu, fence thật ở Postgres (§4.3) | 30 s, gia hạn |
| `genq:wait:{replica}` (ZSET, điểm = thời điểm vào hàng) + `genq:wait_hb` (ZSET, điểm = hạn nhịp tim) | hàng chờ theo replica (story dính replica), mỗi tài khoản tối đa một chỗ trong toàn cụm | phần tử quá hạn nhịp tim bị dọn |
| `genq:run:{replica}` (ZSET, phần tử = vé, điểm = hạn nhịp tim) | vé đang chạy trên từng replica vLLM, theo lớp (`chat`, `bg`) | phần tử quá hạn nhịp tim bị dọn |
| `reply:{reply_id}` (Stream) | delta của câu trả lời để nối lại SSE | `MAXLEN ~ 4000`, hết hạn 10 phút sau `done` |
| `rl:{rule}:{key}` | token bucket: `/api/events` 120/phút/thiết bị, ghi chung 60/phút/tài khoản; theo IP chỉ là lưới thô 1.200/phút/IP (CGNAT, §4.1) | theo cửa sổ |
| `route:story:{story_id}` | replica vLLM đang giữ cache của story (gợi ý, không bắt buộc) | 15 phút |
| `cache:public_cards`, `cache:hot_board` | danh sách Khám phá, bảng xếp hạng | 60 s |

### 6.1 Phiên

- Bảng `sessions` ở Postgres vẫn là nguồn sự thật (thu hồi được, "đăng xuất mọi thiết bị" giữ nguyên). Redis chỉ cache.
- Gia hạn trượt (`last_seen_at`, `expires_at`) ghi DB tối đa một lần mỗi 5 phút cho mỗi phiên.
- Khoá tài khoản, đổi mật khẩu, "đăng xuất mọi thiết bị": xoá dòng `sessions` rồi xoá mọi khoá trong
  `sess_by_acct:{id}`; không chờ 60 s hết hạn cache.
- Không dùng JWT: không thu hồi được trước hạn, và app không cần xác thực ngoài server của mình
  ([quyết định](../wiki/decisions/phien-token-cho-app.md)).

### 6.2 Khoá phân tán

`SET key token NX PX 30000`; nhả bằng Lua "xoá nếu token khớp"; pod đang giữ gia hạn mỗi 10 s. Pod chết → khoá tự hết
sau ≤ 30 s, story mở lại. Khoá Redis **không** nguyên tử với commit Postgres và có thể mất khi Redis failover, nên nó
chỉ là tối ưu; tính đúng nằm ở fence Postgres (§4.3 bước 4 và 7).

### 6.3 Cổng sinh phân tán và hàng chờ công bằng

- **Sức chứa** đếm **theo từng replica**: replica `r` nhận tối đa `chat_capacity[r]` vé lớp `chat` (gateway đọc mỗi
  5 s, §8.6) và tối đa 30 % số đó cho lớp `bg` (việc nền, chỉ khi hàng `chat` rỗng). Bộ đếm toàn cụm không bảo đảm
  được "mỗi replica ≤ `max-num-seqs`" của §8.5, vì story dính một replica (§8.4).
- **Không có bộ đếm trần, chỉ có phần tử có hạn.** Mỗi vé đang chạy là một phần tử của `genq:run:{replica}`, mỗi chỗ chờ
  là một phần tử của `genq:wait:{replica}` + `genq:wait_hb`; điểm là hạn nhịp tim `now + 30 s`, pod gia hạn mỗi 10 s. Pod chết thì
  phần tử của nó hết hạn và bị dọn: không rò sức chứa, không có "phần tử ma" đứng mãi đầu hàng.
- `admit.lua` (một script, nguyên tử, nhận `replica` gateway đã chọn):
  1. `ZREMRANGEBYSCORE genq:run:{r} -inf now`; với `genq:wait_hb` cũng vậy và xoá các phần tử đó khỏi `genq:wait:{r}`.
  2. Tài khoản đã có `gen:acct` → `busy`.
  3. `ZCARD genq:run:{r} < capacity[r]` và tài khoản là đầu hàng (hoặc hàng rỗng) → `ZADD genq:run:{r}`, xoá khỏi hàng,
     nhận.
  4. Không thì `ZADD genq:wait:{r} NX now account` + `ZADD genq:wait_hb (now + 30 s) account`, trả vị trí.
  Pod chờ nhận tín hiệu pub/sub `genq:wake` (mỗi lần có lượt xong) **hoặc** hết 2 s, rồi thử lại (pub/sub mất tin
  không làm kẹt); quá 120 s → bỏ (`GateTimeout`, câu cũ).
- Chờ ở replica của story quá 5 s mà replica khác còn chỗ → gateway chuyển chỗ chờ sang đó (tràn tải, §8.4; giữ thời
  điểm vào hàng cũ), chấp nhận đọc lại cả prompt một lần thay vì chờ.
- Script Lua dùng khoá có cùng hash tag (`{genq}`) để chạy được trên Redis Cluster nếu sau này cần.
- Test `test_redis_gate_dead_waiter_and_dead_runner_do_not_leak` (F51): pod chết khi đang chờ và khi đang sinh; sau
  ≤ 40 s một tài khoản khác được nhận ngay.
- **Công bằng:** mỗi tài khoản tối đa một lượt sinh và một chỗ trong hàng, nên FIFO đã công bằng giữa người dùng.
  Việc nền xen kẽ theo tài khoản như docs/auth.md §5.3, và mỗi tài khoản tối đa 50 job `queued` (`state/rebuild` của một
  người không chặn người khác).
- **Áp lực ngược (backpressure):** ước lượng thời gian chờ = vị trí × thời gian một lượt trung bình / sức chứa. Ước lượng
  > 120 s thì trả bận ngay (không bắt người dùng chờ 2 phút rồi mới báo), câu "Lyris đang bận. Tin của bạn đã lưu, hãy
  thử lại sau ít phút.", giữ chỗ coin được nhả. Sự kiện `reply_failed{reason: queue_full}` cho số liệu.
- Giao diện không đổi: `waiting` → ba chấm + "Có người khác đang trò chuyện. {Tên} sẽ trả lời ngay sau."

## 7. Hàng đợi việc nền

### 7.1 Chọn gì ([quyết định](../wiki/decisions/hang-doi-postgres.md), AI chọn)

**Giữ bảng `jobs` ở Postgres** và chạy nhiều worker lấy job bằng `FOR UPDATE SKIP LOCKED`, đánh thức bằng
`LISTEN/NOTIFY` (kênh LISTEN nối thẳng Postgres, không qua PgBouncer, §5.1; mất kênh thì poll mỗi 2 s). Không dùng
Celery/RQ/arq/Dramatiq trên Redis. Ngữ nghĩa là **ít nhất một lần** (at-least-once), không phải đúng một lần: mọi
handler phải idempotent (§7.2).

| Tiêu chí | Postgres `jobs` (chọn) | Celery / RQ / arq trên Redis |
|---|---|---|
| Xếp job cùng transaction với việc lưu tin nhắn | Có: không bao giờ "lưu tin mà mất job" hay "job chạy cho tin đã rollback" | Không: ghi hai nơi, cần outbox riêng |
| Ngữ nghĩa hiện có (huỷ job khi message hết active, xen kẽ theo tài khoản, `requeue` khi bị nhường) | Giữ nguyên SQL và test của `jobs/queue.py`, `test_jobs.py` | Viết lại |
| Lưu lượng cần | ~4–10 job/giây lúc cao điểm; Postgres xử lý hàng nghìn/giây | Thừa sức |
| Thêm hạ tầng | Không | Thêm Redis bền + broker |
| Chế độ tự chạy | Cùng code chạy trên SQLite (worker trong tiến trình như bây giờ) | Hai đường code |

Khi nào đổi: > 500 job/giây kéo dài, hoặc cần lịch phức tạp nhiều bước. Ở 4A còn cách xa hai mức này.

### 7.2 Bảng `jobs` mở rộng

Thêm cột: `account_id` (khỏi join `stories`), `priority smallint NOT NULL DEFAULT 5` (0 cao nhất),
`run_after timestamptz NOT NULL DEFAULT now()` (để `NULL` thì `run_after <= now()` không bao giờ đúng và job nằm mãi),
`lease_until timestamptz`, `worker_id text`, `payload jsonb`. Kind mới: `prefill`, `hot_board` (bảng xếp hạng của
workflow khác, chạy theo lịch), `posthog_flush`, `payment_reconcile`, `payment_refund_poll`, `image_scan`,
`blob_delete`, `account_purge`, `cleanup_auth`, `ledger_audit`.

```sql
-- claim: job sẵn sàng, ưu tiên cao nhất, xen kẽ theo tài khoản (khác tài khoản job vừa chạy nếu có)
UPDATE jobs SET status = 'running', lease_until = now() + interval '90 seconds', worker_id = %(w)s,
                attempts = attempts + 1
 WHERE id = (SELECT id FROM jobs
              WHERE status = 'queued' AND run_after <= now()
              ORDER BY priority, (account_id = %(last)s), id
              FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *;
```

- Worker gia hạn `lease_until` mỗi 30 s; job `running` quá hạn lease (worker chết) quay về `queued` (thay
  `reset_running_jobs` lúc khởi động).
- **Hoàn tất có fence:** `UPDATE jobs SET status = 'done' … WHERE id = %s AND worker_id = %s AND attempts = %s`; 0 dòng
  nghĩa là job đã bị lấy lại sau khi hết lease (worker chậm), worker bỏ kết quả của mình. Vì một job vẫn có thể chạy hai
  lần (lần đầu chậm, lần hai sau khi hết lease), mọi handler phải idempotent: trích xuất ghi theo `message_id`
  (`ON CONFLICT`), tóm tắt theo khoảng tin, đối soát thanh toán theo `idem_key`, `blob_delete` xoá object đã mất vẫn OK.
- Huỷ job khi message hết active: giữ logic `_Cancelled` hiện tại.
- Nhường lượt chat: bây giờ worker huỷ job khi có stream (`JobQueue.streaming`) vì chỉ có một GPU. Bản host: gửi job
  với `priority` thấp của vLLM (§8.5) và lớp `bg` của cổng (§6.3); không huỷ job đang chạy.

### 7.3 Lịch (scheduler)

Một vòng lặp trong mỗi worker pod; chỉ pod đang giữ dòng **`leader_lease`** mới xếp việc định kỳ (leader). Không dùng
khoá phiên `pg_try_advisory_lock`: qua PgBouncer chế độ transaction, khoá phiên dính vào một kết nối thật bất kỳ và có
thể "mất" hay "được" sai (§5.1).

```sql
INSERT INTO leader_lease (name, holder, until) VALUES ('scheduler', %(me)s, now() + interval '30 seconds')
ON CONFLICT (name) DO UPDATE SET holder = EXCLUDED.holder, until = EXCLUDED.until
 WHERE leader_lease.until < now() OR leader_lease.holder = EXCLUDED.holder
RETURNING holder;            -- có dòng = mình là leader (gia hạn mỗi 10 s)
```

Mỗi việc định kỳ xếp với cột mới `slot text` và chỉ mục duy nhất `(kind, slot)` theo khung giờ
(`posthog_flush` + `2026-11-20T19:00:10`, `INSERT … ON CONFLICT DO NOTHING`), nên hai leader chồng nhau vài giây vẫn
không xếp trùng. Việc định kỳ: `hot_board` (theo lịch của F46), `posthog_flush` mỗi 10 s, `cleanup_auth` mỗi
giờ, `payment_reconcile` mỗi 15 phút cho đơn treo và hằng ngày cho đối soát, `payment_refund_poll` (Google voided
purchases, dự phòng cho RTDN) mỗi giờ, `ledger_audit` 03:00, `hold_sweeper` mỗi 10 s (nhả giữ chỗ hết lease), xoá
`analytics_events` > 180 ngày.

## 8. Tầng suy luận: vLLM trên GPU riêng (PO 2A)

### 8.1 Model và cấu hình ([quyết định](../wiki/decisions/suy-luan-vllm.md))

- **Model:** đúng trọng số đang chạy (`gemma4:12b`), lấy bản gốc safetensors (không lấy file GGUF của Ollama). Sau này:
  LoRA tự train (F41) phục vụ bằng `--enable-lora` (nhiều adapter trên một model gốc, chọn theo request; A/B mù).
  Khoá prefix cache gồm cả adapter: A/B chia đôi tỉ lệ trúng cache của nhóm thử, nên A/B gán **theo story** (cả story
  một adapter) và tính phần cache mất đi vào bài tải. Trước khi dùng thương mại và trước khi fine-tune: kiểm giấy phép
  trọng số gemma4 (điều khoản dùng, danh sách cấm, nghĩa vụ ghi nguồn) — câu hỏi luật ở §20.
- **Lượng tử hoá:** FP8 (W8A8) trên GPU có FP8 (H100, L40S, L4): chất lượng gần bf16, nửa bộ nhớ. AWQ 4-bit chỉ khi buộc
  dùng GPU nhỏ, và phải qua bộ chấm `harness/run_eval.py` bằng hoặc hơn bản hiện tại trước khi dùng. Mốc so sánh là bản
  đang chạy thật: **GGUF đã lượng tử hoá của Ollama**, nên báo cáo eval ghi rõ "FP8 trên vLLM so với GGUF trên Ollama".
- **Lệnh mẫu:** `vllm serve <đường dẫn model> --max-model-len 8192 --enable-prefix-caching --kv-cache-dtype fp8
  --scheduling-policy priority --max-num-seqs 64 --generation-config vllm --api-key $VLLM_KEY --disable-log-requests`
  (`--disable-log-requests`: không ghi chữ của người dùng vào log; `--generation-config vllm`: không lấy mặc định lấy
  mẫu từ `generation_config.json` của model, mọi tham số do `VllmClient` gửi rõ, §8.2). Ghim đúng một phiên bản vLLM;
  đổi phiên bản là một thay đổi phải qua eval.
- **Bộ quản lý KV lai phải bật:** Gemma xen lớp cửa sổ trượt và lớp toàn cục; vLLM V1 cấp KV riêng cho hai loại lớp
  (hybrid KV cache manager). Tắt nó (hay chạy bản cũ) thì lớp cửa sổ trượt chiếm KV như lớp toàn cục và số phần đầu story
  giữ được giảm nhiều lần. Kiểm trong log khởi động của bản đã ghim.
- **Context 8192 không đổi:** prompt builder đã cắt theo 8192; vLLM từ chối (400) request có `prompt + max_tokens` >
  8192 thay vì cắt lặng lẽ, nên `VllmClient` đặt `max_tokens` theo số token thật (§8.2).
- **Đầu ra JSON** (`chat_json`: trích xuất, gợi ý, viết nháp): structured output của vLLM thay cho `format` của Ollama.
  Tên tham số trên `/v1/completions` đổi theo phiên bản (`guided_json` ở bản cũ, `structured_outputs` ở bản mới;
  `response_format` không chắc có trên `/v1/completions`): dùng đúng tên của bản đã ghim, có test hợp đồng với server
  giả. Giữ nguyên bước thử lại 1 lần khi JSON hỏng.
- **Lý luận (`think`):** Lyris tự dựng prompt nên **không** có tham số chat template nào ở đây. Tắt suy nghĩ nằm trong
  `llm/render.py`: generation prompt là `<|turn>model\n<|channel>thought\n<channel|>` (khối suy nghĩ rỗng), y như bản
  Ollama hiện tại.

### 8.2 `VllmClient` thoả `LLMClient`

- `chat_stream`: gọi `/v1/completions` (stream) với **prompt do Lyris tự dựng** bằng `llm/render.py` (renderer của
  gemma4), không gọi `/v1/chat/completions`. Lý do: phần đầu gửi trước (prefill) và prompt thật phải trùng **từng byte**
  thì mới trúng cache; tự dựng một lần ở một chỗ thì không phụ thuộc chat template của server. Test
  `test_vllm_prompt_equals_render_prefix_plus_turn` khoá điều này.
- **Không BOS đôi, gửi token id:** `render.py` đã mở đầu bằng `<bos>`, còn `/v1/completions` khi nhận chuỗi sẽ tự thêm
  BOS. `VllmClient` tự tokenize (tokenizer của đúng model, nạp một lần) và gửi `prompt` là **danh sách token id**; prefill
  và lượt thật vì thế trùng nhau tới từng token, không phụ thuộc cách server tách chữ. Đường dự phòng (gửi chuỗi) phải
  kèm `add_special_tokens: false`. Test `test_vllm_no_double_bos`.
- **`max_tokens` theo token thật:** `estimate_tokens` (3 ký tự/token) chỉ là ước lượng cho prompt builder. Có token id
  rồi thì đếm thật: `max_tokens = min(reply_tokens, 8192 − len(prompt_ids))`; còn < 64 token chỗ thì builder cắt thêm
  lịch sử rồi dựng lại (không bao giờ để vLLM trả 400).
- **Tham số lấy mẫu cố định, giống Ollama:** `options` hiện có chỉ gửi `temperature` 0,8, `top_p` 0,95, `num_predict`;
  phần còn lại Ollama lấy từ Modelfile và mặc định của nó (`top_k`, `repeat_penalty`, `repeat_last_n`, `min_p`…). Bảng ánh
  xạ nằm trong `VllmClient` và ghi đủ mọi tham số (lấy số thật từ lớp `params` trong manifest của model ở thư mục model của Ollama khi
  làm, không đoán, không cần chạy model): `temperature`, `top_p`, `top_k`, `min_p`, `max_tokens` ← `num_predict`, `stop`. `repeat_penalty` của Ollama
  (chia logit của token đã gặp trong `repeat_last_n` token cuối) và `repetition_penalty` của vLLM (trên toàn bộ prompt +
  đầu ra) **không cùng công thức**: chỉ đặt `repetition_penalty` khác 1,0 nếu eval cho thấy cần. Test
  `test_vllm_sampling_params_match_ollama_profile`.
- `chat_json`: `/v1/completions` + tham số structured output của bản vLLM đã ghim (§8.1).
- `embed`: gọi embed server (§8.8).
- Lỗi ánh xạ sang `LLMError.kind` có sẵn (`connect`, `timeout`, `server`, `output`); `friendly()` giữ câu dễ hiểu.
- `FakeLLM` không đổi: mọi test và bot vẫn chạy trên LLM giả.

### 8.3 Cache prompt: từ "prefill raw" của Ollama sang prefix caching của vLLM

Hiện tại (docs/phase3.md §10.6): Ollama chỉ giữ cache của **một** prompt; worker gửi trước phần đầu prompt của lượt kế
(`/api/generate raw`) cho **một** story đang chơi; đo được lượt thường 4,2–5,3 s thay vì 12–47 s.

Trên vLLM, Automatic Prefix Caching băm KV theo khối 16 token và giữ **mọi** khối còn chỗ (LRU), cho mọi người cùng lúc:

| Phần prompt | Ai dùng chung | Kết quả trên vLLM |
|---|---|---|
| Khối A của system (luật, `prompt/templates/vi.py`) | Mọi story cùng ngôn ngữ | Luôn trúng cache trên mọi replica (vài trăm token đầu) |
| Khối B, C (nhân vật, persona, bối cảnh, tóm tắt) + lịch sử | Một story | Trúng nếu lượt trước của story chạy trên **cùng replica** và chưa bị đẩy ra |
| Lượt người chơi mới + ghi chú F | Một lượt | Luôn phải đọc (~300–600 token) |

- **Giữ ý tưởng prefill:** sau job trích xuất của một lượt, worker gửi `prefill` (prompt = `next_prompt_prefix(story)`,
  `max_tokens=1`, `priority` thấp) tới **đúng replica của story**. Giữ luật trung vị độ dài lượt người chơi
  (`_prefill_user_chars`). Chỉ prefill story có lượt trong 10 phút gần nhất.
- **Không còn "chỉ một story":** bộ nhớ KV của một H100 (FP8, ~55 GB trống) giữ được khoảng 100+ phần đầu story 8k token
  cùng lúc (ước tính theo kiến trúc lai cửa sổ trượt/toàn cục của Gemma, cần bộ quản lý KV lai §8.1; đo lại với
  `gemma4:12b`). Lúc cao điểm mỗi replica có ~100 story đang chơi **cộng** các chuỗi đang chạy, nên con số này sát
  ngưỡng. Phương trình ngân sách KV phải thoả cho mỗi replica (số đo thật ở bài tải):
  `story_mỗi_replica × token_đầu_tb × byte_KV_mỗi_token ≤ 0,7 × KV_trống` (30 % còn lại cho chuỗi đang chạy và trích
  xuất). Không thoả → thêm replica, hoặc chỉ prefill story có lượt trong 5 phút.
- **Cửa sổ trượt:** vLLM V1 quản lý KV riêng cho lớp cửa sổ trượt và lớp toàn cục. Cần kiểm trên đúng bản vLLM dùng:
  tỉ lệ trúng cache (`vllm:prefix_cache_hits / vllm:prefix_cache_queries`) ≥ 70 % ở bài tải §15 và TTFT lượt thường
  p50 ≤ 1,5 s. Không đạt → giữ prefill như trên (vẫn có ích) và báo PO trước khi ra mắt.
- **Trích xuất dùng chung phần đầu của story (tạm chọn):** prompt trích xuất (~3.000 token) hiện có system riêng nên
  không trúng cache và là phần đọc prompt lớn nhất lúc cao điểm (§15.1). Bản host dựng prompt trích xuất bằng **chính
  phần đầu của lượt chat** (system + lịch sử, trùng từng token) rồi đặt chỉ dẫn trích xuất ở cuối, nên phần lớn trúng
  cache trên cùng replica. Đổi cấu trúc prompt có thể đổi chất lượng trích xuất, nên chỉ bật khi kịch bản `f10-ky-uc`
  của `harness/run_eval.py` không kém bản cũ; không thì trích xuất mỗi 2 lượt. Chỉ tiêu mới: tỉ lệ trúng cache của prompt
  trích xuất ≥ 60 %.

### 8.4 Định tuyến dính theo story (gateway)

- Gateway là thư viện Python dùng chung trong API và worker (không phải dịch vụ riêng ở giai đoạn đầu):
  `replica = HRW(story_id, replicas_khoẻ)` (rendezvous hashing): thêm/bớt một replica chỉ dời ~1/N story.
- **Tràn tải:** replica của story có `num_requests_waiting > 4` hoặc `gpu_cache_usage > 0,95` → chọn replica ít tải
  nhất (chấp nhận đọc lại cả prompt một lần), ghi `route:story:{id}` sang replica mới.
- Mọi lời gọi của một story (chat, trích xuất, tóm tắt, gợi ý, prefill) đi cùng replica.
- Không dùng router ngoài (vLLM production-stack, llm-d) ở 4A; xem lại khi > 8 replica.

### 8.5 Ưu tiên và hàng chờ trong vLLM

`--scheduling-policy priority`: lượt chat `priority=0`, gợi ý `1`, viết nháp/chat thử `2`, trích xuất/tóm tắt `5`,
prefill `9`. vLLM xếp request ưu tiên cao trước khi có hàng chờ; cổng Redis (§6.3) đếm vé **theo từng replica** và giữ
số request mỗi replica ≤ `max-num-seqs` để hàng chờ nằm ở Redis (nơi có công bằng và câu báo bận), không nằm mù trong
vLLM. Prefill và trích xuất cũng lấy vé lớp `bg` của đúng replica.

### 8.6 Tự co giãn

- Số đo: `vllm:num_requests_waiting`, `vllm:gpu_cache_usage_perc`, TTFT p95, độ dài `genq`.
- Thêm replica khi `genq` > 0 kéo dài 2 phút hoặc TTFT p95 > 4 s trong 5 phút; bớt khi sức dùng < 30 % trong 30 phút.
  Tối thiểu 2 replica lúc cao điểm (N+1), 1 lúc đêm khuya (01:00–07:00). **Đêm khuya không có dự phòng:** replica duy
  nhất chết thì chat ngừng 3–8 phút tới khi GPU mới lên; người chơi thấy câu bận dễ hiểu, không mất coin. Ghi rõ trong
  SLO (§12.3). Thuê cố định theo tháng (§15.3) thì không có lý do bớt xuống 1, giữ 2.
- GPU mới cần 3–8 phút (máy + nạp ~13 GB trọng số). Vì vậy: **tăng theo lịch** trước giờ cao điểm Việt Nam (18:30) và
  trọng số để sẵn trên ổ NVMe/ảnh máy của node GPU, không tải mỗi lần.
- `chat_capacity` của replica = số lượt chat song song mà vẫn đạt SLO (§12.3), đo bằng bài tải (§15), không đoán.

### 8.7 Chi phí mỗi lượt so với giá 6 coin

Xem §15.3. Tóm lại: GPU ~30–45đ mỗi lượt ở mức dùng thực tế; 6 coin bán ra 480–600đ (theo gói). Lượt trả tiền lãi; bài
toán thật là lượt miễn phí (quà 300 coin, +60/ngày, nhiệm vụ tới 30/ngày).

### 8.8 Embedding

`bge-m3` (1024 chiều) qua vLLM chế độ embed (hoặc Text Embeddings Inference) trên một replica nhỏ hay ghép chung một
GPU chat (model 0,6 B). Job `embed` theo lô 32 như bây giờ. Không có embed server → tìm theo từ khoá (`tsvector`), như
bản hiện tại khi không cài `bge-m3`.

## 9. Ảnh: object storage và kiểm duyệt

- `BlobStore` (giao diện mới, hai bản: `FilesystemBlobStore` cho bản tự chạy, `S3BlobStore` cho bản host, S3-compatible).
- **Tải lên:** client gửi ảnh cho API như bây giờ (≤ 8 MB); `studio/avatars.normalize_image` (Pillow, xoay EXIF, bỏ
  metadata, thu nhỏ 768/1500×500, chặn bom giải nén) giữ nguyên; kết quả PNG ghi lên S3 bằng khoá
  `avatars/{loại}/{id}-{8 hex}.png`. Ảnh tạm khi nhập card: `tmp/{account}/{token}.png`, quy tắc vòng đời xoá sau 1 ngày.
- **Phục vụ:** route cũ (`/api/cards/{id}/avatar?v=…`, avatar persona, tài khoản, ảnh bìa) giữ nguyên kiểm quyền rồi trả
  `302`: ảnh của nhân vật công khai và avatar tài khoản → URL CDN công khai (tên có hash, `immutable`); ảnh riêng (persona,
  nhân vật riêng) → URL ký 5 phút, và response `302` đó mang `Cache-Control: private, no-store` (cache `302` lâu hơn hạn
  URL ký thì trình duyệt sẽ đi tới URL đã hết hạn và ảnh vỡ). Frontend không đổi.
- **Xoá:** `pop_orphan_avatars`/xoá tài khoản xếp job `blob_delete` sau commit (S3 không nằm trong transaction).
- **Kiểm duyệt ảnh (F60):** ảnh của nhân vật **công khai** và avatar/ảnh bìa tài khoản (người khác thấy) qua job
  `image_scan` **trước khi** công khai: (1) so hash ảnh lạm dụng trẻ em đã biết bằng một **API đồng bộ** (PhotoDNA Cloud
  khi được cấp, hoặc một nhà cung cấp quét hash có hợp đồng; tạm chọn ở G6). Công cụ quét CSAM của Cloudflare **không**
  dùng làm cổng được: nó chỉ quét ảnh đã phục vụ qua CDN, tức là sau khi công khai; nó chỉ là lớp thứ hai. (2) bộ phân
  loại ảnh nhạy cảm chạy trên GPU/CPU của mình. Nghi vấn → không công khai, vào hàng duyệt của staff; khớp hash CSAM →
  khoá tài khoản và quy trình báo cơ quan chức năng (docs/compliance.md). Ảnh riêng không ai khác thấy thì không quét nội
  dung (chỉ kiểm định dạng).
- Gửi ảnh trong chat (F38) dùng cùng `BlobStore` khi làm.

## 10. Đăng nhập cho web và app

| | Web (PWA) | App Capacitor |
|---|---|---|
| Origin | `https://lyris.example` (API cùng tên miền, `/api`) | `capacitor://localhost` (iOS), `https://localhost` (Android); API ở `https://api.lyris.example` |
| Mang phiên | Cookie `__Host-lyris_session` (`HttpOnly`, `Secure`, `SameSite=Lax`) như bây giờ | `Authorization: Bearer <token>`; token lưu ở Keychain (iOS) / Keystore (Android) qua plugin native nhỏ; không lưu ở `localStorage` |
| CSRF | `X-Lyris: 1` + `Origin` = `Host` + từ chối `Sec-Fetch-Site: cross-site` (giữ) | Có `Authorization: Bearer` → bỏ qua cookie hoàn toàn (kể cả cookie lạc), miễn kiểm `Origin` **và** `Sec-Fetch-Site` (mọi request từ `capacitor://localhost` tới `api.lyris.example` đều là cross-site); vẫn bắt `X-Lyris` |
| CORS | Không cần | Cho đúng hai origin trên, `Authorization` + `X-Lyris`, không `credentials` |
| Token | Cùng bảng `sessions`, cùng hạn trượt 30 ngày / tối đa 180 ngày | Như bên trái; `device_label` "Lyris iOS · iPhone". Token chỉ trả trong body khi đăng nhập có `client: "native"` (web không bao giờ thấy token) |

Vì sao không cookie trong app: WKWebView chặn cookie bên thứ ba (origin app ≠ tên miền API), nên cookie không đi ổn định.
Test `test_bearer_token_auth_and_csrf` (F51): Bearer kèm `Sec-Fetch-Site: cross-site` → 200; cookie kèm
`Sec-Fetch-Site: cross-site` → 403 `csrf`.

**Đăng ký công khai (F61):**
- `LYRIS_SIGNUP=open` (bản host) hoặc `invite` (mặc định của bản tự chạy, như bây giờ).
- Thêm email **tuỳ chọn, đã xác minh** để tự khôi phục mật khẩu (bây giờ chỉ "nhờ người quản lý"). Không bắt buộc email
  để giữ "thu thập tối thiểu".
- **Sign in with Google** trên web và Android; **Sign in with Apple** trên iOS. App Store 4.8 (bản từ 2024) yêu cầu: app
  có đăng nhập bên thứ ba thì phải có thêm **một cách đăng nhập tương đương bảo vệ riêng tư** (chỉ lấy tên + email, cho
  ẩn email, không theo dõi quảng cáo). Sign in with Apple thoả luật này; nó không còn là "bắt buộc" nguyên văn, nhưng là
  cách đơn giản nhất. Lyris giữ đăng nhập @handle + mật khẩu làm cách chính; Apple/Google là thêm.
- **Sign in with Apple đúng cách:** server đổi `authorization code` lấy `refresh_token` (endpoint `/auth/token` của
  Apple) và lưu mã hoá; không có `refresh_token` thì không thu hồi được khi xoá tài khoản. Tài khoản tạo bằng Apple trên
  iOS phải đăng nhập được ở web và Android: web có "Tiếp tục với Apple" (Sign in with Apple JS qua Services ID), và
  trong `#/me` người dùng đặt được mật khẩu cho @handle. Test `test_apple_account_signs_in_on_web`.
- Xoá tài khoản đã liên kết Apple: gọi Apple REST API thu hồi token bằng `refresh_token` đã lưu (yêu cầu của Apple).
- **Chống tạo tài khoản hàng loạt để lấy 300 coin** (định danh thiết bị phải sống qua cài lại app):
  - iOS: **DeviceCheck** (2 bit mỗi thiết bị do Apple giữ, còn sau khi cài lại): bit 0 = "thiết bị đã nhận quà tạo tài
    khoản". Khoá App Attest **không** dùng làm định danh (đổi khi cài lại), chỉ để chứng minh request đến từ app thật.
  - Android: Play Integrity, tính năng *device recall* (vài bit mỗi thiết bị do Google giữ, còn sau khi cài lại; kiểm
    lại trạng thái beta lúc làm) + kết quả `MEETS_DEVICE_INTEGRITY`.
  - Web: Turnstile chỉ chặn bot, không định danh thiết bị. Quà tạo tài khoản trên web **chỉ trao sau khi xác minh email
    hoặc số điện thoại**, hoặc trao dần (100 coin ngay, 200 coin sau 5 lượt chơi ở ngày thứ hai) (tạm chọn).
  - Mỗi thiết bị nhận quà tạo tài khoản tối đa 1 lần mỗi 30 ngày (tạm chọn, khắt hơn bản trước vì đã có định danh thật).
- **Xác thực số điện thoại (móc theo cờ, tạm chọn):** Nghị định 147/2024/NĐ-CP (hiệu lực 25/12/2024) yêu cầu dịch vụ
  mạng xã hội xác thực tài khoản bằng số điện thoại di động Việt Nam trước khi đăng nội dung. Lyris có thể bị xếp là
  mạng xã hội vì có nhân vật công khai và bảng xếp hạng (cần luật sư, §20). F61 làm sẵn móc OTP qua SMS, bật bằng cờ
  `LYRIS_PHONE_VERIFY=publish`: bắt buộc trước khi bật "Công khai" nhân vật (chơi riêng không cần).
- Vai trò `owner` thành `staff` (nhiều người), đăng nhập trang quản trị bắt buộc MFA (TOTP); mọi thao tác staff ghi
  `admin_audit`. Staff dùng chat để kiểm tra thì có ví thường (không còn "chủ máy không tốn coin" ở bản host; bản tự chạy
  giữ luật cũ).
- **Xoá tài khoản trong app** (App Store 5.1.1(v), Google Play): đã có (`DELETE /api/account`); bản host thêm job xoá
  ảnh S3, thu hồi token Apple, và Chính sách ghi "bản sao lưu tự hết sau 35 ngày".

## 11. Thanh toán (PO 5A)

### 11.1 Nguyên tắc

- **Một sổ coin.** Mọi khoản mua (Apple, Google, VNPay, MoMo) thành **một dòng sổ** `kind = 'purchase'` với
  `idem_key = '{provider}:{mã giao dịch của nhà cung cấp}'`. Gửi lại, webhook lặp, app gửi hai lần → không cộng hai lần.
- **Chỉ cộng khi server tự xác minh** với nhà cung cấp. Không bao giờ tin app hay trang "return URL".
- **Cộng cho chủ giao dịch, không cho người gọi.** Giao dịch mang mã tài khoản (`appAccountToken` của Apple,
  `obfuscatedExternalAccountId` của Google) → cộng cho tài khoản chủ mã đó, kể cả khi app đang đăng nhập tài khoản khác
  (mua ở A, đăng xuất, đăng nhập B, StoreKit giao lại giao dịch). Trả 200 để app `finish()`/`consume`. Không có mã (mua từ
  promoted IAP, offer code) → cộng cho tài khoản của phiên. Chỉ từ chối (400) khi chữ ký sai, sai `bundleId`/gói, sai
  `productId`. Từ chối một giao dịch đã trả tiền chỉ vì "sai tài khoản" làm nó kẹt mãi: tiền đã trừ mà không ai có coin.
- **Hoàn tiền / chargeback / thu hồi** → dòng sổ âm `kind = 'purchase_refund'`, `idem_key = '{provider}-refund:{mã}'`.
- **Số dư không âm** (`CHECK` giữ nguyên). Hoàn tiền chỉ trừ tới **`balance − Σ giữ chỗ đang mở`** (khoá ví `FOR UPDATE`),
  để lượt đang sinh vẫn trừ được 6 coin của nó; phần thiếu ghi vào `coin_wallets.debt` và vào cột `shortfall` của biên
  nhận. Lần cộng sau (mua, quà) trả nợ trước (dòng sổ `debt_repay`). `ledger_audit` kiểm
  `debt = Σ shortfall − Σ |debt_repay|` (§5.2) (tạm chọn, [quyết định](../wiki/decisions/thanh-toan-iap-va-cong-vn.md)).
- **Có nợ vẫn mua được**, trên web cũng như trong app: mua chính là cách trả nợ, chặn mua thì nợ không bao giờ hết. Gian
  lận "mua rồi đòi hoàn" xử lý ở §11.6 (khoá mua sau 2 lần hoàn trong 30 ngày), không xử lý bằng nợ.
- **Đa nền tảng (App Store 3.1.3(b)):** coin mua trên web dùng được trong app iOS vì cùng gói coin cũng bán bằng IAP trong
  app. App iOS/Android **không** nhắc, không dẫn link tới thanh toán web (3.1.1, chính sách Google Play Payments).
- Chế độ thử (mã nạp, `test_mode: true`) giữ cho bản tự chạy. Bản host: coin của chế độ thử đặt về 0 khi bắt đầu bán, báo
  trước ≥ 30 ngày (PO đã chốt, [raw](../wiki/raw/2026-11-14-coin-tra-loi-2.md)).

### 11.2 Dữ liệu mới

```sql
-- coin_kinds (bảng tra, §5.2): baseline Postgres đã có sẵn 'purchase', 'purchase_refund', 'debt_repay'.
ALTER TABLE coin_ledger ADD COLUMN provider text, ADD COLUMN receipt_id bigint;
ALTER TABLE coin_wallets ADD COLUMN debt integer NOT NULL DEFAULT 0 CHECK (debt >= 0);
CREATE TABLE payment_orders (          -- web: đơn tạo trước khi chuyển sang VNPay/MoMo
  id bigint generated by default as identity primary key, order_ref text unique not null,  -- vnp_TxnRef / orderId
  account_id bigint not null references accounts(id), pack_id text not null, amount_vnd integer not null,
  provider text not null check (provider in ('vnpay','momo')), status text not null default 'pending'
    check (status in ('pending','paid','failed','expired','refunded')), created_at timestamptz(3) not null default now(),
  provider_create_date text,           -- vnp_CreateDate (yyyyMMddHHmmss) đã ký, cần cho querydr
  paid_at timestamptz(3), provider_txn_id text);
CREATE TABLE payment_receipts (        -- mọi giao dịch đã xác minh, mọi nhà cung cấp
  id bigint generated by default as identity primary key,
  provider text not null check (provider in ('apple','google','vnpay','momo')), provider_txn_id text not null,
  account_id bigint references accounts(id) on delete set null, pack_id text not null, coins integer not null,
  price_amount bigint, price_currency text, storefront text, environment text not null,  -- 'production' | 'sandbox'
  status text not null check (status in ('credited','refunded','revoked','rejected')),
  ledger_id bigint, refund_ledger_id bigint, shortfall integer not null default 0,  -- phần hoàn tiền thành nợ
  payload_sha256 bytea not null,
  created_at timestamptz(3) not null default now(), refunded_at timestamptz(3),
  unique (provider, provider_txn_id));
CREATE TABLE payment_webhook_log (id …, provider, received_at, signature_ok bool, event_type, provider_txn_id, outcome);
```

`payment_receipts` không lưu thông tin thẻ, số điện thoại hay email. Giữ 10 năm theo nghĩa vụ kế toán (tách khỏi xoá tài
khoản: khi xoá tài khoản thì `account_id → NULL`, không xoá biên nhận).

### 11.3 Apple In-App Purchase (iOS)

- Sản phẩm **consumable**: `<bundle-id>.coins.p100`, `.p550`, `.p1200`, `.p2500` (số coin như docs/coins.md §4.1; giá
  là mức giá VND gần nhất của App Store, có thể khác web, hiện theo giá StoreKit trả về).
- Mỗi tài khoản có `iap_account_token uuid` ngẫu nhiên (không phải `uid` công khai); app mua bằng StoreKit 2
  `purchase(options: [.appAccountToken(token)])`.
- App gửi `jwsRepresentation` lên `POST /api/payments/apple/transactions`. Server: kiểm chuỗi chứng chỉ JWS tới Apple Root
  CA (thư viện App Store Server chính thức), `bundleId`, `productId`, `type = Consumable`, chưa có `revocationDate` → tìm
  tài khoản chủ của `appAccountToken` (không có token → tài khoản của phiên, §11.1) → ghi biên nhận + dòng sổ cho **chủ
  đó** trong một transaction → trả 200 (số dư mới nếu chủ là người gọi). **App chỉ gọi `transaction.finish()` sau khi
  server trả 200.** Giao dịch chưa xong (mất mạng) được StoreKit giao lại qua `Transaction.updates` lần mở app sau →
  server trả lại kết quả cũ (idempotent).
- **App Store Server Notifications V2** (`POST /api/payments/apple/notify`, kiểm JWS):
  - `ONE_TIME_CHARGE` (Apple có từ 2024, gửi cho cả consumable) → cộng coin như khi app gửi JWS, cùng
    `idem_key = apple:{transactionId}`: app chết hay mất mạng sau khi trả tiền thì coin vẫn tới (giống RTDN của Google).
  - `REFUND` → dòng sổ âm; `REFUND_REVERSED` → cộng lại (`idem_key` riêng).
  - `CONSUMPTION_REQUEST` → trả thông tin tiêu dùng qua App Store Server API trong 12 giờ **chỉ khi Điều khoản đã có đồng
    ý của người dùng** (không thì không gửi).
- **Sandbox:** bản production phải nhận giao dịch `environment = Sandbox`, vì người duyệt của Apple mua bằng sandbox trên
  bản production, và người duyệt có thể tạo tài khoản Lyris mới ngay lúc duyệt (đăng ký đang mở) nên không thể có danh
  sách trước. Coin sandbox được cộng cho **mọi** tài khoản, nhưng biên nhận ghi `sandbox`, không tính doanh thu, trần
  3 giao dịch sandbox mỗi ngày mỗi tài khoản (tạm chọn). Giao dịch sandbox chỉ tạo được bằng tài khoản tester mà chính
  Lyris tạo trong App Store Connect, hoặc bởi người duyệt, nên trần chỉ là lớp phòng thêm.
- Đối soát: hằng ngày tải báo cáo bán hàng App Store Connect (Sales and Trends API), so với `payment_receipts`.

### 11.4 Google Play Billing (Android)

- Sản phẩm one-time, consumable cùng `pack_id`. Mua với `obfuscatedAccountId = sha256(iap_account_token)`.
- App gửi `purchaseToken` lên `POST /api/payments/google/purchases`. Server gọi Google Play Developer API
  `purchases.products.get`: `purchaseState = 0`, đúng gói → tìm chủ của `obfuscatedExternalAccountId` (cùng luật "cộng
  cho chủ" của §11.1) → ghi biên nhận + sổ → server gọi `purchases.products.consume` (consume cũng là acknowledge; không
  acknowledge trong 3 ngày thì Google tự hoàn).
- **`idem_key = google:{sha256(purchaseToken)}`**, không dùng `orderId`: giao dịch đổi mã khuyến mãi (promo code) không có
  `orderId`. `orderId` vẫn lưu trong biên nhận để đối soát.
- **RTDN** qua Cloud Pub/Sub push (`/api/payments/google/rtdn`, xác thực token OIDC của Pub/Sub):
  `oneTimeProductNotification` → giao dịch mới khi app chưa kịp gửi; `voidedPurchaseNotification` → hoàn tiền /
  chargeback / thu hồi → dòng sổ âm ngay. Job `payment_refund_poll` gọi Voided Purchases API mỗi giờ chỉ là **dự phòng**
  khi Pub/Sub lỡ tin.

### 11.5 VNPay và MoMo (web)

- `POST /api/payments/web/orders {pack_id, provider}` → tạo `payment_orders` (`pending`, hết hạn 15 phút) → trả URL thanh
  toán (VNPay: tham số `vnp_*`, `vnp_Amount = số tiền VND × 100`, chữ ký HMAC-SHA512, lưu `vnp_CreateDate` vào
  `provider_create_date` vì `querydr` cần nó; MoMo: API tạo giao dịch, chữ ký HMAC-SHA256).
- **IPN** (`/api/payments/vnpay/ipn`, `/api/payments/momo/ipn`): kiểm chữ ký → tìm đơn → số tiền khớp →
  - giao dịch **thành công** → trong một transaction: đơn `paid`, biên nhận, dòng sổ;
  - giao dịch **thất bại** (người dùng huỷ, thẻ bị từ chối) → đơn `failed`, không ghi sổ, **vẫn trả `00`** (đã nhận
    xong; trả mã lỗi thì cổng gửi lại mãi).
  Trả mã đúng theo đặc tả của cổng (VNPay `RspCode` 00/01/02/04/97; MoMo HTTP 204) để cổng ngừng gửi lại. Đơn đã `paid`
  → trả "đã xác nhận" (idempotent).
- **Return URL** là đường thật `https://lyris.example/pay/return` (không phải `#/…`: cổng nối query vào sau URL, rơi vào
  sau dấu `#` thì server không thấy và dễ bị chèn sai chỗ). Route đó chỉ đọc `order`, rồi chuyển hướng 302 sang
  `#/coins/top-up?order=…`; trang chỉ **hiện** kết quả bằng cách hỏi server trạng thái đơn; không bao giờ cộng coin.
- Đơn `pending` quá 15 phút: job gọi API tra cứu (VNPay `querydr` với `vnp_TransactionDate = provider_create_date`, MoMo
  query) → `paid` hay `expired`.
- Hoàn tiền (theo yêu cầu, qua staff): gọi API hoàn của cổng → thành công → dòng sổ âm.
- Hoá đơn điện tử cho mỗi giao dịch web (nghĩa vụ của đơn vị bán hàng ở Việt Nam): tích hợp nhà cung cấp hoá đơn điện tử
  khi có pháp nhân (§20).

### 11.6 Gian lận

- Tối đa 5 đơn web `paid`/ngày/tài khoản và 2.000.000đ/ngày (tạm chọn); vượt → chờ staff.
- Theo dõi tỉ lệ hoàn tiền theo tài khoản và thiết bị; ≥ 2 lần hoàn trong 30 ngày → khoá mua (đây là chỗ chặn gian lận
  hoàn tiền; có nợ thôi thì không khoá mua, §11.1).
- Sandbox: trần 3 giao dịch/ngày/tài khoản, không tính doanh thu (§11.3).
- Coin không chuyển được cho người khác, không đổi ra tiền (đã là luật) → giảm động cơ gian lận.
- Không tặng coin theo kiểu ngẫu nhiên (đã chốt ở docs/coins.md §4.1).

## 12. Số liệu và quan sát

### 12.1 Số liệu sản phẩm (PostHog)

- Giữ nguyên luật của docs/tracking-plan.md: không chữ người dùng, không IP, tắt được, `Sec-GPC`, giữ 180 ngày.
- Outbox `analytics_events` ở Postgres; `posthog_flush` là việc định kỳ có leader (§7.3) thay cho task trong lifespan.
- App di động: `anon_id` lưu trong Preferences của app (không phải IDFA). Không SDK quảng cáo, không theo dõi chéo app →
  **không cần ATT**. Nếu sau này thêm quảng cáo thật thay "quảng cáo mẫu" (F45) thì phải có ATT + khai lại nhãn quyền riêng
  tư (quyết định riêng của PO).
- Sự kiện mới: `purchase_started`, `purchase_completed{provider, pack_id}`, `purchase_refunded`, `app_updated`,
  `reply_resumed`.

### 12.2 Quan sát hệ thống

- **Log:** JSON có cấu trúc, `request_id`, `account_uid` băm, không chữ chat, không token, không khoá; giữ 30 ngày như
  Chính sách hiện tại.
- **Số đo:** Prometheus + Grafana (có quản lý hoặc tự chạy). Nguồn: vLLM (`/metrics`), API (OpenTelemetry metrics),
  Postgres, Redis, hàng `jobs`.
- **Trace:** OpenTelemetry API → gateway → vLLM, lấy mẫu 10 % + mọi request lỗi.
- **Lỗi client:** gom lỗi JS và crash native bằng dịch vụ tự chạy được (GlitchTip/Sentry tự chạy) để dữ liệu không rời
  vùng đã chọn.

### 12.3 SLO (đo hằng tháng)

| SLO | Mục tiêu | Đo bằng |
|---|---|---|
| TTFT lượt chat không phải chờ hàng (từ lúc server nhận tới token đầu từ vLLM) | p50 ≤ 1,5 s · p95 ≤ 4 s | `lyris_reply_ttft_seconds` (histogram) |
| Chữ đầu tiên **hiện** cho người chơi (sau bộ lọc đầu ra theo đoạn, §4.3 bước 6) | p50 ≤ 2,5 s · p95 ≤ 5 s | `lyris_reply_first_visible_seconds`; phần thêm do lọc = thời gian sinh đoạn đầu (~0,4–1 s ở 25–60 token/s) + chấm (~30–80 ms) |
| Chặn nhầm của bộ lọc đầu ra | ≤ 1 % câu trả lời | sự kiện `content_filtered` + mẫu staff chấm lại |
| Tốc độ chữ mỗi lượt | p50 ≥ 25 token/s · p05 ≥ 12 token/s (nhanh hơn tốc độ đọc) | `lyris_reply_tokens_per_second` |
| Lượt phải chờ hàng (`waited = true`) lúc cao điểm | ≤ 5 % | sự kiện `reply_completed` |
| Lượt thất bại do hệ thống (`reply_failed` trừ người dùng tự dừng) | ≤ 0,5 % | sự kiện + số đo |
| API không phải stream: sẵn sàng | 99,9 %/tháng (5xx) | LB |
| API không phải stream: độ trễ | p95 ≤ 300 ms | OTel |
| Coin cho giao dịch đã trả tiền | 99 % trong 60 s sau IPN/biên nhận; 0 biên nhận chưa đối soát > 24 giờ | `payment_receipts` |
| Sổ coin | 0 ví lệch tổng sổ; 0 ví lệch nợ | `ledger_audit` |

Ngoại lệ đã biết: 01:00–07:00 nếu chỉ chạy 1 replica thì một replica chết làm chat ngừng 3–8 phút (§8.6); thời gian đó
tính vào "lượt thất bại do hệ thống" chứ không loại ra.

### 12.4 Cảnh báo (gửi người trực)

TTFT p95 > 6 s trong 10 phút · `genq` > 20 trong 5 phút · replica vLLM chết · tỉ lệ 5xx > 1 % trong 5 phút · webhook thanh
toán lỗi chữ ký > 5 trong 10 phút · `ledger_audit` lệch · bản sao lưu đêm thất bại · báo cáo `minor_safety` chưa xem sau
24 giờ (đã có quy trình ở docs/deploy.md §11).

## 13. Bảo mật, quyền riêng tư, nơi lưu dữ liệu

- **Bí mật:** trình quản lý bí mật của cloud (mã hoá bằng KMS), nạp vào pod khi chạy; không file `.env` trong repo hay ảnh
  container. Khoá riêng cho từng môi trường. Khoá Apple (`.p8`), Google service account, VNPay `vnp_HashSecret`, MoMo
  `secretKey`, `VLLM_KEY`, PostHog: xoay vòng 90 ngày hoặc khi người có quyền rời nhóm.
- **Mạng:** VPC riêng; vLLM, Postgres, Redis chỉ nhận từ subnet của API/worker; vLLM bắt `--api-key`.
- **Giới hạn:** WAF (§4.1) + token bucket Redis (§6) + giới hạn thử sai hiện có (docs/auth.md §3.4).
- **Lạm dụng nội dung:** luật an toàn trong prompt (đã có) + lọc đầu ra bằng một model phân loại an toàn nhỏ chạy trên GPU
  của mình (F60). Lọc **trước khi chữ tới client**, không phải sau khi stream xong (lọc sau thì người chơi đã đọc chữ
  bị chặn, App Store 1.2 coi như không lọc):
  - Gom delta thành đoạn (hết câu, hoặc 24 token), chấm đoạn **cùng ngữ cảnh** các đoạn trước, chỉ gửi đoạn `safe`.
  - Đoạn `unsafe` → dừng sinh, không gửi đoạn đó, gửi một câu lảng trong vai thay vào; nhả giữ chỗ coin với lý do mới
    `content_filtered` (bảng tra `hold_release_reasons`, §5.2), ghi sự kiện `content_filtered`.
  - Lưới thứ hai: sau `done`, chấm cả câu trả lời một lần; nếu cả câu (không đoạn nào riêng lẻ) bị gắn `unsafe` thì gửi
    sự kiện SSE mới `retract{from_seq}` để client thay phần từ `from_seq` bằng câu lảng, và không lưu chữ đó.
  - Không lưu chữ bị chặn ngoài log an toàn 30 ngày cho staff.
- **Nội dung người tạo và tuổi (App Store 1.2.1(a)):** app có nội dung của người tạo phải giới hạn được nội dung vượt
  xếp hạng tuổi của app theo tuổi đã khai hoặc đã xác minh. Lyris dành cho người 16+ (Điều khoản §1; đồng ý Điều khoản
  lúc tạo tài khoản là tự xác nhận 16+; **không hỏi năm sinh**, PO chốt 2026-11-15, docs/compliance.md §0). Nút "Nội dung
  an toàn" bật sẵn cho mọi tài khoản nên mọi nhân vật công khai đều chịu luật an toàn mặc định. Nhân vật "18+" (chỉ khi
  có nội dung 18+, F48) chỉ hiện cho tài khoản đã tắt nút và tích "Tôi đã đủ 18 tuổi" (cơ chế "tuổi đã khai").
- **Truy cập của staff:** không ai đọc story của người khác trong app (giữ luật hiện tại). Truy cập DB production qua bastion,
  MFA, mọi phiên được ghi. Báo cáo chỉ có chữ khi người báo cáo đồng ý (đã có).
- **Mã hoá:** TLS mọi chặng (kể cả trong VPC tới Postgres/Redis), mã hoá lúc nghỉ của Postgres, S3, bản sao lưu.
- **Dữ liệu train:** chỉ chat của tài khoản bật `training_opt_in` (F41), tách bucket, xoá khi người dùng rút đồng ý.
- **Nơi lưu dữ liệu (cần PO + luật sư):** nếu đơn vị phát hành là doanh nghiệp Việt Nam, Luật An ninh mạng 2018 (Điều 26) và
  Nghị định 53/2022/NĐ-CP yêu cầu lưu một số loại dữ liệu của người dùng tại Việt Nam; Luật Bảo vệ dữ liệu cá nhân (hiệu lực
  01/01/2026) có thủ tục khi chuyển dữ liệu ra nước ngoài. **Tạm chọn:** Postgres, S3, sao lưu đặt ở trung tâm dữ liệu tại
  Việt Nam; GPU cũng ở Việt Nam nếu nhà cung cấp có H100/L40S (FPT, VNG, Viettel đều có dịch vụ GPU), không thì GPU ở
  Singapore nhưng chỉ nhận prompt khi suy luận, không lưu. PostHog (Mỹ/EU) là chuyển ra nước ngoài: tắt cho tới khi có hồ sơ,
  hoặc tự chạy PostHog trong vùng. §20.
- **Cloudflare và dữ liệu ra nước ngoài:** TLS kết thúc ở PoP của Cloudflare; PoP gần nhất có thể ở ngoài Việt Nam, nên
  chữ chat đi qua máy ngoài Việt Nam (không lưu). Có tính là chuyển dữ liệu ra nước ngoài theo Luật Bảo vệ dữ liệu cá
  nhân không là câu hỏi cho luật sư (§20). Phương án dự phòng: chỉ để Cloudflare trước web tĩnh và ảnh công khai, còn
  `api.lyris.example` đi thẳng vào LB ở Việt Nam (mất WAF của Cloudflare cho API, thay bằng WAF của cloud trong nước).
- **Nghị định 147/2024/NĐ-CP (mạng xã hội):** nhân vật công khai và bảng xếp hạng có thể khiến Lyris bị xếp là dịch vụ
  mạng xã hội, cần đăng ký/giấy phép và xác thực tài khoản bằng số điện thoại Việt Nam trước khi đăng nội dung. F61 làm
  sẵn móc OTP theo cờ (§10). Câu hỏi cho luật sư ở §20.
- **Văn bản pháp lý:** Chính sách hiện nói dữ liệu ở trên máy của người vận hành; bản host phải sửa (nơi lưu, nhà cung cấp
  cloud, cổng thanh toán, Apple/Google, hạn giữ sao lưu 35 ngày, biên nhận 10 năm), đổi `LEGAL_VERSION` để mọi người đồng ý
  lại (docs/compliance.md §3).

## 14. Sao lưu, môi trường, CI/CD

### 14.1 Sao lưu và khôi phục

| Thứ | Cách | RPO / RTO |
|---|---|---|
| Postgres | PITR có quản lý 35 ngày (WAL liên tục) + `pg_dump` mã hoá hằng ngày sang vùng/nhà cung cấp khác, giữ 35 ngày | RPO ≤ 5 phút · RTO ≤ 4 giờ |
| S3 ảnh | Bật versioning (giữ bản cũ 30 ngày) + sao chép sang bucket vùng khác | RPO ≤ 1 giờ |
| Redis | Không sao lưu (chỉ cache, hàng chờ, khoá; mất thì tự dựng lại) | — |
| Trọng số model, adapter LoRA | Bucket riêng có checksum, bất biến | — |
| Cấu hình hạ tầng | Mã (Terraform/Helm) trong git | — |

Diễn tập khôi phục mỗi tháng trên staging: dựng Postgres từ PITR, chạy `ledger_audit`, đếm dòng so với production.

### 14.2 Môi trường

| | dev | staging | prod |
|---|---|---|---|
| Chạy ở | Máy của người làm: chế độ tự chạy (SQLite + Ollama/LLM giả), hoặc Postgres + Redis cục bộ (không Docker trên Mac, như quyết định hiện tại) | Cloud, cùng Helm chart với prod, nhỏ hơn | Cloud |
| LLM | LLM giả (`fake-server.py`) / Ollama | 1 GPU nhỏ (L4) bật theo giờ làm việc + LLM giả cho e2e | vLLM N+1 |
| Thanh toán | Chế độ thử (mã nạp) | Apple sandbox, Google license tester, VNPay/MoMo sandbox | Thật |
| App di động | Simulator / thiết bị dev | TestFlight, Google Play internal testing | App Store, Google Play |
| Dữ liệu | Giả | Giả (không bao giờ chép dữ liệu thật xuống) | Thật |

### 14.3 CI/CD

- Mỗi PR: `ruff`/`tsc`, **pytest hai lần** (SQLite và Postgres tạm), `npm test`, build, bot e2e trên LLM giả,
  kiểm migration (áp cả hai thư mục từ 0, và áp bản mới lên bản sao schema prod), quét phụ thuộc, build ảnh container.
- Nhánh chính → tự triển khai staging → chạy bot e2e + bài tải nhỏ trên staging.
- Production: bấm duyệt; **canary** 10 % pod mới trong 30 phút (SLO §12.3 không xấu đi) → 100 %. Migration chỉ thêm
  (additive, như luật hiện tại); bỏ cột cần hai lần phát hành.
- Rollback: ảnh container cũ (một lệnh Helm). Migration không lùi: chỉ thêm nên code cũ vẫn chạy trên schema mới.
- App di động: Fastlane (hoặc Xcode Cloud) build + ký + đẩy TestFlight/internal track từ CI; phát hành theo đợt
  (phased release 7 ngày của App Store, staged rollout của Google Play).
- `verification/verify.sh` (harness của repo) giữ là cổng chấm tính năng; CI gọi nó với cờ thêm chạy bộ test Postgres.

## 15. Sức chứa và chi phí (ước tính, phải đo ở bài tải của F53)

### 15.1 Nhu cầu lúc cao điểm (C = 300, một lượt mỗi 75 s → λ = 4 lượt/s)

| Thành phần | Mỗi lượt | Mỗi giây |
|---|---|---|
| Chữ sinh ra của câu trả lời | ~350 token | 1.400 token/s |
| Việc nền (trích xuất ~200 token + tóm tắt chia đều ~30) | ~230 token | ~920 token/s |
| **Tổng token sinh ra** | | **~2.300 token/s** |
| Prompt phải đọc của lượt chat: 80 % trúng cache (~800 token mới) + 20 % trượt (~6.000) | ~1.840 token | ~7.400 token/s |
| Prompt của trích xuất (~3.000 token, khác system nên ít trúng cache) | ~3.000 token | ~12.000 token/s |
| **Tổng token prompt phải đọc** | | **~19.000 token/s** |
| *Nếu trích xuất dùng chung phần đầu story (§8.3, 60 % trúng cache)* | ~1.200 token | ~4.800 token/s → tổng **~12.000 token/s** |

Chỗ nghẽn thật là **đọc prompt của trích xuất**, không phải chữ sinh ra. Vì vậy §8.3 đề xuất trích xuất dùng chung phần
đầu story; nếu bài tải xác nhận, H100 chỉ cần 1 replica + 1 dự phòng thay vì 2 + 1. Tỉ lệ trúng cache 80 % của lượt chat
cũng phụ thuộc phương trình ngân sách KV ở §8.3 (≈ 100 story mỗi replica lúc cao điểm là sát ngưỡng).
| Số chuỗi đang chạy cùng lúc (chat ~15 s × 4 + nền ~8 s × 4) | | **~90** |

### 15.2 Một replica làm được bao nhiêu (giả định, phải đo)

| GPU (FP8 trừ khi ghi khác) | Chuỗi song song vẫn ≥ 20 token/s | Token sinh/s | Token prompt đọc/s | Số replica cho §15.1 | Lúc cao điểm (N+1) |
|---|---|---|---|---|---|
| H100 80 GB | ~64 | ~1.600 | ~12.000 | 2 (bị giới hạn bởi đọc prompt: 19k/12k) | **3** |
| L40S 48 GB | ~24 | ~700 | ~5.000 | 4 | **5** |
| L4 24 GB (AWQ 4-bit) | ~8 | ~250 | ~2.000 | 10 | 11 (không khuyên: nhiều máy, chất lượng 4-bit phải chấm lại) |

Bài tải của F53 (`harness/load/chatters.py`, 300 người chơi ảo trên prompt thật lấy từ story mẫu) thay các con số giả
định này bằng số đo trước khi ký hợp đồng GPU. Quy tắc: `chat_capacity` của một replica = số chuỗi song song lớn nhất mà
TTFT p95 ≤ 4 s và p05 ≥ 12 token/s.

### 15.3 Chi phí hằng tháng (giá tham khảo, phải xin báo giá)

Ba mô hình thuê GPU (cloud GPU ở Việt Nam, lựa chọn tạm chọn ở §13, thường cho thuê **theo tháng**, không theo giờ):

| Mô hình thuê | H100 | L40S |
|---|---|---|
| (a) Theo giờ, tự co giãn: 6 giờ cao điểm ở mức N+1 + 18 giờ trung bình 1,5 (H100) hoặc 2,5 (L40S) replica | ~1.350 giờ → **$2.700–4.700** | ~2.250 giờ → **$2.000–3.600** |
| (b) **Cố định theo tháng** ở mức cao điểm: 3 H100 / 5 L40S × 720 giờ | 2.160 giờ → **$4.300–7.600** | 3.600 giờ → **$3.200–5.800** |
| (c) Nền cố định + thêm theo giờ: 2 H100 / 3 L40S cố định + phần cao điểm theo giờ | 1.440 + ~180 giờ → **$3.200–5.700** | 2.160 + ~360 giờ → **$2.300–4.000** |
| Giá mỗi giờ GPU (cloud GPU chuyên dụng; cloud lớn đắt hơn 1,5–2,5 lần) | $2,0–3,5 | $0,9–1,6 |

Bảng dưới dùng (a) để so; nếu nhà cung cấp chỉ cho thuê tháng thì dùng (b) hoặc (c), tổng tăng ~$1.000–3.000.

| Khoản | H100 | L40S |
|---|---|---|
| **GPU/tháng (a)** | **$2.700–4.700** | **$2.000–3.600** |
| Postgres HA, PgBouncer | $300–700 | như trái |
| Redis | $50–150 | |
| API + worker (4–6 máy nhỏ), Kubernetes | $250–600 | |
| S3 + CDN + egress | $50–200 | |
| Số đo, log, sao lưu ngoài vùng | $100–300 | |
| **Tổng** | **~$3.500–6.700/tháng** | **~$2.800–5.600/tháng** |

**Mỗi lượt:** ~2,7 triệu lượt/tháng → GPU ~$0,0010–0,0017/lượt (~26–45đ); toàn bộ hạ tầng ~$0,0013–0,0025/lượt
(~35–65đ). Giá bán 6 coin = 600đ (gói 100 coin) tới 480đ (gói 2.500 coin). Sau phí Apple (15 % nếu được chương trình doanh
nghiệp nhỏ, không thì 30 %) hay phí cổng (~1–3 %) còn ~340–590đ, **trước thuế**. Thuế phải trừ thêm (kế toán xác nhận):
với IAP ở kho Việt Nam, Apple/Google khấu trừ thuế nhà thầu nước ngoài (khoảng 5 % GTGT + 5 % TNDN trên doanh thu); trên
web, Lyris xuất hoá đơn và nộp GTGT. Sau thuế còn khoảng ~300–530đ mỗi lượt trả tiền. **Lượt trả tiền vẫn lãi gấp ~4,5–15
lần chi phí hạ tầng.**

**Hoà vốn:** chi phí cố định ~$3.000–6.700 ≈ 80–175 triệu đồng/tháng. Với 10.000 MAU, cần doanh thu ròng tương đương
~8.000–17.500đ mỗi MAU mỗi tháng (ví dụ 5 % người dùng trả trung bình 160.000–350.000đ). Đòn bẩy có sẵn: lượng coin miễn
phí (300 quà, +60/ngày, nhiệm vụ 30/ngày), tự co giãn GPU theo giờ, cam kết dài hạn (rẻ hơn 30–50 %), FP8 → nhiều lượt hơn
mỗi GPU. Đây là quyết định kinh doanh của PO (§20, ngân sách GPU).

## 16. App di động (PO: "bạn xem cái nào tối ưu và mượt mà nhất thì chọn")

### 16.1 So sánh

| Tiêu chí | **Capacitor bọc React hiện có + plugin native** | React Native / Expo | Swift (iOS) + Kotlin (Android) native |
|---|---|---|---|
| Một codebase cho web, iOS, Android | **Có**: chính `frontend/` (React 18 + Vite + TS), cùng màn hình, cùng test | Một codebase cho 2 app, web phải giữ riêng (hoặc react-native-web, phải viết lại giao diện) | Ba codebase |
| Phải viết lại | Không: thêm lớp nền tảng (API_BASE, token, IAP, push, an toàn vùng) | Mọi màn hình (Story, DM, Studio, Khám phá, Tài khoản, quản trị…); giữ được phần logic thuần `src/lib/*.ts` | Mọi thứ, hai lần |
| Đội hiện có (1 PO + AI, chỉ có React/TS) | **Hợp** | Học thêm RN, Expo build | Cần thêm 2 kỹ sư |
| Stream chat | `fetch` + `ReadableStream` trong WKWebView/WebView Chrome; `lib/sse.ts` dùng lại nguyên. 25–60 token/s là vài chục lần cập nhật chữ mỗi giây: trình duyệt dư sức | `fetch` streaming cần polyfill/thư viện riêng; viết lại `SSEParser` cho RN | Tốt nhất, nhưng phải viết lại |
| Cuộn danh sách tin dài, bàn phím | Ổn nếu ảo hoá danh sách (cần làm cho story > 200 tin) và plugin Keyboard | Tốt | Tốt nhất |
| App Store 4.2 (tối thiểu chức năng) | **Rủi ro nếu chỉ là website bọc lại.** Giảm bằng: đóng gói `dist` trong app (không tải web từ xa), IAP StoreKit, Sign in with Apple, push, haptics, chia sẻ native, Keychain, màn mở offline | Thấp | Thấp |
| IAP, push, haptics | Plugin native (Swift/Kotlin nhỏ do mình viết, hoặc plugin cộng đồng) | Thư viện có sẵn | Có sẵn |
| Offline | Vỏ app + danh sách story đã xem (chỉ đọc) từ cache; chat cần mạng (AI ở server) ở mọi lựa chọn | như trái | như trái |
| Bot e2e, luật chữ (`copyWords.test.ts`), thiết kế (`DESIGN.md`) | **Dùng lại hết** | Viết lại phần lớn | Viết lại hết |
| Thời gian tới bản TestFlight đầu | ~2–3 tuần | ~2–3 tháng | ~4–6 tháng |

### 16.2 Chọn: Capacitor (AI chọn) ([quyết định](../wiki/decisions/app-di-dong-capacitor.md))

Lyris là app đọc và viết chữ: phần nặng nhất là hiện chữ chảy ra từ server, việc trình duyệt làm tốt. Capacitor cho
một codebase, giữ nguyên mọi tính năng đã qua bộ chấm, đội hiện tại làm được, và vẫn có đủ phần native mà Apple muốn thấy.
React Native chỉ đáng khi giao diện web không đạt ngưỡng hiệu năng dưới đây; phần logic thuần (`src/lib/*.ts`:
`sse.ts`, `storyBlocks.ts`, `playerBlocks.ts`, `coins.ts`…) đã tách khỏi React DOM nên mang sang được nếu phải đổi.

**Ngưỡng hiệu năng (cổng đổi hướng).** Đo mỗi bản phát hành trên hai máy cố định: **iPhone 11 (A13, iOS mới nhất máy đó
chạy được)** và **Samsung Galaxy A15 bản 4 GB RAM (Android 14, Android System WebView bản ổn định lúc đo; ghi số phiên bản
WebView vào báo cáo)**. Trượt 2 bản liên tiếp sau khi đã tối ưu → mở lại quyết định; hướng đổi là **chuyển cả app sang
React Native/Expo** (dùng lại `src/lib/*.ts`, viết lại màn hình), không phải ghép một màn RN vào trong app Capacitor
(hai runtime, hai điều hướng, hai bộ trạng thái đăng nhập: không đáng với đội nhỏ).

| Chỉ số | Ngưỡng | Đo bằng |
|---|---|---|
| Mở nguội tới hub tương tác được | p75 ≤ 2,0 s | mốc native lúc tiến trình bắt đầu → `performance.mark("hub-interactive")`, gửi lên RUM (GlitchTip hoặc PostHog tự chạy) |
| Cuộn story 300 tin | ≥ 95 % khung hình ≤ 16,7 ms (60 fps) | Xcode Instruments (Animation Hitches) trên iPhone; `FrameMetrics` / `adb shell dumpsys gfxinfo` trên Android; kịch bản cuộn cố định |
| Delta SSE tới lúc chữ hiện trên màn | p95 ≤ 50 ms | `performance.mark` lúc parser nhận delta → `requestAnimationFrame` sau lần vẽ có chữ đó; RUM |
| Gõ phím tới lúc chữ hiện trong ô nhập | p95 ≤ 50 ms | Event Timing API (`event.processingEnd`/khung vẽ kế) cho `keydown`/`input`; RUM |
| Bộ nhớ khi mở story 300 tin | ≤ 300 MB | Instruments (Allocations) / `dumpsys meminfo`, cả tiến trình app + WebView |
| Phiên không crash | ≥ 99,5 % | Xcode Organizer, Play Console (Android vitals), GlitchTip |

### 16.3 Cách làm (F55)

- `frontend/` thêm `capacitor.config.ts`, thư mục `ios/`, `android/`. `npm run build` → `npx cap sync` → Xcode/Gradle.
- `API_BASE` lấy từ build (`VITE_API_BASE`): web giữ `/api` tương đối; app dùng `https://api.lyris.example/api`.
- `CapacitorHttp` **tắt** (mặc định): bản vá `fetch` của nó không stream được; SSE dùng `fetch` của WebView.
- Plugin: `App` (deep link, vòng đời: quay lại foreground thì nối lại SSE), `Keyboard`, `Haptics` (rung nhẹ khi nhân vật
  trả lời xong), `Share`, `PushNotifications`, `StatusBar`, `SplashScreen`, plugin nhỏ tự viết cho Keychain/Keystore,
  StoreKit 2, Play Billing, Sign in with Apple. Mọi thư viện mới cần PO đồng ý (luật hiện tại cấm thêm npm/pip; §20).
- **Deep link:** Universal Links (iOS, `apple-app-site-association`) và App Links (Android, `assetlinks.json`) cho
  `https://lyris.example/c/{card_uid}` (hồ sơ nhân vật công khai) → mở `#/character/{id}` trong app; không có app → web.
- **Push** (APNs/FCM, tuỳ chọn, hỏi quyền lúc có lý do, không hỏi lúc mở app lần đầu): "{Tên} đã trả lời" khi câu trả lời
  xong lúc app ở nền; quà ngày. Không gửi nội dung story trong push (màn khoá có thể bị người khác nhìn). Bảng
  `push_devices(account_id, platform, token, created_at)`; xoá khi đăng xuất/xoá tài khoản.
- Màn "Cập nhật Lyris" khi bản app < `min_supported_version`.
- Không tải JavaScript từ xa để đổi tính năng (App Store 2.5.2): mỗi thay đổi giao diện là một bản phát hành qua duyệt.

### 16.4 Rủi ro duyệt App Store và việc phải làm

| Guideline | Rủi ro với Lyris | Việc phải làm |
|---|---|---|
| 4.2 Minimum Functionality | App giống website bọc lại | Đóng gói assets; IAP, push, haptics, chia sẻ, Keychain, Sign in with Apple; ghi chú cho người duyệt nêu các phần native |
| 1.2 User-Generated Content (nhân vật công khai, ảnh, AI chat) | Thiếu lọc, thiếu chặn | Đã có: báo cáo câu trả lời, báo cáo nhân vật, ẩn nhân vật, liên hệ. Thêm (F60): lọc đầu ra tự động, **chặn người tạo** (ẩn mọi nhân vật của họ khỏi Khám phá của mình), quét ảnh, hàng duyệt, cam kết xử lý báo cáo trong 24 giờ |
| 3.1.1 In-App Purchase | Bán coin ngoài IAP | Coin trong app iOS chỉ bán qua IAP; không link/nhắc thanh toán web; mã nạp của chế độ thử không có trong bản host |
| 3.1.3(b) Multiplatform | Coin mua trên web dùng trong app | Được, vì cùng gói có bán bằng IAP trong app |
| 5.1.1(v) Account deletion | — | Đã có "Xoá tài khoản" trong app; thêm thu hồi token Apple |
| 4.8 Login Services | Có Google login mà không có cách đăng nhập tương đương bảo vệ riêng tư | Luật từ 2024: có đăng nhập bên thứ ba thì phải có thêm **một** cách đăng nhập chỉ lấy tên + email, cho ẩn email, không theo dõi quảng cáo. Sign in with Apple thoả luật này (không còn là "bắt buộc" nguyên văn); Lyris chọn nó |
| 2.1 App Completeness | Nội dung giữ chỗ ("Quảng cáo mẫu" của F45 thưởng coin); IAP không chạy với tài khoản người duyệt | Ẩn "Quảng cáo mẫu" ở bản host và app (`LYRIS_SAMPLE_ADS=off`; quảng cáo thật thì cần ATT + khai lại nhãn quyền riêng tư, quyết định riêng của PO). Sandbox được nhận cho mọi tài khoản (§11.3) |
| 1.2.1(a) Creator content | Nội dung người tạo vượt xếp hạng tuổi | Luật an toàn mặc định cho mọi nhân vật công khai (nút "Nội dung an toàn" bật sẵn); 16+ theo Điều khoản, không hỏi năm sinh; nhân vật 18+ chỉ cho tài khoản đã tắt nút và tự xác nhận 18+ (F48, §13) |
| 5.1.2 / quyền riêng tư AI | Gửi dữ liệu cho AI bên thứ ba phải nói rõ | AI chạy trên máy chủ của Lyris (2A), không gửi cho bên thứ ba; ghi rõ trong Chính sách và nhãn quyền riêng tư |
| Xếp hạng tuổi | Chat AI, tình cảm, nội dung người dùng tạo | Trả lời bảng hỏi tuổi mới của App Store trung thực; với nội dung an toàn bật sẵn và chưa có nội dung 18+: cân nhắc 12+ hoặc 17+ (Điều khoản vẫn 16+); chế độ 18+ (F48, docs/compliance.md §6) có rồi thì xem lại xếp hạng (17+ / 18+) |
| Nhãn quyền riêng tư (App Privacy) | — | Liên kết với người dùng: định danh (User ID), nội dung người dùng (story, ảnh), mua hàng, dữ liệu sử dụng (nếu bật PostHog), email (nếu người dùng thêm). **Không** dùng để theo dõi. Không có ATT |
| 1.5 Developer info, hỗ trợ | — | Trang hỗ trợ + email hỗ trợ của đơn vị phát hành (không dùng email cá nhân) |
| Tài khoản demo cho người duyệt | Đăng ký mở nên không bắt buộc | Vẫn đưa tài khoản demo có sẵn coin sandbox |

**Google Play tương đương:** Payments policy (Play Billing cho hàng số), AI-Generated Content policy (báo cáo trong app,
đã có), UGC policy, Data safety form, link xoá tài khoản trên web (`https://lyris.example/#/me` → "Xoá tài khoản"), xếp hạng
IARC, target API level mới nhất, Play Integrity cho quà tạo tài khoản. Tài khoản nhà phát triển **cá nhân** mới phải chạy
thử kín (≥ 12 người thử liên tục 14 ngày) trước khi phát hành; Lyris dùng tài khoản **tổ chức** (G0) nên không bắt buộc,
nhưng vẫn chạy thử kín 14 ngày ở G7.

**Kho phát hành (tạm chọn): chỉ Việt Nam** ở lần ra mắt đầu, trên cả App Store và Google Play. Phát hành ở Mỹ kéo theo
luật xác minh tuổi của một số bang cho kho ứng dụng (và API Declared Age Range của Apple / Play Age Signals của Google
phải tích hợp), EU kéo theo DSA và GDPR: để sau, khi có pháp nhân và luật sư (§20).

## 17. Quyết định

| Quyết định | Ai | Trang |
|---|---|---|
| Hướng đi: máy chủ lớn + App Store; viết thiết kế bây giờ, code sau nộp bài | PO chốt (1A, 4A) | [may-chu-lon-va-app-store](../wiki/decisions/may-chu-lon-va-app-store.md) |
| App di động bằng Capacitor, có ngưỡng đổi | AI chọn | [app-di-dong-capacitor](../wiki/decisions/app-di-dong-capacitor.md) |
| vLLM, FP8, định tuyến dính theo story, prompt tự dựng | PO chốt (2A) + AI chọn chi tiết | [suy-luan-vllm](../wiki/decisions/suy-luan-vllm.md) |
| Postgres, giữ `Repo` + lớp dialect, không ORM | PO chốt (4A) + AI chọn chi tiết | [postgres-giu-repo](../wiki/decisions/postgres-giu-repo.md) |
| Hàng đợi việc nền trên Postgres | AI chọn | [hang-doi-postgres](../wiki/decisions/hang-doi-postgres.md) |
| IAP + Play Billing + VNPay/MoMo vào một sổ; tự xác minh; nợ coin khi hoàn tiền | PO chốt (5A) + AI chọn chi tiết | [thanh-toan-iap-va-cong-vn](../wiki/decisions/thanh-toan-iap-va-cong-vn.md) |
| Phiên opaque cho cả web và app (Bearer), không JWT | AI chọn | [phien-token-cho-app](../wiki/decisions/phien-token-cho-app.md) |
| Container chỉ ở bản host; máy dev vẫn không Docker | AI chọn | [container-chi-khi-host](../wiki/decisions/container-chi-khi-host.md) |
| Fence của lượt chat ở Postgres, khoá Redis chỉ để tối ưu; kind/lý do mới qua bảng tra; lọc đầu ra trước khi stream | AI chọn (sau phản biện, tạm chọn) | [fence-postgres-va-loc-truoc-stream](../wiki/decisions/fence-postgres-va-loc-truoc-stream.md) |

## 18. Kế hoạch chuyển đổi theo giai đoạn (bắt đầu sau 15/11/2026)

Luật chung: mỗi giai đoạn bắt đầu bằng trang tính năng (wiki), viết test trước, kết thúc bằng `verify.sh` xanh **ở cả chế
độ tự chạy** (bản nộp bài không được hỏng). Không giai đoạn nào xoá đường SQLite/Ollama.

| # | Giai đoạn | Tính năng | Điều kiện xong (exit) | Quay lại (rollback) |
|---|---|---|---|---|
| G0 | Chuẩn bị: gắn tag bản nộp bài (`v1.0-nop-bai`), PO trả lời §20, chọn cloud, mở tài khoản Apple Developer (tổ chức), Google Play Console, VNPay/MoMo merchant | — | §20 có câu trả lời; ngân sách GPU có số | Không có gì để quay lại |
| G1 | Tách giao diện trong code, chạy chế độ tự chạy, không đổi hành vi: `BlobStore`, `Gate`, `Locks`, `RateLimiter`, `JobBackend`, `LLMClient` (đã có) | F50–F52 (phần giao diện) | `verify.sh` xanh; không đổi số test; không đổi `data/` | Revert commit (không có dữ liệu mới) |
| G2 | Postgres: dialect, `migrations_pg`, trigger sổ coin, test hai backend | F50 | Toàn bộ pytest xanh trên SQLite **và** Postgres; `test_ledger_append_only_pg` xanh; bot e2e xanh trên Postgres | Mặc định vẫn SQLite; tắt cờ `LYRIS_DB_URL` |
| G3 | Redis + API không trạng thái + hàng đợi Postgres; staging với 3 pod | F51, F52, F59 (staging) | Bài kiểm "giết pod giữa lượt": giữ chỗ nhả ≤ 40 s, story mở lại ≤ 30 s, cổng không rò chỗ, không ví nào lệch; bot e2e xanh qua LB với 3 pod; Redis failover giữa lượt không làm trừ coin hai lần | Chạy 1 pod + không Redis (chế độ một tiến trình vẫn có) |
| G4 | vLLM + gateway trên GPU staging; `run_eval.py` thêm `--backend vllm --base-url` (làm trong F53); bài tải 300 người ảo | F53 | Trên GPU staging (không phải máy Mac, không phải `verify.sh`): `run_eval.py --backend vllm` điểm ≥ Ollama (GGUF) ở mọi kịch bản; bài tải `harness/load/chatters.py`: TTFT p95 ≤ 4 s ở 300 người ảo, tỉ lệ trúng cache ≥ 70 %, phương trình KV §8.3 thoả | `LYRIS_LLM=ollama` trỏ về máy Ollama |
| G5 | S3, quan sát, CI/CD prod, sao lưu; **beta đóng trên web** (đăng ký bằng mã mời theo đợt) ở prod mới | F54, F58, F59 | 14 ngày đạt SLO §12.3; diễn tập khôi phục thành công; 0 ví lệch | DNS về máy cũ (docs/deploy.md) + nhập lại dữ liệu bằng công cụ F62 |
| G6 | Đăng ký mở, Sign in with Apple/Google, kiểm duyệt; Điều khoản/Chính sách mới (`LEGAL_VERSION`); báo trước đặt lại coin ≥ 30 ngày; VNPay/MoMo | F61, F60, F57 | Luật sư duyệt văn bản; đối soát VNPay/MoMo 7 ngày sandbox khớp 100 %; 0 coin cộng khi chưa xác minh | Cờ `LYRIS_SIGNUP=invite`; cờ tắt thanh toán web (gói về "Giá dự kiến") |
| G7 | App iOS/Android (Capacitor) + IAP + Play Billing; TestFlight/internal → duyệt → phát hành theo đợt | F55, F56 | Ngưỡng §16.2 đạt; mua/hoàn tiền sandbox khớp sổ 100 %; qua duyệt Apple và Google | Gỡ bản khỏi bán (App Store "Remove from sale"); web vẫn chạy |
| G8 | Nhập dữ liệu từ bản tự chạy (tuỳ chọn); model LoRA tự train qua vLLM | F62, F41 | Nhập file xuất mẫu ra đúng số story/tin/ký ức; A/B mù LoRA ≥ model gốc | Tắt nút nhập; về model gốc (adapter là tuỳ chọn mỗi request) |

### 18.1 Nhập dữ liệu từ Lyris tự chạy vào bản host (tuỳ chọn, F62)

- Định dạng: chính file `GET /api/account/export` đã có (`lyris-<handle>-<YYYYMMDD>.json`, có `version`), cộng ảnh nếu
  dùng gói `.zip` mới (`export?with_images=1`).
- `#/me` → "Nâng cao" → "Nhập dữ liệu từ Lyris tự chạy" → tải lên (≤ 200 MB) → job `account_import` kiểm `version` và
  cấu trúc, cấp id mới, nhập persona, nhân vật của mình (kèm sổ thế giới, **về Riêng tư**), story + mọi tin nhắn (biến thể,
  đánh giá), ký ức; rồi xếp `state/rebuild` cho mỗi story để tính lại cảm xúc/cảnh, và `embed` cho ký ức.
- **Không** nhập: coin (sổ của máy khác, coin chế độ thử), phiên, sự kiện số liệu, báo cáo, mã mời, bản sao nhân vật
  công khai của người khác (thay bằng liên kết tới nhân vật công khai nếu còn).
- Một tài khoản nhập tối đa 3 lần/ngày; nhập trùng (cùng `uid` story) bỏ qua story đã có.
- Chiều ngược lại (bản host → tự chạy) dùng cùng file: "Tải dữ liệu của tôi" rồi nhập ở máy nhà.

## 19. Chế độ tự chạy (local-first) vẫn sống

`LYRIS_MODE=local` (mặc định) giữ đúng bản hiện tại: một tiến trình, SQLite (`LYRIS_DB_PATH`), Ollama (`OLLAMA_URL`),
worker trong tiến trình, ảnh trên đĩa, cổng sinh trong bộ nhớ, mã mời, chủ máy không tốn coin, nạp coin chế độ thử.
`LYRIS_MODE=hosted` bật: `LYRIS_DB_URL` (Postgres), `LYRIS_REDIS_URL`, `LYRIS_LLM=vllm` + `LYRIS_VLLM_REPLICAS`,
`LYRIS_BLOB=s3`, `LYRIS_SIGNUP=open`, `LYRIS_SAMPLE_ADS=off`, lọc đầu ra (F60), thanh toán thật.

| Giao diện | Bản tự chạy | Bản host |
|---|---|---|
| `Repo` + dialect | SQLite | Postgres |
| `LLMClient` | `OllamaClient` (prefill raw) | `VllmClient` + gateway |
| `JobBackend` | worker asyncio trong tiến trình (như `jobs/worker.py`) | worker pod, `SKIP LOCKED`, scheduler leader |
| `Gate`, `Locks` | asyncio (như `chat/gate.py`) | Redis + Lua |
| `RateLimiter` | bảng `auth_attempts` | bảng + Redis |
| `BlobStore` | thư mục `LYRIS_AVATARS_DIR` | S3 + CDN |
| Thanh toán | chế độ thử (mã nạp) | Apple, Google, VNPay, MoMo |

Mọi test hiện có chạy ở `local`; bộ test thêm chạy `hosted` với Postgres + Redis tạm. `verification/verify.sh` không
cần cloud. Postgres và Redis tạm chạy thẳng trên Mac (`pg_ctl` / `redis-server` qua unix socket, không Docker); F50 thêm
kiểm hai lệnh này vào `environment/doctor.mjs`, và thiếu thì bot/test ghi `infra` chứ không skip (test bị skip không phải
bằng chứng).

## 20. Câu hỏi cho PO

Đã ghi vào `memory/po-questions.md`:

1. **Cloud và vùng:** cloud Việt Nam (FPT / VNG / Viettel, dữ liệu ở Việt Nam) hay cloud quốc tế vùng Singapore (dịch vụ có
   quản lý đầy đủ hơn)? Tạm chọn: dữ liệu ở Việt Nam, GPU ở nơi rẻ nhất đạt SLO.
2. **Ngân sách GPU mỗi tháng** cho 4A (ước tính §15.3: $2.000–4.700 GPU nếu thuê theo giờ, $3.200–7.600 nếu thuê cố định
   theo tháng; tổng $2.800–6.700 theo giờ)? Có chấp nhận cam kết 1 năm để rẻ hơn?
3. **Pháp nhân** đứng tên tài khoản Apple Developer (tổ chức, cần D-U-N-S), Google Play Console, merchant VNPay/MoMo, hoá
   đơn điện tử: công ty nào (nhóm, Apero, hay pháp nhân mới)? Cần kế toán xác nhận thuế (thuế nhà thầu nước ngoài với
   doanh thu IAP, GTGT với doanh thu web).
4. **Nơi lưu dữ liệu:** bắt buộc lưu tại Việt Nam không (cần luật sư theo Luật An ninh mạng, Nghị định 53/2022, Luật Bảo vệ
   dữ liệu cá nhân)? PostHog có bật ở bản host không (chuyển dữ liệu ra nước ngoài)?
5. **Ngày ra mắt** dự kiến cho beta web trên máy chủ (G5) và cho App Store (G7)?
6. Cho phép **thêm thư viện** khi làm bản host (psycopg 3, redis-py, pgvector, thư viện App Store Server của Apple,
   Google API client, boto3, Capacitor và plugin)? Luật hiện tại cấm thêm npm/pip.
7. Rớt mạng giữa lượt thì **câu trả lời vẫn sinh tiếp** và trừ 6 coin (tạm chọn, §4.3) hay dừng như bây giờ?
8. **Hoàn tiền sau khi đã tiêu coin:** ghi phần thiếu thành nợ, lần cộng sau trả nợ trước, có nợ vẫn mua được (tạm chọn,
   §11.1), hay chỉ trừ tới 0 rồi bỏ qua phần thiếu?
9. **Luật sư (Nghị định 147/2024, Cloudflare, giấy phép model):** Lyris có nhân vật công khai và bảng xếp hạng thì có bị
   xếp là mạng xã hội không (cần đăng ký/giấy phép, xác thực số điện thoại)? Tạm chọn: làm sẵn OTP số điện thoại, bắt buộc
   trước khi bật "Công khai" nhân vật (§10). Chữ chat đi qua PoP Cloudflare ngoài Việt Nam có tính là chuyển dữ liệu ra
   nước ngoài không (§13)? Giấy phép trọng số gemma4 có cho dịch vụ thương mại trả tiền và cho fine-tune không (§8.1)?
10. **"Quảng cáo mẫu" (F45)** thưởng coin là nội dung giữ chỗ, dễ bị Apple từ chối (2.1). Tạm chọn: ẩn ở bản host và app
    (nhiệm vụ ngày còn 2 việc: trò chuyện với 3 nhân vật khác nhau +10 và gửi 20 lượt +5, tối đa 15 coin/ngày thay vì 30). Hay thay bằng quảng cáo thật (cần ATT, nhãn quyền riêng
    tư, mạng quảng cáo)?
11. **Kho phát hành:** tạm chọn chỉ Việt Nam ở lần ra mắt đầu (§16.4). Có cần thị trường khác ngay không?
12. **Quà trên web:** quà 300 coin trên web chỉ trao sau khi xác minh email hoặc số điện thoại (§10). Đồng ý không?
    (Năm sinh: PO đã trả lời 2026-11-15, **không hỏi năm sinh**; 16+ theo Điều khoản, 18+ bằng ô tự xác nhận, F48.)

## 21. Phản biện đã áp dụng (2026-11-14)

Bản thiết kế đầu được phản biện theo hai góc: kiến trúc backend và duyệt App Store/Google Play. Mỗi điểm đã đối chiếu
với code thật (`coins/holds.py`, `coins/wallet.py`, `0012_coins.sql`, `db/repo.py`, `llm/render.py`,
`auth/middleware.py`, `coins/missions.py`). Nhận = sửa đúng như phản biện; Sửa lại = nhận vấn đề nhưng chọn cách khác;
Bác = không đổi, kèm lý do.

| # | Điểm phản biện | Kết luận | Đã sửa ở |
|---|---|---|---|
| 1 | Cổng Redis rò chỗ khi pod chết, phần tử ma kẹt đầu hàng; đếm toàn cụm không giữ được "mỗi replica ≤ max-num-seqs" | Nhận | §6, §6.3, F51 |
| 2 | Từ chối `appAccountToken` của tài khoản khác làm kẹt giao dịch đã trả tiền; thiếu `ONE_TIME_CHARGE` | Nhận | §11.1, §11.3, F56 |
| 3 | Lọc đầu ra chạy sau khi đã stream | Nhận, **sửa con số**: phản biện ước lượng đệm 1 câu tốn 150–300 ms, nhưng ở 25–60 token/s một câu 20–40 token mất ~0,4–1,5 s. Chọn đoạn = hết câu **hoặc 24 token**, và thêm SLO "chữ đầu tiên hiện" p50 ≤ 2,5 s riêng, giữ SLO TTFT cũ cho phần server | §4.3, §12.3, §13, F60 |
| 4 | PgBouncer chế độ transaction làm hỏng khoá phiên, LISTEN, prepared statement | Nhận; leader dùng dòng `leader_lease` | §2, §5.1, §7.1, §7.3, F52 |
| 5 | "Giữ `Repo`" bỏ qua mô hình một kết nối; phạm vi bị ước lượng thấp | Nhận | §3, §4.2, §5.5, F50 |
| 6 | Giữ chỗ chưa có fence: pod chậm lỡ lease → lượt miễn phí; khoá Redis mất khi failover | Nhận fence (`FOR UPDATE` dòng giữ chỗ, chỉ mục một giữ chỗ mở là khoá thật, ≤ 40 s). **Bác** "không lưu câu trả lời khi giữ chỗ đã bị nhả": người chơi đã đọc câu đó trên màn, xoá nó đi là mất dữ liệu trước mắt họ và trái luật "lỗi máy không làm người chơi thiệt" (docs/coins.md §3). Thay bằng: vẫn lưu, trừ thẳng cùng `idem_key` nếu đủ coin, không đủ thì miễn và đếm `lyris_hold_lost_total` | §4.3, §5.3, §6.2, F50, F51 |
| 7 | Thêm kind/lý do vào `CHECK` không "chỉ thêm" được | Nhận cho Postgres (bảng tra + FK). **Bác** "ngoại lệ dựng lại bảng cho SQLite": bản tự chạy không bao giờ ghi các giá trị mới (thanh toán thật, lọc đầu ra, báo bận sớm chỉ ở bản host), nên SQLite giữ nguyên `CHECK`, không cần ngoại lệ nào cho luật migration chỉ thêm | §5.2, F50, F59 |
| 8 | BOS đôi, tham số lấy mẫu, `think` qua chat template, tên tham số JSON, 400 khi vượt 8192, mốc GGUF | Nhận cả sáu; chọn gửi **token id** | §8.1, §8.2, F53 |
| 9 | Dòng "Model thật" của F53 không chấm được bằng `verify.sh`; test Postgres/Redis cần công cụ trên Mac | Nhận: hai dòng chuyển sang "Ngoài Done when" (cổng G4 ở staging); thêm `--backend vllm --base-url` vào việc của F53; `doctor.mjs` kiểm `pg_ctl`/`redis-server` | §18, §19, F50, F51, F53 |
| 10 | CSRF chặn app vì `Sec-Fetch-Site: cross-site` | Nhận | §3, §10, F51 |
| 11 | Sandbox chỉ cho danh sách tài khoản → người duyệt tạo tài khoản mới sẽ thấy IAP hỏng | Nhận (nhận cho mọi tài khoản, cờ `sandbox`, trần 3/ngày) | §11.3, F56 |
| 12 | Nghị định 147/2024 (mạng xã hội, xác thực số điện thoại); Cloudflare ngoài Việt Nam | Nhận như câu hỏi luật sư + móc OTP theo cờ (tạm chọn) | §10, §13, §20, F61 |
| 13 | Chi phí giả định thuê theo giờ; chưa trừ thuế; đêm 1 replica không dự phòng | Nhận | §8.6, §12.3, §15.3, §20 |
| 14 | Nghẽn thật là prompt trích xuất; thiếu phương trình KV; bộ quản lý KV lai | Nhận; trích xuất dùng chung phần đầu story chỉ bật khi `f10-ky-uc` không kém | §8.1, §8.3, §15.1 |
| 15 | Hoàn tiền khi có giữ chỗ mở vỡ bất biến; `debt` ngoài sổ không được audit; chặn mua khi có nợ là ngược | Nhận cả ba (bỏ luật chặn mua) | §5.2, §5.3, §11.1, §11.2, F56 |
| 16 | `google:{orderId}` thiếu với mã khuyến mãi; dùng RTDN voided; luật chủ token | Nhận | §11.4, F56 |
| 17 | Job chạy ít nhất một lần; hoàn tất cần fence; `run_after` NULL | Nhận | §7.1, §7.2, F52 |
| 18 | Quét CSAM của Cloudflare chỉ quét sau khi công khai | Nhận | §9, F54, F60 |
| 19 | App Attest không định danh thiết bị; web vẫn nuôi tài khoản được | Nhận (DeviceCheck, Play Integrity device recall, quà web sau xác minh) | §10, F61 |
| 20 | Sign in with Apple thiếu `refresh_token`, thiếu đăng nhập chéo nền tảng; câu chữ 4.8 | Nhận | §10, §16.4, F61 |
| 21 | "Quảng cáo mẫu" là nội dung giữ chỗ (2.1) | Nhận: ẩn ở bản host/app (tạm chọn), hỏi PO | §3, §16.4, §19, §20 |
| 22 | Ghép màn RN vào Capacitor không thực tế; thiếu cách đo; máy Android chưa cụ thể | Nhận | §16.2, F55, [quyết định](../wiki/decisions/app-di-dong-capacitor.md) |
| 23 | `COLLATE NOCASE`, `timestamptz(3)`, `BY DEFAULT`, `coin_day` kiểu `date`, thứ hạng FTS | Nhận | §5.2, F50 |
| P3 | SSE `no-transform`; nối lại khi pod gốc chết; `302` URL ký `no-store`; VNPay (`/pay/return`, IPN thất bại trả `00`, `× 100`, `vnp_CreateDate`); CGNAT; xoá mọi `sess:*` khi khoá; LoRA và cache, giấy phép; chạy thử kín Google Play, kho chỉ Việt Nam, 1.2.1(a) | Nhận hết. Riêng chạy thử kín 12 người/14 ngày: chỉ bắt buộc với tài khoản **cá nhân**; Lyris dùng tài khoản tổ chức nhưng vẫn chạy thử kín. Riêng 1.2.1(a): chưa có cổng tuổi, nên thêm khai năm sinh (tạm chọn) thay vì giả định đã có; sau đó PO bỏ năm sinh (2026-11-15): 16+ theo Điều khoản, 18+ bằng ô tự xác nhận (F48) | §4.1, §4.3, §6, §8.1, §9, §11.5, §13, §16.4, F51, F54, F57 |
