#!/usr/bin/env bash
# Chạy Lyris kiểu "production" trên một máy, không Docker (docs/deploy.md §4):
#   1. build frontend (npm run build -> frontend/dist);
#   2. backend: uvicorn KHÔNG --reload, một tiến trình, --no-proxy-headers, chỉ nghe 127.0.0.1;
#   3. frontend: `vite preview` phục vụ frontend/dist và proxy /api sang backend (xfwd, giữ Host).
# Dùng để demo, quay video, chạy cho vài người trong nhà/qua đường hầm HTTPS. Ra mắt open web thật thì dùng
# Caddy phục vụ frontend/dist và proxy /api thẳng vào uvicorn (docs/deploy.md §5), KHÔNG đặt Caddy trước
# vite preview (hai chặng proxy làm mọi người chung một IP với các ngưỡng thử sai).
#
# Dùng:   bash scripts/serve.sh          Dừng: Ctrl+C (tắt cả hai).
# Biến môi trường (tuỳ chọn):
#   LYRIS_API_PORT   cổng backend, mặc định 8000 (chỉ nghe 127.0.0.1)
#   LYRIS_WEB_PORT   cổng frontend, mặc định 5173
#   LYRIS_WEB_HOST   địa chỉ frontend nghe, mặc định 127.0.0.1; 0.0.0.0 để máy khác cùng mạng vào
#   LYRIS_SKIP_BUILD=1  không build lại (dùng frontend/dist đang có)
#   Mọi biến LYRIS_* / OLLAMA_URL của backend (README, docs/deploy.md §6) được truyền nguyên cho uvicorn.
# Lần đầu (chủ máy chưa có mật khẩu) backend in mã thiết lập ra cửa sổ này (stderr). Đừng chuyển output của
# backend vào file log; nếu có làm thì phải lọc khung mã thiết lập (docs/auth.md §9.2).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
UVICORN="$BACKEND/.venv/bin/uvicorn"
# Email liên hệ của nhóm vận hành (trang đăng nhập + văn bản pháp lý). Đặt LYRIS_CONTACT khác để đổi.
export LYRIS_CONTACT="${LYRIS_CONTACT:-lethuhang.cv@gmail.com}"

API_PORT="${LYRIS_API_PORT:-8000}"
WEB_PORT="${LYRIS_WEB_PORT:-5173}"
WEB_HOST="${LYRIS_WEB_HOST:-127.0.0.1}"

if [[ ! -x "$UVICORN" ]]; then
  echo "Không thấy $UVICORN. Hãy tạo môi trường backend: cd backend && uv sync" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Không thấy npm. Hãy cài Node.js 22." >&2
  exit 1
fi

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Cổng $port đang bị chiếm. Hãy tắt tiến trình đang dùng cổng này hoặc chọn cổng khác:" >&2
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2 || true
    exit 1
  fi
done

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "Cài thư viện frontend (npm install)..."
  (cd "$FRONTEND" && npm install)
fi

if [[ "${LYRIS_SKIP_BUILD:-0}" != "1" ]]; then
  echo "Build frontend (frontend/dist)..."
  (cd "$FRONTEND" && npm run build)
elif [[ ! -f "$FRONTEND/dist/index.html" ]]; then
  echo "LYRIS_SKIP_BUILD=1 nhưng chưa có frontend/dist. Bỏ biến này để build." >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

kill_tree() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

cleanup() {
  trap - INT TERM EXIT
  echo
  echo "Đang tắt Lyris..."
  [[ -n "$FRONTEND_PID" ]] && kill_tree "$FRONTEND_PID"
  [[ -n "$BACKEND_PID" ]] && kill_tree "$BACKEND_PID"
  wait 2>/dev/null || true
  echo "Đã tắt backend và frontend."
}
trap 'cleanup; exit 0' INT TERM
trap cleanup EXIT

echo "Khởi động backend: http://127.0.0.1:$API_PORT (không reload, một tiến trình)"
# Một tiến trình duy nhất: cổng sinh chung, giới hạn thử sai và hàng đợi nằm trong bộ nhớ của tiến trình.
# --no-proxy-headers: IP thật do lyris.auth.client_ip() tự đọc (phần tử cuối của X-Forwarded-For).
(cd "$BACKEND" && PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" exec "$UVICORN" lyris.api.app:app \
  --host 127.0.0.1 --port "$API_PORT" --no-proxy-headers --workers 1) &
BACKEND_PID=$!

echo "Khởi động frontend (bản build): http://$WEB_HOST:$WEB_PORT"
(cd "$FRONTEND" && LYRIS_API_URL="http://127.0.0.1:$API_PORT" exec npm run preview -- \
  --host "$WEB_HOST" --port "$WEB_PORT" --strictPort) &
FRONTEND_PID=$!

AUTH_STATE=""
for _ in $(seq 1 30); do
  if AUTH_STATE="$(curl -s --max-time 2 "http://127.0.0.1:$API_PORT/api/auth/me" 2>/dev/null)" && [[ -n "$AUTH_STATE" ]]; then
    break
  fi
  AUTH_STATE=""
  sleep 1
done

echo
if [[ -z "$AUTH_STATE" ]]; then
  echo "Backend chưa trả lời sau 30 giây; xem lỗi ở phía trên." >&2
else
  echo "Lyris đang chạy. Mở trình duyệt: http://localhost:$WEB_PORT"
fi
if [[ "$WEB_HOST" == "0.0.0.0" ]]; then
  echo "Máy khác cùng mạng vào được (cần đăng nhập). Qua http:// mật khẩu không được mã hoá."
fi
if [[ "$AUTH_STATE" == *'"setup_required":true'* ]]; then
  echo
  echo "Lyris cần bạn đặt mật khẩu cho tài khoản chủ máy."
  echo "Mở http://localhost:$WEB_PORT và nhập mã thiết lập in ở phía trên."
  if [[ -n "${LYRIS_DB_PATH:-}" ]]; then
    # Cùng DB với server đang chạy (không có biến này thì lệnh dùng data/lyris.db).
    echo "Không thấy mã? Chạy: LYRIS_DB_PATH=$(printf '%q' "$LYRIS_DB_PATH") bash scripts/lyris-admin.sh setup-code"
  else
    echo "Không thấy mã? Chạy: bash scripts/lyris-admin.sh setup-code"
  fi
fi
echo "Nhấn Ctrl+C để tắt cả hai."
echo

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
echo "Một tiến trình đã dừng; tắt phần còn lại." >&2
exit 1
