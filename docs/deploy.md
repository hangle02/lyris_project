# Chạy Lyris production (open web, không Docker)

> **English summary.** Lyris launches on the open web as a PWA served over HTTPS from one machine with a GPU:
> Ollama runs the 12B model on `127.0.0.1:11434`; the FastAPI backend runs as a single uvicorn process on
> `127.0.0.1:8000` with `--no-proxy-headers` and no `--reload`; **Caddy** terminates HTTPS, serves the static
> build (`frontend/dist`) and proxies `/api` to uvicorn. Caddy is the only proxy hop, so the backend's
> `client_ip()` (last `X-Forwarded-For` element from a 127.0.0.1 peer) sees the real visitor IP. Set
> `LYRIS_COOKIE_SECURE=1`, back up the SQLite file with the online backup command, restart to apply migrations,
> and expect about two replies generated at once per 12B model. For a demo or a quick production-like run on one
> machine: `bash scripts/serve.sh` (frontend build + uvicorn without reload + `vite preview` with the `/api` proxy).

Trạng thái: tài liệu vận hành cho lần ra mắt. `scripts/serve.sh` đã chạy thử (cổng 8064/8065, DB tạm). Cấu hình
Caddy và các file systemd ở dưới **chưa chạy thử trong repo này** (máy phát triển không cài Caddy); làm theo §10 để
kiểm trước khi mở cho người dùng. Docker: chưa dùng ([quyết định](../wiki/decisions/chua-dung-docker.md)).

Kế hoạch sau khi nộp bài (nhiều máy chủ, Postgres, Redis, vLLM, App Store): [server.md](server.md). Trang này vẫn là cách
chạy bản tự chạy một máy.

## 1. Kiến trúc

```
Trình duyệt / PWA ──HTTPS──► Caddy :443 ──┬─ /api/*  ──► uvicorn 127.0.0.1:8000 (1 tiến trình) ──► Ollama 127.0.0.1:11434
                                          └─ còn lại ──► file tĩnh frontend/dist (index.html, assets, manifest)
                                                          SQLite: /var/lib/lyris/lyris.db (+ avatars/)
```

- Chỉ Caddy nghe ra ngoài (80/443). uvicorn và Ollama chỉ nghe `127.0.0.1`.
- **Một tiến trình uvicorn** (`--workers 1`). Cổng sinh chung (`LYRIS_CHAT_SLOTS`), hàng đợi, giới hạn thử sai,
  giới hạn `POST /api/events` và bộ chuyển tiếp PostHog đều nằm trong bộ nhớ của tiến trình; SQLite dùng một kết
  nối. Nhiều worker sẽ làm sai các giới hạn này.
- **Một chặng proxy.** `client_ip()` (docs/auth.md §3.7) tin phần tử **cuối** của `X-Forwarded-For` khi peer là
  127.0.0.1. Caddy đặt `X-Forwarded-For` bằng IP thật của người truy cập, nên đúng. Không đặt Caddy trước
  `vite preview` (hai chặng: Vite nối 127.0.0.1 vào cuối, mọi người chung một IP với các ngưỡng thử sai).
- **Caddy giữ nguyên `Host`** (mặc định). Kiểm CSRF so `Origin` với `Host`; đừng thêm `header_up Host ...`.

## 2. Phần cứng

| | Linux + NVIDIA | Apple Silicon |
|---|---|---|
| Bộ nhớ cho model | GPU từ **16 GB VRAM** (vd. RTX 4080/4090, L4, A10); 24 GB thoải mái hơn cho 2 lượt cùng lúc | Từ **24 GB** bộ nhớ hợp nhất (M2/M3/M4 Pro trở lên khuyên dùng) |
| RAM hệ thống | 16 GB+ | (chung với model) |
| Ổ đĩa | SSD 40 GB+ (model ~8 GB, `bge-m3` ~1.2 GB, DB, sao lưu) | như bên trái |
| Hệ điều hành | Ubuntu 22.04/24.04 LTS (hoặc bản Linux có systemd) | macOS 14+ |
| Mạng | IP công khai, mở cổng 80 và 443, một tên miền trỏ về máy | như bên trái; máy không được ngủ (§9) |

Model 12B với `num_ctx` 8192 và hai lượt song song cần cả trọng số và bộ nhớ đệm KV trên GPU. Nếu `ollama ps` không
báo `100% GPU` (bị đẩy một phần sang CPU), hạ `OLLAMA_NUM_PARALLEL=1` và `LYRIS_CHAT_SLOTS=1`.

## 3. Ollama

**Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh        # cài Ollama và service systemd "ollama"
sudo systemctl edit ollama                           # thêm phần dưới đây, lưu lại
```

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
```

```bash
sudo systemctl restart ollama
ollama pull gemma4:12b         # model chat (mặc định), cũng dùng cho việc nền
ollama pull bge-m3             # tuỳ chọn: tìm ký ức theo nghĩa
ollama ps                      # sau lượt chat đầu: gemma4:12b, 100% GPU
```

**macOS:** cài app Ollama, rồi `bash scripts/ollama-env.sh` (đặt đúng các biến trên bằng LaunchAgent), mở lại
Ollama, `ollama pull` như trên.

- `OLLAMA_NUM_PARALLEL` phải bằng `LYRIS_CHAT_SLOTS`.
- Không bao giờ mở cổng 11434 ra ngoài (Ollama không có xác thực).
- Lyris gửi `keep_alive: 30m` mỗi lần gọi: model rời bộ nhớ sau 30 phút không ai chat, và lượt đầu sau đó phải nạp
  lại (vài chục giây). Muốn giữ nóng giờ cao điểm, gọi định kỳ (mỗi 20 phút, cron/systemd timer) **cùng `num_ctx`
  với app** (khác `num_ctx` làm Ollama nạp lại model):

  ```bash
  curl -s http://127.0.0.1:11434/api/generate \
    -d '{"model":"gemma4:12b","keep_alive":"30m","options":{"num_ctx":8192}}' >/dev/null
  ```

## 4. Chạy nhanh trên một máy: `scripts/serve.sh`

Cho demo, quay video, hoặc vài người dùng qua mạng nhà. Không dùng cho ra mắt open web (không có HTTPS).

```bash
cd backend && uv sync && cd ..
bash scripts/serve.sh                                   # build frontend, uvicorn không reload, vite preview
LYRIS_WEB_HOST=0.0.0.0 bash scripts/serve.sh            # cho máy khác cùng mạng vào
LYRIS_API_PORT=8064 LYRIS_WEB_PORT=8065 LYRIS_DB_PATH=/tmp/lyris-demo/lyris.db bash scripts/serve.sh   # DB riêng, cổng riêng
```

Script làm:
1. `npm run build` → `frontend/dist` (bỏ qua bằng `LYRIS_SKIP_BUILD=1`);
2. `uvicorn lyris.api.app:app --host 127.0.0.1 --port $LYRIS_API_PORT --no-proxy-headers --workers 1` (không `--reload`);
3. `vite preview --host $LYRIS_WEB_HOST --port $LYRIS_WEB_PORT --strictPort`, proxy `/api` sang backend với
   `xfwd` và giữ `Host` (cấu hình `preview.proxy` trong `frontend/vite.config.ts`, giống bản dev);
4. đợi `/api/auth/me`, in hướng dẫn đặt mật khẩu chủ máy nếu cần; Ctrl+C tắt cả hai.

Kiểm cổng trước khi chạy (cổng bận thì dừng, không đụng tiến trình khác). Mọi biến `LYRIS_*` / `OLLAMA_URL` đặt
trước lệnh được truyền cho backend.

## 5. Ra mắt open web: Caddy + systemd (Linux)

### 5.1 Cài app

```bash
sudo useradd --system --create-home --home-dir /opt/lyris --shell /usr/sbin/nologin lyris
# Ubuntu tạo thư mục nhà với HOME_MODE 0750: mở quyền đi qua để bạn `cd` vào được và Caddy (user `caddy`)
# đọc được /opt/lyris/app/frontend/dist (§5.4). Không có dòng này: mọi trang trả 403/404, chỉ /api chạy.
sudo chmod 755 /opt/lyris
sudo -u lyris git clone <repo> /opt/lyris/app
cd /opt/lyris/app
sudo -u lyris bash -c 'cd backend && uv sync --frozen'                   # Python 3.12, cần uv
sudo -u lyris bash -c 'cd frontend && npm ci && npm run build'           # Node.js 22 → frontend/dist
sudo mkdir -p /var/lib/lyris /var/backups/lyris /etc/lyris
sudo chown lyris:lyris /var/lib/lyris /var/backups/lyris
```

### 5.2 Biến môi trường: `/etc/lyris/lyris.env` (`chmod 600`, chủ `root`)

```ini
LYRIS_DB_PATH=/var/lib/lyris/lyris.db
LYRIS_AVATARS_DIR=/var/lib/lyris/avatars
LYRIS_CHAT_MODEL=gemma4:12b
LYRIS_NUM_CTX=8192
LYRIS_CHAT_SLOTS=2
LYRIS_COOKIE_SECURE=1
OLLAMA_URL=http://127.0.0.1:11434
LYRIS_APP_VERSION=1.0.0
# Số liệu: bỏ trống thì sự kiện chỉ nằm trong DB của app
LYRIS_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxx
LYRIS_POSTHOG_HOST=https://eu.i.posthog.com
# Liên hệ của người vận hành (email hoặc https://): trang đăng nhập ("Xin mã mời", "Quên mật khẩu") và văn bản pháp lý
LYRIS_CONTACT=lethuhang.cv@gmail.com
```

Bảng đầy đủ ở §6. Khoá PostHog chỉ nằm trong file này, không commit vào git; Lyris không bao giờ in nó ra log.

### 5.3 Service backend: `/etc/systemd/system/lyris.service`

```ini
[Unit]
Description=Lyris backend
After=network-online.target ollama.service
Wants=ollama.service

[Service]
User=lyris
Group=lyris
WorkingDirectory=/opt/lyris/app/backend
EnvironmentFile=/etc/lyris/lyris.env
Environment=PYTHONPATH=/opt/lyris/app/backend
ExecStart=/opt/lyris/app/backend/.venv/bin/uvicorn lyris.api.app:app \
  --host 127.0.0.1 --port 8000 --no-proxy-headers --workers 1
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/lyris /var/backups/lyris
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now lyris
journalctl -u lyris -f              # log của backend
```

**Mã thiết lập chủ máy.** Lần đầu, backend in mã thiết lập ra stderr, nên mã nằm trong journal. Ngay sau khi chạy,
lấy một mã mới chỉ in ra cửa sổ của bạn (mã cũ trong journal hết hiệu lực), rồi đặt mật khẩu chủ máy qua trang web
ngay:

```bash
sudo -u lyris env LYRIS_DB_PATH=/var/lib/lyris/lyris.db bash /opt/lyris/app/scripts/lyris-admin.sh setup-code
```

Chỉ `root`/nhóm `adm` đọc được journal. Không chuyển log của backend ra file công khai.

**Giữ log tối đa 30 ngày.** Log của backend có @handle và IP của mỗi lần đăng nhập, tạo tài khoản, đổi mật khẩu, xoá
tài khoản. Chính sách quyền riêng tư (§2, §6, §7) hứa giữ tối đa 30 ngày, nên đặt hạn cho journald:

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nMaxRetentionSec=30day\n' | sudo tee /etc/systemd/journald.conf.d/lyris-retention.conf
sudo systemctl restart systemd-journald
```

Nếu sao lưu hay chuyển log đi nơi khác, giữ cùng hạn 30 ngày.

### 5.4 Caddy: `/etc/caddy/Caddyfile`

```caddy
lyris.example.com {
	encode zstd gzip

	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "same-origin"
		-Server
	}

	# API: một chặng proxy. Caddy giữ Host gốc và đặt X-Forwarded-For = IP người truy cập,
	# X-Forwarded-Proto = https. Không thêm header_up Host (hỏng kiểm CSRF Origin == Host).
	handle /api/* {
		reverse_proxy 127.0.0.1:8000 {
			flush_interval -1          # SSE: đẩy từng chữ ngay, không gom
		}
	}

	# Giao diện: file tĩnh của bản build. App dùng đường dẫn dạng #/..., nên try_files chỉ để an toàn.
	handle {
		root * /opt/lyris/app/frontend/dist
		@hashed path /assets/*
		header @hashed Cache-Control "public, max-age=31536000, immutable"
		try_files {path} /index.html
		file_server
	}
}
```

```bash
sudo apt install caddy             # theo hướng dẫn cài của Caddy cho Ubuntu/Debian
sudo systemctl reload caddy        # Caddy tự lấy và gia hạn chứng chỉ HTTPS (Let's Encrypt)
```

- HTTPS là bắt buộc: mật khẩu và cookie phiên đi trên đường truyền. Với `LYRIS_COOKIE_SECURE=1` (và
  `X-Forwarded-Proto: https` từ Caddy), cookie đăng nhập có `Secure` và tiền tố `__Host-`.
- `/docs`, `/openapi.json` đã tắt trong app; Caddy cũng chỉ chuyển `/api/*` nên không có gì khác của backend lộ ra.
- Thư mục gốc web là `frontend/dist`, không phải repo: DB và `data/` không bao giờ nằm dưới thư mục gốc web.
- Đặt đường hầm (Cloudflare Tunnel, Tailscale Funnel...) trước Caddy thì mọi người tới từ 127.0.0.1: giới hạn thử
  sai theo IP thành một nhóm chung (giới hạn theo tài khoản và handle vẫn đúng). Ưu tiên IP công khai; nếu buộc phải
  dùng đường hầm, kiểm `auth_attempts.ip` (§10) trước khi ra mắt.

### 5.5 Apple Silicon

Cùng kiến trúc: Ollama app (+ `scripts/ollama-env.sh`), Caddy (`brew install caddy`, `brew services start caddy`,
Caddyfile ở `$(brew --prefix)/etc/Caddyfile`), backend bằng đúng lệnh uvicorn ở §5.3 chạy trong một LaunchAgent
hoặc một cửa sổ Terminal luôn mở. Router chuyển cổng 80/443 về máy Mac. Tắt ngủ: `sudo pmset -a sleep 0
disksleep 0` (hoặc chạy `caffeinate -s` cùng app).

## 6. Biến môi trường

| Biến | Mặc định | Production | Ý nghĩa |
|---|---|---|---|
| `LYRIS_DB_PATH` | `data/lyris.db` | `/var/lib/lyris/lyris.db` | File SQLite (một file + `-wal`, `-shm`). Thư mục tự tạo. |
| `LYRIS_AVATARS_DIR` | `<thư mục DB>/avatars` | `/var/lib/lyris/avatars` | Ảnh đại diện, ảnh bìa, ảnh persona. Sao lưu cùng DB. |
| `LYRIS_CHAT_MODEL` | `gemma4:12b` | `gemma4:12b` | Model chat, cũng cho trích xuất và tóm tắt nền. |
| `LYRIS_DRAFT_MODEL` | = model chat | để trống | Model cho "AI viết nháp" nhân vật. |
| `LYRIS_EXTRACT_MODEL` | = model chat | để trống | Model cho việc nền (đã đo: dùng chính model chat tốt hơn). |
| `LYRIS_EMBED_MODEL` | `bge-m3` nếu đã cài | `bge-m3` | Tìm ký ức theo nghĩa; không có thì tìm theo từ khoá. |
| `LYRIS_NUM_CTX` | `8192` | `8192` | Context. Mọi lời gọi dùng một giá trị (đổi là Ollama nạp lại model). |
| `LYRIS_CHAT_SLOTS` | `2` | `= OLLAMA_NUM_PARALLEL` | Số lượt sinh cùng lúc trên cả máy; người thứ ba xếp hàng. |
| `LYRIS_COOKIE_SECURE` | `0` | **`1`** | Cookie đăng nhập luôn có `Secure`. Bắt buộc khi chạy HTTPS. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | như mặc định | Địa chỉ Ollama. |
| `LYRIS_POSTHOG_KEY` | trống | khoá dự án `phc_…` | Bật gửi sự kiện sang PostHog (ngoài DB của app). Không bao giờ in ra log. |
| `LYRIS_POSTHOG_HOST` | `https://us.i.posthog.com` | `https://eu.i.posthog.com` nếu dự án ở EU | Phải bắt đầu bằng `https://` (`http://` hay thiếu giao thức: backend báo lỗi và không chạy). |
| `LYRIS_CONTACT` | (trống; `scripts/dev.sh` và `scripts/serve.sh` đặt sẵn `lethuhang.cv@gmail.com`) | Email hỗ trợ của nhóm, hoặc một trang `https://` | Trang đăng nhập hiện "Chưa có mã mời? Xin mã mời" và "Quên mật khẩu? Nhờ người quản lý đặt lại"; `GET /api/legal/*` điền vào chỗ [ĐIỀN EMAIL LIÊN HỆ]. Phải là email hoặc `https://`. |
| `LYRIS_APP_VERSION` | phiên bản gói (`0.1.0`) | số phiên bản ra mắt | Gắn vào mọi sự kiện để so trước/sau mỗi lần cập nhật. |

Chỉ cho `scripts/serve.sh`: `LYRIS_API_PORT` (8000), `LYRIS_WEB_PORT` (5173), `LYRIS_WEB_HOST` (127.0.0.1),
`LYRIS_SKIP_BUILD`. Chỉ cho Vite: `LYRIS_API_URL` (địa chỉ backend của proxy `/api`).

## 7. Sao lưu

SQLite chạy ở chế độ WAL: **không `cp` file `.db` khi app đang chạy** (bản chép có thể hỏng). Dùng lệnh backup trực
tuyến của SQLite (`sudo apt install sqlite3`; macOS có sẵn), chạy được trong lúc app phục vụ:

```bash
# /opt/lyris/backup.sh, chạy bằng user lyris mỗi đêm (cron hoặc systemd timer)
set -euo pipefail
STAMP=$(date +%Y%m%d-%H%M)
sqlite3 /var/lib/lyris/lyris.db ".backup '/var/backups/lyris/lyris-$STAMP.db'"
sqlite3 "/var/backups/lyris/lyris-$STAMP.db" "PRAGMA integrity_check;" | grep -qx ok
tar -C /var/lib/lyris -czf "/var/backups/lyris/avatars-$STAMP.tgz" avatars
find /var/backups/lyris -type f -mtime +14 -delete                 # giữ 14 ngày
```

- Chép bản sao lưu ra ngoài máy (ổ khác, dịch vụ lưu trữ có mã hoá). Bản sao lưu chứa story riêng tư của mọi
  người: chỉ người vận hành đọc được.
- Thử khôi phục mỗi tháng: dừng `lyris`, chép bản `.db` về `LYRIS_DB_PATH` (xoá `-wal`, `-shm` cũ), bung `avatars`,
  chạy lại.
- Chính sách quyền riêng tư đã nói: dữ liệu đã xoá có thể còn trong bản sao lưu cũ tới khi bản đó bị thay thế
  (14 ngày theo lịch trên).

## 8. Cập nhật và migration

```bash
sudo -u lyris bash /opt/lyris/backup.sh                       # 1. sao lưu trước
cd /opt/lyris/app && sudo -u lyris git pull                    # 2. code mới
sudo -u lyris bash -c 'cd backend && uv sync --frozen'          # 3. thư viện
sudo -u lyris bash -c 'cd frontend && npm ci && npm run build'  # 4. giao diện mới (Caddy phục vụ ngay)
sudo systemctl restart lyris                                    # 5. backend; migration tự chạy lúc khởi động
```

- Migration (`backend/lyris/db/migrations/NNNN_*.sql`) chạy theo `PRAGMA user_version` khi backend khởi động, chỉ
  thêm bảng/cột (additive). File migration đã phát hành không bao giờ sửa; thay đổi mới là một file số mới.
- **Không có migration lùi.** Muốn quay về bản cũ: dừng app, khôi phục bản sao lưu ở bước 1, checkout code cũ.
- Restart làm đứt các lượt đang stream (người chơi bấm "Thử lại"). Cập nhật vào giờ vắng; xem DAU theo giờ ở số liệu.
- Đổi `LEGAL_VERSION` (khi sửa Điều khoản/Chính sách) thì mọi người được hỏi đồng ý lại một lần (docs/compliance.md §3).

## 9. Sức chứa (ước tính)

Một model 12B trên một GPU ≈ **2 lượt sinh cùng lúc** (`OLLAMA_NUM_PARALLEL=2`); người thứ ba thấy "Có người khác
đang trò chuyện..." và xếp hàng. Sau mỗi lượt còn một việc nền (ghi nhớ, cảm xúc) cũng dùng model.

| | Apple Silicon 24 GB (đã đo) | GPU NVIDIA 24 GB (ước tính, chưa đo) |
|---|---|---|
| Tốc độ sinh `gemma4:12b` | ~12 token/s (đo ở bake-off, docs/plan.md) | thường nhanh hơn vài lần, tuỳ băng thông bộ nhớ |
| Một câu trả lời (~300 token) + việc nền | ~25 s + ~15 s | ~5-10 s + vài giây |
| Người **đang chat cùng lúc** (mỗi người một lượt mỗi ~60-90 s) | khoảng 3-5 | khoảng 10-20 |

- Chưa đo tốc độ khi hai lượt chạy song song trên cùng model (docs/auth.md §5.1). Số trên là ước tính để lên kế hoạch;
  đo lại bằng `reply_completed` (`ttft_bucket`, `duration_ms`, `waited`) trong tuần đầu.
- Dấu hiệu cần thêm máy: `waited = true` trong > 20 % `reply_completed`, hoặc `reply_failed{reason: queue_timeout}`
  tăng. Lyris chưa chạy được nhiều máy chung một DB; tăng sức chứa = GPU mạnh hơn, hoặc (Round 2) tách Ollama ra
  máy GPU riêng qua `OLLAMA_URL` và giới hạn số tài khoản mời vào.
- Đăng ký hiện **cần mã mời** (chủ máy tạo trong "Quản lý tài khoản"). Với sức chứa trên, ra mắt bằng mã mời theo
  đợt là cách giữ chất lượng: phát mã cho cộng đồng theo từng đợt, xem số liệu rồi mở thêm.

## 10. Kiểm trước khi mở cửa

- [ ] `https://<tên miền>/` mở được, ổ khoá hợp lệ; `http://` chuyển sang `https://`.
- [ ] `curl -s https://<tên miền>/api/legal/privacy | head -c 80` trả JSON (route công khai).
- [ ] Trên máy chủ: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/docs` → 404, và
      `.../openapi.json` → 404 (qua Caddy, đường dẫn ngoài `/api` chỉ trả giao diện).
- [ ] `curl -s -o /dev/null -w '%{http_code}' -X POST https://<tên miền>/api/auth/login` (thiếu `X-Lyris`) → 403.
- [ ] Đặt mật khẩu chủ máy, đăng nhập từ điện thoại qua 4G. DevTools → Application → Cookies: cookie phiên có
      `Secure`, `HttpOnly`, tên bắt đầu bằng `__Host-`.
- [ ] Sai mật khẩu 1 lần từ điện thoại, rồi `sqlite3 -readonly /var/lib/lyris/lyris.db "SELECT ip FROM
      auth_attempts ORDER BY id DESC LIMIT 1"` ra IP 4G của điện thoại (không phải 127.0.0.1).
- [ ] Một lượt chat chạy chữ từng chút (SSE không bị gom), `ollama ps` báo 100% GPU.
- [ ] Thêm vào màn hình chính (iOS Safari: Chia sẻ → "Thêm vào MH chính"; Android Chrome: menu → "Thêm vào màn
      hình chính"): mở ra toàn màn hình, có `app_opened{display_mode: standalone}` trong số liệu.
- [ ] Số liệu: tab "Số liệu" có số; nếu có PostHog thì sự kiện hiện trong PostHog sau ~1 phút.
- [ ] Đã đặt `LYRIS_CONTACT`: trang đăng nhập có "Xin mã mời", `curl -s https://<tên miền>/api/legal/privacy` không còn
      "[ĐIỀN EMAIL LIÊN HỆ]" (docs/compliance.md §5).
- [ ] Đã đặt journald `MaxRetentionSec=30day` (§5.3) để log có handle/IP không giữ quá 30 ngày.
- [ ] Sao lưu đêm đầu tiên đã chạy và đã thử khôi phục.

## 11. Theo dõi

| Theo dõi | Cách |
|---|---|
| App còn sống | Dịch vụ uptime bên ngoài gọi `https://<tên miền>/api/legal/terms` mỗi 5 phút (công khai, nhẹ). `/api/health` cần đăng nhập (chủ máy thấy cả tình trạng model). |
| Model | `curl -s 127.0.0.1:11434/api/tags`; `ollama ps`; `nvidia-smi` (VRAM, nhiệt độ) hoặc Activity Monitor trên Mac. |
| Log | `journalctl -u lyris`, `journalctl -u ollama`, log của Caddy. Log của Lyris không chứa nội dung chat, mật khẩu hay khoá. |
| Chất lượng dịch vụ | Tab "Số liệu" của chủ máy và export: tỉ lệ `reply_failed` (theo `reason`), `ttft_bucket`, `waited`, `login_failed{reason: rate_limited}` (dấu hiệu tấn công). |
| An toàn nội dung | Tab "Báo cáo" mỗi ngày; mọi báo cáo `minor_safety` xem trong 24 giờ. |
| Ổ đĩa | `df -h /var/lib/lyris /var/backups/lyris`; DB lớn dần theo story; sự kiện số liệu tự xoá sau 180 ngày. |
| Chứng chỉ | Caddy tự gia hạn; bật cảnh báo hết hạn chứng chỉ nếu dịch vụ uptime có. |

## Tóm tắt

- Một máy có GPU (NVIDIA ≥ 16 GB VRAM hoặc Apple Silicon ≥ 24 GB), Ollama + `gemma4:12b`, một uvicorn không reload
  với `--no-proxy-headers --workers 1`, Caddy phục vụ `frontend/dist` và proxy `/api` qua HTTPS.
- `LYRIS_COOKIE_SECURE=1`, khoá PostHog trong file env (tuỳ chọn), sao lưu bằng `sqlite3 .backup` mỗi đêm.
- Cập nhật: sao lưu → `git pull` → `uv sync` → `npm ci && npm run build` → restart (migration tự chạy).
- Sức chứa: ~2 lượt sinh cùng lúc mỗi model 12B; ra mắt theo đợt mã mời.
- Demo nhanh trên một máy: `bash scripts/serve.sh`.
