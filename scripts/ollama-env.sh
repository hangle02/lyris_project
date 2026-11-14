#!/usr/bin/env bash
# Đặt biến môi trường cho app Ollama (macOS) mỗi khi đăng nhập, qua một LaunchAgent.
#
#   bash scripts/ollama-env.sh             cài LaunchAgent và đặt biến ngay bây giờ
#   bash scripts/ollama-env.sh --uninstall gỡ LaunchAgent và xoá biến
#
# Sau khi chạy, thoát hẳn app Ollama (biểu tượng trên thanh menu > Quit) rồi mở lại
# để Ollama đọc biến mới.
set -euo pipefail

LABEL="local.lyris.ollama-env"
AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST="$AGENTS_DIR/$LABEL.plist"
DOMAIN="gui/$(id -u)"

VARS=(
  "OLLAMA_FLASH_ATTENTION=1"
  "OLLAMA_KV_CACHE_TYPE=q8_0"
  "OLLAMA_NUM_PARALLEL=2"
  "OLLAMA_MAX_LOADED_MODELS=2"
)

usage() {
  echo "Cách dùng: $0 [--uninstall]"
}

require_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Lỗi: script này chỉ dùng trên macOS." >&2
    exit 1
  fi
}

# Lệnh shell mà LaunchAgent chạy lúc đăng nhập.
setenv_command() {
  local parts=() kv
  for kv in "${VARS[@]}"; do
    parts+=("/bin/launchctl setenv ${kv%%=*} ${kv#*=}")
  done
  local IFS=';'
  echo "${parts[*]}"
}

write_plist() {
  mkdir -p "$AGENTS_DIR"
  cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-c</string>
    <string>$(setenv_command)</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF
  plutil -lint "$PLIST" >/dev/null
}

unload_agent() {
  launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
}

install() {
  write_plist
  unload_agent
  launchctl bootstrap "$DOMAIN" "$PLIST"
  # Đặt luôn cho phiên hiện tại, không chờ LaunchAgent.
  local kv
  for kv in "${VARS[@]}"; do
    launchctl setenv "${kv%%=*}" "${kv#*=}"
  done
  echo "Đã cài LaunchAgent: $PLIST"
  echo "Biến môi trường hiện tại cho các app:"
  for kv in "${VARS[@]}"; do
    echo "  ${kv%%=*}=$(launchctl getenv "${kv%%=*}")"
  done
  echo "Hãy thoát hẳn app Ollama rồi mở lại để áp dụng."
}

uninstall() {
  unload_agent
  rm -f "$PLIST"
  local kv
  for kv in "${VARS[@]}"; do
    launchctl unsetenv "${kv%%=*}" || true
  done
  echo "Đã gỡ LaunchAgent và xoá các biến OLLAMA_* đã đặt."
  echo "Hãy thoát hẳn app Ollama rồi mở lại để quay về cấu hình mặc định."
}

main() {
  require_macos
  case "${1:-}" in
    "") install ;;
    --uninstall) uninstall ;;
    -h|--help) usage ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
