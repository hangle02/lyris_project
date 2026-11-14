"""Event tracking (docs/tracking-plan.md): bảng sự kiện, ghi vào DB của app, chuyển tiếp PostHog (tuỳ chọn).

- `events`: bảng sự kiện và luật thuộc tính (`validate`).
- `buckets`: chia khoảng các số có thể nói lên nội dung.
- `store`: SQL (`analytics_events`, `accounts.analytics_opt_out`).
- `tracker`: `track(request, name, props)` cho route; `Tracker.emit` cho chỗ đã chốt ngữ cảnh (stream);
  `track_detached` cho sự kiện không gắn ai (báo cáo, xoá tài khoản).
- `forwarder`: gửi nền sang PostHog khi có `LYRIS_POSTHOG_KEY`.
- `replies`: theo dõi một lượt trả lời (SSE) để ghi `reply_completed` / `reply_failed` / `lore_unlocked`.
"""
from lyris.analytics.tracker import TrackContext, Tracker, context, track, track_detached, tracker_of

__all__ = ["TrackContext", "Tracker", "context", "track", "track_detached", "tracker_of"]
