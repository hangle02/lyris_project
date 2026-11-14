#!/usr/bin/env bash
# Phase 0: ghép LoRA đồ chơi vào model gốc rồi nạp vào Ollama thành "lyris-toy".
# Chạy từ thư mục gốc dự án, sau khi train_toy.sh xong:  bash training/toy/deploy_toy.sh
#
# Đường chính: mlx_lm.fuse lên trọng số bf16 gốc -> ollama create --quantize q4_K_M
# (Ollama tự đọc safetensors, không cần llama.cpp). Nếu Ollama báo không hỗ trợ
# kiến trúc, sẽ phải chuyển GGUF bằng llama.cpp (chưa làm trong script này).
set -euo pipefail
cd "$(dirname "$0")/../.."

BASE=data/models/gemma-4-12B-it        # bf16 gốc, template gốc (không có bản vá train)
ADAPTER=data/adapters/toy
FUSED=data/models/lyris-toy-fused
NAME=lyris-toy

[ -f "$ADAPTER/adapters.safetensors" ] || { echo "Chưa có adapter ở $ADAPTER. Chạy train_toy.sh trước." >&2; exit 1; }

echo "== 1/3 Ghép LoRA vào trọng số bf16 (khoảng 24GB ghi ra đĩa)"
rm -rf "$FUSED"
/usr/bin/time -l .venv-train/bin/mlx_lm.fuse \
  --model "$BASE" \
  --adapter-path "$ADAPTER" \
  --save-path "$FUSED" 2>&1 | grep -E "Loading|Saving|maximum resident|peak memory|Error|error" || true
[ -f "$FUSED/config.json" ] || { echo "Ghép thất bại." >&2; exit 1; }

# Đảm bảo template là bản gốc của Google, không phải bản vá dùng cho train.
cp "$BASE/chat_template.jinja" "$FUSED/chat_template.jinja"

echo "== 2/3 Nạp vào Ollama và nén Q4_K_M"
cat > "$FUSED/Modelfile" <<EOF
FROM .
PARAMETER num_ctx 8192
EOF
(cd "$FUSED" && ollama create "$NAME" --quantize q4_K_M -f Modelfile)

echo "== 3/3 Sinh thử"
ollama run "$NAME" --think=false "Lạc Dương ơi, tớ vừa thi xong rồi nè!" || ollama run "$NAME" "Lạc Dương ơi, tớ vừa thi xong rồi nè!"

echo
echo "Xong. Có thể xoá $FUSED (khoảng 24GB) sau khi đã kiểm tra $NAME trong Ollama."
