#!/usr/bin/env bash
# Phase 0: train thử LoRA 50 vòng trên dataset đồ chơi, đo RAM và thời gian.
# Chạy từ thư mục gốc dự án:  bash training/toy/train_toy.sh
# Cần có sẵn: data/models/gemma-4-12B-it-mlx-4bit (bước 3 của hướng dẫn lấy trọng số)
set -euo pipefail
cd "$(dirname "$0")/../.."

MODEL=data/models/gemma-4-12B-it-mlx-4bit
ADAPTER=data/adapters/toy
LOG=training/toy/train_toy.log

if [ ! -f "$MODEL/config.json" ]; then
  echo "Chưa có $MODEL. Hãy làm bước 3 (mlx_lm.convert) trước." >&2
  exit 1
fi

echo "Dừng các model Ollama đang nạp để nhường RAM cho train..."
ollama stop gemma4:12b 2>/dev/null || true
ollama stop gemma4:e4b 2>/dev/null || true

python3 training/toy/make_toy.py
mkdir -p "$ADAPTER"

# /usr/bin/time -l in ra "maximum resident set size" (RAM đỉnh) khi chạy xong.
/usr/bin/time -l .venv-train/bin/mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data training/toy/data \
  --adapter-path "$ADAPTER" \
  --fine-tune-type lora \
  --num-layers "${NUM_LAYERS:-8}" \
  --batch-size 1 \
  --iters 50 \
  --learning-rate 1e-4 \
  --max-seq-length "${MAX_SEQ:-2048}" \
  --mask-prompt \
  --grad-checkpoint \
  --steps-per-report 5 \
  --steps-per-eval 25 \
  --val-batches 4 \
  --seed 7 \
  2>&1 | tee "$LOG"

echo
echo "Xong. Log: $LOG  Adapter: $ADAPTER"
