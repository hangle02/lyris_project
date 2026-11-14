#!/usr/bin/env bash
# Lệnh quản lý tài khoản Lyris trên Mac (docs/auth.md §2.4). Chạy được khi app đang chạy.
#   bash scripts/lyris-admin.sh setup-code              # in mã thiết lập mới (khi chủ máy chưa có mật khẩu)
#   bash scripts/lyris-admin.sh reset-password <handle> # đặt mật khẩu tạm, in ra, buộc đổi, đăng xuất mọi thiết bị
#   bash scripts/lyris-admin.sh enable <handle>         # mở khoá tài khoản
#   bash scripts/lyris-admin.sh list                    # handle, vai trò, trạng thái, lần đăng nhập cuối
# DB: LYRIS_DB_PATH nếu có, không thì data/lyris.db. Mã và mật khẩu tạm chỉ in ra cửa sổ này, không vào log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
PYTHON="$BACKEND/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Không thấy $PYTHON. Hãy tạo môi trường backend: cd backend && uv sync" >&2
  exit 1
fi

PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m lyris.auth.cli "$@"
