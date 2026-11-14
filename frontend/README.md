# Lyris frontend

Vite + React 18 + TypeScript + Tailwind v4. Giao diện chat tiếng Việt, nền tối, mobile-first.

## Chạy

```bash
cd frontend
npm install            # lần đầu
npm run dev            # http://localhost:5173, proxy /api -> http://127.0.0.1:8000
```

Backend phải chạy ở cổng 8000 (hoặc chạy cả hai bằng `bash scripts/dev.sh` ở thư mục gốc).
Backend ở chỗ khác: `LYRIS_API_URL=http://127.0.0.1:9000 npm run dev`.

## Kiểm tra

```bash
npm run typecheck      # tsc, không xuất file
npm run build          # typecheck + build ra dist/
npm test               # unit test cho SSE parser và text helpers (node:test)
npm run preview        # xem bản build ở cổng 5173 (cũng proxy /api)
```

## Cấu trúc

- `src/types.ts`: bản sao kiểu dữ liệu của `backend/lyris/models.py` và các shape API.
- `src/api/client.ts`: gọi REST, và SSE qua `fetch` POST (EventSource không POST được).
- `src/lib/sse.ts`: parser SSE tăng dần (sự kiện có thể bị cắt ở bất kỳ đâu giữa các chunk).
- `src/hooks/useChat.ts`: trạng thái chat: gửi, stream, dừng, thử lại, regenerate, variant, sửa, xoá, đánh giá.
- `src/components/`: header (chọn story, Story/DM, chấm trạng thái Ollama), danh sách tin nhắn, ô nhập.
