#!/usr/bin/env bash
# Chạy Lyris ở chế độ phát triển: backend (uvicorn, cổng 8000) + frontend (Vite, cổng 5173).
# Dùng: bash scripts/dev.sh      Dừng: Ctrl+C (tắt cả hai).
# Mặc định frontend mở cho cả mạng LAN (điện thoại cùng Wi-Fi vào được); backend chỉ nghe ở máy này,
# điện thoại gọi API qua proxy của Vite. Mọi người phải đăng nhập. Qua Wi-Fi, mật khẩu không được mã hoá;
# ra ngoài thì dùng Tailscale (Phase 6).
# Lần đầu (chủ máy chưa có mật khẩu) backend in mã thiết lập ra cửa sổ này (stderr). Đừng chuyển output của
# backend vào file log; nếu có làm thì phải lọc khung mã thiết lập (docs/auth.md §9.2).
# Chỉ mở trên máy này: LYRIS_LAN=0 bash scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
UVICORN="$BACKEND/.venv/bin/uvicorn"

if [[ ! -x "$UVICORN" ]]; then
  echo "Không thấy $UVICORN. Hãy tạo môi trường backend: cd backend && uv sync" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Không thấy npm. Hãy cài Node.js 22." >&2
  exit 1
fi

for port in 8000 5173; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Cổng $port đang bị chiếm. Hãy tắt tiến trình đang dùng cổng này rồi chạy lại:" >&2
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2 || true
    exit 1
  fi
done

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "Cài thư viện frontend (npm install)..."
  (cd "$FRONTEND" && npm install)
fi

BACKEND_PID=""
FRONTEND_PID=""

# Tắt cả cây tiến trình con (uvicorn --reload sinh thêm worker, npm sinh vite).
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

echo "Khởi động backend: http://127.0.0.1:8000"
# --no-proxy-headers: IP thật do lyris.auth.client_ip() tự đọc (phần tử cuối của X-Forwarded-For mà Vite
# nối vào); mặc định của uvicorn để client qua 127.0.0.1 tự đặt IP (docs/auth.md §3.7).
(cd "$BACKEND" && PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" exec "$UVICORN" lyris.api.app:app \
  --host 127.0.0.1 --port 8000 --no-proxy-headers --reload --reload-dir "$BACKEND/lyris") &
BACKEND_PID=$!

VITE_HOST_ARGS=()
LAN_URL=""
if [[ "${LYRIS_LAN:-1}" != "0" ]]; then
  VITE_HOST_ARGS=(--host 0.0.0.0)
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  [[ -n "$LAN_IP" ]] && LAN_URL="http://$LAN_IP:5173"
fi

echo "Khởi động frontend: http://localhost:5173"
(cd "$FRONTEND" && exec npm run dev -- ${VITE_HOST_ARGS[@]+"${VITE_HOST_ARGS[@]}"}) &
FRONTEND_PID=$!

# Đợi backend trả lời (tối đa 30 giây) để biết chủ máy đã đặt mật khẩu chưa. Chỉ đọc /api/auth/me.
AUTH_STATE=""
for _ in $(seq 1 30); do
  if AUTH_STATE="$(curl -s --max-time 2 http://127.0.0.1:8000/api/auth/me 2>/dev/null)" && [[ -n "$AUTH_STATE" ]]; then
    break
  fi
  AUTH_STATE=""
  sleep 1
done

echo
echo "Lyris đang chạy. Mở trình duyệt: http://localhost:5173"
if [[ -n "$LAN_URL" ]]; then
  echo "Trên điện thoại (cùng Wi-Fi, cần đăng nhập): $LAN_URL"
  echo "Qua Wi-Fi, mật khẩu không được mã hoá. Chỉ dùng ở mạng nhà; ra ngoài thì dùng Tailscale."
fi
if [[ "$AUTH_STATE" == *'"setup_required":true'* ]]; then
  echo
  echo "Lyris cần bạn đặt mật khẩu cho tài khoản chủ máy."
  echo "Mở http://localhost:5173 trên Mac này và nhập mã thiết lập in ở phía trên."
  echo "Không thấy mã? Chạy: bash scripts/lyris-admin.sh setup-code"
fi
echo "Nhấn Ctrl+C để tắt cả hai."
echo

# Một trong hai tiến trình thoát (lỗi hoặc bị tắt) thì tắt luôn cái còn lại.
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
echo "Một tiến trình đã dừng; tắt phần còn lại." >&2
exit 1
